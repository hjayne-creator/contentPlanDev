from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON

db = SQLAlchemy()

class Job(db.Model):
    """Represents a content planning job."""
    __tablename__ = 'jobs'

    id = db.Column(db.String(36), primary_key=True)
    website_url = db.Column(db.String(500), nullable=False)
    keywords = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    results = db.Column(JSON)
    error_message = db.Column(db.Text)
    workflow_state = db.Column(JSON)

    def __init__(self, job_id, website_url, keywords):
        self.id = job_id
        self.website_url = website_url
        self.keywords = keywords
        self.status = 'pending'
        self.workflow_state = {}

    def to_dict(self):
        return {
            'id': self.id,
            'website_url': self.website_url,
            'keywords': self.keywords,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'results': self.results,
            'error_message': self.error_message,
            'workflow_state': self.workflow_state
        }

    @classmethod
    def get_by_id(cls, job_id):
        return cls.query.get(job_id)

    def update_status(self, status, error_message=None):
        self.status = status
        if error_message:
            self.error_message = error_message
        db.session.commit()

    def update_workflow_state(self, state):
        self.workflow_state = state
        db.session.commit()

    def update_results(self, results):
        self.results = results
        self.status = 'completed'
        db.session.commit() 