from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import pymysql
from sqlalchemy.exc import SQLAlchemyError
import os

app = Flask(__name__)

app.secret_key = b'\xdc\xc1K\x1a\xf4\x8e+|\t\x8a\xb7l\xb1w\xaf\x82\xdd\x07wa\xb6\x0cH\xf8'


 #Verifica se está rodando no Heroku (variável de ambiente DATABASE_URL)
if os.getenv("DATABASE_URL"):
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("MSSQL_TCP_URL")  # URL do banco configurada no Heroku
else:
    # Configuração local
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:12345@127.0.0.1:3306/ecommerce'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Desativa rastreamento de modificações

# Instância do SQLAlchemy para integração com o Flask
db = SQLAlchemy(app)

# Função para verificar a conexão com o banco de dados utilizando PyMySQL
def verificar_conexao_pymysql():
    try:
        connection = pymysql.connect(
            host='host.docker.internal',  # Substitua se necessário
            user='root',
            password='12345',
            database='ecommerce',
            port=3306
        )
        print("Conexão com o banco de dados (PyMySQL) bem-sucedida!")
        connection.close()
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados (PyMySQL): {e}")


# Cadastro de Usuário
class Usuario(db.Model):
    email = db.Column(db.String(120), primary_key=True, unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=False)
    senha = db.Column(db.String(200), nullable=False)

# Produto
class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    preco = db.Column(db.Float, nullable=False)
    imagem_url = db.Column(db.String(200), nullable=True)

# Cliente
class Cliente(db.Model):
    id = db.Column(db.String(120), primary_key=True)  # Usando o e-mail como ID
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)

# Pedido
class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.String(120), db.ForeignKey('cliente.id'), nullable=False)
    total = db.Column(db.Float, nullable=False)
    data_pedido = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

    cliente = db.relationship('Cliente', backref=db.backref('pedidos', lazy=True))

# Item de Pedido
class ItemPedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    preco = db.Column(db.Float, nullable=False)

with app.app_context():
    db.create_all()

# Decorator para exigir login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Verificar se o usuário está logado
            if 'usuario_id' not in session:
                flash('Você precisa estar logado para acessar essa página.', 'error')
                return redirect(url_for('login'))
            
            # Executa a função decorada
            return f(*args, **kwargs)
        
        except KeyError as e:
            # Erro inesperado relacionado à sessão
            print(f"Erro na verificação de login: {e}")
            flash("Erro ao verificar o status de login. Tente novamente mais tarde.", 'error')
            return redirect(url_for('login'))
        
        except Exception as e:
            # Captura erros gerais
            print(f"Erro inesperado no decorador login_required: {e}")
            flash("Erro inesperado ao verificar o login. Entre em contato com o suporte.", 'error')
            return redirect(url_for('login'))

    return decorated_function


@app.route('/')
def index():
    try:
        # Faz a requisição à API externa
        response = requests.get('https://fakestoreapi.com/products', timeout=10)
        response.raise_for_status()  # Lança uma exceção se o status code não for 200

        produtos_parceiro = response.json()

        for produto in produtos_parceiro:
            try:
                # Verifique se o produto já existe no banco de dados para evitar duplicados
                if not Produto.query.filter_by(nome=produto['title']).first():
                    novo_produto = Produto(
                        nome=produto['title'],
                        descricao=produto['description'],
                        preco=float(produto['price']),
                        imagem_url=produto['image']
                    )
                    db.session.add(novo_produto)
                    print(f"Produto '{produto['title']}' adicionado com sucesso.")
            except SQLAlchemyError as db_err:
                print(f"Erro ao salvar produto no banco de dados: {db_err}")
                flash(f"Erro ao salvar o produto '{produto['title']}' no banco de dados.", 'error')
            except Exception as e:
                print(f"Erro inesperado ao processar o produto '{produto['title']}': {e}")
                flash(f"Erro inesperado ao processar o produto '{produto['title']}'.", 'error')

        # Comita as mudanças no banco de dados
        try:
            db.session.commit()
        except SQLAlchemyError as db_commit_err:
            print(f"Erro ao salvar mudanças no banco de dados: {db_commit_err}")
            flash("Erro ao salvar as alterações no banco de dados.", 'error')
    
    except requests.exceptions.Timeout:
        print("Erro: A requisição à API demorou demais e foi cancelada.")
        flash("A requisição à API demorou demais e foi cancelada. Tente novamente mais tarde.", 'error')
    except requests.exceptions.RequestException as req_err:
        print(f"Erro na requisição: {req_err}")
        flash(f"Erro na requisição à API: {req_err}", 'error')
    except Exception as e:
        print(f"Erro inesperado ao importar produtos: {e}")
        flash(f"Ocorreu um erro inesperado ao importar os produtos: {str(e)}", 'error')

    try:
        # Após importar os produtos da API, buscar todos os produtos (incluindo os do banco de dados)
        produtos = Produto.query.all()  # Consulta todos os produtos
    except SQLAlchemyError as db_query_err:
        print(f"Erro ao consultar produtos no banco de dados: {db_query_err}")
        flash("Erro ao carregar os produtos do banco de dados.", 'error')
        produtos = []
    except Exception as e:
        print(f"Erro inesperado ao carregar os produtos: {e}")
        flash("Erro inesperado ao carregar os produtos.", 'error')
        produtos = []

    return render_template('index.html', produtos=produtos)


