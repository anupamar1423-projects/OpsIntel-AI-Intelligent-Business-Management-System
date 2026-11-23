import io
import re
from pathlib import Path

from apps.core.models import BusinessDocument

STOP={"what","when","where","which","how","does","this","that","with","from","about","show","tell","have","your","the","and","for","are","was","were","can"}

def _tokens(value):
    return {word for word in re.findall(r"[a-z0-9]{3,}",value.lower()) if word not in STOP}

def _extract(document):
    suffix=Path(document.original_name).suffix.lower()
    with document.file.storage.open(document.file.name,"rb") as stream: raw=stream.read(10*1024*1024+1)
    if len(raw)>10*1024*1024:return ""
    if suffix==".pdf":
        from pypdf import PdfReader
        reader=PdfReader(io.BytesIO(raw));return "\n".join((page.extract_text() or "") for page in reader.pages[:8])[:10000]
    if suffix==".docx":
        from docx import Document
        doc=Document(io.BytesIO(raw));return "\n".join(p.text for p in doc.paragraphs)[:10000]
    if suffix==".csv":
        text=raw.decode("utf-8-sig",errors="replace")
        return "\n".join(text.splitlines()[:120])[:10000]
    if suffix==".xlsx":
        from openpyxl import load_workbook
        book=load_workbook(io.BytesIO(raw),read_only=True,data_only=True)
        rows=[]
        for sheet in book.worksheets[:3]:
            for row in sheet.iter_rows(min_row=1,max_row=100,values_only=True):rows.append(" | ".join(str(c) for c in row if c is not None))
        book.close();return "\n".join(rows)[:10000]
    return ""

def relevant_documents(organization,question,limit=3):
    query=_tokens(question)
    if not query:return []
    results=[]
    for doc in BusinessDocument.objects.filter(organization=organization,size_bytes__lte=10*1024*1024).order_by("-created_at")[:20]:
        name_score=len(query & _tokens(doc.original_name))
        try:text=_extract(doc)
        except Exception:text=""
        body_tokens=_tokens(text)
        score=name_score+len(query & body_tokens)
        if score and text:results.append((score,doc.original_name,text))
    results.sort(key=lambda item:item[0],reverse=True)
    snippets=[]
    for score,name,text in results[:limit]:
        snippets.append({"file":name,"text":text[:5000]})
    return snippets
