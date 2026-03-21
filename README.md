KabuSys — 日本株自動売買フレームワーク
=================================

概要
----
KabuSys は日本株のデータ取得・ETL・特徴量計算・シグナル生成・発注監査までを想定した
モジュール群です。J-Quants API など外部データソースから株価・財務・マーケットカレンダー・ニュースを収集し、
DuckDB に蓄積、研究（research）モジュールでファクターを計算、strategy モジュールで
正規化・スコア合成を行って売買シグナルを生成します。発注・監視のためのスキーマ・監査ロジックも含みます。

主な特徴
--------
- J-Quants API クライアント（ページネーション・レート制御・自動トークンリフレッシュ・リトライ）
- DuckDB を用いた永続ストア（Raw / Processed / Feature / Execution 層のスキーマ定義）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集（RSS、URL 正規化、SSRF 対策、記事 → 銘柄マッチング）
- 研究向けファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 特徴量正規化・合成（Z スコア正規化、ユニバースフィルタ）
- シグナル生成（コンポーネントを重み合算、Bear レジーム抑制、エグジット判定）
- 監査ログ（シグナル → 発注 → 約定までトレース可能なスキーマ）
- 外部依存を極力避けた実装（標準ライブラリと duckdb / defusedxml 等の最小依存）

前提条件
--------
- Python 3.10+
- 必要パッケージ例:
  - duckdb
  - defusedxml
  - （その他、実行環境に応じて urllib など標準ライブラリで対応可能）
- 環境変数に API トークンなどを設定（下記参照）

セットアップ手順
----------------

1. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb defusedxml

   ※ プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください。

3. 環境変数の準備
   - プロジェクトルートに .env / .env.local を置くと、自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_api_password
     - SLACK_BOT_TOKEN=your_slack_bot_token
     - SLACK_CHANNEL_ID=your_slack_channel_id
   - 省略可能な設定（デフォルトあり）:
     - KABUSYS_ENV=development|paper_trading|live  (default: development)
     - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL (default: INFO)
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env 自動読み込みを無効化

   例 .env（テンプレート）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=secret-password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから実行:
     ```
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")
     ```
   - init_schema(":memory:") でインメモリ DB を利用可能。

使い方（簡易ガイド）
------------------

- ETL（日次パイプライン）を実行する
  ```
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定しなければ今日で実行
  print(result.to_dict())
  ```

- 研究用ファクター計算 → 特徴量構築
  ```
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.strategy import build_features
  import duckdb
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  cnt = build_features(conn, target_date=date(2024, 1, 10))
  print(f"features upserted: {cnt}")
  ```

- シグナル生成
  ```
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection, init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024,1,10))
  print(f"signals written: {total}")
  ```

- ニュース収集ジョブ実行例
  ```
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema, get_connection

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- J-Quants API を直接使ってデータ取得する（テスト・バッチ用）
  ```
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を利用
  recs = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

設定 / 環境変数（主要）
---------------------
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 連携パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（必須）
- DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（省略時: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development|paper_trading|live）
- LOG_LEVEL: ログレベル

注意事項 / 実装上のポイント
--------------------------
- .env の自動読み込み: プロジェクトルート（.git または pyproject.toml を探索）から .env / .env.local を読み込みます。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマは init_schema() で一度作成してください。get_connection() は既存 DB への接続のみ行います。
- J-Quants クライアントは API レート制限（120 req/min）を厳守するため内部でスロットリングとリトライを行います。
- ニュース取得は SSRF・XML Bomb 等を考慮し defusedxml とカスタムリダイレクト検査を使用しています。
- Strategy 層はルックアヘッドバイアス（future leakage）を避ける設計で、target_date 時点の利用可能データのみを使用します。
- ログや Slack 通知等は別途アプリ側で設定して用いる想定です。

ディレクトリ構成（主要ファイル）
----------------------------
- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py             — RSS ニュース収集・前処理・DB 保存
    - schema.py                     — DuckDB スキーマ定義と初期化（init_schema）
    - pipeline.py                   — ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py        — マーケットカレンダー管理（営業日判定等）
    - features.py                   — feature utilities (zscore re-export)
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査ログスキーマ（信頼性追跡用）
    - quality.py?                   — 品質チェック（存在する場合）
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum/volatility/value）
    - feature_exploration.py        — IC 計算・将来リターン・統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py        — 特徴量構築（正規化・ユニバースフィルタ）
    - signal_generator.py           — シグナル生成（スコア合成・売買判定）
  - execution/                      — 発注・約定管理用パッケージ（空または実装）
  - monitoring/                     — 監視・アラート関連（空または実装）

拡張・運用メモ
---------------
- 本番運用時は KABUSYS_ENV を live にし、paper_trading モードを用意してブロックしきい値等を切り替えます。
- 発注実装（execution 層）はシステムに依存するため、kabuステーション等ブローカー API に合わせた実装を追加してください。
- DB バックアップ、監査ログのエクスポート、監視（Prometheus/Grafana 等）との連携を検討してください。
- テストは id_token 注入や HTTPクライアントのモックで容易に行える設計になっています（モジュール内で注入可能な設計を参照）。

ライセンス・貢献
----------------
- 本リポジトリのライセンス情報が無い場合は、運用方針に合わせて LICENSE ファイルを追加してください。
- バグ報告や機能提案は Issue を立ててください。PR はモジュール単位で小さく分けることを推奨します。

お問い合わせ
------------
- 実装や設計の意図に関する問い合わせは README に追記する連絡先（例: Slack チャンネル、メール）を用意してください。

以上が KabuSys の概要と基本的な導入・利用手順です。README に追記したい実行例や CI / デプロイ手順、requirements.txt / pyproject.toml の内容があれば追記します。