@app.route('/adicionar', methods=['GET', 'POST']) # função do sistema adicionar mais produtos na tela e banco
@login_required
def adicionar_produto():
    if request.method == 'POST':
        nome = request.form['nome']
        preco = round(float(request.form['preco']), 2)
        descricao = request.form['descricao']
        estoque = int(request.form['estoque'])

        novo_produto = Produto(nome=nome, preco=preco, descricao=descricao, estoque=estoque)
        print(f"Produto para adicionar: {novo_produto}")  # Log para depuração
        db.session.add(novo_produto)
        db.session.commit()

        #flash('Produto adicionado com sucesso!')
        return redirect(url_for('index'))

    return render_template('adicionar_produtos.html')

@app.route('/deletar_produto/<int:produto_id>', methods=['POST']) # função do sistema adicionar mais produtos na tela e banco
@login_required
def deletar_produto(produto_id):
    produto = Produto.query.get(produto_id)
    
    if not produto:
        flash('Produto não encontrado.')
        return redirect(url_for('index'))
    
    db.session.delete(produto)
    db.session.commit()
    flash('Produto deletado com sucesso.')
    
    return redirect(url_for('index'))

@app.route('/editar_produto/<int:produto_id>', methods=['GET', 'POST']) # função do sistema adicionar mais produtos na tela e banco
@login_required
def editar_produto(produto_id):
    produto = Produto.query.get_or_404(produto_id)
    
    if request.method == 'POST':
        produto.nome = request.form['nome']
        produto.preco = float(request.form['preco'])
        produto.descricao = request.form['descricao']
        produto.estoque = int(request.form['estoque'])
        
        db.session.commit()
        
        flash('Produto atualizado com sucesso!')
        return redirect(url_for('index'))

    return render_template('editar_produto.html', produto=produto)





@app.route('/adicionar_ao_carrinho', methods=['POST'])
@login_required
def adicionar_ao_carrinho():
    try:
        # Obter dados do formulário
        produto_id = request.form.get('produto_id')
        quantidade = request.form.get('quantidade', 1)

        # Validação dos dados do formulário
        if not produto_id or not quantidade:
            flash("Produto ou quantidade inválidos.", 'error')
            return redirect(url_for('index'))
        
        try:
            quantidade = int(quantidade)
        except ValueError:
            flash("Quantidade deve ser um número válido.", 'error')
            return redirect(url_for('index'))

        # Buscar produto no banco de dados
        produto = Produto.query.get(produto_id)
        if not produto:
            flash("Produto não encontrado.", 'error')
            return redirect(url_for('index'))

        # Inicializar o carrinho na sessão, se não existir
        if 'carrinho' not in session:
            session['carrinho'] = []

        carrinho = session['carrinho']

        # Verificar se o produto já está no carrinho
        for item in carrinho:
            if item['id'] == produto.id:
                # Se estiver, atualize a quantidade
                item['quantidade'] += quantidade
                flash(f"A quantidade do produto '{produto.nome}' foi atualizada no carrinho.", 'success')
                break
        else:
            # Se não estiver, adicione o produto com a quantidade
            carrinho.append({
                'id': produto.id,
                'nome': produto.nome,
                'preco': float(produto.preco),
                'quantidade': quantidade
            })
            flash(f"O produto '{produto.nome}' foi adicionado ao carrinho.", 'success')

        # Atualizar a sessão
        session['carrinho'] = carrinho
        session.modified = True  # Marca a sessão como modificada

    except KeyError as e:
        print(f"Erro ao acessar dados do formulário: {e}")
        flash("Erro ao processar o pedido. Por favor, tente novamente.", 'error')
    except Exception as e:
        print(f"Erro inesperado ao adicionar ao carrinho: {e}")
        flash("Erro inesperado ao adicionar ao carrinho. Por favor, tente novamente mais tarde.", 'error')

    return redirect(url_for('carrinho'))








