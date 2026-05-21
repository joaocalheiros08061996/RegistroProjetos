# Manual do Usuário - Registro de Projetos

Versão: 1.0  
Data: 19/05/2026

## 1. Finalidade do sistema

O Registro de Projetos é uma aplicação para acompanhar projetos, tarefas, atividades de rotina e indicadores de desempenho. O objetivo é centralizar o planejamento, registrar o tempo real de execução, organizar responsáveis e facilitar a análise dos resultados por meio de gráficos.

O sistema possui três módulos principais:

- Registro de Projetos: cadastro e acompanhamento de projetos, tarefas, prazos, custos e tempos registrados.
- Atividades de Rotina: apontamento de atividades diárias que não pertencem necessariamente a um projeto.
- Dashboard: consulta de gráficos e indicadores de desempenho.

Este manual foi escrito para usuários finais. Ele explica como usar a aplicação no dia a dia, o que preencher, como interpretar as telas e quais cuidados tomar para manter os dados confiáveis.

## 2. Antes de começar

Para usar o sistema, você precisa de:

- Um link de acesso à aplicação.
- Uma conta de usuário com e-mail e senha.
- Um navegador atualizado.
- Orientação interna sobre quais projetos, tarefas e atividades devem ser registrados.

Use sempre a conta correta. Os dados de projetos e atividades são vinculados ao usuário autenticado. Se você entrar com outra conta, poderá não visualizar os mesmos registros.

## 3. Acesso, login e saída

Abra o link da aplicação no navegador. Em ambiente local, o endereço padrão é:

`http://127.0.0.1:8000/app`

Em ambiente online, use o link fornecido pela equipe responsável pelo sistema.

Para entrar:

1. Acesse a tela de login.
2. Informe seu e-mail.
3. Informe sua senha.
4. Clique em `Entrar`.

Caso ainda não tenha conta:

1. Clique em `Criar conta`.
2. Informe um e-mail válido.
3. Informe uma senha com pelo menos 6 caracteres.
4. Clique em `Cadastrar`.
5. Se necessário, volte para a tela de login e entre com a conta criada.

Para sair do sistema, clique em `Sair`. Em computadores compartilhados, sempre saia ao terminar o uso.

Faça:

- Use seu próprio usuário.
- Digite o e-mail com atenção.
- Avise o responsável pelo sistema se não conseguir acessar.

Não faça:

- Não compartilhe sua senha.
- Não use a conta de outra pessoa.
- Não deixe a sessão aberta em computadores compartilhados.

## 4. Tela de escolha do módulo

Após o login, o sistema mostra a tela `Escolha o módulo`. Nela você pode acessar:

- `Registro de Projetos`, para criar e acompanhar projetos e tarefas.
- `Atividades de Rotina`, para registrar atividades diárias.
- `Dashboard`, para consultar gráficos e indicadores.

Use `Trocar módulo` para voltar a essa tela a partir de um módulo. Use `Sair` para encerrar a sessão.

## 5. Módulo Registro de Projetos

O módulo `Projetos` apresenta a lista de projetos cadastrados e permite criar novos projetos.

### 5.1 Lista de projetos

Cada projeto pode exibir:

- Nome do projeto.
- Tipo do projeto.
- Responsável.
- Período planejado.
- Quantidade de tarefas.
- Percentual de progresso.
- Prioridade.

Use `Atualizar` para recarregar os dados. Use `Abrir projeto` para acessar os detalhes. Use `Excluir projeto` apenas quando tiver certeza de que o registro deve ser removido.

### 5.2 Criar um projeto

Na seção `Novo projeto`, preencha os campos:

- Nome: nome claro e identificável do projeto.
- Responsável: pessoa ou login responsável.
- Tipo: classificação do projeto.
- Classificação do processo: indica se o projeto está relacionado a processos novos ou processos existentes.
- FTE: capacidade ou dedicação planejada.
- Início planejado: data e hora previstas para o início.
- Fim planejado: data e hora previstas para o término.
- Gravidade, Urgência e Tendência: critérios usados para priorização.
- Objetivo: nível de clareza do objetivo do projeto.
- Método: nível de clareza do método de execução.
- Custo estimado: valor previsto para o projeto.

Depois de preencher os campos obrigatórios, clique em `Criar projeto`.

Tipos de projeto disponíveis:

- LAYOUT.
- EXPORTAÇÃO.
- NORMATIZAÇÃO.
- PADRONIZAÇÃO.
- TRY OUT.
- MAPEAMENTO.
- PEÇAS.

Observação: tipos de melhoria cadastrados no histórico continuam disponíveis para consulta, mas não devem ser usados em novos projetos.

Boas práticas:

- Use nomes específicos.
- Confira as datas antes de salvar.
- Padronize o preenchimento do responsável.
- Escolha o tipo de projeto com atenção, pois ele afeta os indicadores.
- Preencha a classificação do processo quando essa informação estiver disponível.
- Use gravidade, urgência e tendência de forma consistente.

Evite:

