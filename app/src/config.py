from dynaconf import Dynaconf, Validator

def group_has_username(groups):
    for group in groups:
        if not group.get('username'):
            return False
    return True

def process_group_usernames(groups):
    for group in groups:
        group.username = group.username.replace('@', '')
    return groups

config = Dynaconf(
    settings_files=['/etc/config.toml'],
    validators=[
        Validator('bot_token', must_exist=True, cast=str),
        Validator('defaults.emoji_list', must_exist=True, cast=str),
        Validator('defaults.emoji_rowsize', must_exist=True, gte=1, lte=8, cast=int),
        Validator('defaults.welcome_text', must_exist=True, cast=str),
        Validator('defaults.success_text', must_exist=True, cast=str),
        Validator('defaults.fail_text', must_exist=True, cast=str),
        Validator('defaults.error_text', must_exist=True, cast=str),
        Validator('defaults.timeout_text', must_exist=True, cast=str),
        Validator('defaults.captcha_timeout', must_exist=True, cast=int),
        Validator('defaults.delete_joins', must_exist=True, cast=bool),
        Validator('defaults.logchatid', default=None),
        Validator(
            'groups',
            must_exist=True,
            condition=group_has_username,
            messages={'condition': 'One or more groups has no username'}
        ),
        Validator(
            'groups',          
            cast=process_group_usernames
        )
    ]
)



