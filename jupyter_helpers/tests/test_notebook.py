from jupyter_helpers import notebook

def test_get_session():
    sm = notebook.SessionManager()
    sm.get_session()
