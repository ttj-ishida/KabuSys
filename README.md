KabuSys
=======

日本株自動売買・データ基盤ライブラリ（軽量版）  
本リポジトリは日本株向けのデータETL、ニュース収集・NLPスコアリング、ファクター研究、監査ログなどのユーティリティ群を提供します。DuckDB を中心にローカルでデータを蓄積し、J-Quants / JPYX カレンダー等の外部 API と連携してデータパイプラインを構築することを想定しています。

主な特徴
-------
- J-Quants API クライアント（差分取得・ページネーション・自動トークンリフレッシュ・レート制御）
- 日次 ETL パイプライン（市場カレンダー / 株価 / 財務データ）
- ニュース収集（RSS）とニュース→銘柄紐付け
- OpenAI を用いたニュースセンチメント（銘柄ごと）スコアリング（news_nlp）
- OpenAI を用いたマクロセンチメントと ETF MA を組み合わせた市場レジーム判定（regime_detector）
- 研究用モジュール（ファクター計算、将来リターン、IC、統計サマリー）
- データ品質チェックモジュール（欠損・重複・スパイク・日付整合性）
- 監査ログ（signal / order_request / executions）のスキーマ初期化ユーティリティ
- 各種ユーティリティ（カレンダー管理、統計正規化など）

セットアップ手順
------------

前提
- Python 3.10+ を推奨
- ネットワーク経由で J-Quants / OpenAI を利用する場合はそれぞれの API キーが必要

基本手順（ローカル開発）
1. 仮想環境の作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージインストール（最低限の依存）
   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使ってください）

3. 環境変数の設定
   - .env または環境変数で下記を設定してください（必須項目は後述）

自動 .env ロード
- パッケージインポート時にプロジェクトルート（.git または pyproject.toml）を探索し、
  .env → .env.local の順に読み込みます（OS 環境変数が優先）。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須 / 主要な環境変数
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（発注系で使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID: Slack チャネル ID
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector の呼び出しで使用可能）
オプション（デフォルト値あり）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB の保存先（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

使い方（主な機能の呼び出し例）
-----------------------

※ 下記は最小限の利用例です。実運用ではログ設定や例外ハンドリングを行ってください。

1) DuckDB 接続を作成して日次 ETL を実行する
- ETL は prices / financials / market_calendar を差分取得し品質チェックを行います。

Python 例:
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())

2) ニュース記事のセンチメントを付与する（銘柄ごと）
- OpenAI API キーは環境変数 OPENAI_API_KEY、または関数引数で指定できます。

Python 例:
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None→環境変数参照
print(f"scored {count} stocks")

3) 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM スコアを合成）
Python 例:
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

4) 監査ログスキーマを初期化する
- 監査専用の DuckDB を作る場合:

from pathlib import Path
import duckdb
from kabusys.data.audit import init_audit_db

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)
# conn は初期化済みの DuckDB 接続

5) J-Quants クライアント単体利用例（トークン取得 / データ取得）
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()  # settings.jquants_refresh_token を参照
records = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,1,31))

主な公開 API（抜粋）
- kabusys.data.pipeline.run_daily_etl(...)
- kabusys.data.pipeline.run_prices_etl(...)
- kabusys.data.pipeline.run_financials_etl(...)
- kabusys.data.pipeline.run_calendar_etl(...)
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.fetch_financial_statements(...)
- kabusys.data.jquants_client.fetch_market_calendar(...)
- kabusys.data.audit.init_audit_db / init_audit_schema(...)
- kabusys.ai.news_nlp.score_news(...)
- kabusys.ai.regime_detector.score_regime(...)
- kabusys.research.calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.stats.zscore_normalize(...)

設計上の重要点（運用上の注意）
----------------------------
- Look-ahead バイアス防止: 多くの関数は内部で datetime.today() を直接参照せず、呼び出し時に target_date を明示する設計です。バックテスト用途では target_date を厳密に渡してください。
- .env 自動読み込みはプロジェクトルートを基準に行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効にできます。
- OpenAI 呼び出しはリトライ・フォールバック（API エラー時はセンチメント 0.0 等）を行うものの、API のコスト・レート制限を考慮してください。
- DuckDB の executemany はバージョン依存の挙動があるため、空リスト送信等に注意して実装済みです。

ディレクトリ構成
----------------

src/kabusys/
- __init__.py               : パッケージ定義（version 等）
- config.py                 : 環境変数 / 設定管理（.env 自動ロード、Settings クラス）
- ai/
  - __init__.py             : ai パッケージ公開
  - news_nlp.py             : ニュース NLU（OpenAI を用いた銘柄別センチメント）
  - regime_detector.py      : ETF MA + マクロニュースから市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py       : J-Quants API クライアント（取得・保存ユーティリティ）
  - pipeline.py             : 日次 ETL パイプライン（run_daily_etl 等）
  - etl.py                  : ETLResult の再エクスポート
  - news_collector.py       : RSS 収集と前処理
  - calendar_management.py  : マーケットカレンダー管理（営業日判定等）
  - quality.py              : データ品質チェック（欠損・重複・スパイク等）
  - stats.py                : 統計ユーティリティ（zscore_normalize）
  - audit.py                : 監査ログスキーマ定義・初期化
- research/
  - __init__.py
  - factor_research.py      : Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py  : 将来リターン / IC / 統計サマリー 等
- research/*.py             : 研究ユーティリティ群

補足（依存関係）
--------------
主な外部ライブラリ:
- duckdb
- openai
- defusedxml

その他、標準ライブラリのみで実装されている箇所が多く、ネットワーク呼び出しは urllib を利用しています。

トラブルシューティング
----------------------
- 環境変数未設定によるエラー:
  - settings の必須プロパティ（JQUANTS_REFRESH_TOKEN 等）が未設定だと ValueError が発生します。README の「必須環境変数」を確認してください。
- OpenAI 呼び出しで 5xx/429/タイムアウトが発生:
  - モジュール内で指数バックオフとリトライを行いますが、長時間失敗する場合は API キーやネットワーク、モデル名（gpt-4o-mini）を確認してください。
- DuckDB ファイルのパーミッション・パス問題:
  - デフォルトの DUCKDB_PATH=data/kabusys.duckdb は親ディレクトリが存在しないと作れない場合があります。事前に data ディレクトリを作成するか、Path を変更してください。

最後に
-----
この README はコードベースから機能・設計を抽出してまとめたものです。実稼働で使用する場合はログ設定、エラーハンドリング、CI/デプロイ、シークレット管理（Vault 等）を別途整備してください。必要ならば README の追加・具体的な運用手順（cron / Airflow ジョブ定義、Slack 通知の有効化など）も作成します—要件があれば教えてください。