from pathlib import Path


import tomli
from pydantic import BaseModel, Field, ValidationError


CONFIG_PATH = Path('/etc/config.toml')


class DefaultsConfig(BaseModel):
    emoji_list: str
    emoji_rowsize: int = Field(ge=1, le=8)
    welcome_text: str
    success_text: str
    fail_text: str
    error_text: str
    timeout_text: str
    captcha_timeout: int
    delete_joins: bool
    logchatid: int | None = None


class GroupConfig(BaseModel):
    id: int
    emoji_list: str | None = None
    emoji_rowsize: int | None = Field(default=None, ge=1, le=8)
    welcome_text: str | None = None
    success_text: str | None = None
    fail_text: str | None = None
    error_text: str | None = None
    timeout_text: str | None = None
    captcha_timeout: int | None = None
    delete_joins: bool | None = None
    logchatid: int | None = None


class ResolvedGroupConfig(BaseModel):
    id: int
    emoji_list: str
    emoji_rowsize: int = Field(ge=1, le=8)
    welcome_text: str
    success_text: str
    fail_text: str
    error_text: str
    timeout_text: str
    captcha_timeout: int
    delete_joins: bool
    logchatid: int | None = None


class AppConfig(BaseModel):
    bot_token: str
    defaults: DefaultsConfig
    groups: list[GroupConfig]


class ConfigFileError(Exception):
    pass


def format_validation_errors(exc: ValidationError) -> str:
    messages = []
    for error in exc.errors():
        location = '.'.join(str(part) for part in error['loc'])
        message = error['msg']
        messages.append(f'{location}: {message}' if location else message)
    return '\n'.join(messages)


def load_config(path: Path) -> AppConfig:
    try:
        with path.open('rb') as config_file:
            data = tomli.load(config_file)
    except FileNotFoundError as exc:
        raise ConfigFileError(f'Config file not found: {path}') from exc
    except tomli.TOMLDecodeError as exc:
        raise ConfigFileError(f'Cannot parse config file {path}: {exc}') from exc
    except OSError as exc:
        raise ConfigFileError(f'Cannot read config file {path}: {exc}') from exc

    try:
        return AppConfig.model_validate(data)
    except ValidationError as exc:
        message = format_validation_errors(exc)
        raise ConfigFileError(f'Invalid config file {path}\n{message}') from exc


class Config:
    def __init__(self, path: Path = CONFIG_PATH):
        self.path = path
        self.reload()

    def _resolve_group(self, defaults: DefaultsConfig, group: GroupConfig) -> ResolvedGroupConfig:
        data = defaults.model_dump()
        data.update(group.model_dump(exclude_none=True))
        return ResolvedGroupConfig.model_validate(data)

    def reload(self) -> None:
        loaded_config = load_config(self.path)
        self.bot_token = loaded_config.bot_token
        self.defaults = loaded_config.defaults
        self.groups = {
            group.id: self._resolve_group(loaded_config.defaults, group)
            for group in loaded_config.groups
        }
        self.allowed_chats = set(
            [group.id for group in loaded_config.groups] + \
            [group.logchatid for group in loaded_config.groups] + \
            [loaded_config.defaults.logchatid]
        )
