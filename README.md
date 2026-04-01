KabuSys — 日本株データパイプライン／研究／AI ツールキット
================================================================

概要
----
KabuSys は日本株の自動売買・研究基盤向けライブラリ群です。本コードベースは主に以下を含みます。

- J-Quants からのデータ取得（株価・財務・上場情報・市場カレンダー）と DuckDB への ETL
- RSS ベースのニュース収集（raw_news）とニュース前処理（SSRF 対策、トラッキング除去等）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価・市場レジーム判定
- ファクター算出（モメンタム／バリュー／ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損／重複／スパイク／日付不整合）
- 監査ログ（signal → order_request → executions のトレース）用スキーマ定義
- 環境設定管理（.env の自動読み込み・保護機能）

機能一覧
--------
主な機能（抜粋）:

- data
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
  - pipeline: 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
  - news_collector: RSS 収集・前処理・記事ID生成（SSRF 対策、サイズ制限）
  - quality: データ品質チェック群（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ用テーブル / 初期化ユーティリティ
  - calendar_management: 市場カレンダー管理と営業日判定ユーティリティ
  - stats: Zスコア正規化などの統計ユーティリティ
- ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを計算して ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースから市場レジーム判定
- research
  - factor_research: モメンタム/バリュー/ボラティリティ等のファクター計算
  - feature_exploration: 将来リターン計算・IC（情報係数）・統計サマリ等

セットアップ手順
----------------

前提
- Python 3.10 以上を推奨（Union 型注記などを利用）
- ネットワーク接続（J-Quants / OpenAI / RSS ソース）

1. リポジトリをクローン／チェックアウト
   - 例: git clone <repo-url>

2. 依存ライブラリをインストール
   - 代表的な依存パッケージ:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - 開発用に editable インストールする場合:
     - pip install -e .

3. 環境変数の設定 (.env)
   - プロジェクトルートに .env を置くと自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（少なくとも以下を設定してください）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=your_openai_api_key
     - KABU_API_PASSWORD=（kabu API を使う場合）
     - SLACK_BOT_TOKEN=（Slack 通知を使う場合）
     - SLACK_CHANNEL_ID=（Slack）
   - 任意（デフォルト値あり）:
     - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
     - LOG_LEVEL=DEBUG|INFO|... (デフォルト: INFO)
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PID_FILE_PATH=data/execution.pid
     - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

   サンプル (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. データベース初期化（監査用など）
   - 監査 DB を初期化する例:
     - python:
       >>> from kabusys.data.audit import init_audit_db
       >>> conn = init_audit_db("data/audit.duckdb")

使い方（主要 API と実行例）
-------------------------

以下はライブラリの代表的な利用イメージです。すべての関数は DuckDB 接続を受け取る設計になっており、ルックアヘッドバイアスに注意して日付を明示することを推奨します。

1. 日次 ETL を実行する（J-Quants から差分取得し保存）
   - 例:
     >>> import duckdb
     >>> from datetime import date
     >>> from kabusys.data.pipeline import run_daily_etl
     >>> conn = duckdb.connect("data/kabusys.duckdb")
     >>> result = run_daily_etl(conn, target_date=date(2026,3,20))
     >>> print(result.to_dict())

2. ニュースセンチメント（銘柄別）を算出して ai_scores に保存
   - 例:
     >>> from kabusys.ai.news_nlp import score_news
     >>> from datetime import date
     >>> conn = duckdb.connect("data/kabusys.duckdb")
     >>> n = score_news(conn, target_date=date(2026,3,20))  # 要 OPENAI_API_KEY
     >>> print(f"書込銘柄数: {n}")

3. 市場レジーム判定（MA200 と LLM のマクロセンチメントの合成）
   - 例:
     >>> from kabusys.ai.regime_detector import score_regime
     >>> conn = duckdb.connect("data/kabusys.duckdb")
     >>> score_regime(conn, target_date=date(2026,3,20))  # 要 OPENAI_API_KEY

4. J-Quants API を直接呼んでデータを取得 / 保存
   - 例:
     >>> from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
     >>> records = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
     >>> save_daily_quotes(conn, records)

5. RSS を取得する（ニュースコレクタの一部）
   - 例:
     >>> from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
     >>> articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")

6. 監査ログスキーマの初期化
   - 例:
     >>> from kabusys.data.audit import init_audit_db
     >>> conn = init_audit_db("data/audit.duckdb")

注意事項 / トラブルシューティング
---------------------------------
- 環境変数が不足している場合、Settings のプロパティが ValueError を投げます（例: OPENAI_API_KEY 未設定）。
- J-Quants API にはレート制限があり、ライブラリは固定間隔スロットリングとリトライを実装しています。大量取得時は時間がかかる場合があります。
- OpenAI 呼び出しはリトライとフォールバック（失敗時は中立スコア 0.0）を実装していますが、API キーや利用制限には注意してください。
- DuckDB の executemany はバージョンによって空リストの扱いが異なるため、コードは空リストの場合に呼ばないよう設計されています。

ディレクトリ構成
----------------
（主なファイル／モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/.env 読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（銘柄別センチメント）
    - regime_detector.py            — 市場レジーム判定（MA200 + マクロ）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + 保存処理
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult のエクスポート
    - news_collector.py             — RSS 取得 / 前処理 / raw_news 保存
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize 等）
    - calendar_management.py        — 市場カレンダー管理 / 営業日判定
    - audit.py                      — 監査ログ用 DDL と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py            — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py        — 将来リターン / IC / summaries
  - ai/
  - monitoring/                     — 監視モジュール（ディレクトリは存在想定）
  - strategy/                       — 戦略レイヤ（ディレクトリは存在想定）
  - execution/                      — 注文実行関連（ディレクトリは存在想定）

開発・貢献
---------
- コードはモジュール単位でテスト可能なように設計されています（例: OpenAI 呼出部分をモックしてテスト可能）。
- PR や Issue を通じてバグ報告・機能提案を受け付けてください（内部プロジェクトの場合はチームルールに従ってください）。

ライセンス
---------
- 本リポジトリに明記されていないため、使用時はリポジトリ内の LICENSE ファイルやプロジェクト規約を確認してください。

最後に
------
この README はコードベースの主要な使い方と構成を簡潔にまとめたものです。具体的な関数や引数の詳細は各モジュールのドキュメンテーション（関数 docstring）を参照してください。必要であれば使い方のサンプルや運用手順書（デプロイ・監視・ローテーション等）を追加します。