KabuSys — 日本株自動売買 / データ基盤ライブラリ
================================

概要
----
KabuSys は日本株向けのデータパイプライン、リサーチ用ファクター計算、ニュース NLP（LLM）によるセンチメント評価および監査ログ／実行ログ管理を目的とした Python モジュール群です。  
主に以下機能を備え、DuckDB をデータストアとして利用する設計になっています。

主な特徴
--------
- J-Quants API 経由の株価・財務・マーケットカレンダー差分 ETL（ページネーション・レート制御・トークン自動リフレッシュ対応）
- ニュース収集（RSS）とニュースの前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースのセンチメント / マクロセンチメント評価（JSON Mode を利用）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロ記事センチメントを合成）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）および特徴量解析ユーティリティ（forward returns, IC, summary, rank）
- データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
- 監査ログ（signal_events / order_requests / executions）スキーマ定義と初期化ユーティリティ
- 環境変数ベースの設定管理（.env 自動ロード機能あり、無効化可能）

必要条件
--------
- Python 3.10 以上（PEP 604 の | 型注釈を使用）
- 推奨主要依存パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外の依存は用途に応じて追加）

セットアップ手順
----------------
1. ソースを取得
   - git clone でリポジトリを取得してください。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 例:
     - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

4. インストール（開発モード）
   - pip install -e .

5. 環境変数設定
   - ルートに .env / .env.local を置くと自動で読み込まれます（config.py の自動ロード）。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（必須）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL / API 呼び出しに必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（発注などに使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector が必要とする場合）
- その他（任意、デフォルトあり）:
  - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト data/monitoring.db)
  - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - KABUSYS_ENV: development / paper_trading / live
  - LOG_LEVEL: DEBUG/INFO/...

例 .env（簡易）
- JQUANTS_REFRESH_TOKEN=xxxxx
- OPENAI_API_KEY=sk-xxxxx
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-xxxxx
- SLACK_CHANNEL_ID=C01234567
- DUCKDB_PATH=data/kabusys.duckdb

使い方（概要と例）
-----------------

設定読み込み
- from kabusys.config import settings
- settings.jquants_refresh_token 等で設定値にアクセスします。

DuckDB 接続例
- import duckdb
- from kabusys.config import settings
- conn = duckdb.connect(str(settings.duckdb_path))

日次 ETL 実行（株価 / 財務 / カレンダー & 品質チェック）
- from datetime import date
- from kabusys.data.pipeline import run_daily_etl
- res = run_daily_etl(conn, target_date=date(2026, 3, 20))
- res は ETLResult（取得数・保存数・品質問題などを含む）

ニュースセンチメントスコア（AI）
- from kabusys.ai.news_nlp import score_news
- from datetime import date
- count = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None の場合は OPENAI_API_KEY を読む

市場レジーム判定
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date=date(2026,3,20), api_key=None)

監査ログデータベース初期化
- from kabusys.data.audit import init_audit_db
- audit_conn = init_audit_db(settings.duckdb_path)  # または別ファイルパスを指定

ニュース収集（RSS）
- from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
- articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")

リサーチ機能
- from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
- from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
- 各関数は DuckDB 接続と target_date を受け取り、銘柄ごとの dict のリストを返します。

注意点 / 動作方針
-----------------
- Look-ahead バイアス防止: 多くの関数は明示的な target_date を受け取り、内部で datetime.today() を直接参照しない設計です。
- LLM 呼び出しは失敗時にフォールバック（スコア 0.0）するなどフェイルセーフ設計です。
- J-Quants クライアントはレート制御・リトライ・401 リフレッシュを実装しています。
- news_collector は SSRF 対策・gzip対応・トラッキング除去などを行います。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                 — 記事センチメント（AI）と score_news
  - regime_detector.py          — 市場レジーム判定（MA200 + マクロ）
- data/
  - __init__.py
  - jquants_client.py           — J-Quants API クライアント & 保存関数
  - pipeline.py                 — ETL パイプライン（run_daily_etl など）
  - etl.py                      — ETLResult の再エクスポート
  - news_collector.py           — RSS 収集と前処理
  - calendar_management.py      — マーケットカレンダー管理 / 営業日ユーティリティ
  - quality.py                  — データ品質チェック
  - stats.py                    — 統計ユーティリティ（zscore_normalize）
  - audit.py                    — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py          — モメンタム/バリュー/ボラティリティ計算
  - feature_exploration.py      — forward returns / IC / summary / rank

開発 / テスト時の便利機能
------------------------
- .env 自動読み込みはデフォルトで有効。テストで無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しや外部 API 呼び出しはモジュール内でラッパー関数化されており、ユニットテストでは unittest.mock.patch により差し替え可能です（実装内コメント参照）。

ライセンス / 貢献
-----------------
（この README では明記されていません。実際のリポジトリに LICENSE や CONTRIBUTING を追加してください。）

付記
----
この README はリポジトリ内のソースコードの docstring / コメントに基づいて作成しています。実運用する際は .env.example を作成し、必要なスキーマ（DuckDB のテーブル定義）を準備してから実行してください。