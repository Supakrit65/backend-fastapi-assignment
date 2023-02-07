from fastapi import FastAPI, HTTPException, Body, status
from datetime import date, datetime
from pymongo import MongoClient
from pydantic import BaseModel

DATABASE_NAME = "hotel"
COLLECTION_NAME = "reservation"
MONGO_DB_URL = "mongodb://localhost"
MONGO_DB_PORT = 27017


class Reservation(BaseModel):
    name: str
    start_date: date
    end_date: date
    room_id: int


DATETIME_STR_FORMAT = "%Y-%m-%d"

client = MongoClient(f"{MONGO_DB_URL}:{MONGO_DB_PORT}")

db = client[DATABASE_NAME]

collection = db[COLLECTION_NAME]

app = FastAPI()


def get_reservation_info(reservation: Reservation):
    return {
        "name": reservation.name,
        "start_date": reservation.start_date.strftime(DATETIME_STR_FORMAT),
        "end_date": reservation.end_date.strftime(DATETIME_STR_FORMAT),
        "room_id": reservation.room_id,
    }


def room_avaliable(room_id: int, start_date: str, end_date: str):
    query = {
        "room_id": room_id,
        "$or": [
            {
                "$and": [
                    {"start_date": {"$lte": start_date}},
                    {"end_date": {"$gte": start_date}},
                ]
            },
            {
                "$and": [
                    {"start_date": {"$lte": end_date}},
                    {"end_date": {"$gte": end_date}},
                ]
            },
            {
                "$and": [
                    {"start_date": {"$gte": start_date}},
                    {"end_date": {"$lte": end_date}},
                ]
            },
        ],
    }

    result = collection.find(query, {"_id": 0})
    list_cursor = list(result)

    return not len(list_cursor) > 0


@app.get("/reservation/by-name/{name}", status_code=status.HTTP_200_OK)
def get_reservation_by_name(name: str):
    return {"result": [i for i in collection.find({"name": name}, {"_id": False})]}


@app.get("/reservation/by-room/{room_id}", status_code=status.HTTP_200_OK)
def get_reservation_by_room(room_id: int):
    return {
        "result": [i for i in collection.find({"room_id": room_id}, {"_id": False})]
    }


@app.post("/reservation", status_code=status.HTTP_200_OK)
def reserve(reservation: Reservation):
    if reservation.end_date < reservation.start_date:
        raise HTTPException(400)
    filter = get_reservation_info(reservation=reservation)
    if filter["room_id"] not in range(1, 11):
        raise HTTPException(400)
    if room_avaliable(filter["room_id"], filter["start_date"], filter["end_date"]):
        collection.insert_one(filter)
    else:
        raise HTTPException(400)


@app.put("/reservation/update")
def update_reservation(
    reservation: Reservation, new_start_date: date = Body(), new_end_date: date = Body()
):
    if new_end_date < new_start_date:
        raise HTTPException(400)
    filter = get_reservation_info(reservation=reservation)
    update = {
        "$set": {
            "start_date": new_start_date.strftime(DATETIME_STR_FORMAT),
            "end_date": new_end_date.strftime(DATETIME_STR_FORMAT),
        }
    }
    if room_avaliable(
        filter["room_id"], update["$set"]["start_date"], update["$set"]["end_date"]
    ):
        collection.update_one(filter, update)
    else:
        raise HTTPException(400)


@app.delete("/reservation/delete")
def cancel_reservation(reservation: Reservation):
    collection.delete_one(get_reservation_info(reservation))
