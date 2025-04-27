import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
from flask import render_template, Flask, abort
import logging
import db

APP = Flask(__name__)

# Start page
@APP.route('/')
def index():
    stats = db.execute('''
        SELECT * FROM
            (SELECT COUNT(*) n_exposicoes FROM Exposicoes)
        JOIN
            (SELECT COUNT(*) n_artistas FROM Artistas)
        JOIN
            (SELECT COUNT(*) n_pinturas FROM Pinturas)
        JOIN
            (SELECT COUNT(*) n_museus FROM Museus)
        JOIN
            (SELECT COUNT(*) n_paises FROM Paises)
    ''').fetchone()
    logging.info(stats)
    return render_template('index.html',stats=stats)


@APP.route('/exposicoes/')
def list_exposicoes():
    exposicoes= db.execute(
      '''
      SELECT *
      FROM Exposicoes
      ORDER BY nome
      ''').fetchall()
    return render_template('exposicoes-list.html', exposicoes=exposicoes)

@APP.route('/exposicoes/<string:id>/')
def view_by_exposicoes(id):
    exposicao = db.execute(
    '''
    SELECT *
    FROM exposicoes
    WHERE exposicao_id= ?
    ''', [id]).fetchone()

    if exposicao is None:
        abort(404, 'Exposicao id {} não existe.'.format(id))

    artistas = db.execute(
    '''
    SELECT a.artista_id, a.nome
    FROM artistas a join Artistas_Exposicoes ae on (a.artista_id = ae.artistas_id)
		join Exposicoes e on (ae.exposicao_id = e.exposicao_id)
    WHERE e.exposicao_id= ?
    ORDER BY a.artista_id
    ''', [id]).fetchall()

    paises = db.execute(
    '''
    SELECT p.pais_id, p.nome
    FROM paises p JOIN Paises_Exposicoes pe ON (p.pais_id = pe.pais_id)
		JOIN Exposicoes e ON (pe.exposicao_id = e.exposicao_id)
    WHERE e.exposicao_id = ?
    ORDER BY p.nome
    ''', [id]).fetchall()

    return render_template('exposicao.html', exposicao=exposicao, artistas=artistas, paises=paises)


@APP.route('/exposicoes/search/<expr>/')
def search_exposicoes(expr):
  search = { 'expr': expr }

  exposicao = db.execute(
      ' SELECT exposicao_id, nome'
      ' FROM exposicoes'
      ' WHERE nome LIKE \'%' + expr + '%\''
    ).fetchall()

  return render_template('exposicao-search.html',
           search=search,exposicao=exposicao)



@APP.route('/pinturas/')
def list_pinturas():
    pinturas = db.execute('''
      SELECT pintura_id, nome, artista_id, estilo, museu_id
      FROM Pinturas
      ORDER BY nome
    ''').fetchall()
    return render_template('pinturas-list.html', pinturas=pinturas)

@APP.route('/pinturas/<int:id>/')
def view_by_pinturas(id):
    pinturas = db.execute(
        '''
        SELECT pintura_id, nome, artista_id, estilo, museu_id
        FROM pinturas
        WHERE pintura_id = ?
        ''', [id]).fetchone()

    if pinturas is None:
        abort(404, 'Pintura id {} não existe.'.format(id))

    museus = db.execute(
        '''
        SELECT m.museu_id, m.nome
        FROM pinturas p JOIN museus m ON (p.museu_id = m.museu_id)
        WHERE p.pintura_id = ?
        ''', [id]).fetchall()

    artistas = db.execute(
        '''
        SELECT a.artista_id, a.nome
        FROM artistas a JOIN pinturas p ON (a.artista_id = p.artista_id )
        WHERE p.pintura_id = ?
        ORDER BY p.nome
        ''', [id]).fetchall()

    return render_template('pintura.html',
                           pinturas=pinturas, museus=museus, artistas=artistas)

@APP.route('/pinturas/search/<expr>/')
def search_pinturas(expr):
  search = { 'expr': expr }

  pinturas = db.execute(
      ' SELECT pintura_id, nome'
      ' FROM pinturas'
      ' WHERE nome LIKE \'%' + expr + '%\''
    ).fetchall()

  return render_template('pintura-search.html',
           search=search,pinturas=pinturas)


