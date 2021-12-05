from flask import render_template

class WebAppInfoController:
    """Controller for Web App Info views (like the 'about' section)"""      
    def __init__(self):
        pass

    @classmethod
    def render_about_page(cls):
        return render_template('about.html')

    # @classmethod
    # def render_dashboard(cls):
    #     return render_template('user_home.html')