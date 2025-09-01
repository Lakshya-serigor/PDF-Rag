import os
import pickle
import numpy as np
import faiss
from openai import OpenAI
from dotenv import load_dotenv
import datetime

# Load environment variables from .env file
load_dotenv()

class DroolsRAGPipeline:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables. Check your .env file.")
        self.client = OpenAI(api_key=self.api_key)
        self.index = None
        self.metadata = None

    def load_vector_db(self, faiss_path="data/model/faiss_index.bin", metadata_path="data/model/metadata.pkl"):
        """Load FAISS index and metadata"""
        self.index = faiss.read_index(faiss_path)
        with open(metadata_path, 'rb') as f:
            self.metadata = pickle.load(f)

    def embed_query(self, query):
        """Generate embedding for query"""
        response = self.client.embeddings.create(
            model="text-embedding-3-large",
            input=query
        )
        return np.array(response.data[0].embedding, dtype=np.float32)

    def search_chunks(self, query, k=15):
        e_query = f"{query} tax calculation Maryland county rate filing status income threshold deduction"
        query_embedding = self.embed_query(e_query).reshape(1, -1)
        
        # Get more results than needed for diversity filtering
        scores, indices = self.index.search(query_embedding, k*2)
        
        chunks = []
        seen_embeddings = []
        
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self.metadata):
                # Get current chunk embedding for similarity check
                current_emb = self.index.reconstruct(int(idx))
                
                # Check if too similar to already selected chunks
                too_similar = False
                for prev_emb in seen_embeddings:
                    similarity = np.dot(current_emb, prev_emb)
                    if similarity > 0.95:  # 95% similarity threshold
                        too_similar = True
                        break
                
                if not too_similar:
                    chunks.append({
                        'content': self.metadata[idx].get('text', ''),
                        'score': float(score)
                    })
                    seen_embeddings.append(current_emb)
                    
                    if len(chunks) >= k:
                        break
        return chunks


    def load_form(self, form_path="data/markdowns/output_form.md"):
        """Load form content"""
        with open(form_path, 'r', encoding='utf-8') as f:
            return f.read()

    def load_java_model(self, java_path="MarylandForm502.java"):
        """Load Java model file"""
        try:
            with open(java_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return """// Java model file not found. Using default structure reference.
public class MarylandForm502 {
    // Add your Java model fields here
}"""

    def create_prompt(self, form_content, chunks, query, java_model_path="MarylandForm502.java"):
        """Create prompt for Drools generation with Java model included"""

        # Load Java model content
        java_model_content = self.load_java_model(java_model_path)

        retrieved_context = "\n\n".join([
            f"CHUNK {i+1}: {chunk['content']}"
            for i, chunk in enumerate(chunks)
        ])

        prompt = f"""System Role:
You are an expert in Maryland state tax laws and Drools rule engine development with 15+ years of experience.

Your task is to read:
1. A Java model class defining all available fields and structure
2. A subset of the Maryland tax form (from the user query)
3. Retrieved authoritative rules from the Maryland rule booklet (via FAISS search)

...and produce ONLY a syntactically correct Drools `.drl` file.

**Key Requirements:**
- Use ONLY logic, tax rates, thresholds, and conditions explicitly present in the retrieved rule snippets.
- Use ONLY field names that exist in the provided Java model class.
- Access nested fields using proper dot notation (e.g., $form.getAddresses().getMarylandPhysical().getCounty())
- Replicate EVERY conditional branch exactly as documented, including:
  - County-specific local tax rates
  - Special handling for counties like Anne Arundel & Frederick
  - Different rates based on filing status & income thresholds
- DO NOT collapse multiple branches into a single formula.
- If any data is missing from retrieved snippets, insert `// TODO` comments in correct locations.
- Always end each Drools rule with `end`.
- No text output outside the `.drl` code.

**JAVA MODEL CLASS:**
```java
{java_model_content}
```

**FORM CONTENT:**
{form_content}

**USER QUERY:**
{query}
(Form section related to the logic)

**RETRIEVED CONTEXT:**
{retrieved_context}
(Authoritative Maryland rule booklet excerpts containing the exact tax rates, income thresholds, and conditions)

**Execution Steps:**
1. Parse the **Java model class** to identify:
   - Package name and class structure
   - Exact field names and their types
   - Nested class relationships and access patterns

2. Parse the **form section** to understand:
   - Which calculations are needed
   - Input and output fields involved

3. Parse the **retrieved context** to extract:
   - All county-specific logic
   - Special rules and exemptions
   - Income thresholds and filing status differences

4. Generate Drools code:
   - Correct `package` declaration
   - Correct `import` statement for the Java class
   - Full conditional branching logic from retrieved context
   - Proper field access using getter methods or direct field access
   - Update statements for calculated values

**Output Format Example:**
```
package tax.rules

import com.example.MarylandForm502;

rule "Calculate Deduction Amount Line 17"
when
    $form : MarylandForm502(
        deductions.method != null,
        $method : deductions.method,
        $income : line16MarylandAdjustedGrossIncome
    )
then
    if ("standard".equals($method)) {{
        double deduction;
        int filingStatus = $form.filingStatus;
        // Standard deduction thresholds (approximate as per Maryland guidelines)
        if (filingStatus == 1 || filingStatus == 3 || filingStatus == 6) {{ // Single, Married Sep, Dependent
            deduction = Math.max(1700, Math.min(2550, 0.15 * $income));
        }} else {{ // Joint, HOH, Surviving Spouse
            deduction = Math.max(3450, Math.min(5150, 0.15 * $income));
        }}
        $form.deductions.line17StandardDeduction = deduction;
    }} else if ("itemized".equals($method) && 
               $form.deductions.line17ItemizedDeductions != null) {{
        double line17a = $form.deductions.line17ItemizedDeductions.line17aTotal;
        double line17b = $form.deductions.line17ItemizedDeductions.line17bStateLocalTax;
        $form.deductions.line17StandardDeduction = line17a - line17b;
    }}
end
```

**Field Access Guidelines:**
- For primitive fields: $form.getFieldName() or $form.fieldName
- For nested objects: $form.getParentObject().getChildField()
- For calculations: Use appropriate getter methods to access input values
- For results: Use setter methods to update calculated fields

**Example Context Use:**
If the retrieved text contains:
"Anne Arundel County: single/married filing separately/local brackets differ by taxable net income thresholds..."

You MUST reproduce that **exact logic**, including numeric thresholds, inside the Drools `if/else` blocks.

**Response Policy:**
- Your output must be a `.drl` file only.
- Do not summarize the rules — implement them in full.
- Use proper Java field access patterns based on the provided model class.
- If part of the logic or a county rate is not retrieved, leave `// TODO: missing rate for [county name]` in place of a hardcoded number.
- Do not change variable names or model fields from the Java class.
- Ensure all field references match the actual Java model structure."""

        return prompt

    def generate_drools(self, query, form_path="data/markdowns/output_form.md", java_model_path="data/Pdfs/MarylandForm502.java", k=15):
        """Main pipeline function"""
        # Load form content
        form_content = self.load_form(form_path)

        # Search for relevant chunks
        chunks = self.search_chunks(query, k)
        print(chunks)

        # Create prompt with Java model included
        prompt = self.create_prompt(form_content, chunks, query, java_model_path)

        # Generate Drools code
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=6000
        )

        return response.choices[0].message.content

# Usage
if __name__ == "__main__":
    # Initialize pipeline
    pipeline = DroolsRAGPipeline()

    # Load vector database
    pipeline.load_vector_db()

    # Generate Drools code
    query = input("Enter your query: ")
    drools_code = pipeline.generate_drools(query)
    chunks = pipeline.search_chunks(query)

    context = "\n\n".join([
        f"CHUNK {i+1}: {chunk['content']}"
        for i, chunk in enumerate(chunks)
    ])

    # print("\nGenerated Drools Code:")
    # print("=" * 50)
    # print(drools_code)

    # Save to file
    timestamp = datetime.datetime.now().strftime("%m_%d_%H_%M")
    filename = f"data/drools/generated_rule_{timestamp}.drl"
    with open(filename, "w") as f:
        f.write(drools_code)
    print("\nSaved :", {filename})

    # with open("data/drools/generated_rule_context.txt", "w") as f:
    #     f.write("QUERY: " + query + "\n\n")
    #     f.write(context)
    # print("\nSaved to: generated_rule_context.txt")
