# -*-coding:utf-8-*-

import datetime
import json
import logging
from urllib import unquote

from karlooper.config.config import ContentType, COOKIE_SECURITY_DEFAULT_STRING
from karlooper.utils.security import DES
from karlooper.template import render

__author__ = 'karlvorndoenitz@gmail.com'


class Request(object):
    def __init__(self, http_data_dict, http_message, settings):
        """

        :param http_data_dict: converted http data, dict type
        :param http_message: http message, string type

        """
        self.__http_data = http_data_dict
        self.header = "ServerName: karlooper\r\n"
        self.__http_message = http_message
        self.logger = logging.getLogger()
        self.cookie_dict = self.__parse_cookie()
        self.param_dict = self.__parse_param()
        self.__settings = settings

    def __parse_cookie(self):
        """

        :return: a dict contain cookie or None or error

        """
        cookie_string = self.__http_data["header"].get("cookie", "")
        if not cookie_string:
            return {}
        try:
            cookie_dict = dict((cookie.split("=")[0], cookie.split("=")[1]) for cookie in cookie_string.split("; "))
            return cookie_dict
        except Exception, e:
            raise e

    def __parse_param(self):
        """

        :return: a dict contain params

        """
        url_param = self.__http_data["url"].split("?")[1] if "?" in self.__http_data["url"] else None
        if not url_param:
            url_param_dict = {}
        else:
            url_param_dict = dict((param.split("=")[0], param.split("=")[1]) for param in url_param.split("&"))
        content_type = self.get_header("content-type")
        http_body = self.__http_data.get("body", "")
        if content_type == ContentType.FORM and http_body:
            body_param = dict((param.split("=")[0], param.split("=")[1]) for param in http_body.split("&"))
        elif content_type == ContentType.JSON and http_body:
            body_param = eval(http_body)
        else:
            body_param = {}
        param = dict(url_param_dict, **body_param)
        return param

    def get_cookie(self, key, default=None):
        """

        :param key: cookie's key
        :param default: cookie's default value
        :return: cookie's value

        """
        return self.cookie_dict.get(key, default)

    def get_security_cookie(self, key, default=None):
        """

        :param key: cookie's key
        :param default: cookie's default value
        :return: cookie's value

        """
        cookie = self.get_cookie(key)
        if not cookie:
            return default
        des = DES()
        security_key = self.__settings.get("cookie", COOKIE_SECURITY_DEFAULT_STRING)
        des.input_key(security_key)
        return des.decode(cookie)

    def get_parameter(self, key, default=None):
        """

        :param key: param's key
        :param default: param's default value
        :return: param's value

        """
        return self.param_dict.get(key, default)

    def decode_parameter(self, key, default=None):
        """

        :param key: value's key
        :param default: default value
        :return: decoded parameter

        """
        parameter = self.get_parameter(key)
        if not parameter:
            return default
        return unquote(parameter)

    def get_header(self, key, default=None):
        """

        :param key: header data's key
        :param default: default value
        :return: value

        """
        header_data = self.__http_data["header"]
        return header_data.get(key, default)

    def __check_cookies(self, key):
        feature_key = "Set-Cookie: %s=" % key
        header_list = self.header.split("\r\n")
        for header_string in header_list:
            if feature_key in header_string:
                return header_string

    def set_cookie(self, key, value, expires_days=1, path="/", domain=None):
        """

        :param key: cookie's key
        :param value: cookie's value
        :param expires_days: cookie's expires days
        :param path: cookie's value path
        :param domain: cookie's domain
        :return: None

        """
        key = str(key)
        value = str(value)
        now_time = datetime.datetime.now()
        expires_days = now_time + datetime.timedelta(days=expires_days)
        expires_days = expires_days.strftime("%a, %d %b %Y %H:%M:%S GMT")
        cookie_string = 'Set-Cookie: %s=%s; expires=%s; Path=%s' % (key, value, expires_days, path)
        if domain:
            cookie_string += "; Domain=%s" % domain
        check_cookie = self.__check_cookies(key)
        if not check_cookie:
            self.header += "%s\r\n" % cookie_string
        else:
            self.header = self.header.replace(check_cookie, cookie_string)

    def set_security_cookie(self, key, value, expires_days=1, path="/", domain=None):
        """

        :param key: cookie's key
        :param value: cookie's value
        :param expires_days: cookie's expires days
        :param path: cookie's value path
        :param domain: cookie's domain
        :return: None

        """
        des = DES()
        security_key = self.__settings.get("cookie", COOKIE_SECURITY_DEFAULT_STRING)
        des.input_key(security_key)
        security_value = des.encode(value)
        self.set_cookie(key, security_value, expires_days, path, domain)

    def clear_cookie(self, key, path="/", domain=None):
        """

        :param key: clear cookie by key
        :param path: cookie's path
        :param domain: cookie's domain
        :return: None

        """
        self.set_cookie(key, "", 0, path, domain)

    def clear_all_cookie(self, path="/", domain=None):
        """

        :param path: cookie's path
        :param domain: cookie's domain
        :return: None

        """
        for key in self.cookie_dict:
            self.clear_cookie(key, path, domain)

    def set_header(self, header_dict):
        """

        :param header_dict: http header data dict type
        :return: None

        """
        for header_key in header_dict:
            self.header += "%s: %s\r\n" % (header_key, header_dict[header_key])

    def clear_header(self, name):
        """

        :param name: header's name
        :return:

        """
        header_list = self.header.split("\r\n")
        name = "%s: " % name
        for header_string in header_list:
            if name in header_string:
                header_string += "\r\n"
                self.header = self.header.replace(header_string, "")

    def get_response_header(self):
        """

        :return: http message's header

        """
        return "\r\n" + self.header + "\r\n"

    def response_as_json(self, data):
        """

        :param data: the response data
        :return: json data

        """
        self.set_header({"Content-Type": "application/json"})
        return json.dumps(data, ensure_ascii=False)

    def render(self, template_path, **kwargs):
        root_path = self.__settings.get("template", ".")
        template_path = root_path + template_path
        return render(template_path, **kwargs)

    def get_http_request_message(self):
        return self.__http_message

    def get(self):
        pass

    def post(self):
        pass

    def put(self):
        pass

    def head(self):
        self.logger.info(self.__http_data.get("url", ""))
        return ""

    def options(self):
        pass

    def delete(self):
        pass

    def trace(self):
        return self.__http_message.split("\r\n\r\n") if "\r\n\r\n" in self.__http_message else ""

    def connect(self):
        pass