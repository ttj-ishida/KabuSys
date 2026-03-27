KabuSys
=======

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。本リポジトリは
- データ取得・ETL（J-Quants API 経由）、
- ニュース収集と LLM を用いたニュースセンチメント推定、
- 市場レジーム判定（MA + LLM）、
- 研究・ファクター計算、
- データ品質チェック、監査ログ（発注〜約定トレーサビリティ）、
といった機能を提供します。

プロジェクト概要
--------------
KabuSys は日本株の自動売買システムや研究用データプラットフォームを構築するためのモジュール群です。主要な設計方針は以下です。

- Look-ahead bias を避ける（内部で datetime.today() を直接参照しない等の実装）
- ETL は差分更新・冪等保存（ON CONFLICT）で実行
- J-Quants / OpenAI 等外部 API の呼び出しはレート制御・再試行を実装
- DuckDB をデータストアとして想定
- 監査・トレーサビリティを重視したテーブル設計

主な機能一覧
-------------
- データ ETL（kabusys.data.pipeline.run_daily_etl）:
  - 株価日足、財務データ、マーケットカレンダーの差分取得と保存
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- J-Quants クライアント（kabusys.data.jquants_client）:
  - 日足・財務・カレンダーなどの取得・DuckDB へ保存（save_* 関数）
  - レートリミット制御・トークン自動リフレッシュ・リトライ
- ニュース収集（kabusys.data.news_collector）:
  - RSS 取得、前処理、raw_news への冪等保存、SSRF/サイズ制限対策
- ニュース NLP（kabusys.ai.news_nlp）:
  - ニュースを銘柄ごとにまとめて OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores へ書き込み
  - バッチ・リトライ・レスポンス検証あり
- 市場レジーム判定（kabusys.ai.regime_detector）:
  - ETF 1321 の 200 日 MA 乖離 + マクロニュース LLM センチメントを合成して日次レジーム判定（bull/neutral/bear）
- 研究用関数（kabusys.research）:
  - momentum / value / volatility 等のファクター計算、将来リターン・IC 計算・統計サマリ等
- データ品質チェック（kabusys.data.quality）:
  - 欠損、スパイク、重複、日付不整合を検出し QualityIssue を返す
- 監査ログ（kabusys.data.audit）:
  - signal_events / order_requests / executions の DDL と初期化ユーティリティ（init_audit_schema / init_audit_db）
- 設定管理（kabusys.config）:
  - .env ファイル or 環境変数読み込み、Settings オブジェクト経由で各種設定を取得
  - 自動 .env ロード機能（プロジェクトルート探索）と無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD

セットアップ手順
----------------

前提
- Python 3.10 以上（typing の | 演算子や型表記を利用）
- DuckDB を利用できる環境

1. リポジトリをチェックアウト／プロジェクトルートへ移動

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (または Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合はそれを使ってください）

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（kabusys.config の自動ロード）
   - 自動ロードを無効化する場合:
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（jquants_client に使用）
- SLACK_BOT_TOKEN : Slack 通知を行う場合
- SLACK_CHANNEL_ID : Slack 通知先チャンネルID
- KABU_API_PASSWORD : kabuステーション API を使う場合のパスワード
- OPENAI_API_KEY : OpenAI を使う処理（news_nlp / regime_detector）を実行する際に利用可能（関数呼び出しで api_key を渡すことも可）
- （オプション）DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL

.env の例（.env.example を参考に作成してください）
- JQUANTS_REFRESH_TOKEN=xxxx
- OPENAI_API_KEY=xxxx
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- KABU_API_PASSWORD=...
- DUCKDB_PATH=data/kabusys.duckdb

使い方（主要な実行例）
--------------------

以下は Python スクリプトや REPL から呼び出す例です。DuckDB の接続は duckdb.connect(...) を使用します。

1) DuckDB 接続を作り ETL を回す（日次ETL）
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

2) ニュースの NLP スコアリング（前日 15:00 JST ～ 当日 08:30 JST ウィンドウ）
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")

- 注意: OpenAI API キーは OPENAI_API_KEY 環境変数に設定するか、score_news の api_key 引数に渡してください。

3) 市場レジーム判定を実行（ETF 1321 の MA200 + マクロセンチメント合成）
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))

4) 監査用 DuckDB を初期化
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# schema が作成され、接続が返る

5) J-Quants のデータ取得単体実行例
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))
recs = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))
saved = save_daily_quotes(conn, recs)

注意点 / テスト用フック
- OpenAI 呼び出しは内部で _call_openai_api を経由しているため、ユニットテストでは関数を patch して差し替えやすくなっています。
- kabusys.config はプロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込みします。テストで自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB への executemany に空リストを渡すとエラーになるバージョンがあるため、実装側で空チェックを行う設計になっています。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                       — 環境変数/設定管理
- ai/
  - __init__.py
  - news_nlp.py                    — ニュースセンチメント（OpenAI 経由）
  - regime_detector.py             — マーケットレジーム判定
- data/
  - __init__.py
  - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
  - jquants_client.py              — J-Quants API クライアント（fetch/save）
  - news_collector.py              — RSS 収集・前処理・保存
  - quality.py                     — データ品質チェック
  - stats.py                       — 統計ユーティリティ（zscore_normalize）
  - calendar_management.py         — 市場カレンダー管理（is_trading_day 等）
  - audit.py                       — 監査ログ DDL / 初期化
  - etl.py                         — ETLResult 再エクスポート
- research/
  - __init__.py
  - factor_research.py             — ファクター計算（momentum/value/volatility）
  - feature_exploration.py         — 将来リターン / IC / 統計サマリ
- research/*（上記に続く）

API の概要（主な公開関数）
- kabusys.data.pipeline.run_daily_etl(...)
- kabusys.data.pipeline.run_prices_etl(...)
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.save_daily_quotes(...)
- kabusys.data.news_collector.fetch_rss(...) / preprocess_text(...)
- kabusys.ai.news_nlp.score_news(...)
- kabusys.ai.regime_detector.score_regime(...)
- kabusys.data.audit.init_audit_db(...) / init_audit_schema(...)

推奨動作環境と依存
-----------------
- Python >= 3.10
- 必須/推奨パッケージ（一例）:
  - duckdb
  - openai
  - defusedxml
- ネットワーク経由の API（J-Quants, OpenAI）を利用するため各種 API キーが必要

その他
-----
- 本ライブラリはバックテスト／運用どちらにも利用できるよう設計されていますが、実際の注文送信や本番運用を行う場合はリスク管理・二重発注防止・アクセス制御等の追加実装と十分な検証を行ってください。
- ドキュメントやコード内にある設計方針コメント（Look-ahead bias 対策、フェイルセーフ挙動など）を順守して利用してください。

もし README に追加したい例や、セットアップで使う具体的なコマンド（requirements.txt、CI、Dockerfile 等）を用意したい場合は教えてください。必要に応じて .env.example も作成します。