@app.route('/remover_do_carrinho', methods=['POST'])
@login_required
def remover_do_carrinho():
    try:
        # Obter o produto_id e a quantidade a remover do formulário
        produto_id = request.form.get('produto_id')
        quantidade_a_remover = request.form.get('quantidade', 1)

        # Validação dos dados do formulário
        if not produto_id or not quantidade_a_remover:
            flash("Produto ou quantidade inválidos.", 'error')
            return redirect(url_for('carrinho'))
        
        try:
            produto_id = int(produto_id)
            quantidade_a_remover = int(quantidade_a_remover)
        except ValueError:
            flash("ID do produto ou quantidade inválidos.", 'error')
            return redirect(url_for('carrinho'))

        if 'carrinho' not in session:
            flash("Carrinho está vazio.", 'error')
            return redirect(url_for('carrinho'))

        carrinho = session['carrinho']

        # Verificar se o produto existe no carrinho
        for item in carrinho:
            if item['id'] == produto_id:
                if item['quantidade'] > quantidade_a_remover:
                    item['quantidade'] -= quantidade_a_remover
                    flash(f"A quantidade do produto '{item['nome']}' foi atualizada.", 'success')
                else:
                    carrinho.remove(item)
                    flash(f"O produto '{item['nome']}' foi removido do carrinho.", 'success')
                break
        else:
            flash("Produto não encontrado no carrinho.", 'error')

        # Atualizar o carrinho na sessão
        session['carrinho'] = carrinho
        session.modified = True

    except KeyError as e:
        print(f"Erro ao acessar dados do formulário: {e}")
        flash("Erro ao processar o pedido. Por favor, tente novamente.", 'error')
    except Exception as e:
        print(f"Erro inesperado ao remover do carrinho: {e}")
        flash("Erro inesperado ao remover do carrinho. Por favor, tente novamente mais tarde.", 'error')

    return redirect(url_for('carrinho'))





@app.route('/finalizar_compras', methods=['POST'])
@login_required
def finalizar_compras():
    try:
        # Receber os dados bancários diretamente do formulário
        numero_cartao = request.form.get('numero_cartao')
        nome_titular = request.form.get('nome_titular')
        validade = request.form.get('validade')
        cvv = request.form.get('cvv')

        # Print para depuração
        print(f"Recebido - Cartão: {numero_cartao}, Titular: {nome_titular}, Validade: {validade}, CVV: {cvv}")

        # Validar os dados bancários
        if not numero_cartao or not nome_titular or not validade or not cvv:
            flash('Por favor, preencha todos os dados bancários.', 'error')
            return redirect(url_for('dados_bancarios'))

        # Salvar os dados bancários na sessão
        session['dados_bancarios'] = {
            'numero_cartao': numero_cartao,
            'nome_titular': nome_titular,
            'validade': validade,
            'cvv': cvv
        }
        session.modified = True

        # Verificar se o carrinho está vazio
        carrinho = session.get('carrinho', [])
        if not carrinho:
            flash('Seu carrinho está vazio.', 'error')
            return redirect(url_for('carrinho'))

        # Verificar se o cliente existe
        cliente_id = session.get('usuario_id')
        cliente = Cliente.query.filter_by(email=cliente_id).first()
        if not cliente:
            flash('Cliente não encontrado.', 'error')
            print("Erro: Cliente não encontrado.")
            return redirect(url_for('index'))

        # Corrigir o cálculo do total
        total = sum(item['preco'] * item['quantidade'] for item in carrinho)

        # Criar um novo pedido
        try:
            novo_pedido = Pedido(cliente_id=cliente.id, total=total)
            db.session.add(novo_pedido)
            db.session.commit()
        except Exception as e:
            print(f"Erro ao criar pedido: {e}")
            flash("Erro ao processar seu pedido. Tente novamente.", 'error')
            return redirect(url_for('carrinho'))

        # Adicionar itens ao pedido
        try:
            for item in carrinho:
                novo_item = ItemPedido(
                    pedido_id=novo_pedido.id,
                    produto_id=item['id'],
                    quantidade=item['quantidade'],
                    preco=item['preco']
                )
                db.session.add(novo_item)
            db.session.commit()
        except Exception as e:
            print(f"Erro ao adicionar itens ao pedido: {e}")
            flash("Erro ao adicionar itens ao seu pedido. Tente novamente.", 'error')
            return redirect(url_for('carrinho'))

        # Limpar o carrinho e os dados bancários da sessão
        session.pop('carrinho', None)
        session.pop('dados_bancarios', None)
        session.modified = True

        flash('Compra finalizada com sucesso!', 'success')
        return redirect(url_for('confirmacao_pedido', pedido_id=novo_pedido.id))

    except KeyError as e:
        print(f"Erro ao acessar dados na sessão: {e}")
        flash("Erro ao processar a compra. Tente novamente.", 'error')
        return redirect(url_for('carrinho'))
    except Exception as e:
        print(f"Erro inesperado ao finalizar compras: {e}")
        flash("Erro inesperado ao finalizar a compra. Entre em contato com o suporte.", 'error')
        return redirect(url_for('carrinho'))







