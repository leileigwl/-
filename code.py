import requests
from bs4 import BeautifulSoup
import time
import os
import re
from urllib.parse import urljoin
import json
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import textwrap

pdfmetrics.registerFont(TTFont('SimSun', 'simsun.ttc'))  # 宋体
pdfmetrics.registerFont(TTFont('SimHei', 'simhei.ttf'))  # 黑体
chinese_font = 'SimSun'

class ArticleScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.articles = []
        self.delay = 2  # 请求间隔时间（秒）
    
    def get_article_content(self, url, title):
        """获取单篇文章内容"""
        try:
            print(f"正在爬取: {title}")
            response = self.session.get(url, timeout=10)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                print(f"请求失败，状态码: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找post-title post-main区域内的所有p标签
            post_main = soup.find('div', class_=['post-title', 'post-main']) or soup.find('div', class_='post-main')
            
            if not post_main:
                # 尝试其他可能的选择器
                post_main = soup.find('article') or soup.find('div', class_='content') or soup.find('div', class_='post')
            
            if not post_main:
                print(f"未找到文章内容区域: {title}")
                return None
            
            # 提取所有p标签内容
            paragraphs = post_main.find_all('p')
            content_paragraphs = []
            
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 10:  # 过滤掉过短的段落
                    content_paragraphs.append(text)
            
            if not content_paragraphs:
                print(f"未找到有效段落: {title}")
                return None
            
            article_data = {
                'title': title,
                'url': url,
                'content': content_paragraphs
            }
            
            print(f"成功爬取: {title} ({len(content_paragraphs)}段)")
            return article_data
            
        except Exception as e:
            print(f"爬取失败 {title}: {str(e)}")
            return None
    
    def scrape_all_articles(self, urls_data):
        """爬取所有文章"""
        for i, (title, url) in enumerate(urls_data, 1):
            print(f"\n进度: {i}/{len(urls_data)}")
            
            article = self.get_article_content(url, title)
            if article:
                self.articles.append(article)
            
            # 添加延迟避免被封IP
            if i < len(urls_data):
                time.sleep(self.delay)
        
        print(f"\n爬取完成！成功获取 {len(self.articles)} 篇文章")
    
    def save_to_json(self, filename='articles.json'):
        """保存为JSON格式"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.articles, f, ensure_ascii=False, indent=2)
        print(f"已保存到 {filename}")
    
    def format_article(self, article, format_type='markdown'):
        """格式化单篇文章"""
        if format_type == 'markdown':
            formatted = f"# {article['title']}\n\n"
            formatted += f"**来源:** {article['url']}\n\n"
            formatted += "---\n\n"
            
            for para in article['content']:
                formatted += f"{para}\n\n"
            
            return formatted
        
        elif format_type == 'html':
            formatted = f"<article>\n"
            formatted += f"  <header>\n"
            formatted += f"    <h1>{article['title']}</h1>\n"
            formatted += f"    <p><strong>来源:</strong> <a href='{article['url']}'>{article['url']}</a></p>\n"
            formatted += f"  </header>\n"
            formatted += f"  <main>\n"
            
            for para in article['content']:
                formatted += f"    <p>{para}</p>\n"
            
            formatted += f"  </main>\n"
            formatted += f"</article>\n\n"
            
            return formatted
        
        elif format_type == 'txt':
            formatted = f"{article['title']}\n"
            formatted += "=" * len(article['title']) + "\n\n"
            formatted += f"来源: {article['url']}\n\n"
            
            for para in article['content']:
                formatted += f"{para}\n\n"
            
            formatted += "-" * 50 + "\n\n"
            
            return formatted
    
    def export_to_pdf(self, filename='./经典英语美文集1.pdf'):
        if not self.articles:
            print("没有文章数据，请先爬取文章")
            return
        
        try:
            # 创建PDF文档
            doc = SimpleDocTemplate(
                filename,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            # 定义样式
            styles = getSampleStyleSheet()
            
            # 标题样式
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
            
            # 正文样式
            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['Normal'],
                fontSize=11,
                spaceAfter=12,
                alignment=TA_LEFT,
                fontName='Helvetica',
                leading=16
            )
            
            # 源URL样式
            source_style = ParagraphStyle(
                'CustomSource',
                parent=styles['Normal'],
                fontSize=8,
                spaceAfter=20,
                alignment=TA_CENTER,
                fontName='Helvetica-Oblique',
                textColor='grey'
            )
            
            # 构建PDF内容
            story = []
            
            for i, article in enumerate(self.articles):
                print(f"正在处理第 {i+1}/{len(self.articles)} 篇文章: {article['title']}")
                
                # 添加标题
                title = Paragraph(article['title'], title_style)
                story.append(title)
                
                # 添加来源信息
                source_text = f"来源: {article['url']}"
                source = Paragraph(source_text, source_style)
                story.append(source)
                
                # 添加文章内容
                for paragraph_text in article['content']:
                    # 清理文本，确保没有特殊字符导致PDF生成问题
                    cleaned_text = self.clean_text_for_pdf(paragraph_text)
                    if cleaned_text.strip():
                        para = Paragraph(cleaned_text, body_style)
                        story.append(para)
            
            # 生成PDF
            print("正在生成PDF文件...")
            doc.build(story)
            print(f"PDF已成功生成: {filename}")
            
        except Exception as e:
            print(f"生成PDF时出错: {str(e)}")
            print("提示：请确保已安装reportlab库: pip install reportlab")
    
    def clean_text_for_pdf(self, text):
        """清理文本以适应PDF生成"""
        # 移除或替换可能导致PDF问题的字符
        text = re.sub(r'\s+', ' ', text)  # 标准化空白字符
        text = text.strip()
        
        # 转义XML特殊字符
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        
        return text
    
    def export_to_pdf_advanced(self, filename='经典英语美文集_高级版1.pdf'):
        """导出PDF高级版本，每篇文章单独分页，无封面、目录、来源"""
        if not self.articles:
            print("没有文章数据，请先爬取文章")
            return
        try:
            doc = SimpleDocTemplate(
                filename,
                pagesize=A4,
                rightMargin=50,
                leftMargin=50,
                topMargin=50,
                bottomMargin=50
            )
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=16,
                spaceBefore=10,
                alignment=TA_CENTER,
                fontName='SimHei'
            )
            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=12,
                alignment=TA_LEFT,
                fontName='SimSun',
                leading=18,
                firstLineIndent=20
            )
            story = []
            for i, article in enumerate(self.articles, 1):
                print(f"正在处理第 {i}/{len(self.articles)} 篇文章: {article['title']}")
                title = Paragraph(article['title'], title_style)
                story.append(title)
                for paragraph_text in article['content']:
                    cleaned_text = self.clean_text_for_pdf_advanced(paragraph_text)
                    if cleaned_text.strip() and len(cleaned_text) > 10:
                        para = Paragraph(cleaned_text, body_style)
                        story.append(para)
                # 每篇文章后分页，最后一篇不分页
                if i < len(self.articles):
                    story.append(PageBreak())
            print("正在生成PDF文件...")
            doc.build(story)
            print(f"高级PDF已成功生成: {filename}")
        except Exception as e:
            print(f"生成PDF时出错: {str(e)}")
            print("提示：请确保已安装reportlab库: pip install reportlab")
    
    def clean_text_for_pdf_advanced(self, text):
        """高级文本清理，保持更多格式"""
        # 保留基本标点和常用符号
        text = re.sub(r'\s+', ' ', text)  # 标准化空白字符
        text = text.strip()
        
        # 只转义必要的XML字符
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        
        # 处理引号
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        return text

def parse_article_list(file_content):
    """解析文章列表文件"""
    urls_data = []
    lines = file_content.strip().split('\n')
    
    for line in lines:
        if line.strip() and '[' in line and ']' in line:
            # 提取标题和URL
            title_match = re.search(r'\[(.*?)\]', line)
            url_match = re.search(r'https://[^\s]+', line)
            
            if title_match and url_match:
                title = title_match.group(1).strip()
                url = url_match.group(0).strip()
                urls_data.append((title, url))
    
    return urls_data
def export_pdf_from_json(json_file='articles.json', pdf_file='经典英语美文集.pdf'):
    """从JSON文件直接导出PDF，不需重新爬取"""
    scraper = ArticleScraper()
    with open(json_file, 'r', encoding='utf-8') as f:
        scraper.articles = json.load(f)
    print(f"已从 {json_file} 读取 {len(scraper.articles)} 篇文章，开始导出PDF...")
    scraper.export_to_pdf_advanced(pdf_file)

def just_export():
   export_pdf_from_json()

def run_full():
    with open('经典美文网站原始数据.txt', 'r', encoding='utf-8') as f:
            file_content = f.read()
        # 解析URL列表
    urls_data = parse_article_list(file_content)
    print(f"准备爬取 {len(urls_data)} 篇文章...")

    scraper.scrape_all_articles(urls_data)
    if scraper.articles:
        # 保存原始数据
        scraper.save_to_json()
        print("\n程序执行完成！")
    else:
        print("未成功爬取任何文章，请检查网络连接和URL有效性")

def main():
    # run_full()
    # just_export()
if __name__ == "__main__":
    main()