#!/usr/bin/env python3
import os
import sys
import subprocess
import venv
from pathlib import Path

def run_command(command, cwd=None):
    """Run a command"""
    try:
        result = subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        sys.exit(1)

def clone_repository():
    """Clone the PDF RAG repository"""
    repo_url = "https://github.com/lakshy-606/PDF-Rag.git"
    project_dir = "PDF-Rag"

    if Path(project_dir).exists():
        print(f"Directory '{project_dir}' exists, skipping clone.")
    else:
        print("Cloning repository...")
        run_command(["git", "clone", repo_url])

    return Path(project_dir).resolve()

def create_virtual_environment(project_dir):
    """Create virtual environment"""
    venv_dir = project_dir / "venv"

    if venv_dir.exists():
        print("Virtual environment exists.")
        return venv_dir

    print("Creating virtual environment...")
    venv.create(venv_dir, with_pip=True)
    return venv_dir

def get_venv_python(venv_dir):
    """Get venv Python path"""
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    else:
        return venv_dir / "bin" / "python"

def install_requirement(project_dir, venv_python):
    """Install requirement"""
    requirement_file = project_dir / "requirement.txt"

    if not requirement_file.exists():
        print("Creating requirement.txt...")
        basic_requirement =""" streamlit
            openai
            faiss-cpu
            python-dotenv>=1.0.0           
            numpy 
            pdfplumber """
        requirement_file.write_text(basic_requirement)

    print("Installing requirement...")
    run_command([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])
    run_command([str(venv_python), "-m", "pip", "install", "-r", "requirement.txt"], cwd=project_dir)

def create_env_file(project_dir):
    """Create .env file"""
    env_file = project_dir / ".env"

    if env_file.exists():
        print(".env file exists.")
        return

    api_key = input("Enter OpenAI API key (or press Enter to skip): ").strip()

    if api_key:
        env_content = f"OPENAI_API_KEY={api_key}\n"
    else:
        env_content = "OPENAI_API_KEY=your_api_key_here\n"

    env_file.write_text(env_content)
    print("Created .env file")

def main():
    """Main setup function"""
    print("PDF RAG Setup")

    # Check git
    run_command(["git", "--version"])

    # Setup
    project_dir = clone_repository()
    venv_dir = create_virtual_environment(project_dir)
    venv_python = get_venv_python(venv_dir)
    install_requirement(project_dir, venv_python)
    create_env_file(project_dir)

    print("\nSetup complete!")
    print(f"Project: {project_dir}")
    print("Add your OpenAI API key to .env file if needed.")

if __name__ == "__main__":
    main()