@app.route('/confirmacao_pedido/<int:pedido_id>')
@login_required
def confirmacao_pedido(pedido_id):
    try:
        # Tenta buscar o pedido no banco de dados
        pedido = Pedido.query.get_or_404(pedido_id)
        nome_titular = request.args.get('nome_titular', 'Desconhecido')  # Default para 'Desconhecido' se não fornecido
        return render_template('finalizar_compras.html', pedido=pedido, nome_titular=nome_titular)
    except SQLAlchemyError as db_err:
        print(f"Erro ao buscar pedido no banco de dados: {db_err}")
        flash("Erro ao carregar a confirmação do pedido. Tente novamente mais tarde.", 'error')
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Erro inesperado ao carregar a página de confirmação: {e}")
        flash("Erro inesperado ao carregar a confirmação do pedido. Entre em contato com o suporte.", 'error')
        return redirect(url_for('index'))




@app.route('/dados_bancarios', methods=['GET', 'POST'])
@login_required
def dados_bancarios():
    try:
        if request.method == 'POST':
            # Coletar os dados bancários do formulário
            numero_cartao = request.form.get('numero_cartao')
            nome_titular = request.form.get('nome_titular')
            validade = request.form.get('validade')
            cvv = request.form.get('cvv')

            # Debugging: Verifique se os dados estão sendo recebidos corretamente
            print(f"Recebido - Cartão: {numero_cartao}, Titular: {nome_titular}, Validade: {validade}, CVV: {cvv}")

            # Validar se todos os campos estão preenchidos
            if not numero_cartao or not nome_titular or not validade or not cvv:
                flash("Por favor, preencha todos os dados bancários.", 'error')
                return redirect(url_for('dados_bancarios'))

            # Salvar os dados bancários na sessão
            session['dados_bancarios'] = {
                'numero_cartao': numero_cartao,
                'nome_titular': nome_titular,
                'validade': validade,
                'cvv': cvv
            }
            session.modified = True

            # Printar os dados bancários para verificação
            print("Dados bancários salvos na sessão:", session['dados_bancarios'])

            flash("Dados bancários salvos com sucesso!", 'success')
            return redirect(url_for('finalizar_compras'))
    except KeyError as e:
        print(f"Erro ao acessar dados do formulário: {e}")
        flash("Erro ao processar os dados bancários. Tente novamente.", 'error')
        return redirect(url_for('dados_bancarios'))
    except Exception as e:
        print(f"Erro inesperado ao salvar dados bancários: {e}")
        flash("Erro inesperado ao salvar os dados bancários. Entre em contato com o suporte.", 'error')
        return redirect(url_for('dados_bancarios'))

    return render_template('dados_bancarios.html')




