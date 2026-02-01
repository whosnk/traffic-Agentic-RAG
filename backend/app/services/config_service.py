from sqlalchemy.orm import Session
from app.models.config import AIConfig


class ConfigService:
    @staticmethod
    def get_active_config(db: Session, config_type: str):
        """获取当前启用的配置"""
        config = db.query(AIConfig).filter(
            AIConfig.config_type == config_type,
            AIConfig.is_active == True
        ).first()
        return config

    @staticmethod
    def update_config(db: Session, config_data: dict):
        """更新配置（后台管理页面用）"""
        # 先把同类型的其他配置设为不启用
        db.query(AIConfig).filter(
            AIConfig.config_type == config_data['config_type']
        ).update({"is_active": False})

        # 插入或更新当前配置
        new_config = AIConfig(**config_data, is_active=True)
        db.merge(new_config)
        db.commit()