
import logging
import json
from wechatpy.utils import check_signature
from wechatpy import parse_message, create_reply
from wechatpy.replies import TextReply, ImageReply,ArticlesReply
from wechatpy.exceptions import InvalidSignatureException
import numpy as np
import re
from cgi import parse_qs, escape
import xlrd

tfidf = open('tfidf.txt','r',encoding = 'utf-8').readlines()
tfidf_dict = {}
for i in tfidf:
    i = i.strip().split('\t')
    tfidf_dict[i[0]] = float(i[1])
adding_list = ['AR','APP','2D','3D','CMS','视网么','内容管理系统']
#for i in adding_list:
    #jieba.add_word(i)
def apiReply(reply, txt=False, content_type='application/json', code=200):
    return {
        "isBase64Encoded":False,
        "statusCode": code,
        "headers": {'Content-Type': content_type},
        "body":json.dumps(reply, ensure_ascii=False) if not txt else str(reply)
    }

def sentence_similarity(s1,s2,tfidf_dict):
    def sentence_vector(s):
        stopwords = open('stop_word.txt','r',encoding = 'utf-8').read()
        stop_words = [word for word in stopwords if word != '\n']
        words = jieba.lcut(s)
        words = [x for x in words if x not in stop_words]
        v = np.zeros(64)
        for word in words:
            try:
                v += model[word]*tfidf_dict[word]
            except:
                  pass
        v /= len(words)
        return v
    v1,v2 = sentence_vector(s1),sentence_vector(s2)
    return np.dot(v1,v2)/(np.linalg.norm(v1) * np.linalg.norm(v2))

def turning(ques):
    turning_list = [['增强现实','AR'],['如何','怎么','怎样'],['流程','步骤','方法'],['创建','新建'],['内容管理系统','CMS']]
    for i in turning_list:
        for k in i:
            if k in ques:
                ques = re.sub(k,i[0],ques)
    return ques

def jaccard(s_max,question):
    s_dict = [x for x in s_max if x != '吗']
    q_dict = [x for x in question if x != '吗']
    count = 0
    for i in s_dict:
        if i in q_dict:
            count += 1
    s_dict.extend(q_dict)
    length = len(set(s_dict))
    j = count/length
    return j

def ques_read(f):
    wb = xlrd.open_workbook(filename = f)
    sheet1 = wb.sheet_by_index(0)
    ques = sheet1.col_values(0)
    answ = sheet1.col_values(1)
    token = sheet1.col_values(2)
    media_id = sheet1.col_values(3)
    return ques,answ,token,media_id
f = 'test1.xlsx'
ques,answ,token,media_id = ques_read(f)
def wechat(httpMethod, requestParameters,):
    WECHAT_TOKEN = 'lty108230999'
    signature = requestParameters['signature']
    timestamp = requestParameters['timestamp']
    nonce = requestParameters['nonce']
    echo_str = requestParameters['echostr']
    #print('signature=',signature,'&timestamp=',timestamp,'&nonce=',nonce,'&echo_str=',echo_str)
    if httpMethod == 'GET':
        try:
            check_signature(WECHAT_TOKEN, signature, timestamp, nonce)
        except InvalidSignatureException:
            echo_str = 'error'
        return apiReply(echo_str, txt=True, content_type="text/plain")
    else:
        pass
def myMain(httpMethod, requestParameters, body=''):
    return wechat(httpMethod, requestParameters, body=body)

def wechat_back(event):
    event = re.sub(r'\<xml\>','<xml>\n',event)
    xml = event
    msg = parse_message(xml)
    if msg.type == 'text':
        question = turning(msg.content)
        s = {}
        ss = {}
        lib = {}
        lib_qt = {}
        lib_qm = {}
        s_max = ''
        for i in range(0,len(ques)):
            lib_qt[ques[i]] = int(token[i])
        for i in range(0,len(ques)):
            lib_qm[ques[i]] = media_id[i]   
        for i in range(0,len(ques)):
            lib[ques[i]] = answ[i]
        text = [x.strip() for x in ques if len(x)>2]
        if question in lib:
            s_max = question
            answer = lib[question]
        else:
            for i in text:
                similarity = sentence_similarity(i,question,tfidf_dict)
                s[i] = similarity
            s_max = max(s,key = s.get)
        #print(s_max)
        for i in range(0,10):
            if jaccard(s_max,question) < 0.20:
                del s[s_max]
                s_max = max(s,key = s.get)
            else:
                try:
                    ss[s_max] = s[s_max]+jaccard(s_max,question)
                except:
                    ss[s_max] = 1.5
        #print(ss)
        try:
            s_max = max(ss,key = ss.get)
        except:
            s_max = '   '                 
        #print(s_max)
        '''try:
            print(lib_qt[s_max])
        except:
            lib_qt[s_max] = 9
            print(ss)'''
        print('最大值已经取到')
        if lib_qt[s_max] == 1:
            answer = lib_qm[s_max]
            reply = ImageReply(content = 'AAAAAAAAA',media_id = answer ,message = msg)
            xml = reply.render()
  
        elif lib_qt[s_max] == 2: 
            answer = lib[s_max]
            img = lib_qm[s_max].split(' ')[0]
            url = lib_qm[s_max].split(' ')[1]
            reply = ArticlesReply(message=msg)
            reply.add_article({
                'title': question,
                'description': answer,
                'image': img,
                'url': url
            })
            xml = reply.render()
  
        else:
            try:
                answer = lib[s_max]
            except:
                answer = '暂无此问题'
                answer = answer.encode('utf-8')
                #print(answer)
            reply = TextReply(content=answer, message=msg)
            xml = reply.render()
        print('问题：'+question)
        print('匹配结果:'+s_max)     
        print('答案：',answer)
        resp = apiReply(reply, txt=True, content_type="application/xml")
        #resp = json.dumps(reply,encoding = 'utf-8')
        print(resp)
        return resp

def time_out_reply(event):
    event = re.sub(r'\<xml\>','<xml>\n',event)
    xml = event
    msg = parse_message(xml)
    reply = TextReply(content='【系统已激活，请再次提问】', message=msg)
    resp = apiReply(reply, txt=True, content_type="application/xml")
    return resp


def handler(environ, start_response):
    request_body_size = int(environ.get('CONTENT_LENGTH', 0))
    request_body = environ['wsgi.input'].read(request_body_size)
    event_body = request_body.decode('utf-8')
    httpMethod = environ['REQUEST_METHOD']
    try:
        QUERY_STRING = environ['QUERY_STRING']
        requestParameters = {}
        for i in QUERY_STRING.split('&'):
            k = i.split('=')
            requestParameters[k[0]] = k[1]
    except:
        pass
    if httpMethod == 'GET':
        try:
            resp = wechat(httpMethod,requestParameters)
            status = '200 OK'
            response_headers = [('Content-type', 'text/plain')]
            start_response(status, response_headers)
            print('接收公众号请求')
            resp = resp['body'].encode('utf-8')
            print(type(resp))
            return [resp]
        except:
            return b'AAAAAA'
    elif httpMethod == 'POST':
        '''try:
            resp = wechat_back(event_body)
        except:
            resp = time_out_reply(event_body)'''
        resp =wechat_back(event_body)
        status = '200 OK'
        response_headers = [('Content-type', 'application/xml')]
        start_response(status, response_headers)
        return [resp['body'].encode('utf-8')]
