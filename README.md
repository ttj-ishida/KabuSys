KabuSys — 日本株自動売買基盤（README）
====================================

概要
----
KabuSys は日本株向けの自動売買／データ基盤ライブラリです。  
DuckDB をデータレイヤに使い、J-Quants API から市場データ・財務データ・市場カレンダーを取得して ETL → 特徴量生成 → シグナル生成 → 発注（実装は execution 層で行う想定）までのワークフローを想定しています。  
設計方針として、ルックアヘッドバイアスの防止、冪等性（ON CONFLICT）やトランザクションによる原子性、API レート制御・リトライ、セキュリティ（SSRF/XML攻撃対策）などに配慮しています。

主な機能
---------
- 環境変数・設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込み（無効化可）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足・財務・市場カレンダー取得、トークン自動リフレッシュ、レート制御、リトライ
  - DuckDB へ冪等保存（save_* 関数）
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新、バックフィル、品質チェック統合（run_daily_etl 等）
- スキーマ定義・初期化（kabusys.data.schema）
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution 層）
  - init_schema() でデータベース初期化
- ニュース収集（kabusys.data.news_collector）
  - RSS 収集、前処理、記事ID 正規化、銘柄抽出・紐付け、DB 保存
  - SSRF・XML攻撃対策、受信サイズ制限、重複回避
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日検索、カレンダー更新ジョブ
- 研究・ファクター計算（kabusys.research）
  - モメンタム、ボラティリティ、バリュー等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン、IC（Spearman）計算、統計サマリー
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - raw ファクターを統合 → Z スコア正規化 → features テーブルへ UPSERT
- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算、BUY/SELL シグナル生成、signals テーブルへ保存
- 統計ユーティリティ（kabusys.data.stats）
  - Z スコア正規化など

要件
----
- Python 3.10 以上（型注釈に PEP 604 形式（A | B）を使用）
- 必要なパッケージ（例）
  - duckdb
  - defusedxml
（外部 HTTP は標準ライブラリ urllib を使用するため追加 HTTP ライブラリは不要）

セットアップ手順
----------------

1. リポジトリをクローン / コピー
   - 例:
     - git clone <リポジトリURL>
     - cd <project>

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml

   （パッケージ管理には pyproject.toml / requirements.txt があればそれに従ってください。開発インストール: pip install -e .）

4. 環境変数設定
   - プロジェクトルートに .env を作成するか OS の環境変数を設定します。自動読み込みは kabusys.config で行われます（.env.local は上書き優先）。
   - 主要な必須変数:
     - JQUANTS_REFRESH_TOKEN = <J-Quants のリフレッシュトークン>
     - KABU_API_PASSWORD = <kabuステーションAPI パスワード>
     - SLACK_BOT_TOKEN = <Slack Bot Token>
     - SLACK_CHANNEL_ID = <Slack チャンネルID>
   - 任意:
     - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
     - SQLITE_PATH (監視用 DB デフォルト data/monitoring.db)
     - KABUSYS_ENV = development | paper_trading | live
     - LOG_LEVEL = DEBUG|INFO|WARNING|ERROR|CRITICAL
     - KABUSYS_DISABLE_AUTO_ENV_LOAD = 1 （自動 .env ロードを無効化）

   - .env の例:
     - JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     - KABU_API_PASSWORD=your_kabu_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C0123456789

5. データベース初期化
   - Python REPL やスクリプトから init_schema() を呼び出して DuckDB を初期化します。
   - 例:
     - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

使い方（よく使う操作例）
-----------------------

以下は Python スクリプト / REPL での実行例です（必要に応じてスクリプト化してください）。

1. DuckDB 接続とスキーマ初期化
   - from kabusys.data.schema import init_schema, get_connection
     conn = init_schema("data/kabusys.duckdb")  # 初回は init_schema、以降は get_connection

2. 日次 ETL（市場カレンダー + 株価 + 財務 + 品質チェック）
   - from kabusys.data.pipeline import run_daily_etl
     result = run_daily_etl(conn)  # 戻り値は ETLResult オブジェクト
     print(result.to_dict())

3. 特徴量を作る（build_features）
   - from kabusys.strategy import build_features
     from datetime import date
     n = build_features(conn, date(2024, 1, 31))
     print(f"upserted features: {n}")

4. シグナル生成（generate_signals）
   - from kabusys.strategy import generate_signals
     from datetime import date
     total = generate_signals(conn, date(2024, 1, 31))
     print(f"signals written: {total}")

5. ニュース収集・保存
   - from kabusys.data.news_collector import run_news_collection
     # known_codes があれば記事中の 4 桁銘柄コード抽出で紐付けを行う
     res = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
     print(res)

6. カレンダー更新ジョブ（夜間バッチ）
   - from kabusys.data.calendar_management import calendar_update_job
     saved = calendar_update_job(conn)
     print(f"calendar saved: {saved}")

7. J-Quants から直接データを取得して保存（開発用）
   - from kabusys.data import jquants_client as jq
     records = jq.fetch_daily_quotes(date_from=..., date_to=...)
     jq.save_daily_quotes(conn, records)

補足 / 運用上の注意
-------------------
- .env の自動読み込みは kabusys.config でプロジェクトルートを .git または pyproject.toml を基準に探索して行います。テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API はレート制限（デフォルト 120 req/min）や 401 トークン期限切れ対応、リトライロジックが組み込まれています。長時間のバッチ実行やページネーション時はログを確認してください。
- ETL や DB 更新は各ステップでエラーハンドリングされていますが、監査や運用のために ETLResult のログ・保存を行ってください。
- シグナル生成は features / ai_scores / positions に依存します。AI スコアやポジション情報は別プロセスで投入してください。
- execution 層は発注 API 統合を想定しています。本リポジトリでは execution パッケージは空の初期化が含まれています（実装はプロジェクト固有に追加してください）。

ディレクトリ構成
----------------
（主要ファイルを抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント + 保存
    - news_collector.py              — RSS 収集・前処理・保存
    - schema.py                      — DuckDB スキーマ定義・初期化
    - pipeline.py                    — ETL パイプライン（run_daily_etl など）
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py         — 市場カレンダー管理
    - features.py                    — data.stats の公開ラッパー
    - audit.py                       — 監査ログスキーマ
  - research/
    - __init__.py
    - factor_research.py             — モメンタム/ボラティリティ/バリュー等
    - feature_exploration.py         — IC/将来リターン/統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py         — features テーブル生成（build_features）
    - signal_generator.py            — final_score 計算・signals 生成
  - execution/
    - __init__.py                    — 発注層（実装は運用側で追加）
  - monitoring/                       — 監視・Slack 通知等を想定（存在するとして）

ライセンス・貢献
----------------
- 本 README はコードベースに基づく概要と使い方の説明です。実運用での使用にあたっては J-Quants 利用規約、証券会社 API の利用規約、及び各種法令に従ってください。
- バグ報告・機能追加等は Issue / Pull Request を送ってください。

問い合わせ
----------
- 開発者ドキュメントや追加の API 仕様（StrategyModel.md / DataPlatform.md 等）はリポジトリ内のドキュメントを参照してください。README の内容や使用方法で不明点があればお知らせください。