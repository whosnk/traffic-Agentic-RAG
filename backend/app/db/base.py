# app/db/base.py
from sqlalchemy.ext.declarative import declarative_base

# 所有的表都要继承这个 Base
Base = declarative_base()