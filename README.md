# KabuSys

KabuSys は日本株向けの自動売買基盤ライブラリです。J-Quants API から市場データを取得して DuckDB に保存し、リサーチ用ファクター計算、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどの機能を提供します。戦略層と発注層は分離され、ルックアヘッドバイアス対策や冪等性を重視した設計になっています。

主な用途
- 日次 ETL（株価・財務・カレンダーの差分取得と保存）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 特徴量作成（Z スコア正規化・ユニバースフィルタ）
- シグナル生成（複数コンポーネントを統合した final_score に基づく BUY/SELL）
- ニュース収集（RSS → raw_news、記事と銘柄紐付け）
- DuckDB スキーマ初期化 / 管理 / 監査ログ

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（認証、ページネーション、リトライ、レート制限）
  - schema: DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）
  - news_collector: RSS 収集と raw_news / news_symbols への保存（SSRF 対策、トラッキング除去）
  - calendar_management: JPX カレンダー管理・営業日計算
  - stats / features: 統計ユーティリティ（Z スコア正規化 など）
  - audit: 発注〜約定の監査ログ用 DDL（トレーサビリティ）
- research/
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration: IC 計算、将来リターン計算、統計サマリー
- strategy/
  - feature_engineering: research の raw factor を正規化して features テーブルへ保存
  - signal_generator: features と ai_scores を統合して BUY / SELL シグナルを生成
- config: 環境変数を読み込む設定ヘルパー（.env/.env.local の自動読み込みを実装）
- execution, monitoring: 発注・監視のための名前空間（将来実装部分／拡張ポイント）

---

## 前提・依存関係

- Python 3.10+
  - typing の `X | Y` を利用しているため Python 3.10 以降が必要です。
- 必須パッケージ（少なくとも以下をインストールしてください）
  - duckdb
  - defusedxml
- 標準ライブラリで動作する部分が多く、追加の外部依存は最小限に抑えられています。

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージを editable インストールする場合（プロジェクトルートに pyproject.toml/setup.py がある場合）
# pip install -e .
```

---

## 環境変数（必須・任意）

このライブラリは環境変数から各種機密情報や挙動設定を取得します。`.env` / `.env.local` をプロジェクトルートに置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

必須（使う機能による）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（jquants_client で必要）
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注連携など）
- SLACK_BOT_TOKEN — Slack 通知ボットのトークン（モニタリング）
- SLACK_CHANNEL_ID — Slack チャネル ID

その他:
- DUCKDB_PATH — DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視等用、デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 ("development", "paper_trading", "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）

例（.env のテンプレート）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. ソースをクローン／ダウンロード
2. 仮想環境作成（推奨）
3. 依存ライブラリをインストール（duckdb, defusedxml など）
4. プロジェクトルートに `.env`（または `.env.local`）を配置して環境変数を設定
5. DuckDB スキーマを初期化

DuckDB スキーマ初期化の例:
```python
from kabusys.data import schema
from kabusys.config import settings

# settings.duckdb_path は .env の DUCKDB_PATH を参照
conn = schema.init_schema(settings.duckdb_path)
# これで必要なテーブルがすべて作成されます
```

またはコマンドラインで Python スクリプトを作って実行してください。

---

## 使い方（主要なワークフロー例）

- データベース初期化
  ```python
  from kabusys.data import schema
  from kabusys.config import settings

  conn = schema.init_schema(settings.duckdb_path)
  ```

- 日次 ETL を実行（J-Quants から差分取得して保存）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data import schema
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)  # 既存 DB に接続
  # run_daily_etl は ETLResult を返す
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量作成（research モジュールで計算した raw factor を Z スコア化して features に保存）
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features
  from kabusys.config import settings
  from kabusys.data import schema

  conn = schema.get_connection(settings.duckdb_path)
  cnt = build_features(conn, target_date=date.today())
  print("features upserted:", cnt)
  ```

- シグナル生成（features と ai_scores を統合して signals に書き込む）
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data import schema

  conn = schema.get_connection(some_duckdb_path)
  written = generate_signals(conn, target_date=date.today())
  print("signals written:", written)
  ```

- ニュース収集（RSS 取得 → raw_news 保存 → 銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data import schema

  conn = schema.get_connection(settings.duckdb_path)
  known_codes = {"7203", "6758", ...}  # 自分の有効コードセット
  results = run_news_collection(conn, sources=None, known_codes=known_codes)
  print(results)
  ```

- J-Quants API を直接利用する（トークン取得やデータ取得）
  ```python
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  token = get_id_token()  # settings.jquants_refresh_token を使って自動で取得
  quotes = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
  ```

---

## 開発者向けノート

- config.Settings はアプリ設定・必須環境変数チェック（_require）を提供します。自動でプロジェクトルートの .env / .env.local を読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- jquants_client は内部で固定間隔スロットリング（120 req/min）、リトライ（指数バックオフ）・401 トークンリフレッシュを実装しています。
- DuckDB への保存は可能な限り冪等（ON CONFLICT 等）にしています。
- news_collector は SSRF 対策 / トラッキング除去 / gzip サイズチェック / XML 疎通対策（defusedxml）など堅牢性を意識して設計されています。
- strategy 層の設計方針はルックアヘッドバイアス防止を重視しており、target_date 時点までにシステムが知り得るデータのみを使用します。

---

## ディレクトリ構成

概略（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py
  - execution/                # 発注・ブローカー連携層（名前空間）
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - data/
    - __init__.py
    - jquants_client.py
    - schema.py
    - pipeline.py
    - news_collector.py
    - calendar_management.py
    - features.py
    - stats.py
    - audit.py
    - (その他 ETL / 品質チェックモジュール等)
  - monitoring/               # 監視・Slack 通知用（名前空間）
  - その他モジュール...

各モジュールの役割は上記「主な機能一覧」を参照してください。

---

## テスト・運用について（簡単な指針）

- 本番稼働前に DuckDB スキーマを作成し、ETL を少量の期間で実行して保存ロジックの確認を行ってください。
- J-Quants の API レート制限・利用規約に注意し、取得範囲を適切に設定してください。
- 実際の発注（execution 層）をつなぐ場合は paper_trading 環境で十分に検証してから live に切り替えてください（KABUSYS_ENV=paper_trading / live）。
- ログレベルは LOG_LEVEL で制御できます。調査時は DEBUG に上げると詳細情報が得られます。

---

この README はコードベースの現状に合わせて作成しています。具体的な CLI、ユーティリティスクリプト、テストケース、CI 設定などはプロジェクトに合わせて追加してください。必要であればサンプルスクリプトや環境ファイルのテンプレートも作成します。