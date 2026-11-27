import markdown
from weasyprint import HTML, CSS
import tempfile
import os
from datetime import datetime
import logging
import base64
from pathlib import Path

logger = logging.getLogger(__name__)

class PDFService:
    @staticmethod
    def _process_images_in_markdown(markdown_content: str, base_path: str = "/app") -> str:
        """
        Convert local image paths in markdown to base64 embedded images.
        This ensures images are included in the PDF.
        
        Image paths in DB are stored as:
        - haber_gorselleri_tavily/image.jpg
        - haber_gorselleri_google/image.png
        
        We combine with base_path to get full Docker path:
        - /app/haber_gorselleri_tavily/image.jpg
        """
        import re
        
        # Find all markdown images: ![alt](path)
        image_pattern = r'!\[([^\]]*)\]\(([^\)]+)\)'
        
        def replace_image(match):
            alt_text = match.group(1)
            image_path = match.group(2)
            
            # Skip if already a URL or base64
            if image_path.startswith(('http://', 'https://', 'data:')):
                return match.group(0)
            
            # Try to read local file
            try:
                # Remove leading slash if present (haber_gorselleri_tavily/... or /haber_gorselleri_tavily/...)
                image_path = image_path.lstrip('/')
                
                # Combine with base path
                full_path = os.path.join(base_path, image_path)
                
                logger.info(f"🖼️ Processing image: {full_path}")
                
                if os.path.exists(full_path):
                    # Determine mime type
                    ext = Path(full_path).suffix.lower()
                    mime_types = {
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.png': 'image/png',
                        '.gif': 'image/gif',
                        '.webp': 'image/webp'
                    }
                    mime_type = mime_types.get(ext, 'image/jpeg')
                    
                    # Read and encode to base64
                    with open(full_path, 'rb') as img_file:
                        img_data = base64.b64encode(img_file.read()).decode('utf-8')
                    
                    logger.info(f"✅ Image encoded successfully: {image_path}")
                    # Return base64 embedded image
                    return f'![{alt_text}](data:{mime_type};base64,{img_data})'
                else:
                    logger.warning(f"⚠️ Image not found: {full_path}")
                    return f'*[Görsel bulunamadı: {alt_text}]*'
            except Exception as e:
                logger.error(f"🔥 Error processing image {image_path}: {e}")
                return f'*[Görsel yüklenemedi: {alt_text}]*'
        
        return re.sub(image_pattern, replace_image, markdown_content)
    
    @staticmethod
    def generate_pdf_report(markdown_content: str, company_name: str, image_base_path: str = "/app") -> str:
        """
        Converts markdown content to a fancy PDF report and returns the file path.
        
        Args:
            markdown_content: Markdown formatted report content
            company_name: Company name for header
            image_base_path: Base directory path for resolving relative image paths (default: /app for Docker)
        """
        
        logger.info("📝 Converting Markdown to HTML...")
        
        # Process images in markdown (convert to base64)
        markdown_content = PDFService._process_images_in_markdown(markdown_content, image_base_path)
        
        # Convert Markdown to HTML
        html_body = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code'])
        
        # Prepare HTML Template with CSS
        date_str = datetime.now().strftime("%d.%m.%Y")
        
        full_html = f"""
        <!DOCTYPE html>
        <html lang="tr">
        <head>
            <meta charset="UTF-8">
            <title>Şirket İstihbarat Raporu - {company_name}</title>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
                
                body {{
                    font-family: 'Inter', sans-serif;
                    line-height: 1.6;
                    color: #333;
                    margin: 0;
                    padding: 0;
                }}
                
                @page {{
                    size: A4;
                    margin: 2cm;
                    @bottom-center {{
                        content: "Sayfa " counter(page) " / " counter(pages);
                        font-size: 10pt;
                        color: #777;
                    }}
                }}
                
                .header {{
                    border-bottom: 2px solid #D32F2F;
                    padding-bottom: 20px;
                    margin-bottom: 30px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                
                .logo-text {{
                    font-size: 24pt;
                    font-weight: 700;
                    color: #D32F2F;
                }}
                
                .meta {{
                    text-align: right;
                    font-size: 10pt;
                    color: #666;
                }}
                
                h1 {{
                    font-size: 20pt;
                    color: #2c3e50;
                    margin-top: 0;
                }}
                
                h2 {{
                    font-size: 16pt;
                    color: #D32F2F;
                    border-bottom: 1px solid #eee;
                    padding-bottom: 5px;
                    margin-top: 30px;
                }}
                
                h3 {{
                    font-size: 14pt;
                    color: #444;
                    margin-top: 20px;
                }}
                
                p {{
                    margin-bottom: 15px;
                    text-align: justify;
                }}
                
                /* Image styling */
                img {{
                    max-width: 100%;
                    height: auto;
                    margin: 15px 0;
                    border-radius: 5px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    display: block;
                }}
                
                /* Center images */
                p img {{
                    margin-left: auto;
                    margin-right: auto;
                }}
                
                ul {{
                    margin-bottom: 15px;
                }}
                
                li {{
                    margin-bottom: 5px;
                }}
                
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                
                th, td {{
                    padding: 10px;
                    border: 1px solid #ddd;
                    text-align: left;
                }}
                
                th {{
                    background-color: #f8f9fa;
                    font-weight: 600;
                }}
                
                code {{
                    background-color: #f1f1f1;
                    padding: 2px 5px;
                    border-radius: 3px;
                    font-family: monospace;
                }}
                
                .footer {{
                    margin-top: 50px;
                    font-size: 9pt;
                    color: #999;
                    text-align: center;
                    border-top: 1px solid #eee;
                    padding-top: 20px;
                }}
                
                .risk-score {{
                    display: inline-block;
                    padding: 5px 10px;
                    border-radius: 5px;
                    font-weight: bold;
                    color: white;
                }}
                
                .risk-low {{ background-color: #2ecc71; }}
                .risk-medium {{ background-color: #f1c40f; color: #333; }}
                .risk-high {{ background-color: #e74c3c; }}
                
            </style>
        </head>
        <body>
            <div class="header">
                <div class="logo-text">ŞİRKET İSTİHBARAT</div>
                <div class="meta">
                    <strong>Şirket:</strong> {company_name}<br>
                    <strong>Tarih:</strong> {date_str}
                </div>
            </div>
            
            <div class="content">
                {html_body}
            </div>
            
            <div class="footer">
                Bu rapor AI Agent tarafından otomatik oluşturulmuştur.<br>
                Resmi belge niteliği taşımaz, sadece istihbarat amaçlıdır.
            </div>
        </body>
        </html>
        """
        
        # Generate PDF using WeasyPrint
        fd, temp_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        
        try:
            logger.info("🖨️ Rendering PDF with WeasyPrint...")
            HTML(string=full_html).write_pdf(temp_path)
            logger.info(f"✅ PDF rendered successfully at {temp_path}")
            return temp_path
        except Exception as e:
            logger.error(f"🔥 WeasyPrint error: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e