- Criar projetos duplicados.
- Usar nomes genéricos, como `Projeto novo`.
- Informar data final anterior à data inicial.
- Excluir projetos para corrigir pequenos erros.

### 5.3 Excluir um projeto

A exclusão de um projeto pode remover informações importantes, incluindo tarefas e registros relacionados.

Antes de excluir:

- Confirme se o projeto correto está aberto.
- Verifique se existem tarefas ou tempos registrados.
- Consulte a equipe responsável quando houver dúvida.

Não exclua projetos históricos apenas porque eles estão concluídos. Projetos concluídos podem ser importantes para os indicadores do Dashboard.

## 6. Detalhes do projeto e tarefas

Ao abrir um projeto, o sistema mostra um resumo com progresso, quantidade de tarefas, dias reais, custo estimado, início planejado e fim planejado.

### 6.1 Criar uma tarefa

Na seção `Nova tarefa`, preencha:

- Nome da tarefa.
- Custo.
- Início planejado.
- Fim planejado.

Clique em `Criar tarefa` para salvar.

Boas práticas:

- Crie tarefas com escopo claro.
- Separe trabalhos longos em tarefas menores quando fizer sentido.
- Use nomes que expliquem o trabalho a ser realizado.
- Informe datas planejadas realistas.

Evite:

- Criar várias tarefas com o mesmo nome dentro do mesmo projeto.
- Registrar tarefas sem relação com o projeto.
- Usar a tarefa como campo livre para observações.

### 6.2 Abrir e acompanhar uma tarefa

Ao abrir uma tarefa, você pode:

- Iniciar o registro de tempo.
- Parar o registro de tempo.
- Concluir a tarefa.
- Excluir a tarefa.
- Consultar detalhes e entradas de tempo.

Os detalhes mostram status, progresso, início planejado, fim planejado, custo e tempo real.

### 6.3 Controle de tempo

Use `Iniciar` quando começar a trabalhar na tarefa. Use `Parar` quando interromper ou finalizar aquele período de trabalho. O sistema registra uma entrada de tempo com início e fim.

Use `Concluir` somente quando a tarefa estiver realmente finalizada.

Faça:

- Inicie a tarefa apenas quando estiver trabalhando nela.
- Pare a tarefa ao encerrar o trabalho ou fazer uma pausa longa.
- Confira se a tarefa correta está aberta antes de iniciar.
- Conclua apenas quando não houver pendências.

Não faça:

- Não deixe uma tarefa rodando por esquecimento.
- Não registre tempo em uma tarefa errada.
- Não conclua uma tarefa apenas para melhorar indicadores.
- Não exclua tarefas com histórico relevante sem validação.

## 7. Módulo Atividades de Rotina

Use o módulo `Atividades de Rotina` para registrar atividades diárias que não estão necessariamente ligadas a um projeto específico.

Tipos disponíveis:

- Atendimento de Fábrica.
- Cadastro.
- Atualização de Custos.
- Finame.
- Reuniões.
- Análise de Processos.

### 7.1 Iniciar uma atividade

Para iniciar:

1. Informe o responsável.
2. Selecione o tipo de atividade.
3. Opcionalmente, preencha a descrição.
4. Clique em `Iniciar`.

Enquanto houver uma atividade em andamento, o sistema bloqueia a troca de tipo até que ela seja finalizada.

### 7.2 Finalizar uma atividade

Ao terminar a atividade, clique em `Finalizar`. O sistema calcula as horas trabalhadas e registra a atividade como concluída.

Boas práticas:

- Informe o responsável de forma padronizada.
- Use a descrição para explicar o contexto quando necessário.
- Finalize a atividade assim que ela terminar.
- Registre atividades de rotina no módulo correto, não como tarefas de projeto.

Evite:

- Deixar atividade aberta ao final do expediente.
- Misturar atividades diferentes em um único registro.
- Selecionar um tipo que não representa o trabalho feito.

## 8. Módulo Dashboard

O Dashboard apresenta indicadores globais de projetos e atividades de rotina. Ele ajuda a analisar prazos, esforço, complexidade, valor agregado e desempenho.

Principais gráficos:

- Lead Time Médio por Tipo de Projeto.
- Lead Time Médio: Planejado vs Real.
- Dias Totais para Atividades de Rotina.
- Análise Mensal de Projetos.
- Lead Time Mensal por Tipo de Projeto.
- Atraso Médio Mensal por Tipo de Projeto.
- Eficiência Mensal por Tipo de Projeto.
- Taxa de Projetos que Estouram o Prazo.
- Quantidade de Projetos por Complexidade.
- Quantidade de Projetos por Complexidade por Mês.
- Valor Agregado por Mês.
- Índice de Desempenho de Prazo (IDP) por Mês.
- Índice de Desempenho de Custo (IDC) por Mês.
- Desvio de Esforço por Mês.

### 8.1 Filtros

Alguns gráficos permitem filtrar por:

- Ano.
- Mês.
- Tipo de projeto.
- Tipo de atividade.
- Usuário ou responsável.

