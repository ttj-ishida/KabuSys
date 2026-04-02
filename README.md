KabuSys — 日本株自動売買システム
=================================

プロジェクト概要
---------------
KabuSys は日本株向けのデータパイプライン、ファクター研究、ニュースNLP、及び市場レジーム判定を備えた自動売買・リサーチ基盤のライブラリです。  
主に以下を目的としています:

- J-Quants API からの株価・財務・カレンダー等の差分ETL
- DuckDB によるデータ永続化と品質チェック
- ニュース記事の収集・NLP（OpenAI）による銘柄別センチメント算出
- ETF 指標とマクロニュースからの市場レジーム判定（bull/neutral/bear）
- ファクター計算（モメンタム／バリュー／ボラティリティ）と研究用ユーティリティ
- 監査ログ（シグナル→発注→約定）用スキーマの初期化

機能一覧
--------
主な機能（抜粋）:

- データ取得・ETL
  - J-Quants API からの日次株価（OHLCV）、財務諸表、JPXマーケットカレンダー取得
  - 差分取得・バックフィル・冪等保存（ON CONFLICT）
  - run_daily_etl による一括日次ETL
- データ品質チェック
  - 欠損／重複／将来日付／スパイク等のチェック（quality.run_all_checks）
- ニュース収集・NLP
  - RSS からの安全なニュース収集（SSRF 対策・トラッキング除去）
  - OpenAI（gpt-4o-mini）での銘柄別センチメント付与（news_nlp.score_news）
- 市場レジーム判定
  - ETF（1321）200日MA乖離 + マクロニュースセンチメントの合成（regime_detector.score_regime）
- 研究用機能
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（情報係数）、Zスコア正規化
- 監査ログ
  - signal_events / order_requests / executions 等の監査スキーマ初期化（init_audit_db / init_audit_schema）

セットアップ手順
----------------
1. Python 環境作成（例）:
   - Python 3.10+ を推奨
   - 仮想環境作成:
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール:
   - 必須（本コードベースで参照されている主なパッケージの例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   注: 実際の requirements.txt / pyproject.toml がある場合はそちらを使用してください。

3. パッケージをローカルインストール（任意）:
   - pip install -e .  （パッケージ化されている場合）

4. 環境変数 (.env) の準備:
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと、自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須の環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN — Slack 通知用ボットトークン（本システムで Slack を使う場合）
     - SLACK_CHANNEL_ID — Slack チャネル ID
     - KABU_API_PASSWORD — kabuステーション API を使用する場合
     - OPENAI_API_KEY — OpenAI API を使用する場合（score_news/score_regime の引数でも指定可）
   - データベースパスは環境変数で上書き可能（デフォルト値は例を参照）:
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
   - 例（.env）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=sk-...
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - DUCKDB_PATH=data/kabusys.duckdb

使い方（簡易例）
----------------

- 設定の利用:
  - from kabusys.config import settings
  - settings.jquants_refresh_token などでアクセス。未設定の必須変数は _require によって ValueError を投げます。

- DuckDB 接続を作成:
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行（run_daily_etl）:
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - result は ETLResult オブジェクト。to_dict() で内容を取得できます。

- ニュースセンチメント (ai.news_nlp.score_news):
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  - api_key を None にすると環境変数 OPENAI_API_KEY を参照します。

- 市場レジーム判定 (ai.regime_detector.score_regime):
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - r = score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  - 内部で ETF 1321 の ma200_ratio とマクロニュースを合成して market_regime テーブルへ書き込みます。

- 監査ログスキーマ初期化:
  - from kabusys.data.audit import init_audit_db
  - conn_audit = init_audit_db(settings.duckdb_path)  # 既存DB に付け加えたい場合はその接続を使って init_audit_schema を呼ぶ

重要な挙動・注意点
------------------
- .env の自動読み込みは、プロジェクトルートを .git または pyproject.toml で探索して行われます。テストなどで自動ロードを止めたいときは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しは gpt-4o-mini を想定し、JSON Mode（response_format）の使用をコード内で行っています。API 呼び出し失敗時はフェイルセーフとして 0.0（中立）やスキップ動作を行い、例外を上位に上げない設計の箇所があります（ログ出力あり）。
- DuckDB に対する executemany で空リストを渡すと一部バージョンでエラーになるため、コード内で空チェックを行っています。
- Look-ahead bias を避けるため、内部関数は date.today()/datetime.today() を直接参照しないよう設計されています（target_date を明示的に渡すことを推奨）。

ディレクトリ構成（概要）
----------------------
下記は src/kabusys 以下の主要モジュールの一覧（抜粋）です:

- kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（銘柄別）
    - regime_detector.py     — 市場レジーム判定（1321 + マクロ）
  - data/
    - __init__.py
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL 結果型のエクスポート
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - news_collector.py      — RSS ニュース収集（セキュア実装）
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（Zスコア等）
    - audit.py               — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Value / Volatility 計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー等

（プロジェクトルート）
- src/
  - kabusys/ (上記)
- pyproject.toml / setup.cfg / .git/ など（存在する想定）

開発者向けメモ
--------------
- OpenAI の呼び出しはモジュール内でラップしており、ユニットテスト時には _call_openai_api を patch して差し替える想定です。
- J-Quants API 呼び出しは内部で固定間隔レートリミッタを使用し、401 発生時は自動でトークンリフレッシュを試みる実装です。
- DuckDB の日付列は date オブジェクトで扱うことを前提にしています。time zone の混入を避けるため、監査モジュールなどでは SET TimeZone='UTC' を明示しています。

サポート / 追加情報
-------------------
- 実運用で使用する前に、必須環境変数の設定、APIキーの権限、DuckDBのバックアップ・権限などを確認してください。
- 実稼働環境（live）では settings.env が 'live' となるよう KABUSYS_ENV を設定してください（有効値: development / paper_trading / live）。

以上がこのコードベースのREADME（日本語）です。必要であれば、具体的な .env.example や実行コマンド集、API シーケンス図など追記します。どの部分を詳しく書けば良いか教えてください。