from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import io
import os

# Configuração inicial do Flask
app = Flask(__name__, static_folder='static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ---------------------------------------------------------------
# MODELOS DE DADOS
# ---------------------------------------------------------------

class Veiculo(db.Model):
    """Modelo para representar veículos"""
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, comment="Nome do veículo (ex: Fiat Toro)")
    marca = db.Column(db.String(50), comment="Marca do veículo")
    ano = db.Column(db.Integer, comment="Ano de fabricação")

class Abastecimento(db.Model):
    """Modelo para registrar abastecimentos"""
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime, nullable=False, comment="Data do abastecimento")
    odometro = db.Column(db.Float, nullable=False, comment="Quilometragem atual")
    litros = db.Column(db.Float, nullable=False, comment="Litros abastecidos")
    preco_litro = db.Column(db.Float, nullable=False, comment="Preço por litro")
    veiculo_id = db.Column(db.Integer, db.ForeignKey('veiculo.id'), nullable=False)
    
    # Relacionamento
    veiculo = db.relationship('Veiculo', backref='abastecimentos')
    
    @property
    def total(self):
        """Calcula o valor total do abastecimento"""
        return self.litros * self.preco_litro

class Receita(db.Model):
    """Modelo para registrar receitas"""
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime, nullable=False, comment="Data da receita")
    descricao = db.Column(db.String(200), nullable=False, comment="Descrição (ex: Frete SP-RJ)")
    valor = db.Column(db.Float, nullable=False, comment="Valor recebido")
    veiculo_id = db.Column(db.Integer, db.ForeignKey('veiculo.id'), nullable=False)
    
    # Relacionamento
    veiculo = db.relationship('Veiculo', backref='receitas')

# Cria tabelas no primeiro acesso
with app.app_context():
    db.create_all()

# ---------------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------------

def calcular_km_litro(abastecimentos):
    """Calcula km/litro comparando com abastecimento anterior"""
    for i in range(1, len(abastecimentos)):
        anterior = abastecimentos[i-1].odometro
        atual = abastecimentos[i].odometro
        litros = abastecimentos[i].litros
        
        if litros > 0:
            km_por_litro = round((atual - anterior) / litros, 2)
            setattr(abastecimentos[i], 'km_litro', km_por_litro)
    return abastecimentos

# ---------------------------------------------------------------
# ROTAS PRINCIPAIS
# ---------------------------------------------------------------

@app.route('/')
def index():
    """Página inicial com lista de abastecimentos"""
    veiculo_id = request.args.get('veiculo_id')
    veiculos = Veiculo.query.all()
    abastecimentos = Abastecimento.query.filter_by(veiculo_id=veiculo_id).order_by(Abastecimento.data.desc()).all() if veiculo_id else []
    abastecimentos = calcular_km_litro(abastecimentos)
    return render_template('index.html', 
                         abastecimentos=abastecimentos, 
                         veiculos=veiculos, 
                         veiculo_id=veiculo_id)

@app.route('/add', methods=['GET', 'POST'])
def add_abastecimento():
    """Adiciona novo abastecimento"""
    veiculos = Veiculo.query.all()
    if request.method == 'POST':
        novo = Abastecimento(
            data=datetime.strptime(request.form['data'], '%Y-%m-%d'),
            odometro=float(request.form['odometro']),
            litros=float(request.form['litros']),
            preco_litro=float(request.form['preco_litro']),
            veiculo_id=int(request.form['veiculo_id'])
        )
        db.session.add(novo)
        db.session.commit()
        return redirect(url_for('index', veiculo_id=novo.veiculo_id))
    return render_template('add_abastecimento.html', veiculos=veiculos)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_abastecimento(id):
    """Edita abastecimento existente"""
    abast = Abastecimento.query.get_or_404(id)
    veiculos = Veiculo.query.all()
    if request.method == 'POST':
        abast.data = datetime.strptime(request.form['data'], '%Y-%m-%d')
        abast.odometro = float(request.form['odometro'])
        abast.litros = float(request.form['litros'])
        abast.preco_litro = float(request.form['preco_litro'])
        abast.veiculo_id = int(request.form['veiculo_id'])
        db.session.commit()
        return redirect(url_for('index', veiculo_id=abast.veiculo_id))
    return render_template('edit_abastecimento.html', abast=abast, veiculos=veiculos)

