from flask import Flask, render_template, request, jsonify
from flask_bootstrap import Bootstrap
import qrcode
from io import BytesIO
import base64
import json
from datetime import datetime
import re
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

app = Flask(__name__)
Bootstrap(app)

def validar_cpf(cpf):
    # Remove caracteres não numéricos
    cpf = re.sub(r'[^0-9]', '', cpf)
    
    if len(cpf) != 11:
        return False
        
    # Verifica se todos os dígitos são iguais
    if len(set(cpf)) == 1:
        return False
    
    # Calcula primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito = (soma * 10) % 11
    if digito == 10:
        digito = 0
    if digito != int(cpf[9]):
        return False
    
    # Calcula segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito = (soma * 10) % 11
    if digito == 10:
        digito = 0
    if digito != int(cpf[10]):
        return False
    
    return True

def validar_cnpj(cnpj):
    # Remove caracteres não numéricos
    cnpj = re.sub(r'[^0-9]', '', cnpj)
    
    if len(cnpj) != 14:
        return False
        
    # Verifica se todos os dígitos são iguais
    if len(set(cnpj)) == 1:
        return False
    
    # Primeiro dígito
    soma = sum(int(cnpj[i]) * (5 - i if i < 4 else 13 - i) for i in range(12))
    digito = 11 - (soma % 11)
    if digito >= 10:
        digito = 0
    if digito != int(cnpj[12]):
        return False
    
    # Segundo dígito
    soma = sum(int(cnpj[i]) * (6 - i if i < 5 else 14 - i) for i in range(13))
    digito = 11 - (soma % 11)
    if digito >= 10:
        digito = 0
    if digito != int(cnpj[13]):
        return False
    
    return True

def gerar_codigo_unico(documento):
    # Gera um código único baseado no timestamp e últimos 4 dígitos do documento
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    ultimos_digitos = re.sub(r'[^0-9]', '', documento)[-4:]
    return f"{timestamp}-{ultimos_digitos}"

def gerar_pdf_plantio(dados):
    # Cria um buffer para o PDF
    buffer = BytesIO()
    
    # Cria o documento PDF
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1  # Centralizado
    )
    
    # Título
    elements.append(Paragraph("Informações do Plantio", title_style))
    elements.append(Spacer(1, 12))
    
    # Adiciona o código único em destaque
    codigo_style = ParagraphStyle(
        'CodigoStyle',
        parent=styles['Normal'],
        fontSize=16,
        textColor=colors.HexColor('#28a745'),
        spaceAfter=20,
        alignment=1
    )
    elements.append(Paragraph(f"Código: {dados['codigo_unico']}", codigo_style))
    elements.append(Spacer(1, 12))
    
    # Prepara os dados para a tabela
    table_data = []
    labels = {
        'tipo_documento': 'Tipo de Documento',
        'documento': 'Documento',
        'nome_vegetal': 'Nome do Vegetal',
        'data_plantio': 'Data do Plantio',
        'tipo_solo': 'Tipo de Solo',
        'frequencia_rega': 'Frequência de Rega',
        'exposicao_sol': 'Exposição ao Sol',
        'tempo_colheita': 'Tempo até Colheita',
        'observacoes': 'Observações',
        'data_cadastro': 'Data do Cadastro'
    }
    
    for key, label in labels.items():
        if key in dados:
            table_data.append([Paragraph(label, styles['Normal']), 
                             Paragraph(str(dados[key]), styles['Normal'])])
    
    # Cria a tabela
    table = Table(table_data, colWidths=[2.5*inch, 4*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BOX', (0, 0), (-1, -1), 2, colors.black),
    ]))
    
    elements.append(table)
    
    # Gera o PDF
    doc.build(elements)
    
    # Retorna o PDF em base64
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return base64.b64encode(pdf_bytes).decode()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/validar-documento', methods=['POST'])
def validar_documento():
    documento = request.form.get('documento', '')
    tipo = request.form.get('tipo', '')
    
    # Remove caracteres não numéricos para validação
    documento_limpo = re.sub(r'[^0-9]', '', documento)
    
    if tipo == 'cpf':
        valido = validar_cpf(documento_limpo)
    else:  # cnpj
        valido = validar_cnpj(documento_limpo)
    
    return jsonify({'valido': valido})

@app.route('/cadastrar', methods=['POST'])
def cadastrar():
    try:
        print("Iniciando cadastro...")
        # Coleta os dados do formulário
        dados = {
            'tipo_documento': request.form.get('tipo_documento'),
            'documento': request.form.get('documento'),
            'nome_vegetal': request.form.get('nome_vegetal'),
            'data_plantio': request.form.get('data_plantio'),
            'tipo_solo': request.form.get('tipo_solo'),
            'frequencia_rega': request.form.get('frequencia_rega'),
            'exposicao_sol': request.form.get('exposicao_sol'),
        }

        # Validação dos campos obrigatórios
        campos_obrigatorios = ['tipo_documento', 'documento', 'nome_vegetal', 'data_plantio']
        for campo in campos_obrigatorios:
            if not dados[campo]:
                return jsonify({
                    'success': False,
                    'error': f'O campo {campo.replace("_", " ")} é obrigatório.'
                }), 400

        # Validação do documento
        documento_limpo = re.sub(r'[^0-9]', '', dados['documento'])
        if dados['tipo_documento'] == 'cpf':
            if not validar_cpf(documento_limpo):
                return jsonify({
                    'success': False,
                    'error': 'CPF inválido. Por favor, verifique o número informado.'
                }), 400
        else:  # cnpj
            if not validar_cnpj(documento_limpo):
                return jsonify({
                    'success': False,
                    'error': 'CNPJ inválido. Por favor, verifique o número informado.'
                }), 400

        # Gera código único
        codigo_unico = gerar_codigo_unico(documento_limpo)
        dados['codigo_unico'] = codigo_unico

        # Gera QR Code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(f'http://localhost:5000/visualizar/{codigo_unico}')
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Converte QR code para base64
        buffered = BytesIO()
        qr_image.save(buffered, format="PNG")
        qr_code_base64 = base64.b64encode(buffered.getvalue()).decode()

        return jsonify({
            'success': True,
            'info': dados,
            'qr_code': qr_code_base64
        })

    except Exception as e:
        print(f"Erro no cadastro: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ocorreu um erro ao processar o cadastro. Por favor, tente novamente.'
        }), 500

@app.route('/plantio/<codigo_unico>')
def visualizar_plantio(codigo_unico):
    try:
        # Simular a busca dos dados usando o código único
        # Em um ambiente real, isso viria do banco de dados
        dados = {
            'codigo_unico': codigo_unico,
            'tipo_documento': request.args.get('tipo_documento', ''),
            'documento': request.args.get('documento', ''),
            'nome_vegetal': request.args.get('nome_vegetal', ''),
            'data_plantio': request.args.get('data_plantio', ''),
            'tipo_solo': request.args.get('tipo_solo', ''),
            'frequencia_rega': request.args.get('frequencia_rega', ''),
            'exposicao_sol': request.args.get('exposicao_sol', ''),
            'tempo_colheita': request.args.get('tempo_colheita', ''),
            'observacoes': request.args.get('observacoes', ''),
            'data_cadastro': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        }
        return render_template('visualizar_plantio.html', info=dados)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/gerar-pdf', methods=['POST'])
def gerar_pdf():
    try:
        dados = request.json
        if not dados:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'})
            
        pdf_base64 = gerar_pdf_plantio(dados)
        return jsonify({'success': True, 'pdf': pdf_base64})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
