# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けに設計された Python パッケージです。J-Quants API から市場データ・財務データ・カレンダー・ニュースを収集し、DuckDB に保存、特徴量算出・シグナル生成・発注トレーサビリティまでのデータ処理パイプラインと戦略ロジックを備えています。

---

## 主な特徴

- J-Quants API クライアント（レート制御、リトライ、トークン自動更新）
- DuckDB を用いた三層データモデル（Raw / Processed / Feature / Execution）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 特徴量計算（Momentum / Volatility / Value 等）と Z スコア正規化
- シグナル生成（ファクター + AI スコアの統合、BUY/SELL 生成、エグジット判定）
- ニュース収集（RSS、URL 正規化、銘柄抽出、SSRF 対策、冪等保存）
- マーケットカレンダー管理（営業日判定・前後営業日取得）
- 監査ログ / 発注・約定・ポジション管理のためのスキーマ
- 環境変数 / .env 自動読み込み機能（.env.local を優先）

---

## 必要条件（Dependencies）

主な Python パッケージ（例）:
- Python 3.8+
- duckdb
- defusedxml

※ 実行環境に合わせて `pip install` でインストールしてください。

例:
```bash
pip install duckdb defusedxml
```

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます（優先度: OS 環境 > .env.local > .env）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

オプション（デフォルトあり）:
- KABUSYS_ENV — 実行環境: `development` / `paper_trading` / `live`（デフォルト `development`）
- LOG_LEVEL — ログレベル（`INFO` 等、デフォルト `INFO`）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — 監視 DB パス（デフォルト `data/monitoring.db`）

設定は `from kabusys.config import settings` でアクセスできます。

---

## セットアップ手順

1. リポジトリをクローン／展開
2. Python 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   ```
4. 環境変数を設定（`.env` / `.env.local` をプロジェクトルートに作成）
   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```
5. DuckDB スキーマ初期化
   Python から初期化する例:
   ```python
   from kabusys.data.schema import init_schema, get_connection
   conn = init_schema("data/kabusys.duckdb")  # ファイル作成とテーブル作成
   conn.close()
   ```

---

## 使い方（主な API と実行例）

下記は代表的なワークフローの例です。各関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）と日付を受け取ります。

- 日次 ETL を実行（市場カレンダー取得 → 株価 → 財務 → 品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- 特徴量（features）を構築
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features

  conn = get_connection("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2024, 1, 31))
  print(f"features updated: {count}")
  ```

- シグナル生成
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  n = generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)
  print(f"signals written: {n}")
  ```

- ニュース収集ジョブ実行（既存の銘柄コードセットを与えて紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- カレンダーの夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn, lookahead_days=90)
  print(f"calendar saved: {saved}")
  ```

---

## 実行環境切替（KABUSYS_ENV）

`KABUSYS_ENV` は以下のいずれかを指定します:
- development — 開発用（デフォルト）
- paper_trading — ペーパートレード用
- live — 本番実行（注意: 実際の発注など）

この値は `kabusys.config.settings.env` で検証されます。`is_live`, `is_paper`, `is_dev` のプロパティも利用可能です。

---

## 推奨運用上の注意

- J-Quants API のレートリミット（120 req/min）を意識してください。クライアントは内部でレート制御を行いますが、大規模バッチは適切にスケジュールしてください。
- DuckDB ファイルはバックアップを定期的に取ってください。
- 本番環境（live）では秘密情報やログの管理に注意し、SLACK など通知設定を整えてください。
- 自動発注や実口座接続は十分にテストした後に有効化してください（KABU_API_PASSWORD 等）。

---

## ディレクトリ構成（主なファイル）

以下はパッケージ内の主要モジュール一覧（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（fetch/save）
    - schema.py                     — DuckDB スキーマ定義・初期化
    - stats.py                      — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - news_collector.py             — RSS ニュース収集・保存
    - calendar_management.py        — 市場カレンダー管理（営業日判定等）
    - features.py                   — features の再エクスポート
    - audit.py                      — 監査ログスキーマ
    - execution/                     — 発注関連（プレースホルダ）
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum/value/volatility 等）
    - feature_exploration.py        — IC / forward returns / summary
  - strategy/
    - __init__.py
    - feature_engineering.py        — features を作るロジック（build_features）
    - signal_generator.py           — シグナル生成ロジック（generate_signals）
  - monitoring/                      — 監視・Slack 等（場所確保）
  - execution/                       — 実際の発注処理（将来的な実装用）

（実際のファイルと細部実装はソースを参照してください）

---

## ライセンス / 貢献

本ドキュメントはコードベースに基づく README のサンプルです。実際のプロジェクトでは LICENSE ファイルや Contributing ガイドラインを用意してください。

---

必要であれば、README に記載するコマンド例や CI/CD、デプロイ手順、より詳しい開発者向けドキュメント（テスト実行、モジュール別の API リファレンス等）も作成します。どの部分を優先して拡充しましょうか？