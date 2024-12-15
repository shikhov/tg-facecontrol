from dynaconf import Dynaconf, Validator

def group_has_id(groups):
    for group in groups:
        if not group.get('id'):
            return False
    return True

def process_groups(groups):
    for group in groups:
        group.id = int(group.id)
        if group.get('emoji_list'):
            group.emoji_list = str(group.emoji_list)
        if group.get('emoji_rowsize'):
            group.emoji_rowsize = int(group.emoji_rowsize)
        if group.get('welcome_text'):
            group.welcome_text = str(group.welcome_text)
        if group.get('success_text'):
            group.success_text = str(group.success_text)
        if group.get('fail_text'):
            group.fail_text = str(group.fail_text)
        if group.get('error_text'):
            group.error_text = str(group.error_text)
        if group.get('timeout_text'):
            group.timeout_text = str(group.timeout_text)
        if group.get('captcha_timeout'):
            group.captcha_timeout = int(group.captcha_timeout)
        if group.get('delete_joins'):
            group.delete_joins = bool(group.delete_joins)
        if group.get('logchatid'):
            group.logchatid = int(group.logchatid)
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
            condition=group_has_id,
            messages={'condition': 'One or more groups has no id'},
        ),
        Validator(
            'groups',
            cast=process_groups
        )
    ]
)



