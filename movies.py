from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from bson import ObjectId
from app.schemas import MovieCreate, MovieResponse, MovieUpdate
from app.database import get_database
from app.security import get_current_user, is_admin

router = APIRouter()

@router.post("/", response_model=MovieResponse)
async def add_movie(
    movie: MovieCreate, 
    db = Depends(get_database),
    current_user = Depends(is_admin)  # Only admins can add movies
):
    movie_dict = movie.model_dump()
    result = await db.movies.insert_one(movie_dict)
    return {**movie_dict, "id": str(result.inserted_id)}

@router.get("/", response_model=List[MovieResponse])
async def get_movies(
    db = Depends(get_database),
    current_user = Depends(get_current_user)  # Both users and admins can view
):
    movies = await db.movies.find().to_list(length=100)
    return [{**movie, "id": str(movie["_id"])} for movie in movies]

@router.get("/search", response_model=List[MovieResponse])
async def search_movies(
    title: Optional[str] = None,
    genre: Optional[str] = None,
    director: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    min_score: Optional[float] = None,
    sort_by: Optional[str] = None,
    db = Depends(get_database),
    current_user = Depends(get_current_user)
):
    query = {}
    
    if title:
        query["title"] = {"$regex": title, "$options": "i"}
        
    if genre:
        query["genre"] = {"$regex": genre, "$options": "i"}
        
    if director:
        query["director"] = {"$regex": director, "$options": "i"}
        
    if year_from or year_to:
        query["release_year"] = {}
        if year_from:
            query["release_year"]["$gte"] = year_from
        if year_to:
            query["release_year"]["$lte"] = year_to
            
    if min_score:
        query["imdb_score"] = {"$gte": min_score}
    
    # Sorting
    sort_options = None
    if sort_by:
        if sort_by == "year_asc":
            sort_options = [("release_year", 1)]
        elif sort_by == "year_desc":
            sort_options = [("release_year", -1)]
        elif sort_by == "title_asc":
            sort_options = [("title", 1)]
        elif sort_by == "score_desc":
            sort_options = [("imdb_score", -1)]
    
    cursor = db.movies.find(query)
    if sort_options:
        cursor = cursor.sort(sort_options)
        
    movies = await cursor.to_list(length=100)
    return [{**movie, "id": str(movie["_id"])} for movie in movies]


@router.get("/{movie_id}", response_model=MovieResponse)
async def get_movie(
    movie_id: str,
    db = Depends(get_database),
    current_user = Depends(get_current_user)  # Both users and admins can view
):
    try:
        movie = await db.movies.find_one({"_id": ObjectId(movie_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid movie ID format")
        
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found in the database")
        
    return {**movie, "id": str(movie["_id"])}

@router.put("/{movie_id}", response_model=MovieResponse)
async def update_movie(
    movie_id: str,
    movie_update: MovieUpdate,
    db = Depends(get_database),
    current_user = Depends(is_admin)  # Only admins can update movies
):
    try:
        movie_obj_id = ObjectId(movie_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid movie ID format")
    
    update_data = {k: v for k, v in movie_update.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    result = await db.movies.update_one(
        {"_id": movie_obj_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Movie not found in the database")
    
    updated_movie = await db.movies.find_one({"_id": movie_obj_id})
    return {**updated_movie, "id": str(updated_movie["_id"])}

@router.delete("/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(
    movie_id: str,
    db = Depends(get_database),
    current_user = Depends(is_admin)  # Only admins can delete movies
):
    try:
        movie_obj_id = ObjectId(movie_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid movie ID format")
    
    result = await db.movies.delete_one({"_id": movie_obj_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Movie not found in the database")
    
    return None