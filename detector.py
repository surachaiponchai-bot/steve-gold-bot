
import numpy as np
import pandas as pd

def detect_mountain(df, sim_thresh=55):
    try:
        closes=df['Close'].values
        if len(closes)<30: return {"sim":0,"perc":0,"start":0,"end":0,"found":False}
        # simple mountain detection
        recent=closes[-15:]
        mmax=recent.max(); mmin=recent.min()
        # similarity crude
        sim = 80 if (mmax-mmin)/mmin*100 > 1 else 20
        return {"sim":sim,"perc":(mmax-mmin)/mmin*100,"start":recent[0],"end":recent[-1],"found":sim>=sim_thresh}
    except:
        return {"sim":0,"perc":0,"start":0,"end":0,"found":False}

def detect_ruay(df):
    try:
        # count bullish/bearish
        c=df['Close'].values
        bullish = np.sum(np.diff(c)>0)
        score = bullish/len(c)*100
        return {"sim":int(score)}
    except:
        return {"sim":0}

def detect_box(df):
    try:
        closes=df['Close'].values[-20:]
        high=closes.max(); low=closes.min()
        perc = (high-low)/low*100
        sim = 70 if perc<0.5 else 30
        return {"sim":sim,"box_low":low,"box_high":high,"perc":perc}
    except:
        return {"sim":0,"box_low":0,"box_high":0,"perc":0}

def detect_all(df):
    m=detect_mountain(df)
    r=detect_ruay(df)
    t=detect_box(df)
    return m,r,t