@app.route('/delete/<int:id>')
def delete_abastecimento(id):
    """Remove abastecimento"""
    abast = Abastecimento.query.get_or_404(id)
    veiculo_id = abast.veiculo_id
    db.session.delete(abast)
    db.session.commit()
    return redirect(url_for('index', veiculo_id=veiculo_id))

@app.route('/veiculos', methods=['GET', 'POST'])
def veiculos():
    """Gerencia veículos cadastrados"""
    if request.method == 'POST':
        novo = Veiculo(
            nome=request.form['nome'],
            marca=request.form['marca'],
            ano=request.form['ano'])
        db.session.add(novo)
        db.session.commit()
        return redirect(url_for('veiculos'))
    veiculos = Veiculo.query.all()
    return render_template('veiculos.html', veiculos=veiculos)

@app.route('/receitas', methods=['GET', 'POST'])
def receitas():
    """Gerencia receitas"""
    veiculos = Veiculo.query.all()
    if request.method == 'POST':
        nova = Receita(
            data=datetime.strptime(request.form['data'], '%Y-%m-%d'),
            descricao=request.form['descricao'],
            valor=float(request.form['valor']),
            veiculo_id=int(request.form['veiculo_id'])
        )
        db.session.add(nova)
        db.session.commit()
        return redirect(url_for('relatorios', veiculo_id=nova.veiculo_id))
    return render_template('receitas.html', veiculos=veiculos)

@app.route('/delete_receita/<int:id>')
def delete_receita(id):
    """Remove receita"""
    receita = Receita.query.get_or_404(id)
    veiculo_id = receita.veiculo_id
    db.session.delete(receita)
    db.session.commit()
    return redirect(url_for('relatorios', veiculo_id=veiculo_id))

@app.route('/relatorios')
def relatorios():
    """Gera relatórios detalhados"""
    veiculo_id = request.args.get('veiculo_id')
    if not veiculo_id:
        return redirect(url_for('index'))
    
    veiculo = Veiculo.query.get_or_404(veiculo_id)
    abastecimentos = Abastecimento.query.filter_by(veiculo_id=veiculo_id).order_by(Abastecimento.data).all()
    abastecimentos = calcular_km_litro(abastecimentos)
    
    # Cálculo do saldo
    total_receitas = sum(r.valor for r in veiculo.receitas)
    total_combustivel = sum(a.total for a in abastecimentos)
    saldo = total_receitas - total_combustivel
    
    # Geração de gráfico
    if len(abastecimentos) > 1:
        datas = [a.data.strftime('%d/%m') for a in abastecimentos[1:]]
        km_litro = [a.km_litro for a in abastecimentos[1:]]
        
        plt.figure()
        plt.plot(datas, km_litro, marker='o')
        plt.title(f'Desempenho - {veiculo.nome}')
        plt.xlabel('Data')
        plt.ylabel('km/l')
        plt.grid(True)
        plt.savefig('static/img/grafico.png')
        plt.close()
    
    return render_template('relatorios.html',
                         veiculo=veiculo,
                         abastecimentos=abastecimentos,
                         saldo=saldo)

@app.route('/exportar/excel')
def exportar_excel():
    """Exporta dados para Excel"""
    veiculo_id = request.args.get('veiculo_id')
    abastecimentos = Abastecimento.query.filter_by(veiculo_id=veiculo_id).all()
    
    df = pd.DataFrame([{
        'Data': a.data.strftime('%d/%m/%Y'),
        'Odômetro': a.odometro,
        'Litros': a.litros,
        'Preço/L': a.preco_litro,
        'Total': a.total,
        'km/l': getattr(a, 'km_litro', None)
    } for a in abastecimentos])
    
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        download_name=f'relatorio_{veiculo_id}.xlsx'
    )

if __name__ == '__main__':
    os.makedirs('static/img', exist_ok=True)
    app.run(debug=True)