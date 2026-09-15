import os, pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

MODEL_PATH = os.path.join(os.path.dirname(__file__), "expense_model.pkl")

TRAINING = [
("swiggy dinner","Food"),("restaurant lunch","Food"),("pizza","Food"),("groceries","Food"),
("uber ride","Transport"),("ola cab","Transport"),("bus ticket","Transport"),("petrol","Transport"),
("amazon clothes","Shopping"),("shoes","Shopping"),("mall shopping","Shopping"),("online purchase","Shopping"),
("electricity bill","Bills"),("water bill","Bills"),("internet recharge","Bills"),("mobile bill","Bills"),
("netflix","Entertainment"),("movie ticket","Entertainment"),("concert","Entertainment"),("gaming","Entertainment"),
("doctor","Health"),("medicine","Health"),("pharmacy","Health"),("hospital","Health"),
("college fees","Education"),("books","Education"),("course fee","Education"),("udemy course","Education"),
("misc expense","Other"),("gift","Other"),("repair","Other"),("cash expense","Other")
]

def train_model():
    if os.path.exists(MODEL_PATH):
        return
    x=[a for a,b in TRAINING]; y=[b for a,b in TRAINING]
    model=Pipeline([("tfidf",TfidfVectorizer(ngram_range=(1,2))),("clf",LogisticRegression(max_iter=1000))])
    model.fit(x,y)
    with open(MODEL_PATH,"wb") as f: pickle.dump(model,f)

def predict_category(text):
    train_model()
    with open(MODEL_PATH,"rb") as f: model=pickle.load(f)
    if not text.strip(): return "Other"
    return model.predict([text])[0]
