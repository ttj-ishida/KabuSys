# KabuSys

KabuSys は日本株向けの自動売買プラットフォームを想定したライブラリ群です。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ/監査ログなど、戦略運用に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 主要機能

- データ取得
  - J-Quants API クライアント（株価日足、財務、マーケットカレンダー、認証・リトライ・レート制御付き）
- ETL（差分更新）
  - 日次 ETL（市場カレンダー、株価、財務データの差分取得／保存）
  - 品質チェックとの連携（quality モジュール）
- データストア
  - DuckDB ベースのスキーマ初期化 / 接続管理（冪等な DDL）
- 特徴量エンジニアリング
  - research で計算した raw ファクターの正規化・フィルタリング -> features テーブル保存
- シグナル生成
  - features と ai_scores を統合して final_score を算出、BUY/SELL シグナルを生成して signals テーブルへ保存
- ニュース収集
  - RSS フィードから記事収集、前処理、記事と銘柄の紐付け、raw_news / news_symbols への保存
  - SSRF 対策、XML 脆弱性対策、最大受信サイズ制限
- マーケットカレンダー管理
  - 営業日判定、翌営業日／前営業日の計算、カレンダー更新ジョブ
- 監査ログ（audit）
  - signal → order → execution のトレーサビリティ用テーブル群

---

## 要求環境 / 依存

主な依存（抜粋）:
- Python 3.10+
- duckdb
- defusedxml

（プロジェクト実際の依存は pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   ```
   （requirements.txt がない場合は duckdb, defusedxml などを個別にインストールしてください）

4. 環境変数を設定
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を作成すると自動で読み込まれます。
   - 自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. データベース（DuckDB）スキーマ初期化
   - デフォルトでは `data/kabusys.duckdb` に作成されます（`DUCKDB_PATH` で変更可）。
   - Python REPL やスクリプトで:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```

---

## 環境変数一覧（主なもの）

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- kabu ステーション（発注連携等）
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意; デフォルト: http://localhost:18080/kabusapi)
- Slack（通知など）
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベース
  - DUCKDB_PATH (任意; デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (任意; デフォルト: data/monitoring.db)
- 実行環境 / ログ
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト 'development'
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト 'INFO'
- その他
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env の自動読み込みを無効化

.env のサンプル（例）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要なサンプル）

以下はライブラリの主要機能を Python から呼び出す例です。実運用ではエラーハンドリングやログ設定を行ってください。

- スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（J-Quants トークンは Settings 経由で自動取得）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定することも可能
  print(result.to_dict())
  ```

- 特徴量ビルド（strategy の前段処理）
  ```python
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  cnt = build_features(conn, date(2025, 3, 1))
  print(f"built {cnt} features")
  ```

- シグナル生成
  ```python
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, date(2025, 3, 1))
  print(f"generated {total} signals")
  ```

- ニュース収集ジョブ実行
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes に有効な銘柄コード set を渡すと、記事から銘柄抽出して紐付けを行う
  results = run_news_collection(conn, known_codes={"7203", "6758"})
  print(results)
  ```

- カレンダー更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

---

## ディレクトリ構成

（抜粋: src 内の主要モジュール）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - schema.py              — DuckDB スキーマ定義・初期化
    - stats.py               — 汎用統計ユーティリティ（zscore_normalize 等）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - news_collector.py      — RSS 収集・保存・銘柄抽出
    - calendar_management.py — マーケットカレンダー管理
    - features.py            — data 層の特徴量ユーティリティ公開
    - audit.py               — 監査ログ用 DDL / 初期化
    - (その他: quality などの補助モジュールを想定)
  - research/
    - __init__.py
    - factor_research.py     — モメンタム/ボラティリティ/バリュー等の raw ファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features の作成（正規化・フィルタ）
    - signal_generator.py    — final_score 計算・BUY/SELL 判定
  - execution/               — 発注 / 実行関連（パッケージ用プレースホルダ）
  - monitoring/              — 監視・通知用モジュール（プレースホルダ）

---

## 開発・テスト

- 自動環境読み込み
  - パッケージはプロジェクトルート（.git または pyproject.toml を含む場所）を探索して `.env`, `.env.local` を自動で読み込みます（優先度: OS 環境 > .env.local > .env）。テストで自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- 単体テスト
  - モジュールは外部 API 呼び出し部分（HTTP/ネットワークやファイル操作）を注入可能/モック可能に設計されています。テスト時は jquants_client の HTTP 呼び出しや news_collector._urlopen などをモックしてください。

---

## トラブルシューティング（よくある問題）

- DuckDB ファイルが作成されない / パーミッションエラー
  - `DUCKDB_PATH` の親ディレクトリが存在するか確認。`init_schema` は親ディレクトリを自動作成しますが、実行環境の権限に注意してください。

- .env が読み込まれない
  - 自動検索はパッケージファイル位置からプロジェクトルートを探索します。CWD に依存しないため、実行パスが期待と異なる場合は環境変数を直接エクスポートするか `KABUSYS_DISABLE_AUTO_ENV_LOAD` を使って手動で読み込んでください。

- J-Quants API の認証エラー（401）
  - `JQUANTS_REFRESH_TOKEN` の値を確認してください。jquants_client は 401 を受けると自動でトークンをリフレッシュして再試行します。

- RSS の取得でリダイレクトや内部アドレスアクセスが拒否される
  - セキュリティ対策（SSRF 対策）によるものです。外部の RSS を利用する場合、URL が HTTP/HTTPS で公開ホストであることを確認してください。

---

## 貢献・ライセンス

この README はコードベースの説明用サンプルです。実際のプロジェクトでは CONTRIBUTING.md や LICENSE を追加してください。

---

README の他に知りたいこと（例: .env.example, DB スキーマ図、運用フロー）や、特定のモジュールの使い方（例: signal -> order のフロー）を記載希望であれば教えてください。