from setuptools import setup, find_packages

setup(
    name="verificai",
    version="1.0.0",
    description="VerificAI - Generazione verifiche scolastiche",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "streamlit>=1.28.0",
        "google-generativeai>=0.3.0",
        "python-dotenv>=1.0.0",
        "pdf2image>=1.16.0",
        "pymupdf>=1.23.0",
        "python-docx>=0.8.11",
        "mammoth>=1.8.0",
        "supabase>=2.6.0",
        "stripe>=7.0.0",
        "extra-streamlit-components>=0.1.0",
        "streamlit-cookies-controller>=0.1.0",
        "requests>=2.31.0",
    ],
)
