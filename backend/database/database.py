import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from sqlalchemy import create_engine, select, desc, func, and_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .models import Base, ProcessModel, AlertModel, RuleExecutionLog
from models import ProcessCreate, AlertCreate

logger = logging.getLogger(__name__)

# Database URL - using SQLite for simplicity
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./edr_lite.db")
ASYNC_DATABASE_URL = os.getenv("ASYNC_DATABASE_URL", "sqlite+aiosqlite:///./edr_lite.db")


class Database:
    """Database manager for EDR Lite"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.engine = None
        self.async_engine = None
        self.SessionLocal = None
        self.AsyncSessionLocal = None
        self._initialized = True
    
    def initialize(self, db_url: str = None):
        """Initialize database connection"""
        if db_url:
            self.db_url = db_url
        else:
            self.db_url = DATABASE_URL
        
        # Create sync engine for initialization
        self.engine = create_engine(
            self.db_url,
            connect_args={"check_same_thread": False} if "sqlite" in self.db_url else {},
            poolclass=StaticPool if "sqlite" in self.db_url else None
        )
        
        # Create async engine for FastAPI
        async_url = self.db_url.replace("sqlite://", "sqlite+aiosqlite://")
        self.async_engine = create_async_engine(
            async_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.AsyncSessionLocal = async_sessionmaker(
            self.async_engine, class_=AsyncSession, expire_on_commit=False
        )
        
        logger.info(f"Database initialized: {self.db_url}")
    
    def create_tables(self):
        """Create all database tables"""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created")
    
    def get_session(self) -> Session:
        """Get synchronous database session"""
        return self.SessionLocal()
    
    async def get_async_session(self) -> AsyncSession:
        """Get asynchronous database session"""
        async with self.AsyncSessionLocal() as session:
            yield session
    
    # Process operations
    def create_process(self, process: ProcessCreate) -> ProcessModel:
        """Create a new process record"""
        with self.get_session() as session:
            db_process = ProcessModel(
                process_name=process.process_name,
                parent_name=process.parent_name,
                command_line=process.command_line,
                process_id=process.process_id,
                parent_process_id=process.parent_process_id,
                timestamp=process.timestamp,
                user=process.user,
                computer=process.computer
            )
            session.add(db_process)
            session.commit()
            session.refresh(db_process)
            logger.debug(f"Created process record: {db_process.id}")
            return db_process
    
    async def create_process_async(self, process: ProcessCreate, session: AsyncSession) -> ProcessModel:
        """Create a new process record (async)"""
        db_process = ProcessModel(
            process_name=process.process_name,
            parent_name=process.parent_name,
            command_line=process.command_line,
            process_id=process.process_id,
            parent_process_id=process.parent_process_id,
            timestamp=process.timestamp,
            user=process.user,
            computer=process.computer
        )
        session.add(db_process)
        await session.commit()
        await session.refresh(db_process)
        return db_process
    
    def get_processes(self, limit: int = 100, offset: int = 0, 
                     search: str = None) -> List[ProcessModel]:
        """Get process records with optional search"""
        with self.get_session() as session:
            query = select(ProcessModel).order_by(desc(ProcessModel.timestamp))
            
            if search:
                query = query.where(
                    (ProcessModel.process_name.contains(search)) |
                    (ProcessModel.parent_name.contains(search)) |
                    (ProcessModel.command_line.contains(search))
                )
            
            query = query.offset(offset).limit(limit)
            result = session.execute(query)
            return result.scalars().all()
    
    async def get_processes_async(self, session: AsyncSession, limit: int = 100, 
                                  offset: int = 0, search: str = None) -> List[ProcessModel]:
        """Get process records (async)"""
        query = select(ProcessModel).order_by(desc(ProcessModel.timestamp))
        
        if search:
            query = query.where(
                (ProcessModel.process_name.contains(search)) |
                (ProcessModel.parent_name.contains(search)) |
                (ProcessModel.command_line.contains(search))
            )
        
        query = query.offset(offset).limit(limit)
        result = await session.execute(query)
        return result.scalars().all()
    
    def get_process_by_id(self, process_id: int) -> Optional[ProcessModel]:
        """Get a specific process by ID"""
        with self.get_session() as session:
            return session.get(ProcessModel, process_id)
    
    def get_recent_processes(self, minutes: int = 5) -> List[ProcessModel]:
        """Get processes from the last N minutes"""
        with self.get_session() as session:
            cutoff = datetime.utcnow() - timedelta(minutes=minutes)
            query = select(ProcessModel).where(
                ProcessModel.timestamp >= cutoff
            ).order_by(desc(ProcessModel.timestamp))
            result = session.execute(query)
            return result.scalars().all()
    
    def count_processes_by_parent(self, parent_name: str, 
                                   minutes: int = 1) -> int:
        """Count processes spawned by a parent in time window"""
        with self.get_session() as session:
            cutoff = datetime.utcnow() - timedelta(minutes=minutes)
            query = select(func.count(ProcessModel.id)).where(
                and_(
                    ProcessModel.parent_name == parent_name,
                    ProcessModel.timestamp >= cutoff
                )
            )
            result = session.execute(query)
            return result.scalar()
    
    # Alert operations
    def create_alert(self, alert: AlertCreate) -> AlertModel:
        """Create a new alert"""
        with self.get_session() as session:
            db_alert = AlertModel(
                process_id=alert.process_id,
                rule_triggered=alert.rule_triggered,
                severity=alert.severity,
                description=alert.description,
                risk_score=alert.risk_score,
                details=alert.details
            )
            session.add(db_alert)
            session.commit()
            session.refresh(db_alert)
            logger.info(f"Created alert: {db_alert.id} - {alert.rule_triggered}")
            return db_alert
    
    async def create_alert_async(self, alert: AlertCreate, session: AsyncSession) -> AlertModel:
        """Create a new alert (async)"""
        db_alert = AlertModel(
            process_id=alert.process_id,
            rule_triggered=alert.rule_triggered,
            severity=alert.severity,
            description=alert.description,
            risk_score=alert.risk_score,
            details=alert.details
        )
        session.add(db_alert)
        await session.commit()
        await session.refresh(db_alert)
        return db_alert
    
    def get_alerts(self, limit: int = 100, offset: int = 0,
                   severity: str = None, acknowledged: bool = None) -> List[AlertModel]:
        """Get alerts with optional filters"""
        with self.get_session() as session:
            query = select(AlertModel).order_by(desc(AlertModel.timestamp))
            
            if severity:
                query = query.where(AlertModel.severity == severity)
            if acknowledged is not None:
                query = query.where(AlertModel.acknowledged == acknowledged)
            
            query = query.offset(offset).limit(limit)
            result = session.execute(query)
            return result.scalars().all()
    
    async def get_alerts_async(self, session: AsyncSession, limit: int = 100, 
                               offset: int = 0, severity: str = None,
                               acknowledged: bool = None) -> List[AlertModel]:
        """Get alerts (async)"""
        query = select(AlertModel).order_by(desc(AlertModel.timestamp))
        
        if severity:
            query = query.where(AlertModel.severity == severity)
        if acknowledged is not None:
            query = query.where(AlertModel.acknowledged == acknowledged)
        
        query = query.offset(offset).limit(limit)
        result = await session.execute(query)
        return result.scalars().all()
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Get alert statistics"""
        with self.get_session() as session:
            # Total counts by severity
            stats = {
                "total_alerts": 0,
                "critical_severity": 0,
                "high_severity": 0,
                "medium_severity": 0,
                "low_severity": 0
            }
            
            query = select(AlertModel.severity, func.count(AlertModel.id)).group_by(AlertModel.severity)
            result = session.execute(query)
            
            for severity, count in result:
                stats["total_alerts"] += count
                if severity == "critical":
                    stats["critical_severity"] = count
                elif severity == "high":
                    stats["high_severity"] = count
                elif severity == "medium":
                    stats["medium_severity"] = count
                elif severity == "low":
                    stats["low_severity"] = count
            
            # Recent alerts (last 24 hours by hour)
            cutoff = datetime.utcnow() - timedelta(hours=24)
            query = select(
                func.strftime('%H', AlertModel.timestamp),
                func.count(AlertModel.id)
            ).where(AlertModel.timestamp >= cutoff).group_by(
                func.strftime('%H', AlertModel.timestamp)
            )
            result = session.execute(query)
            stats["alerts_by_hour"] = {hour: count for hour, count in result}
            
            return stats
    
    def acknowledge_alert(self, alert_id: int) -> bool:
        """Mark an alert as acknowledged"""
        with self.get_session() as session:
            alert = session.get(AlertModel, alert_id)
            if alert:
                alert.acknowledged = True
                session.commit()
                return True
            return False
    
    def delete_old_data(self, days: int = 30):
        """Delete data older than specified days"""
        with self.get_session() as session:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            # Delete old processes
            session.query(ProcessModel).where(ProcessModel.timestamp < cutoff).delete()
            
            # Delete old alerts
            session.query(AlertModel).where(AlertModel.timestamp < cutoff).delete()
            
            session.commit()
            logger.info(f"Deleted data older than {days} days")


# Global database instance
db = Database()


def init_db(db_url: str = None):
    """Initialize the database"""
    db.initialize(db_url)
    db.create_tables()


async def get_db():
    """Dependency for FastAPI to get database session"""
    async for session in db.get_async_session():
        yield session