# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
DuckDB をデータレイヤに使い、J-Quants から市場データ・財務データ・カレンダーを取得して ETL → 特徴量生成 → シグナル生成 → 実行（発注）へと接続することを想定したモジュール群を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築を支援する Python パッケージです。主な役割は以下の通りです。

- J-Quants API からのデータ取得（株価日足、財務、マーケットカレンダー）
- DuckDB を用いたデータスキーマ定義と永続化（冪等保存）
- ETL（差分取得／バックフィル／品質チェック）パイプライン
- 研究用ファクター計算（momentum / volatility / value 等）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ）
- シグナル生成ロジック（最終スコア計算、BUY / SELL 判定）
- ニュース収集（RSS → raw_news、銘柄抽出）
- 発注・監査テーブル等のスキーマ（execution / audit 層）

設計方針として、ルックアヘッドバイアスを避けること、ETL/保存/集計の冪等性・トレーサビリティを重視しています。

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
  - schema: DuckDB のスキーマ定義 & 初期化（raw / processed / feature / execution 層）
  - pipeline: 差分 ETL（prices / financials / calendar）と日次 ETL run_daily_etl
  - news_collector: RSS 取得・前処理・DB 保存・銘柄抽出
  - calendar_management: 営業日判定・翌営業日/前営業日のユーティリティ、カレンダー更新ジョブ
  - stats: Z スコア正規化などの統計ユーティリティ
  - audit: 発注〜約定の監査ログ用DDL（トレーサビリティ）
- research
  - factor_research: momentum / volatility / value ファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリ等（研究用）
- strategy
  - feature_engineering.build_features: 生ファクターの正規化・フィルタ・features テーブルへのアップサート
  - signal_generator.generate_signals: features + ai_scores を統合して final_score を計算、signals テーブルへ保存
- config
  - 環境変数管理（.env 自動読み込み、必須 env の取得ヘルパ）
- execution / monitoring
  - 発注層 / 監視層のためのスケルトン（スキーマや設計を含む）

---

## セットアップ手順

前提: Python 3.9+（typing の | 型アノテーションを利用するため）を推奨します。

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（推奨）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存パッケージをインストール
   - 最低限必要なパッケージ:
     - duckdb
     - defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - （プロジェクトに requirements.txt があれば）
     ```
     pip install -r requirements.txt
     ```
   - パッケージを開発モードでインストールできる場合:
     ```
     pip install -e .
     ```

4. 環境変数の設定
   - .env または .env.local をプロジェクトルートに置くと自動読み込みされます（config.py）。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須の環境変数（例）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD : kabu API のパスワード（必須）
     - SLACK_BOT_TOKEN : Slack 通知用ボットトークン（必須）
     - SLACK_CHANNEL_ID : Slack チャネル ID（必須）
   - 任意またはデフォルトあり:
     - KABUSYS_ENV : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL : DEBUG/INFO/...（デフォルト INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env 読み込み無効化
     - DUCKDB_PATH : デフォルト `data/kabusys.duckdb`
     - SQLITE_PATH : デフォルト `data/monitoring.db`

   例の .env（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=yyyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本例）

以下はパッケージ API を使った典型的な操作例です（Python スクリプト/REPL）。

1. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema, get_connection
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)  # ファイルを作成して全テーブルを作成
   # 既存 DB に接続するだけなら:
   # conn = get_connection(settings.duckdb_path)
   ```

2. 日次 ETL 実行（J-Quants から差分フェッチして保存）
   ```python
   from kabusys.data.pipeline import run_daily_etl

   result = run_daily_etl(conn)  # target_date は省略で今日（営業日に補正）
   print(result.to_dict())
   ```

3. 特徴量の構築（features テーブルへ保存）
   ```python
   from kabusys.strategy import build_features
   from datetime import date

   target = date(2025, 1, 31)
   count = build_features(conn, target)
   print(f"features upserted: {count}")
   ```

4. シグナル生成（signals テーブルへ保存）
   ```python
   from kabusys.strategy import generate_signals
   from datetime import date

   generated = generate_signals(conn, date(2025, 1, 31))
   print(f"signals written: {generated}")
   ```

5. ニュース収集ジョブ（RSS → raw_news）
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   # known_codes は銘柄抽出に使う有効コード集合（例: DB の銘柄リスト）
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
   print(results)
   ```

