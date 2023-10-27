from flask import Blueprint, request, render_template, jsonify, redirect, url_for, json

views = Blueprint("views", __name__)

@views.route("/")
def test():
    return render_template("home.html")