@app.route('/buscar_produtos', methods=['GET'])
def buscar_produtos():
    try:
        # Obter a consulta do usuário
        query = request.args.get('query', '').strip()
        
        if query:  # Se houver uma consulta
            produtos = Produto.query.filter(Produto.nome.ilike(f'%{query}%')).all()
            if not produtos:
                flash(f"Nenhum produto encontrado para a consulta '{query}'.", 'info')
        else:  # Se o campo de busca estiver vazio, retorne todos os produtos
            produtos = Produto.query.all()

        return render_template('index.html', produtos=produtos)

    except SQLAlchemyError as db_err:
        print(f"Erro ao buscar produtos no banco de dados: {db_err}")
        flash("Erro ao buscar produtos. Tente novamente mais tarde.", 'error')
        return redirect(url_for('index'))

    except Exception as e:
        print(f"Erro inesperado ao buscar produtos: {e}")
        flash("Erro inesperado ao buscar produtos. Entre em contato com o suporte.", 'error')
        return redirect(url_for('index'))



@app.route('/dados_pessoais', methods=['GET', 'POST'])
def dados_pessoais():
    try:
        if request.method == 'POST':
            print("Dados recebidos:", request.form)  # Debugging

            nome = request.form.get('nome')
            endereco = request.form.get('endereco')
            cidade = request.form.get('cidade')
            estado = request.form.get('estado')
            cep = request.form.get('cep')

            print(f"Nome: {nome}, Endereço: {endereco}, Cidade: {cidade}, Estado: {estado}, CEP: {cep}")

            # Validação dos campos
            if not nome or not endereco or not cidade or not estado or not cep:
                flash("Por favor, preencha todos os campos obrigatórios.", 'error')
                return redirect(url_for('dados_pessoais'))

            # Processar e salvar os dados na sessão
            session['nome'] = nome
            session['endereco'] = endereco
            session['cidade'] = cidade
            session['estado'] = estado
            session['cep'] = cep
            session.modified = True

            flash("Dados pessoais salvos com sucesso!", 'success')

            # Redirecionar para a página de dados bancários
            return redirect(url_for('dados_bancarios'))

    except KeyError as e:
        print(f"Erro ao acessar dados do formulário: {e}")
        flash("Erro ao processar os dados pessoais. Tente novamente.", 'error')
    except Exception as e:
        print(f"Erro inesperado ao salvar dados pessoais: {e}")
        flash("Erro inesperado ao salvar dados pessoais. Entre em contato com o suporte.", 'error')

    return render_template('dados_pessoais.html')




@app.route('/carrinho')
@login_required
def carrinho():
    try:
        # Obter o carrinho da sessão
        carrinho = session.get('carrinho', [])

        if not isinstance(carrinho, list):
            flash("Erro no formato dos dados do carrinho. Carrinho reiniciado.", 'error')
            carrinho = []
            session['carrinho'] = carrinho
            session.modified = True

        if not carrinho:
            flash("Seu carrinho está vazio.", 'info')

        # Debugging: Printar itens do carrinho e preços
        for item in carrinho:
            try:
                print(f"Produto: {item['nome']}, Quantidade: {item['quantidade']}, Preço unitário: {item['preco']}, Subtotal: {item['preco'] * item['quantidade']}")
            except KeyError as e:
                print(f"Erro ao acessar dados do item no carrinho: {e}")
                flash("Erro ao acessar dados de um produto no carrinho. Verifique os itens adicionados.", 'error')
        
        # Calcula o total considerando a quantidade de cada item
        total = sum(item.get('preco', 0) * item.get('quantidade', 0) for item in carrinho)

        print(f"Total do carrinho: R$ {total:.2f}")

        return render_template('carrinho.html', carrinho=carrinho, total=total)

    except KeyError as e:
        print(f"Erro ao acessar dados do carrinho: {e}")
        flash("Erro ao acessar os dados do carrinho. Tente novamente.", 'error')
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Erro inesperado ao carregar o carrinho: {e}")
        flash("Erro inesperado ao carregar o carrinho. Entre em contato com o suporte.", 'error')
        return redirect(url_for('index'))





