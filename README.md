KabuSys — 日本株自動売買プラットフォーム（ライブラリ）
======================================================

概要
----
KabuSys は日本株向けのデータパイプライン、特徴量算出、ニュースNLP、マーケットレジーム判定、監査ログ管理などを備えた自動売買基盤の Python パッケージです。DuckDB をデータストアとして利用し、J-Quants API / RSS / OpenAI（LLM）などと連携することで、データ収集（ETL）→ 品質チェック → 特徴量生成 → シグナル/監査記録 のワークフローをサポートします。

主な機能
--------
- データ取得・ETL
  - J-Quants から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得・保存（冪等）
  - 日次 ETL のエントリポイント（run_daily_etl）
- データ品質チェック
  - 欠損、重複、スパイク（急騰/急落）、日付整合性などのチェック（quality.run_all_checks）
- ニュース収集
  - RSS 取得・前処理・SSRF対策・トラッキング除去・raw_news への保存ロジック（news_collector）
- ニュース NLP（LLM）
  - 銘柄ごとのニュースセンチメントスコア化（news_nlp.score_news）
  - マクロ経済ニュースによる市場レジーム判定（regime_detector.score_regime）
- 研究用ユーティリティ
  - モメンタム／ボラティリティ／バリュー等のファクター計算（research.factor_research）
  - 将来リターン、IC、統計サマリ等の特徴量評価ツール（research.feature_exploration）
  - z-score 正規化ユーティリティ（data.stats.zscore_normalize）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions を含む監査テーブルの初期化・管理（data.audit.init_audit_db）
- J-Quants クライアント
  - レートリミット・リトライ・401トークンリフレッシュ対応の HTTP クライアント（data.jquants_client）
  - DuckDB への冪等保存関数（save_daily_quotes 等）

セットアップ手順
---------------
1. リポジトリを取得（例）
   - git clone ... または package を適切に pip install してください（本 README はソース利用前提）。

2. Python 環境（推奨）
   - Python 3.10+ を推奨。venv / Poetry 等で仮想環境を作成してください。

3. 必要パッケージをインストール
   - 最低依存（例）:
     - duckdb
     - openai
     - defusedxml
   - pip の例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

4. 環境変数 / .env
   - プロジェクトルート（.git や pyproject.toml がある場所）に .env を置くと自動で読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必要な環境変数（主要なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL — kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN — Slack ボットトークン（必須）
     - SLACK_CHANNEL_ID — Slack チャネル ID（必須）
     - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 実行時に利用）
     - DUCKDB_PATH — DuckDB ファイルパス（省略時: data/kabusys.duckdb）
     - SQLITE_PATH — SQLite 監視 DB（省略時: data/monitoring.db）
     - KABUSYS_ENV — 環境 (development | paper_trading | live)（省略時: development）
     - LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
   - サンプル（.env）:
     - JQUANTS_REFRESH_TOKEN=your_refresh_token
     - OPENAI_API_KEY=sk-...
     - DUCKDB_PATH=./data/kabusys.duckdb

使い方（コード例）
-----------------

基本的な DuckDB 接続と日次 ETL 実行例
- 目的: J-Quants からデータを差分取得・保存し品質チェックまで実行する。

Python スニペット:
- import duckdb
- from datetime import date
- from kabusys.data.pipeline import run_daily_etl
- from kabusys.config import settings
- conn = duckdb.connect(str(settings.duckdb_path))
- result = run_daily_etl(conn, target_date=date.today())
- print(result.to_dict())

ニュースのスコアリング（LLM を使う）
- OpenAI API キーを環境変数 OPENAI_API_KEY に設定してから実行。

例:
- from kabusys.ai.news_nlp import score_news
- from kabusys.config import settings
- import duckdb
- conn = duckdb.connect(str(settings.duckdb_path))
- n_written = score_news(conn, target_date=date(2026, 3, 20))
- print(f"書込銘柄数: {n_written}")

市場レジーム判定（ETF 1321 とマクロ記事）
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date=date(2026,3,20), api_key=None)  # None 時は OPENAI_API_KEY を参照

監査ログ DB の初期化
- from kabusys.data.audit import init_audit_db
- conn_audit = init_audit_db("./data/audit.duckdb")
- # 以後 conn_audit を使って発注/約定ログを保存

J-Quants データ取得（ライブラリ呼び出し）
- from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
- data = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
- # 取得したレコードは save_daily_quotes で DuckDB に保存可能

注意点
- LLM 呼び出し時は API エラー時にフェイルセーフで 0.0（中立）にフォールバックする設計です。
- ETL / データ取得は差分更新・バックフィルを取り入れており、look-ahead bias を避ける工夫が組み込まれています。
- DuckDB の executemany は空リストを受け付けないバージョン向けのガードが各所に入っています。

ディレクトリ構成（主要ファイル）
---------------------------
- src/kabusys/
  - __init__.py
  - config.py                 # 環境変数 / .env 自動ロード・設定クラス
  - ai/
    - __init__.py
    - news_nlp.py             # ニュースセンチメント（score_news）
    - regime_detector.py      # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       # J-Quants API クライアント、保存ロジック
    - pipeline.py             # ETL パイプライン、run_daily_etl 等
    - etl.py                  # ETLResult の再エクスポート
    - news_collector.py       # RSS 取得・前処理
    - calendar_management.py  # 市場カレンダー管理（is_trading_day 等）
    - quality.py              # データ品質チェック
    - stats.py                # 統計ユーティリティ（zscore_normalize）
    - audit.py                # 監査ログテーブル初期化
  - research/
    - __init__.py
    - factor_research.py      # momentum/value/volatility ファクター
    - feature_exploration.py  # 将来リターン・IC・summary・rank 等
  - monitoring/ (パッケージ宣言は __all__ に含むが本リストは省略可能)
  - strategy/ (戦略/実装層、今回のコードベースでは参照用)

サンプルワークフロー（概略）
- 1) run_daily_etl で市場カレンダー・株価・財務を差分取得
- 2) quality.run_all_checks で品質問題を検知
- 3) research のファクター計算で特徴量を作成 → zscore 正規化
- 4) 戦略ロジックでシグナル生成 → audit テーブルへ保存
- 5) 発注処理（execution モジュール等）→ order_requests/executions に記録
- 6) news_nlp / regime_detector で追加情報を取得しモデルへ用いる

テストとデバッグ
----------------
- 環境変数ロードは自動的に .env / .env.local を読みます（自動ロードを止めるには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
- OpenAI 呼び出し等は各モジュールで内部関数をモック可能に実装されており、ユニットテストが容易です（例: unittest.mock.patch で _call_openai_api を差し替え）。
- DuckDB はインメモリ(":memory:") が使えるためテスト時にファイルを作らずに検証できます。

ライセンス / 貢献
-----------------
- 本 README にライセンス情報は含みません。実際のリポジトリでは LICENSE を参照してください。
- バグ修正や機能追加は PR を通じて行ってください。設計方針（Look-ahead bias 回避、冪等性、フェイルセーフ）を尊重してください。

補足
----
- この README はコードベース内のドキュメント文字列（docstring）から主な機能と利用方法を要約しています。より詳細な API 仕様や実運用手順（監視、運用時の秘密情報管理、Slack 通知など）は別途運用ドキュメントを用意してください。

以上。必要であれば README の英語版や、実際の .env.example のテンプレート、よくあるエラーと対処集（FAQ）を追記します。どの部分を詳細化しますか？