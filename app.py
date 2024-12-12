from flask import Flask, render_template, request, redirect, session, jsonify, url_for
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

# Criação da aplicação Flask
app = Flask(__name__)
app.secret_key = '123'  # Chave secreta para sessões

# Função para obter a conexão com o banco de dados SQLite
def get_db_connection():
    try:
        conn = sqlite3.connect('BancoDeDados.db')
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None

# Criando função para criação do banco de dados 
def create_table():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()

        # Criação da tabela de pizzas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cardapio_pizza( 
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_pizza TEXT NOT NULL,
            descricao TEXT NOT NULL, 
            preco REAL NOT NULL
            )
        ''')

        # Criação da tabela de sobremesas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cardapio_sobremesa( 
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_sobremesa TEXT NOT NULL,
            preco REAL NOT NULL
            )
        ''')

        # Criação da tabela de bebidas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cardapio_bebidas( 
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_bebida TEXT NOT NULL,
            preco REAL NOT NULL 
            )
        ''')

        # Criação da tabela de contas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conta( 
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            idade INTEGER NOT NULL,
            telefone TEXT NOT NULL,
            senha TEXT NOT NULL
            )
        ''')

        # Criação da tabela de carrinho
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS carrinho( 
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,  -- 'pizza', 'sobremesa' ou 'bebida'
            nome TEXT NOT NULL,
            preco REAL NOT NULL
            )
        ''')

        # Criação da tabela de pedidos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pedidos( 
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total REAL NOT NULL,
            data TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES conta (id)
            )
        ''')

        # Inserir dados iniciais se as tabelas estiverem vazias
        cursor.execute("SELECT COUNT(*) FROM cardapio_pizza")
        if cursor.fetchone()[0] == 0:
            cursor.executemany('''
            INSERT INTO cardapio_pizza (nome_pizza, descricao, preco) VALUES (?, ?, ?)
            ''', [
            ("Pizza Marguerita", "molho de tomate, queijo, manjericão", 30.00),
            ("Pizza Calabresa", "molho de tomate, calabresa, queijo", 35.00),
            ("Pizza Quatro Queijos", "molho de tomate, queijo mussarela, queijo parmesão, queijo cheddar", 40.00),
            ("Pizza Pepperoni", "molho de tomate, pepperoni, queijo", 45.00),
        ])
            
        cursor.execute("SELECT COUNT(*) FROM cardapio_sobremesa")
        if cursor.fetchone()[0] == 0:
            cursor.executemany('''
            INSERT INTO cardapio_sobremesa (nome_sobremesa, preco) VALUES (?, ?)
            ''', [
            ("Pudim", 8.00),
            ("Torta de Limão", 9.00),
            ("Quindim", 6.00),
            ("Pavê", 10.00),
        ])
            
        cursor.execute("SELECT COUNT(*) FROM cardapio_bebidas")
        if cursor.fetchone()[0] == 0:
            cursor.executemany('''
            INSERT INTO cardapio_bebidas (nome_bebida, preco) VALUES (?, ?)
            ''', [
            ("Água", 3.00),
            ("Refri Lata", 6.00),
            ("Refri Vidro", 10.00),
            ("Jarra de Suco", 10.00),
        ])

        conn.commit()  # Salva as alterações
        conn.close()   # Fecha a conexão

@app.route('/')
def home():
    return render_template('index.html')

# Rota para registro de conta
@app.route('/cadastrar', methods=['GET', 'POST'])
def registrar():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        idade = request.form['idade']
        telefone = request.form['telefone']
        senha = request.form['senha']
        
        hashed_senha = generate_password_hash(senha)  # Hash da senha
        
        conn = get_db_connection()
        if conn:
            try:
                conn.execute('INSERT INTO conta (nome, email, idade, telefone, senha) VALUES (?, ?, ?, ?, ?)',
                             (nome, email, idade, telefone, hashed_senha))
                conn.commit()
                return redirect('/login')  # Redireciona para a página de login após o registro
            except sqlite3.IntegrityError:
                return "Email já cadastrado. Tente outro."
            finally:
                conn.close()

    return render_template('cadastrar.html')

