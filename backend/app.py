import warnings
warnings.filterwarnings("ignore", message="resource_tracker: There appear to be.*")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os

from config import config
from rag_system import RAGSystem

# Initialize FastAPI app
app = FastAPI(title="Course Materials RAG System", root_path="")

# Add trusted host middleware for proxy
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

# Enable CORS with proper settings for proxy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Initialize RAG system
rag_system = RAGSystem(config)

# Pydantic models for request/response
class QueryRequest(BaseModel):
    """Request model for course queries"""
    query: str
    session_id: Optional[str] = None

class SourceLink(BaseModel):
    """A source citation with display label and viewer URL"""
    label: str
    url: str

class QueryResponse(BaseModel):
    """Response model for course queries"""
    answer: str
    sources: List[SourceLink]
    session_id: str

class CourseStats(BaseModel):
    """Response model for course statistics"""
    total_courses: int
    course_titles: List[str]

class SessionSummary(BaseModel):
    session_id: str
    title: str
    created_at: str
    message_count: int

class SessionListResponse(BaseModel):
    sessions: List[SessionSummary]

class MessageItem(BaseModel):
    role: str
    content: str

class SessionMessagesResponse(BaseModel):
    session_id: str
    messages: List[MessageItem]

class LessonResponse(BaseModel):
    """Response model for lesson content viewer"""
    course_title: str
    course_link: Optional[str]
    lesson_number: int
    lesson_title: str
    lesson_link: Optional[str]
    content: str

# API Endpoints

@app.post("/api/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Process a query and return response with sources"""
    try:
        # Create session if not provided
        session_id = request.session_id
        if not session_id:
            session_id = rag_system.session_manager.create_session()
        
        # Process query using RAG system
        answer, sources = rag_system.query(request.query, session_id)
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            session_id=session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/courses", response_model=CourseStats)
async def get_course_stats():
    """Get course analytics and statistics"""
    try:
        analytics = rag_system.get_course_analytics()
        return CourseStats(
            total_courses=analytics["total_courses"],
            course_titles=analytics["course_titles"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions", response_model=SessionListResponse)
async def list_sessions():
    """Return the last 10 sessions with metadata"""
    sessions = rag_system.session_manager.get_all_sessions()
    return SessionListResponse(sessions=sessions)

@app.get("/api/sessions/{session_id}", response_model=SessionMessagesResponse)
async def get_session_messages(session_id: str):
    """Return all messages for a given session"""
    messages = rag_system.session_manager.get_session_messages(session_id)
    if messages is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionMessagesResponse(session_id=session_id, messages=messages)

@app.on_event("startup")
async def startup_event():
    """Load initial documents on startup"""
    docs_path = "../docs"
    if os.path.exists(docs_path):
        print("Loading initial documents...")
        try:
            courses, chunks = rag_system.add_course_folder(docs_path, clear_existing=False)
            print(f"Loaded {courses} courses with {chunks} chunks")
        except Exception as e:
            print(f"Error loading documents: {e}")

@app.get("/api/lesson", response_model=LessonResponse)
async def get_lesson(course_title: str, lesson_number: Optional[int] = None):
    """Return full lesson content for the lesson viewer page"""
    result = rag_system.get_lesson_content(course_title, lesson_number)
    if result is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return LessonResponse(**result)


# Custom static file handler with no-cache headers for development
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pathlib import Path


class DevStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if isinstance(response, FileResponse):
            # Add no-cache headers for development
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response
    
    
# Serve static files for the frontend
app.mount("/", DevStaticFiles(directory="../frontend", html=True), name="static")