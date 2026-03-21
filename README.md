KabuSys
=======

日本株向けの自動売買基盤コンポーネント群です。データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査（発注→約定トレーサビリティ）などの機能を含むライブラリ群として設計されています。

主な設計方針
- ルックアヘッドバイアス対策：各処理は target_date 時点までのデータのみを使うよう設計されています。
- 冪等性：DB への保存は ON CONFLICT / トランザクション等で冪等に行います。
- DuckDB を分析用 DB に採用（ローカルファイル / :memory: をサポート）。
- 外部 API 呼び出し（J-Quants）に対してレート制御・リトライ・トークン自動更新を実装。
- ニュース収集は RSS を想定し、SSRF・XML bomb 等のセキュリティ対策を実装。

機能一覧
- データ取得 & 保存
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - 差分 ETL パイプライン（run_daily_etl など）
  - raw レイヤー / processed / feature / execution 用の DuckDB スキーマ定義と初期化
- データ品質管理
  - ETL 実行後の品質チェック（quality モジュールに依存）
- 特徴量（Feature）関連
  - research 層のファクター計算（モメンタム、ボラティリティ、バリュー等）
  - feature_engineering.build_features による正規化・ユニバースフィルタ・features テーブルへの保存
- シグナル生成
  - signal_generator.generate_signals による最終スコア計算（複数コンポーネント合成）と BUY/SELL シグナル生成
  - Bear レジーム抑制やストップロス等のエグジット判定を含む
- ニュース収集
  - RSS 取得、前処理、raw_news への冪等保存、銘柄コード抽出と news_symbols への紐付け
- マーケットカレンダー管理
  - market_calendar の更新ジョブ、営業日判定ユーティリティ（next/prev/is_trading_day 等）
- 監査・トレーサビリティ
  - signal_events / order_requests / executions 等の監査テーブル定義（発注〜約定のトレース）

セットアップ手順（ローカル開発用）
1. リポジトリをクローン
   - git clone <リポジトリURL>
   - cd <repo>

2. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  # Unix/macOS
   - .venv\Scripts\activate     # Windows

3. 必要パッケージのインストール（最小）
   - pip install duckdb defusedxml
   - （プロジェクトをパッケージ化している場合）pip install -e .

   ※requirements.txt / pyproject.toml がある場合はそれに従ってください。上記は最低限の実行に必要な外部依存の一例です。

4. 環境変数の設定
   - このライブラリは .env / .env.local または OS 環境変数から設定値を読み込みます（config.py の自動読み込み機能）。
   - 重要な環境変数（少なくとも開発で使う主なもの）:
     - JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD：kabu API のパスワード（必須）
     - SLACK_BOT_TOKEN：Slack 通知に使う Bot トークン（必須）
     - SLACK_CHANNEL_ID：通知先チャンネル ID（必須）
     - DUCKDB_PATH：DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH：監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV：development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL：DEBUG/INFO/...（デフォルト: INFO）
   - 自動ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. データベース初期化
   - Python REPL またはスクリプトで DuckDB スキーマを初期化します。例:

     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" も可

使い方（代表的なワークフロー）
- 日次 ETL 実行（市場カレンダー・株価・財務を差分取得）
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- 特徴量の作成（research の生ファクター → features テーブル）
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features

  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024, 1, 31))
  print(f"features upserted: {n}")

- シグナル生成（features + ai_scores + positions を参照 → signals テーブル）
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.strategy import generate_signals

  conn = init_schema("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024, 1, 31))
  print(f"signals written: {total}")

- ニュース収集ジョブ（RSS フィードから raw_news を保存）
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 既知銘柄セット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)

- J-Quants API を直接利用する例
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  token = get_id_token()  # settings.jquants_refresh_token を使用
  recs = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

設定ファイル（.env）について
- .env / .env.local はプロジェクトルート（.git または pyproject.toml を探索して決定）から自動で読み込まれます。
- 読み込み順は: OS環境 > .env.local > .env です（.env.local が優先で上書き）。
- テストや特殊用途で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須環境変数が不足していると Settings 呼び出し時に ValueError が発生します。

主要モジュール・ディレクトリ構成
（src/kabusys 配下。主要ファイルのみ抜粋）

- kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - schema.py            — DuckDB スキーマ定義と init_schema
    - stats.py             — zscore_normalize 等の統計ユーティリティ
    - news_collector.py    — RSS ニュース取得・保存・銘柄抽出
    - calendar_management.py — カレンダー更新 / 営業日ユーティリティ
    - features.py          — features 用公開インターフェース
    - audit.py             — 監査ログ用 DDL（signal_events / order_requests / executions）
  - research/
    - __init__.py
    - factor_research.py   — momentum / volatility / value 等のファクター計算
    - feature_exploration.py — forward returns / IC / summary 等の分析ユーティリティ
  - strategy/
    - __init__.py          — build_features / generate_signals を公開
    - feature_engineering.py — features の構築（正規化・フィルタ・UPSERT）
    - signal_generator.py  — final_score 計算と signals への書き込み
  - execution/              — （発注 / execution 層の骨格）
  - monitoring/             — 監視・運用用コード（DB監視など）

補足 / 運用上の注意
- DuckDB のファイルはデフォルトで data/kabusys.duckdb に保存されます。運用環境では適切な永続ストレージに配置してください。
- J-Quants の API レート制限（120 req/min）やリトライ挙動は jquants_client に実装済みですが、運用スケジュールは充分に検討してください。
- ニュース収集では RSS のサイズ・XML の安全性・SSRF を考慮した堅牢な実装を行っていますが、外部フィードの信頼性は変動するため例外処理を行ってください。
- 本コードベースは戦略のロジック／パラメータ（閾値、重み等）を含みます。実運用する場合は paper_trading 環境で十分な検証を行ってください（KABUSYS_ENV=paper_trading）。

貢献・拡張
- 新しいファクターやシグナルロジックの追加、外部ブローカー接続の実装、品質チェック（quality モジュール）の拡張などが想定されます。
- 変更時は DB スキーマ互換性や既存データの移行方針に注意してください。

ライセンス・連絡
- 本リポジトリのライセンス情報や連絡先はリポジトリのトップレベル（LICENSE / CONTRIBUTING）を参照してください（ここには含まれていません）。

以上。README に記載してほしい追加事項（例えば実運用手順、CI 設定、requirements.txt の内容など）があれば教えてください。必要に応じて README を拡張します。