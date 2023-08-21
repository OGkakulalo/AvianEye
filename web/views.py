from flask import Blueprint, request, render_template, jsonify, redirect, url_for, json
from backend.anomaly_detection import AnomalyDetection
from config import dbController
import plotly.graph_objs as go

anomaly_detector = AnomalyDetection()
views = Blueprint(__name__, "views")
dbController.connect()


@views.route("/")
def home():
    anomaly_figures = anomaly_detector.detect_anomaly()
    return render_template("home.html", anomaly_figures=anomaly_figures)