# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどの機能を提供します。DuckDB をデータ層に用いた設計で、分析（研究）と本番ワークフローを意識したモジュール構成になっています。

## 主な特徴
- J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
- DuckDB ベースのスキーマ定義と初期化（冪等な DDL）
- 日次 ETL（株価・財務・カレンダーの差分取得と保存）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー など）
- 特徴量エンジニアリング（Zスコア正規化・ユニバースフィルタ）
- シグナル生成（ファクタースコア＋AIスコア統合、BUY/SELL 判定）
- ニュース収集（RSS、URL 正規化、SSRF 対策、銘柄抽出）
- マーケットカレンダー管理（営業日判定、前後営業日取得）
- 監査ログ（signal → order → execution のトレース構造）

---

## 必要条件
- Python 3.10 以上（型ヒントに `|` を利用）
- 推奨ライブラリ（最低限）:
  - duckdb
  - defusedxml

実際には標準ライブラリ中心で実装されていますが、DuckDB や XML の安全パースに必要なパッケージをインストールしてください。

---

## セットアップ

1. 仮想環境を作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   # 開発中はパッケージを編集可能モードでインストール
   pip install -e .
   ```

3. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただしテスト等で自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須環境変数（少なくともこれらを用意してください）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード
     - SLACK_BOT_TOKEN: Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意 / デフォルト:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

   例 `.env`（テンプレート）
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本例）

以下はライブラリの主要機能を簡単に呼び出す例です。実運用時はログ設定やエラーハンドリング、運用ジョブ（cron / Airflow 等）から呼び出す想定です。

1. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL を実行（J-Quants から差分取得）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from datetime import date

   res = run_daily_etl(conn, target_date=date.today())
   print(res.to_dict())
   ```

3. 特徴量をビルド（features テーブルへ保存）
   ```python
   from kabusys.strategy import build_features
   from datetime import date

   count = build_features(conn, target_date=date.today())
   print(f"features upserted: {count}")
   ```

4. シグナル生成（signals テーブルへ保存）
   ```python
   from kabusys.strategy import generate_signals
   from datetime import date

   total_signals = generate_signals(conn, target_date=date.today())
   print(f"generated signals: {total_signals}")
   ```

5. ニュース収集（RSS）と銘柄紐付け
   ```python
   from kabusys.data.news_collector import run_news_collection
   known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)
   ```

6. マーケットカレンダー更新ジョブ（夜間バッチ）
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print(f"saved calendar records: {saved}")
   ```

---

## モジュール別の短い説明

- kabusys.config
  - 環境変数の自動読み込み（.env / .env.local）と設定のラッパー（Settings）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存関数含む）
  - schema: DuckDB スキーマ定義・初期化
  - pipeline: ETL（差分更新 / 日次 ETL）
  - news_collector: RSS 収集・正規化・DB保存・銘柄抽出
  - calendar_management: 市場カレンダー管理（営業日判定等）
  - features / stats: Zスコア正規化などの統計ユーティリティ
  - audit: 監査ログ用のDDL（signal/events/order/execution など）
- kabusys.research
  - factor_research: モメンタム/ボラティリティ/バリューのファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー
- kabusys.strategy
  - feature_engineering.build_features: 生ファクターの正規化と features テーブルへの保存
  - signal_generator.generate_signals: features + ai_scores を統合して signals を生成
- kabusys.execution / kabusys.monitoring
  - 発注 / 監視に関する層（インターフェース用のパッケージとして存在）

---

## ディレクトリ構成（抜粋）

プロジェクトは src/kabusys 配下に実装されています（主要ファイルのみ抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - schema.py
    - pipeline.py
    - news_collector.py
    - calendar_management.py
    - stats.py
    - features.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - monitoring/
    - (監視用モジュール)

ファイルの説明は各ソースコードの docstring に詳述されています。

---

## 運用上の注意 / ベストプラクティス
- 環境（KABUSYS_ENV）に応じた動作:
  - development / paper_trading / live を適切に切り替えてください。live では実取引との連携に注意。
- 自動.env 読み込み:
  - デフォルトで .env/.env.local をプロジェクトルートから検出して読み込みます。テスト時などで無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の永続化:
  - デフォルト DB は data/kabusys.duckdb です。バックアップ・スナップショット運用を推奨します。
- トークン管理:
  - J-Quants トークン等は安全に管理し、ログやリポジトリに埋め込まないでください。
- ニュース収集のセキュリティ:
  - RSS のリダイレクト検査やプライベート IP チェック、受信サイズ上限などを実装してありますが、外部フィード追加時は注意してください。
- 例外・ロールバック:
  - DB 操作はトランザクションで行われ、失敗時はロールバックされます。運用スクリプトで適切に例外をハンドリングしてください。

---

## 貢献・拡張
- 新しい ETL ソースやニュースソースを追加する場合は、既存の save_* / fetch_* のインターフェースに従うと統合が容易です。
- 監査ログ（audit）や execution 層は、実ブローカーの API に合わせて拡張してください（冪等キー設計を尊重）。
- テスト: 各モジュールは外部依存（HTTP / DB）を注入可能な設計になっているため、モックを使った単体テストが書きやすくなっています。

---

README に記載してほしい追加情報や、特定の使い方（例: Airflow 組み込み、Slack 通知サンプル、kabuAPI 発注ラッパーなど）があればお知らせください。必要に応じてサンプルスクリプトや運用手順を追記します。