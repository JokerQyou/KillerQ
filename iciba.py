# coding: utf-8
import json

import keypirinha as kp
import keypirinha_util as kpu
import keypirinha_net as kpnet


class IcibaDict(kp.Plugin):
    '''
    www.iciba.com Dictionary

    Look up words from Youdao.com.
    '''
    API_REQUEST_HEADERS = [
        ('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'),
        ('DNT', '1'),
        ('Host', 'www.iciba.com'),
    ]
    API_URL = 'http://www.iciba.com/index.php?a=getWordMean&c=search&list=1'

    ITEMCAT_GET_WORDMEAN = kp.ItemCategory.USER_BASE + 1
    ITEMCAT_RESULT = kp.ItemCategory.USER_BASE + 2

    def __init__(self):
        super().__init__()

    def on_start(self):
        pass

    def on_catalog(self):
        item_get_wordmean = self.create_item(
            category=self.ITEMCAT_GET_WORDMEAN,
            label='iciba',
            short_desc='Lookup on iciba.com',
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

        # results = []
        try:
            opener = kpnet.build_urllib_opener()
            opener.addheaders = self.API_REQUEST_HEADERS
            url = self.API_URL + '&word=' + user_input
            with opener.open(url) as conn:
                response = conn.read()

            if self.should_terminate():
                return
        except Exception as e:
            self.suggest_error(user_input, str(e))
        else:
            self.suggest_word_means(json.loads(response))

    def suggest_error(self, label, description):
        self.set_suggestions([
            self.create_error_item(label=label, short_desc=description)
        ], kp.Match.ANY, kp.Sort.NONE)

    def suggest_word_means(self, json_response):
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
                                target=label,
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