6. カレンダー更新ジョブ（夜間バッチ向け）
   ```python
   from kabusys.data.calendar_management import calendar_update_job

   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")
   ```

注意:
- 各処理は DuckDB の接続（conn: duckdb.DuckDBPyConnection）を受け取ります。
- 設定（J-Quants トークン等）は kabusys.config.settings から取得されます。環境変数が未設定だと例外となります。

---

## よく使う API の説明（短縮）

- kabusys.data.schema.init_schema(db_path): DuckDB の初期化（全 DDL 実行）
- kabusys.data.pipeline.run_daily_etl(conn, target_date=None): 日次 ETL（カレンダー・株価・財務・品質チェック）
- kabusys.strategy.build_features(conn, target_date): features の構築（正規化・フィルタ）
- kabusys.strategy.generate_signals(conn, target_date, threshold=0.6, weights=None): signals 作成
- kabusys.data.jquants_client.fetch_daily_quotes(...), save_daily_quotes(conn, records): API 取得 + 保存
- kabusys.data.news_collector.fetch_rss(url, source), save_raw_news(conn, articles): RSS 収集・保存

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

設定は .env / .env.local をプロジェクトルートに置くことで自動読み込みされます（但しテスト等で無効化可能）。

---

## ディレクトリ構成

（抜粋、主要ファイルのみ）

- src/
  - kabusys/
    - __init__.py
    - config.py              — 環境変数管理・settings
    - data/
      - __init__.py
      - jquants_client.py    — J-Quants API クライアント（取得・保存ユーティリティ）
      - schema.py            — DuckDB スキーマ定義と初期化
      - pipeline.py          — ETL パイプライン（run_daily_etl 等）
      - news_collector.py    — RSS 収集・前処理・保存・銘柄抽出
      - calendar_management.py — 営業日判定・カレンダー更新
      - audit.py             — 監査ログ（発注・約定）DDL
      - stats.py             — zscore_normalize 等
      - features.py          — data.stats の公開インターフェース
    - research/
      - __init__.py
      - factor_research.py   — momentum/volatility/value の計算
      - feature_exploration.py — 将来リターン / IC / 統計サマリ
    - strategy/
      - __init__.py
      - feature_engineering.py — features 構築ロジック
      - signal_generator.py    — final_score / signals 生成ロジック
    - execution/
      - __init__.py           — 発注層（実装の拡張点）
    - monitoring/             — モニタリング関連（エクスポート対象に含まれるが実装は別途）
- pyproject.toml / setup.cfg / requirements.txt 等（プロジェクトルートに配置される想定）

---

## 運用上の注意

- 自動売買（実運用）を行う場合は必ず paper_trading 環境で十分に検証してください。
- KABUSYS_ENV を `live` にすると実運用向けのフラグが有効化される可能性があります（実行時設定を確認してください）。
- データ取得は API レート制御やリトライを組んでいますが、J-Quants の利用規約・レート制限を順守してください。
- DuckDB のファイルは定期的なバックアップや権限管理を行ってください（取引データは機密情報になり得ます）。
- コード上の TODO / 未実装箇所（トレーリングストップ等）はドキュメント内コメントに記載されています。必要に応じて実装を拡張してください。

---

## 貢献・拡張ポイント

- execution 層のブローカー統合（kabu ステーションや他ブローカーへの送信ロジック）
- リアルタイム・モニタリング用の監視ダッシュボード
- ファクターやシグナルのハイパーパラメータ最適化用ユーティリティ
- AI スコア（ai_scores）生成パイプラインの実装
- 単体テスト・統合テストの追加（ETL のモック化、HTTP の差し替え）

---

README に不足している点や、サンプルスクリプト（cron / Airflow ジョブ例、Slack 通知連携、実運用用の設定ファイルテンプレート等）が必要であれば、用途に合わせた追加ドキュメントを作成します。必要な形式（Markdown / HTML / PDF）や対象読者（開発者 / 運用担当）を教えてください。