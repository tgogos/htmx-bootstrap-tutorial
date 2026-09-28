"""Seed demo user when the users table is empty."""

import logging

from app.auth.passwords import hash_password
from app.auth.users import count_users, create_user
from app.core import config

logger = logging.getLogger(__name__)


async def seed_demo_user() -> None:
    if await count_users() > 0:
        return
    await create_user(
        config.DEMO_USERNAME,
        hash_password(config.DEMO_PASSWORD),
        role="admin",
    )
    logger.info("Seeded demo admin username=%s", config.DEMO_USERNAME)