Ao mudar filtros, aguarde o gráfico atualizar. Se não houver dados para o filtro escolhido, o sistema exibirá uma mensagem informando que não há dados suficientes.

### 8.2 Interpretação dos indicadores

- Lead time real: tempo registrado nas tarefas, convertido em dias.
- Lead time planejado: diferença entre data final planejada e data inicial planejada.
- Atraso: diferença entre dias reais e dias planejados. Valores positivos indicam estouro.
- Eficiência: comparação entre prazo planejado e tempo real.
- Complexidade: combinação entre clareza do objetivo e clareza do método.
- Valor Agregado (VA): valor associado ao escopo efetivamente entregue.
- IDP: indicador de desempenho de prazo. Abaixo de 1 indica atraso.
- IDC: indicador de desempenho de custo. Abaixo de 1 indica desempenho de custo desfavorável.
- Desvio de esforço: diferença entre horas reais e horas planejadas.

Use os gráficos para apoiar análises e decisões. Não use o Dashboard como única fonte para julgar desempenho sem entender os filtros e a qualidade dos dados cadastrados.

## 9. Regras importantes de uso

Faça:

- Registre projetos e tarefas o mais próximo possível da execução.
- Mantenha nomes, responsáveis e tipos padronizados.
- Use `Atualizar` quando suspeitar que a tela está desatualizada.
- Finalize tarefas e atividades quando terminar o trabalho.
- Revise os dados antes de excluir qualquer item.
- Avise rapidamente se encontrar inconsistências.

Não faça:

- Não compartilhe sua conta.
- Não cadastre dados de teste em ambiente de produção.
- Não exclua projetos ou tarefas sem certeza.
- Não use o mesmo nome para tarefas diferentes no mesmo projeto.
- Não deixe timers abertos por longos períodos sem acompanhamento.
- Não interprete gráficos sem considerar os filtros aplicados.

## 10. Problemas comuns

### 10.1 O sistema voltou para a tela de login

Isso pode acontecer quando a sessão expira ou quando o token de autenticação não é aceito pelo servidor.

O que fazer:

1. Entre novamente com e-mail e senha.
2. Se o problema continuar, avise o responsável técnico.
3. Informe em qual módulo o problema aconteceu.

### 10.2 Fiz login, mas não vejo meus projetos

Os dados são vinculados ao usuário autenticado. Se você entrou com outra conta, pode não ver os mesmos projetos.

O que fazer:

- Confirme se está usando a conta correta.
- Verifique com a equipe se os dados foram importados ou cadastrados para esse usuário.

### 10.3 O gráfico não mostra dados

Pode não haver dados suficientes para o filtro escolhido.

O que fazer:

- Revise filtros de ano, mês, tipo e usuário.
- Confira se existem projetos, tarefas ou atividades finalizadas.
- Clique em `Atualizar`.

### 10.4 Esqueci uma tarefa ou atividade aberta

Avise a equipe responsável pelo processo. Dependendo das regras internas, pode ser necessário ajustar o registro no banco ou substituir por um lançamento correto.

### 10.5 Excluí algo por engano

Entre em contato com o responsável técnico imediatamente. Evite cadastrar muitos dados novos antes de avisar, pois isso dificulta a verificação.

## 11. Responsabilidades do usuário

Cada usuário é responsável por:

- Registrar dados de forma correta e honesta.
- Conferir informações antes de salvar ou excluir.
- Usar a conta correta.
- Manter a confidencialidade de sua senha.
- Comunicar erros ou inconsistências rapidamente.

## 12. Segurança

- Acesse o sistema apenas por links confiáveis.
- Não salve senha em computadores compartilhados.
- Sempre clique em `Sair` ao terminar em máquinas compartilhadas.
- Não envie capturas de tela com informações sensíveis sem necessidade.
- Em caso de suspeita de acesso indevido, avise imediatamente o responsável pelo sistema.

## 13. Glossário rápido

- FTE: indicador de capacidade ou dedicação planejada.
- Lead time: tempo total entre início e fim de uma atividade, tarefa ou projeto.
- Tempo real: tempo efetivamente registrado nas entradas de tempo.
- Tempo planejado: tempo previsto no planejamento.
- VA: Valor Agregado. Representa o valor do escopo entregue.
- VP: Valor Planejado. Representa o valor esperado conforme o cronograma.
- IDP: Índice de Desempenho de Prazo.
- IDC: Índice de Desempenho de Custo.
- Complexidade: classificação calculada a partir de objetivo e método.
- Atividade de rotina: atividade diária registrada fora do fluxo de tarefas de projeto.

## 14. Resumo para uso diário

1. Entre com sua conta.
2. Escolha o módulo correto.
3. Cadastre projetos apenas quando houver informações mínimas confiáveis.
4. Crie tarefas claras dentro do projeto.
5. Inicie e pare o tempo enquanto trabalha.
6. Conclua tarefas finalizadas.
7. Registre atividades de rotina no módulo de rotina.
8. Use o Dashboard para acompanhar desempenho.
9. Revise antes de excluir.
10. Saia do sistema ao terminar.
