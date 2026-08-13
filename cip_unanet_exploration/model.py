from pulearn import ElkanotoPuClassifier
from imblearn.ensemble import BalancedRandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report, precision_recall_curve
from sklearn.model_selection import train_test_split
import json
import pandas as pd
import numpy as np

def ingest_data():
    with open('data/cip.json') as f:
        cip_dict = json.load(f) 

    unanet = pd.read_csv('data/unanet2.csv')
    cip = pd.DataFrame(cip_dict.get('records'))
    df = cip.copy()

    unanet['ID'] = unanet['Solicitation Number'].str.extract(r'(\d+)', expand=False)
    df['Lead'] = df['ID Number'].isin(unanet['ID']).astype(int)
    df = df.replace(r'^\s*$', np.nan, regex=True)
    df = df.replace(r"^\s*\$\s*$", np.nan, regex=True)

    vectorizer = TfidfVectorizer(
        max_features=2000,
        min_df=5,
        max_df=0.8,
        ngram_range=(1,2),
        stop_words='english'
    )

    X = vectorizer.fit_transform(df['Description']).toarray()
    y = df['Lead'].replace(0, -1).to_numpy()
    combined_data = np.column_stack((X, y))
    np.savetxt('output.txt', combined_data, delimiter=',')

    return X, y

def pu_score(y_true, y_pred):
    known_pos = (y_true == 1)
    recall = (y_pred[known_pos] == 1).mean()
    pr_f1 = (y_pred == 1).mean()
    return (recall ** 2) / pr_f1 if pr_f1 > 0 else 0.0

if __name__ == "__main__":
    X, y = ingest_data() 
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y)

    rf = BalancedRandomForestClassifier()
    pu_estimator = ElkanotoPuClassifier(estimator=rf, hold_out_ratio=0.1)
    pu_estimator.fit(X_train, y_train)
    y_predict = pu_estimator.predict(X_test)
     
    print(classification_report(y_test, y_predict, zero_division=0.0))  
