KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は、J‑Quants 等のデータソースから日本株データを取得・整備し、特徴量作成→シグナル生成→実行（発注管理）までを想定した自動売買プラットフォームのコアライブラリです。本リポジトリは主に以下の責務を持つモジュール群で構成されています。

- データ取得・ETL（J‑Quants API 経由で株価・財務・カレンダーを取得し DuckDB に保存）
- 特徴量計算（research 層で算出した生ファクターの正規化・合成）
- シグナル生成（特徴量 + AI スコアなどを統合して BUY/SELL シグナルを作成）
- ニュース収集（RSS から記事を収集して DB に保存）
- DuckDB スキーマ定義・初期化、カレンダー管理、品質チェック（品質モジュールは別途）

主な機能
--------
- J‑Quants API クライアント（レートリミット・リトライ・トークン自動更新を考慮）
- DuckDB ベースのスキーマ定義と初期化（冪等な DDL）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- ファクター計算（モメンタム / ボラティリティ / バリュー等）
- Z スコア正規化ユーティリティ
- 特徴量の構築（ユニバースフィルタ・正規化・クリップ・features テーブルへの upsert）
- シグナル生成（重み付けされた最終スコア計算、Bear レジーム抑制、エグジット判定、signals テーブルへの書込）
- RSS ニュース収集・正規化・銘柄抽出（SSRF 対策、XML 安全パース、トラッキング除去）
- マーケットカレンダー管理（営業日判定 / 次営業日・前営業日の取得 / カレンダー更新ジョブ）
- 実行・監査用スキーマ（signal / order / execution / positions 等／監査のためのテーブル設計）

動作環境（推奨）
----------------
- Python 3.10 以上（ソース内で | 型構文を使用）
- 推奨パッケージ（最低限）:
  - duckdb
  - defusedxml
（プロジェクトの requirements.txt / pyproject.toml を用意している場合はそちらに従ってください）

セットアップ手順
----------------

1. リポジトリをクローンし、仮想環境を作成
   - 例:
     python -m venv .venv
     source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 必要パッケージをインストール
   - 最低限:
     pip install duckdb defusedxml
   - （任意）開発用に他のパッケージがあれば pyproject.toml / requirements.txt を参照してインストールしてください。

3. 環境変数（.env）を用意
   - ルートに .env/.env.local を置くと自動で読み込まれます（自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須の環境変数（config.Settings から取得されるもの）:
     - JQUANTS_REFRESH_TOKEN — J‑Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知に利用するボットトークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
   - 任意 / デフォルト有り:
     - KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   - 最小の .env 例:
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb

4. DuckDB スキーマ初期化
   - Python REPL / スクリプトから:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

使い方（代表的な操作）
--------------------

- 日次 ETL 実行
  - ETL はデータ取得 → 保存 → 品質チェックを行うエントリポイント run_daily_etl で実行します。
  - 例:
    from datetime import date
    import duckdb
    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_daily_etl

    conn = init_schema("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- 特徴量（features）構築
  - DuckDB 接続と対象日を渡して features を構築します。
  - 例:
    from datetime import date
    from kabusys.strategy import build_features
    from kabusys.data.schema import get_connection

    conn = get_connection("data/kabusys.duckdb")
    n = build_features(conn, date(2024, 1, 15))
    print(f"built features for {n} symbols")

- シグナル生成
  - 生成された features と ai_scores, positions を元に signals テーブルへ書き込みます。
  - 例:
    from datetime import date
    from kabusys.strategy import generate_signals
    from kabusys.data.schema import get_connection

    conn = get_connection("data/kabusys.duckdb")
    total = generate_signals(conn, date(2024, 1, 15), threshold=0.6)
    print(f"signals written: {total}")

- ニュース収集ジョブ
  - RSS を取得して raw_news に保存、必要なら銘柄紐付けを行います。
  - 例:
    from kabusys.data.news_collector import run_news_collection
    from kabusys.data.schema import get_connection

    conn = get_connection("data/kabusys.duckdb")
    results = run_news_collection(conn)
    print(results)

- カレンダー更新ジョブ
  - DataPlatform 用のカレンダー更新を行う:
    from kabusys.data.calendar_management import calendar_update_job
    conn = get_connection("data/kabusys.duckdb")
    saved = calendar_update_job(conn)
    print(f"saved calendar rows: {saved}")

運用上の注意
------------
- 環境変数の取り扱い:
  - .env の自動読込はプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト時など自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Look‑ahead バイアス防止:
  - 特徴量やシグナル生成は target_date 時点の情報のみを使用するように設計されています（将来情報を参照しないことに注意）。
- 冪等性:
  - DuckDB への保存関数は基本的に ON CONFLICT を用い冪等的に動作します（重複更新は上書き、重複挿入はスキップ等）。
- API レート制限:
  - J‑Quants など外部 API へのアクセスはレート制限・リトライ・トークンリフレッシュ等を実装済みです。大規模な同時リクエストは避けてください。

主要ディレクトリ構成
--------------------

(src 以下を基準に簡易ツリー)

- src/kabusys/
  - __init__.py               — パッケージ定義（__version__ 等）
  - config.py                 — 環境変数 / 設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py       — J‑Quants API クライアント（fetch / save / rate limit）
    - news_collector.py       — RSS ニュース取得・保存・銘柄抽出
    - schema.py               — DuckDB スキーマ定義と init_schema / get_connection
    - stats.py                — zscore_normalize 等の統計ユーティリティ
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  — 市場カレンダー管理ジョブ / 営業日ユーティリティ
    - features.py             — data 層の features インターフェース（再エクスポート）
    - audit.py                — 発注～約定にかかる監査用スキーマ
  - research/
    - __init__.py
    - factor_research.py      — モメンタム / ボラティリティ / バリュー等のファクター算出
    - feature_exploration.py  — 将来リターン計算 / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py  — 生ファクターを正規化・合成して features テーブルに保存
    - signal_generator.py     — features + ai_scores から BUY/SELL シグナル生成
  - execution/                 — 発注/実行関連（骨組み）  ※詳細実装は別途
  - monitoring/                — 監視系（定義あり） ※詳細は別途

ドキュメント参照（コード内注記）
-------------------------------
多くの動作仕様（ユニバース定義、StrategyModel、DataPlatform、Research の設計方針等）はコード内 docstring やコメントにまとめられています。実運用に際しては、各モジュールにある docstring（例: strategy/*, data/*, research/*）を参照してください。

開発に貢献するには
-------------------
- コードの可読性とテストを重視してください。
- 新しい機能を追加する際はドキュメント（docstring）と型注釈を付けてください。
- API の外部呼び出し部分はモック可能な設計（id_token 注入や _urlopen の差し替え）になっています。ユニットテストではこれらを利用してください。

ライセンス・注意事項
--------------------
- 本 README はコードベースの説明と基本的な手順をまとめたものです。実際に運用する際は自己責任で行ってください（特にリアルマネーでの運用は十分な検証・リスク管理のもとで行ってください）。
- ライセンス・著作権情報はリポジトリルートの LICENSE ファイル（ある場合）を参照してください。

以上。プロジェクトを立ち上げる際に不明点があれば、どの操作の手順やコード例が必要か教えてください。追加で README に含めるコマンド例や systemd / cron ジョブサンプル等も作成できます。