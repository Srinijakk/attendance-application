from sqlalchemy import Column, Integer, String, Date, Time, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, unique=True, index=True)
    name = Column(String)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String)  # 'employee' or 'admin'
    status = Column(String, default="active")

    attendances = relationship("Attendance", back_populates="employee")

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    date = Column(Date)
    check_in = Column(Time)
    check_out = Column(Time, nullable=True)
    check_in_lat = Column(Float, nullable=True)
    check_in_lon = Column(Float, nullable=True)
    check_out_lat = Column(Float, nullable=True)
    check_out_lon = Column(Float, nullable=True)
    check_in_selfie = Column(String)  # Path to image
    check_out_selfie = Column(String, nullable=True)

    employee = relationship("Employee", back_populates="attendances")