@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    try:
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            senha = request.form.get('senha', '').strip()

            # Validação dos campos
            if not username or not email or not senha:
                flash("Todos os campos são obrigatórios.", 'error')
                return redirect(url_for('cadastro'))

            if Usuario.query.filter_by(email=email).first():
                flash("Email já cadastrado.", 'error')
                return redirect(url_for('cadastro'))

            # Criar novo usuário e cliente
            senha_hash = generate_password_hash(senha)
            novo_usuario = Usuario(username=username, email=email, senha=senha_hash)
            novo_cliente = Cliente(id=email, nome=username, email=email)

            try:
                db.session.add(novo_usuario)
                db.session.add(novo_cliente)
                db.session.commit()
            except Exception as db_err:
                print(f"Erro ao salvar no banco de dados: {db_err}")
                db.session.rollback()
                flash("Erro ao realizar o cadastro. Tente novamente.", 'error')
                return redirect(url_for('cadastro'))

            # Adicionar informações à sessão
            session['usuario_id'] = novo_usuario.email
            session['username'] = novo_usuario.username

            flash("Cadastro realizado com sucesso!", 'success')
            return redirect(url_for('login'))
    except Exception as e:
        print(f"Erro inesperado no cadastro: {e}")
        flash("Erro inesperado ao realizar o cadastro. Entre em contato com o suporte.", 'error')
        return redirect(url_for('cadastro'))

    return render_template('cadastro.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if request.method == 'POST':
            email = request.form.get('email', '').strip()
            senha = request.form.get('senha', '').strip()

            # Validação dos campos
            if not email or not senha:
                flash("Email e senha são obrigatórios.", 'error')
                return redirect(url_for('login'))

            usuario = Usuario.query.filter_by(email=email).first()
            if usuario:
                if check_password_hash(usuario.senha, senha):
                    # Adicionar informações à sessão
                    session['usuario_id'] = usuario.email
                    session['username'] = usuario.username
                    session['nome_titular'] = usuario.username

                    flash("Login realizado com sucesso!", 'success')
                    return redirect(url_for('index'))
                else:
                    flash("Senha incorreta.", 'error')
            else:
                flash("Email não encontrado.", 'error')

            return redirect(url_for('login'))
    except Exception as e:
        print(f"Erro inesperado no login: {e}")
        flash("Erro inesperado ao realizar o login. Entre em contato com o suporte.", 'error')
        return redirect(url_for('login'))

    return render_template('login.html')




@app.route('/logout', methods=['POST'])
def logout():
    try:
        session.clear()  # Limpa todos os dados da sessão
        flash("Você saiu da sessão com sucesso.", 'success')
    except Exception as e:
        print(f"Erro ao realizar logout: {e}")
        flash("Erro ao realizar o logout. Entre em contato com o suporte.", 'error')
    return redirect(url_for('index'))  # Redireciona para a página inicial



@app.route('/importar_produtos_parceiro')  # função do sistema
def importar_produtos_parceiro():
    try:
        print("Fazendo a requisição para a API...")
        response = requests.get('https://fakestoreapi.com/products', timeout=10)  # Define um timeout para a requisição
        print(f"Status Code: {response.status_code}")
        response.raise_for_status()  # Lança uma exceção se o status code não for 200

        produtos_parceiro = response.json()
        print(f"Produtos recebidos: {produtos_parceiro}")

        # Itera sobre os produtos e verifica se já existem no banco
        for produto in produtos_parceiro:
            try:
                print(f"Verificando se o produto '{produto['title']}' já existe...")
                if not Produto.query.filter_by(nome=produto['title']).first():
                    novo_produto = Produto(
                        nome=produto['title'],
                        descricao=produto['description'],
                        preco=float(produto['price']),
                        imagem_url=produto['image']
                    )
                    db.session.add(novo_produto)
                    print(f"Produto '{produto['title']}' adicionado com sucesso.")
            except Exception as e:
                print(f"Erro ao processar o produto '{produto['title']}': {e}")
                flash(f"Erro ao processar o produto '{produto['title']}': {e}", 'error')

        # Comita as mudanças no banco de dados
        try:
            db.session.commit()
            flash('Produtos importados com sucesso!', 'success')
        except Exception as db_err:
            print(f"Erro ao salvar produtos no banco de dados: {db_err}")
            db.session.rollback()  # Reverte alterações em caso de erro
            flash("Erro ao salvar produtos no banco de dados. Tente novamente.", 'error')

    except requests.exceptions.Timeout:
        print("A requisição para a API expirou.")
        flash("A requisição para a API demorou muito tempo e foi interrompida. Tente novamente.", 'error')
    except requests.exceptions.RequestException as req_err:
        print(f"Erro na requisição à API: {req_err}")
        flash(f"Erro ao acessar os dados da API: {req_err}", 'error')
    except Exception as e:
        print(f"Erro inesperado ao importar produtos: {e}")
        flash(f"Ocorreu um erro inesperado ao importar os produtos. Entre em contato com o suporte.", 'error')

    return redirect(url_for('index'))




if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)

