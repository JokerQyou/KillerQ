# coding: utf-8
import json
import urllib

import keypirinha as kp
import keypirinha_util as kpu
import keypirinha_net as kpnet


class IcibaDict(kp.Plugin):
    '''
    www.iciba.com Dictionary

    Look up words from Youdao.com.
    '''
    API_REQUEST_HEADERS = [
        ('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'),  # noqa
        ('DNT', '1'),
        ('Host', 'www.iciba.com'),
        ('X-Requested-With', 'XMLHttpRequest'),
    ]
    API_URL = 'http://www.iciba.com/index.php'

    ITEMCAT_GET_WORDMEAN = kp.ItemCategory.USER_BASE + 1
    ITEMCAT_RESULT = kp.ItemCategory.USER_BASE + 2

    ACTION_BROWSE = "browse"
    ACTION_BROWSE_PRIVATE = "browse_private"

    ARG_SEPARATOR = '<|>'

    def __init__(self):
        super().__init__()

    def on_start(self):
        actions = [
            self.create_action(
                name=self.ACTION_BROWSE,
                label='查看',
                short_desc='在浏览器中查看词条'
            ),
            self.create_action(
                name=self.ACTION_BROWSE_PRIVATE,
                label='隐身查看',
                short_desc='在浏览器（隐身模式）中查看词条'
            ),
        ]
        self.set_actions(self.ITEMCAT_RESULT, actions)

    def on_catalog(self):
        item_get_wordmean = self.create_item(
            category=self.ITEMCAT_GET_WORDMEAN,
            label='iciba',
            short_desc='使用 iciba.com 查找',
            target='lookup',
            args_hint=kp.ItemArgsHint.REQUIRED,
            hit_hint=kp.ItemHitHint.NOARGS
        )
        self.set_catalog([item_get_wordmean, ])

    def on_suggest(self, user_input, items_chain):
        if not user_input or not items_chain\
                or items_chain[-1].category() != self.ITEMCAT_GET_WORDMEAN:
            return

        if self.should_terminate(.5):
            return

        try:
            web_url = 'http://www.iciba.com/{}'.format(urllib.parse.quote(user_input))
            opener = kpnet.build_urllib_opener()
            opener.addheaders = self.API_REQUEST_HEADERS + [
                ('Referer', web_url),
            ]
            url = self.API_URL + '?' + urllib.parse.urlencode({
                'word': user_input,
                'a': 'getWordMean',
                'c': 'search',
                'list': '1',
                # Observed value for `list` includes:
                # 1,2,3,4,5,8,9,10,12,13,14,15,18,21,22,24,3003,3004,3005
            })

            with opener.open(url) as conn:
                response = conn.read()

            if self.should_terminate():
                return
        except Exception as e:
            self.suggest_error(user_input, str(e))
        else:
            self.suggest_word_means(json.loads(response), web_url)

    def on_execute(self, item, action):
        if item.category() != self.ITEMCAT_RESULT:
            return

        if action:
            if action.name() == self.ACTION_BROWSE:
                kpu.web_browser_command(
                    url=self.get_url_for_cataitem(item), execute=True
                )
            elif action.name() == self.ACTION_BROWSE_PRIVATE:
                kpu.web_browser_command(
                    private_mode=True,
                    url=self.get_url_for_cataitem(item),
                    execute=True
                )

    def get_url_for_cataitem(self, item):
        what, which, _ = item.target().split(self.ARG_SEPARATOR)
        if what == 'url':
            return which
        else:
            return None

    def suggest_error(self, label, description):
        self.set_suggestions([
            self.create_error_item(label=label, short_desc=description)
        ], kp.Match.ANY, kp.Sort.NONE)

    def suggest_word_means(self, json_response, url):
        if json_response['errno'] == 0:
            # self.info(json_response)
            suggestions = []
            if 'symbols' not in json_response['baesInfo']:
                self.info(json_response)
                return

            try:
                for symbol in json_response['baesInfo']['symbols']:
                    for meaning in symbol['parts']:
                        label = '{}  Eng. [{}] Amr. [{}]'.format(
                            meaning['part'],
                            symbol['ph_en'],
                            symbol['ph_am']
                        )
                        suggestions.append(
                            self.create_item(
                                category=self.ITEMCAT_RESULT,
                                label=label,
                                short_desc='; '.join(meaning['means']),
                                target=self.ARG_SEPARATOR.join(['url', url, label]),
                                args_hint=kp.ItemArgsHint.REQUIRED,
                                hit_hint=kp.ItemHitHint.IGNORE
                            )
                        )
            except Exception as e:
                self.suggest_error('Error presenting', str(e))
            else:
                self.set_suggestions(suggestions, kp.Match.ANY, kp.Sort.NONE)
        else:
            self.suggest_error(
                json_response['errmsg'],
                'Error code {}'.format(json_response['errno'])
            )