@APP.route ('/artistas/')
def list_artistas():
    artistas= db.execute(
    '''
    SELECT *
    FROM Artistas
    ORDER BY nome
    ''').fetchall()
    return render_template ('artistas-list.html',artistas=artistas)

@APP.route('/artistas/<int:id>/')
def view_by_artistas(id):
  artista = db.execute(
    '''
    SELECT *
    FROM artistas
    WHERE artista_id= ?
    ''', [id]).fetchone()

  if artista is None:
     abort(404, 'Artista id {} não existe.'.format(id))

  pintura = db.execute(
    '''
    SELECT p.pintura_id, p.nome , p.estilo
    FROM pinturas p JOIN artistas a ON (a.artista_id = p.artista_id )
    WHERE a.artista_id = ?
    ORDER BY p.nome
    ''', [id]).fetchall()

  return render_template('artista.html',
            artista=artista, pintura=pintura)

@APP.route('/artistas/search/<expr>/')
def search_artista(expr):
  search = { 'expr': expr }

  artista = db.execute(
      ' SELECT artista_id, nome'
      ' FROM artistas'
      ' WHERE nome LIKE \'%' + expr + '%\''
    ).fetchall()

  return render_template('artista-search.html',
           search=search,artista=artista)


@APP.route ('/museus/')
def list_museus():
    museus= db.execute(
    '''
    SELECT museu_id, nome
    FROM Museus
    ORDER BY nome
    ''').fetchall()
    return render_template ('museus-list.html', museus=museus)

@APP.route('/museus/<int:id>/')
def view_by_museus(id):
    museus = db.execute(
    '''
    SELECT *
    FROM Museus m
    WHERE m.museu_id= ?
    ''', [id]).fetchone()

    if museus is None:
        abort(404, 'Museu id {} não existe.'.format(id))

    paises = db.execute(
    '''
    SELECT DISTINCT p.pais_id, p.nome
    FROM paises p JOIN Paises_Exposicoes pe ON (pe.pais_id = p.pais_id)
		JOIN Exposicoes e on (pe.exposicao_id = e.exposicao_id )
        JOIN Museus m on (m.pais_id = p.pais_id)
    WHERE m.museu_id = ?
    ORDER BY p.nome
    ''', [id]).fetchall()

    return render_template ('museus.html', museus=museus, paises=paises)

@APP.route('/museus/search/<expr>/')
def search_museus(expr):
  search = { 'expr': expr }

  museus = db.execute(
      ' SELECT museu_id, nome'
      ' FROM museus'
      ' WHERE nome LIKE \'%' + expr + '%\''
    ).fetchall()

  return render_template('museu-search.html',
           search=search,museus=museus)



@APP.route ('/paises/')
def list_paises():
    paises= db.execute(
        '''
        SELECT *
        FROM paises
        ORDER BY nome
        ''').fetchall()
    return render_template ('paises-list.html', paises=paises)

@APP.route('/paises/<string:id>/')
def view_by_paises(id):
    paises = db.execute(
    '''
    SELECT *
    FROM Paises p
    WHERE p.pais_id= ?
    ''', [id]).fetchone()

    if paises is None:
        abort(404, 'País id {} não existe.'.format(id))

    museus = db.execute(
    '''
    SELECT m.museu_id, m.nome
    FROM museus m
    WHERE pais_id= ?
    ORDER BY m.museu_id
    ''', [id]).fetchall()

    exposicoes = db.execute(
    '''
    SELECT e.exposicao_id, e.nome
    FROM exposicoes e JOIN Paises_Exposicoes pe ON (e.exposicao_id = pe.exposicao_id)
		JOIN Paises p ON (pe.pais_id = p.pais_id)
    WHERE p.pais_id= ?
    ORDER BY e.exposicao_id
    ''', [id]).fetchall()

    return render_template ('paises.html', paises=paises, museus=museus, exposicoes=exposicoes)


@APP.route('/paises/search/<expr>/')
def search_paises(expr):
  search = { 'expr': expr }
  paises = db.execute(
      ' SELECT pais_id, nome'
      ' FROM paises'
      ' WHERE nome LIKE \'%' + expr + '%\''
    ).fetchall()

  return render_template('paises-search.html',
                         search=search,paises=paises)
