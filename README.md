# KabuSys — 日本株自動売買システム

KabuSys は日本株向けのデータ取得・ETL・特徴量生成・シグナル生成・監視・発注トレーサビリティを想定した Python パッケージです。  
本リポジトリは以下の層を持つ設計に基づいており、研究（research）および本番（execution）ワークフローを分離しています。

- Raw Layer（生データの永続化）
- Processed Layer（整形済みマーケットデータ）
- Feature Layer（戦略・AI 用特徴量）
- Execution Layer（シグナル・発注・約定・ポジション管理）

バージョン: 0.1.0

## 主な機能一覧

- J-Quants API クライアント（レートリミット・リトライ・トークン自動リフレッシュ対応）
  - 日足価格、財務データ、マーケットカレンダーの取得
- DuckDB によるデータスキーマ定義・初期化（冪等）
- ETL パイプライン（差分取得 / バックフィル / 品質チェック組込み）
- 特徴量計算（momentum, volatility, value 等）
- クロスセクション Z スコア正規化ユーティリティ
- シグナル生成（複数ファクター + AI スコア統合・Bear レジーム抑制・エグジット判定）
- ニュース収集（RSS → raw_news、SSRF / XML 注入対策、記事ID 正規化）
- マーケットカレンダー管理（営業日判定、次/前営業日取得、夜間更新ジョブ）
- 監査ログ（signal / order_request / executions 等、トレーサビリティ確保）
- 設定管理（.env 自動ロード・必須項目チェック）

## 必要条件

- Python 3.10 以上（PEP 604 型記法や union 演算子 `|` を利用しているため）
- 主要ライブラリ（最低限）
  - duckdb
  - defusedxml

インストール方法はプロジェクトのパッケージ化方法に依存しますが、ローカルで使う場合の例を以下に示します。

## セットアップ手順（ローカル）

1. リポジトリをクローンして作業ディレクトリへ移動

   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成・有効化（任意）

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存関係のインストール

   例（pip）:

   ```bash
   pip install duckdb defusedxml
   # またはパッケージに setup / pyproject があれば:
   # pip install -e .
   ```

4. 環境変数の設定

   プロジェクトルートに `.env` / `.env.local` を置くことで自動読み込みできます（`src/kabusys/config.py` が起点）。  
   自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須の環境変数（少なくとも以下を設定する必要があります）:

   - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
   - KABU_API_PASSWORD — kabu API（kabuステーション）パスワード
   - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID — Slack チャネル ID

   任意 / デフォルトあり:

   - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db
   - KABUSYS_ENV — 有効値: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   例 `.env`:

   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=secret_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベーススキーマ初期化

   DuckDB のスキーマを作成します（デフォルトのパスは環境変数 `DUCKDB_PATH`）。

   例スクリプト（初期化）:

   ```python
   # scripts/init_db.py
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   print("Initialized:", settings.duckdb_path)
   conn.close()
   ```

   実行:

   ```bash
   python scripts/init_db.py
   ```

## 主要な使い方（例）

以下はライブラリの主要関数を呼ぶ例です。実運用ではジョブスクリプトや cron / Airflow 等でラップしてください。

- 日次 ETL（市場カレンダー → 日足 → 財務 を取得し品質チェック）

  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.data.pipeline import run_daily_etl

  # 初回のみ init_schema(settings.duckdb_path)
  conn = init_schema(settings.duckdb_path)

  # 今日を対象に日次ETLを実行
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- 特徴量のビルド（research で計算済み raw factors を正規化し features テーブルへ保存）

  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features

  conn = get_connection(settings.duckdb_path)
  n = build_features(conn, target_date=date(2024, 1, 25))
  print("features upserted:", n)
  conn.close()
  ```

- シグナル生成（features と ai_scores を統合して signals テーブルへ書き込む）

  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals

  conn = get_connection(settings.duckdb_path)
  total = generate_signals(conn, target_date=date(2024, 1, 25))
  print("signals written:", total)
  conn.close()
  ```

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）

  ```python
  from kabusys.config import settings
  from kabusys.data.schema import get_connection
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = get_connection(settings.duckdb_path)
  # known_codes: 銘柄抽出に使う有効コード集合（例: DB から全銘柄を取得）
  known_codes = {"7203", "6758", "9433"}  # 例
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  conn.close()
  ```

- カレンダー夜間更新ジョブ

  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  saved = calendar_update_job(conn)
  print("calendar saved:", saved)
  conn.close()
  ```

## 開発時のヒント

- 設定は `kabusys.config.settings` からアクセスできます（必須変数はアクセス時に例外が発生）
- `.env` の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください
- DuckDB をインメモリで使うには `db_path=":memory:"` を渡してください（単体テスト等）
- RSS フェッチなどネットワーク呼び出しはテスト時にモック可能（例えば内部関数を差し替え）

## 主要ディレクトリ / ファイル構成

（src 配下の主なモジュールを抜粋）

- src/kabusys/
  - __init__.py — パッケージ初期化（version 等）
  - config.py — 環境変数・設定管理（.env 自動ロード、必須チェック）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 / 保存ユーティリティ）
    - schema.py — DuckDB スキーマ定義と初期化（init_schema / get_connection）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - stats.py — zscore_normalize 等統計ユーティリティ
    - news_collector.py — RSS 取得・保存・銘柄抽出
    - calendar_management.py — market_calendar 管理・営業日判定・update_job
    - features.py — data.stats の再エクスポート
    - audit.py — 発注〜約定トレーサビリティ用の監査 DDL
    - (その他: quality 等品質チェックモジュールを想定)
  - research/
    - __init__.py — 研究用ユーティリティの再エクスポート
    - factor_research.py — Momentum/Volatility/Value のファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py — build_features / generate_signals を公開
    - feature_engineering.py — raw factor → normalized features の構築
    - signal_generator.py — features + ai_scores を使ったシグナル生成
  - execution/ — 発注/約定を取り扱う層（実装は別途）
  - monitoring/ — 監視 / アラート用コード（実装は別途）

## ロギング・デバッグ

- 設定 `LOG_LEVEL`（環境変数）でログレベルを制御できます（デフォルト: INFO）
- 各モジュールは標準 logging に従っており、適宜ハンドラを設定してログを収集してください。

## 安全性・設計上の注意点

- ニュース収集では SSRF や XML インジェクション対策を実装済み（URL スキーム検証、プライベートホストブロック、defusedxml 使用）
- J-Quants クライアントはレート制御・リトライ・トークン更新に対応
- DuckDB スキーマは多くのチェック制約（CHECK / PRIMARY KEY）を付与し、データ整合性を強化
- 実運用での「発注」や「本番口座接続」は慎重に扱ってください（paper_trading/live のフラグを正しく使用すること）

---

この README はコードベース（src/kabusys 以下）の主要機能・利用方法・初期化手順をまとめたものです。追加の運用手順や詳細設計（StrategyModel.md / DataPlatform.md / Security.md 等）は別ドキュメントを参照してください。必要であれば README を拡張して CI/CD、デプロイ、運用 runbook などを追記できます。