# Rota para login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        
        conn = get_db_connection()
        if conn:
            try:
                user = conn.execute('SELECT * FROM conta WHERE email = ?', (email,)).fetchone()
                if user and check_password_hash(user['senha'], senha): 
                    user_id = user['id']
                    session['user_id'] = user_id
                    return redirect(url_for('index'))
                return redirect('/')  # Redireciona para a página inicial após o login
            except sqlite3.Error as e:
                return "Email ou senha incorretos."
            finally:
                conn.close()  # Fecha a conexão
        else:
            return "Erro ao conectar ao banco de dados."
        
    return render_template('login.html')

def usuario_logado():
    return 'user_id' in session

def verificar_login():
    if not usuario_logado():
        return redirect(url_for('login'))

# Rota para adicionar itens ao carrinho
@app.route('/adicionar_ao_carrinho', methods=['POST'])
def adicionar_ao_carrinho():
    data = request.get_json()
    nome = data.get('nome')
    preco = data.get('preco')

    if nome and preco:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Inserir o item no carrinho
            cursor.execute('INSERT INTO carrinho (tipo, nome, preco) VALUES (?, ?, ?)', ('custom', nome, preco))
            conn.commit()
            return jsonify({'status': 'success', 'message': f'{nome} adicionado ao carrinho!'})
        except sqlite3.Error as e:
            return jsonify({'status': 'error', 'message': f'Erro no banco de dados: {str(e)}'}), 500
        finally:
            conn.close()
    else:
        return jsonify({'status': 'error', 'message': 'Dados inválidos!'}), 400

# Rota para finalizar a compra
@app.route('/compra', methods=['POST'])
def compra():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Obter todos os itens do carrinho
        itens_carrinho = cursor.execute('SELECT * FROM carrinho').fetchall()

        if not itens_carrinho:
            return jsonify({'status': 'error', 'message': 'Carrinho vazio!'}), 400

        # Calcular o total da compra
        total = sum(item['preco'] for item in itens_carrinho)

        # Obter o ID do usuário da sessão
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'status': 'error', 'message': 'Usuário não autenticado!'}), 401

        # Inserir o pedido na tabela de pedidos
        cursor.execute('INSERT INTO pedidos (user_id, total, data) VALUES (?, ?, datetime("now"))', (user_id, total))
        conn.commit()

        # Limpar o carrinho após a compra
        cursor.execute('DELETE FROM carrinho')
        conn.commit()

        return jsonify({'status': 'success', 'message': 'Compra finalizada com sucesso!', 'total': total}) 
    except sqlite3.Error as e:
        return jsonify({'status': 'error', 'message': f'Erro no banco de dados: {str(e)}'}), 500
    finally:
        conn.close()

# Rota para exibir o carrinho
@app.route('/carrinho', methods=['GET'])
def carrinho():
    conn = get_db_connection()
    cursor = conn.cursor()
    itens_carrinho = cursor.execute('SELECT * FROM carrinho').fetchall()

    # Obter detalhes dos itens
    detalhes_itens = []
    for item in itens_carrinho:
        detalhes_itens.append({'nome': item['nome'], 'tipo': item['tipo'], 'preco': item['preco']})

    conn.close()
    return render_template('carrinho.html', itens=detalhes_itens)

@app.route('/finalizar_compra', methods=['POST'])
def finalizar_compra():
    verificar_login()

    # Código para finalizar a compra

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT nome, preco, tipo FROM carrinho')
        itens_carrinho = cursor.fetchall()

        if not itens_carrinho:
            return redirect(url_for('carrinho'))

        total_compra = sum(item['preco'] for item in itens_carrinho)

        cursor.execute(
            'INSERT INTO pedidos (user_id, total, data) VALUES (?, ?, datetime("now"))',
            (user_id, total_compra) # type: ignore
        )

        cursor.execute('DELETE FROM carrinho')
        conn.commit()

        return redirect(url_for('pagina_confirmacao'))

    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': f'Erro no banco de dados: {str(e)}'}), 500

    finally:
        conn.close()


@app.route('/confirmacao')
def pagina_confirmacao():
    return render_template('confirmacao.html')


if __name__ == '__main__':
    create_table()  # Cria as tabelas no banco de dados
    app.run(debug=True)