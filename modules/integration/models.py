from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float, Uuid
from sqlalchemy.orm import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class TrendReport(Base):
    __tablename__ = 'trend_reports'

    # User specified UUID. SQLAlchemy 2.0+ supports Uuid type, but for compatibility 
    # with older versions or SQLite, we can generate a default.
    # Note: Using String(36) for broad compatibility if Uuid type causes issues in older SQLA/SQLite combos,
    # but let's try standard UUID implementation.
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    rank = Column(Integer)  # 1 to 5
    fabric_name = Column(String(255))
    main_color = Column(String(255)) # Pantone Name
    probability = Column(Float) # 0.0 - 1.0
    market_status = Column(String(50)) # "Rising", "Stable"
    
    description = Column(Text) # Marketing Pitch
    specs = Column(JSON) # Technical details (GSM, Comp)
    
    image_url = Column(String(512)) # URL of generated image
    evidence = Column(JSON) # Array of source links
    
    # Keeping created_at
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<TrendReport(rank={self.rank}, fabric='{self.fabric_name}', status='{self.market_status}')>"
