
## Testes Automatizados para o Sistema de Loja Online ##
Descrição
Este projeto utiliza o framework pytest para realizar testes unitários e de integração no sistema de loja online. Os testes verificam a funcionalidade das principais rotas e operações, como cadastro, login, manipulação de carrinho de compras, finalização de compras, e busca de produtos, etc.

Estrutura dos Testes
Os testes estão organizados em funções individuais, cada uma responsável por validar uma funcionalidade específica do sistema.

Testes Disponíveis

1. Importação e Exibição de Produtos
Funções:

test_index_successful_import
test_index_timeout
test_index_database_error
test_index_empty_products
Descrição: Verifica a funcionalidade da rota principal (/), que importa produtos de uma API externa e os exibe.

Cenários Testados:

Importação bem-sucedida de produtos.
Tratamento de timeout ao acessar a API externa.
Erros no banco de dados ao salvar produtos.
Exibição da página inicial com banco de dados vazio.

2. Cadastro de Usuário
Função: test_cadastro_usuario
Descrição: Verifica se o cadastro de um novo usuário funciona corretamente.
Cenário Testado:
Usuário envia os dados válidos no formulário.
Usuário é cadastrado com sucesso no banco de dados.
Redirecionamento ocorre e uma mensagem de sucesso é exibida.

3. Login
Funções:
test_login_sucesso
test_login_senha_incorreta
test_login_email_nao_encontrado
Descrição:
Testa o processo de login em diferentes cenários:
Sucesso no login.
Senha incorreta.
Email inexistente.
Cenários Testados:
Login válido redireciona para a página inicial.
Login inválido exibe mensagens de erro adequadas.

4. Carrinho de Compras
Funções:
test_adicionar_ao_carrinho
test_remover_do_carrinho
Descrição:
Verifica as operações de adicionar e remover produtos no carrinho.
Cenários Testados:
Produtos são adicionados ao carrinho corretamente.
Produtos são removidos parcialmente ou completamente.
Carrinho é manipulado corretamente na sessão do usuário.

5. Finalização de Compras
Funções:
test_finalizar_compras_sem_carrinho
test_finalizar_compras_sucesso
Descrição:
Testa a finalização de compras em diferentes condições.
Cenários Testados:
Tentativa de finalizar compra com carrinho vazio retorna erro.
Finalização de compra com dados válidos processa o pedido e cria registros no banco de dados.

6. Busca de Produtos
Função: test_buscar_produtos
Descrição: Verifica se a busca de produtos retorna resultados corretos.
Cenário Testado:
Termo de busca retorna os produtos esperados.


7. Logout
Funções:

test_logout
Descrição: Valida a funcionalidade de logout.

Logout bem-sucedido:
A sessão é limpa corretamente.
O usuário é redirecionado para a página inicial com uma mensagem de sucesso.

8. Dados do Usuário
Funções:

test_dados_pessoais
test_dados_bancarios
Descrição: Valida a manipulação e o salvamento de dados pessoais e bancários.

Cenários Testados:

Salvamento de dados pessoais:
Nome, endereço, cidade, estado e CEP são salvos na sessão com sucesso.
Mensagem de confirmação é exibida.
Salvamento de dados bancários:
Número do cartão, nome do titular, validade e CVV são validados e salvos.
Mensagem de confirmação é exibida.

9. Confirmação de Pedido
Funções:

test_confirmacao_pedido
Descrição: Valida o fluxo de confirmação de pedidos.

Cenários Testados:

Página de confirmação:
Pedido existente é recuperado do banco de dados.
Informações do pedido, como ID e total, são exibidas corretamente na página de confirmação.

10. Dados Bancários
Função:

test_dados_bancarios
Descrição: Valida a funcionalidade de salvamento de dados bancários.

11. test_adicionar_ao_carrinho
Objetivo: Garantir que produtos são adicionados ao carrinho corretamente.
Cenário: Simula a adição de um produto ao carrinho por meio de uma requisição POST à rota /adicionar_ao_carrinho.
Expectativas:
O sistema armazena o produto no carrinho com a quantidade especificada.
O carrinho é persistido na sessão do usuário.
O status de redirecionamento (302) é retornado.
Cobertura:
Adição de produtos inexistentes no carrinho.
Atualização da quantidade de produtos já presentes.

12. test_remover_do_carrinho
Objetivo: Verificar a funcionalidade de remoção de itens do carrinho.
Cenário: Simula a remoção parcial de um produto do carrinho por meio de uma requisição POST à rota /remover_do_carrinho.
Expectativas:
O sistema reduz a quantidade do produto especificado.
Remove o item completamente se a quantidade for zerada.
O status de redirecionamento (302) é retornado.
Cobertura:
Atualização correta da quantidade.
Exclusão de itens com quantidade igual a zero.


Cenários Testados:

Salvamento bem-sucedido:
Os campos de número do cartão, nome do titular, validade e CVV são validados e salvos na sessão.
O sistema retorna o status 302 (redirecionamento) e exibe a mensagem de sucesso: "Dados bancários salvos com sucesso!".

Requisitos para Executar os Testes
Python 3.7+
Dependências Instaladas:
pytest
Flask
Werkzeug
SQLAlchemy
Configuração do Ambiente:
Banco de dados configurado como sqlite:///:memory: para testes.
Como Executar os Testes
Instale as dependências:

pip install -r requirements.txt
Execute os testes:

pytest test_app.py
Para obter um relatório em HTML:

pytest --html=report.html
Organização das Fixtures
test_app:
Configura a aplicação Flask para os testes.
client:
Fornece um cliente de teste para realizar requisições.
test_db:
Configura o banco de dados para testes.
Cobertura dos Testes
Cadastro e Login:
Verifica fluxos de autenticação e mensagens de erro.
Carrinho de Compras:
Manipulação de produtos na sessão do usuário.
Finalização de Compras:
Confirmação de pedido e criação de itens no banco.
Busca de Produtos:
Validação de busca dinâmica por termos.
test_logout:
Valida se o logout limpa a sessão corretamente.
Garante que a mensagem "Você saiu da sessão com sucesso." é exibida.
Dados do Usuário
test_dados_pessoais:
Valida o salvamento de nome, endereço, cidade, estado e CEP.
test_dados_bancarios:
Garante que os dados bancários (cartão, nome do titular, validade e CVV) são validados e salvos corretamente.
Confirmação de Pedido
test_confirmacao_pedido:
Verifica se a página de confirmação exibe as informações do pedido corretamente.

Melhorias Futuras
Testes Adicionais:
Testar mensagens de erro mais detalhadas.
Cobrir cenários com permissões e usuários administrativos.
Automatização:
Integrar testes em pipelines CI/CD.
Relatórios:
Melhorar a apresentação dos resultados com ferramentas como pytest-html.