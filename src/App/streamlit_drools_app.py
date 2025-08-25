import os
import pickle
import numpy as np
import faiss
from openai import OpenAI
from dotenv import load_dotenv
import streamlit as st
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

    @st.cache_resource
    def load_vector_db(_self, faiss_path="data/model/faiss_index.bin", metadata_path="data/model/metadata.pkl"):
        """Load FAISS index and metadata"""
        _self.index = faiss.read_index(faiss_path)
        with open(metadata_path, 'rb') as f:
            _self.metadata = pickle.load(f)
        return _self.index, _self.metadata

    def embed_query(self, query):
        """Generate embedding for query"""
        response = self.client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        return np.array(response.data[0].embedding, dtype=np.float32)

    def search_chunks(self, query, k=20):
        """Search for relevant chunks"""
        query_embedding = self.embed_query(query).reshape(1, -1)
        scores, indices = self.index.search(query_embedding, k)
        chunks = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self.metadata):
                chunks.append({
                    'content': self.metadata[idx].get('text', ''),
                    'score': float(score)
                })
        return chunks

    @st.cache_data
    def load_form(_form_path="data/markdowns/output_form.md"):
        """Load form content"""
        try:
            with open(_form_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return "Form content not found."

    @st.cache_data
    def load_java_model(_java_path="data/Pdfs/MarylandForm502.java"):
        """Load Java model file"""
        try:
            with open(_java_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return """// Java model file not found. Using default structure reference.
public class MarylandForm502 {
    // Add your Java model fields here
}"""

    def create_prompt(self, form_content, chunks, query, java_model_content):
        """Create prompt for Drools generation with Java model included"""

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

    def generate_drools(self, query, form_content, java_model_content, k=15):
        """Main pipeline function"""
        # Search for relevant chunks
        chunks = self.search_chunks(query, k)

        # Create prompt with Java model included
        prompt = self.create_prompt(form_content, chunks, query, java_model_content)

        # Generate Drools code
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=4000
        )

        return response.choices[0].message.content, chunks

# Streamlit App
def main():
    st.set_page_config(
        page_title="Drools RAG Pipeline", 
        page_icon="🔧", 
        layout="wide"
    )

    st.title("🔧 Maryland Tax Drools Rule Generator")
    st.markdown("Generate Drools rules for Maryland tax calculations using RAG pipeline")

    # Initialize session state
    if 'pipeline' not in st.session_state:
        try:
            st.session_state.pipeline = DroolsRAGPipeline()
            # Load vector database
            st.session_state.pipeline.load_vector_db()
            st.success("✅ Pipeline initialized and vector database loaded!")
        except Exception as e:
            st.error(f"❌ Error initializing pipeline: {str(e)}")
            return

    # Load form and Java model content (cached)
    form_content = DroolsRAGPipeline.load_form()
    java_model_content = DroolsRAGPipeline.load_java_model()

    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        k_value = st.slider("Number of chunks to retrieve", min_value=5, max_value=30, value=15)
        st.info("Adjust the number of context chunks to retrieve for rule generation")

        # Show model info
        st.subheader("📋 Loaded Resources")
        if "Form content not found" in form_content:
            st.warning("⚠️ Form content not loaded")
        else:
            st.success(f"✅ Form loaded ({len(form_content)} chars)")

        if "Java model file not found" in java_model_content:
            st.warning("⚠️ Java model not loaded")
        else:
            st.success(f"✅ Java model loaded ({len(java_model_content)} chars)")

    # Main input
    st.subheader("💬 Enter Your Query")
    query = st.text_area(
        "Enter your query for Drools rule generation:",
        placeholder="e.g., Calculate local tax based on county and filing status",
        help="Describe what tax calculation or rule you want to generate"
    )

    # Generate button
    if st.button("🚀 Generate Drools Rule", type="primary", disabled=not query.strip()):
        if query.strip():
            with st.spinner("🔍 Searching context and generating rules..."):
                try:
                    # Generate drools code and get chunks
                    drools_code, chunks = st.session_state.pipeline.generate_drools(
                        query, form_content, java_model_content, k_value
                    )

                    # Display results in columns
                    col1, col2 = st.columns([1, 1])

                    with col1:
                        st.subheader("📄 Retrieved Context")
                        st.info(f"Found {len(chunks)} relevant chunks")

                        # Display chunks in expandable sections
                        for i, chunk in enumerate(chunks):
                            with st.expander(f"📝 Chunk {i+1} (Score: {chunk['score']:.4f})"):
                                st.text_area(
                                    f"Content:",
                                    chunk['content'],
                                    height=150,
                                    key=f"chunk_{i}",
                                    disabled=True
                                )

                    with col2:
                        st.subheader("⚙️ Generated Drools Rule")
                        st.code(drools_code, language="java", line_numbers=True)

                        # Download button for the code
                        timestamp = datetime.datetime.now().strftime("%m_%d_%H_%M")
                        st.download_button(
                            label="💾 Download DRL File",
                            data=drools_code,
                            file_name=f"generated_rule_{timestamp}.drl",
                            mime="text/plain"
                        )

                    # Additional info
                    st.success("✅ Rule generation completed!")

                    # Context summary
                    st.subheader("📊 Generation Summary")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Chunks Retrieved", len(chunks))
                    with col2:
                        st.metric("Rule Length", f"{len(drools_code)} chars")
                    with col3:
                        avg_score = sum(chunk['score'] for chunk in chunks) / len(chunks) if chunks else 0
                        st.metric("Avg. Relevance", f"{avg_score:.4f}")

                except Exception as e:
                    st.error(f"❌ Error generating rules: {str(e)}")
                    st.exception(e)
        else:
            st.warning("⚠️ Please enter a query first!")

    # Footer
    st.markdown("---")
    st.markdown("• OpenAI • FAISS")

if __name__ == "__main__":
    main()
