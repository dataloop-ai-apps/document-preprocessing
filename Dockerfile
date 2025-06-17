FROM dataloopai/dtlpy-agent:cpu.py3.10.opencv
USER 1000
RUN pip install -U \
    pypdfium2==4.28.0 \
    pypdf==4.2.0 \
    nltk==3.8.1 \
    PyMuPDF==1.24.0 \
    autocorrect==2.6.1 \
    langchain==0.1.14 \
    requests-toolbelt==1.0.0 \
    python-pptx==0.6.23\
    openai==1.30.3\
    opencv-python==4.8.1.78\
    numpy==1.26.4\
    "unstructured[all-docs]==0.12.0"\
    Spire.Doc==12.7.1\
    python-pptx


# docker build --no-cache -t gcr.io/viewo-g/piper/agent/runner/cpu/document-preprocessing:0.1.2 -f Dockerfile .
# docker push gcr.io/viewo-g/piper/agent/runner/cpu/document-preprocessing:0.1.2
