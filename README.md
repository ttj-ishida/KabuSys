# KabuSys

日本株向けの自動売買・データ基盤ライブラリ (KabuSys)。  
J-Quants / kabuステーション 等から市場データ・財務データ・ニュースを収集し、DuckDB に保存・品質チェック・ETL を行うためのモジュール群を提供します。

---

## 主な概要

- J-Quants API から株価（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得
- RSS フィードからニュースを安全に収集して記事・銘柄紐付けを行う
- DuckDB 上に多層（Raw / Processed / Feature / Execution / Audit）スキーマを定義・初期化
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- 監査ログ（order / execution のトレーサビリティ）をサポート
- レートリミット / リトライ / トークン自動リフレッシュ等の堅牢な HTTP ロジックを実装

---

## 機能一覧

- 環境設定読み込み（.env / .env.local の自動読み込み。無効化可能）
- J-Quants クライアント
  - 株価日足（ページネーション対応）
  - 財務データ（ページネーション対応）
  - マーケットカレンダー
  - ID トークン自動リフレッシュ、レートリミット（120 req/min）、指数バックオフリトライ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ニュース収集
  - RSS フィード取得（defusedxml を利用）
  - SSRF 対策（スキーム検証、プライベート IP 拒否、リダイレクト検査）
  - レスポンスサイズ上限（デフォルト 10 MB）
  - 記事ID は正規化 URL の SHA-256（先頭32文字）
  - 銘柄コード抽出（4桁数字、既知リストでフィルタ）
  - DuckDB への冪等保存（INSERT ... RETURNING）と一括挿入
- スキーマ管理
  - raw_prices / raw_financials / raw_news / market_calendar / features / signals / orders / trades / positions / audit テーブル群
  - インデックス定義
  - init_schema()/init_audit_schema()/init_audit_db()
- ETL パイプライン
  - 差分更新（最終取得日ベース）、backfill（デフォルト3日）
  - カレンダー先読み（デフォルト90日）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - run_daily_etl() で一括実行
- カレンダー管理ユーティリティ
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
- 品質チェック（QualityIssue オブジェクトで詳細を返す）
- 監査ログ（signal / order_request / executions）テーブル

---

## 要件

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml

（上記は最小限。プロジェクトによって他のパッケージが必要になる場合があります）

---

## 環境変数

自動的にプロジェクトルートの `.env` → `.env.local` を読み込みます（OS 環境変数優先）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に使用する環境変数:

- JQUANTS_REFRESH_TOKEN   (必須) — J-Quants の refresh token
- KABU_API_PASSWORD       (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL       (任意) — デフォルト `http://localhost:18080/kabusapi`
- SLACK_BOT_TOKEN         (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID        (必須) — Slack チャネル ID
- DUCKDB_PATH             (任意) — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH             (任意) — 監視用 SQLite（デフォルト `data/monitoring.db`）
- KABUSYS_ENV             (任意) — `development|paper_trading|live`（デフォルト `development`）
- LOG_LEVEL               (任意) — `DEBUG|INFO|WARNING|ERROR|CRITICAL`（デフォルト `INFO`）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

設定はコード上で `from kabusys.config import settings` をインポートして `settings.jquants_refresh_token` 等で利用できます。

---

## セットアップ手順

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```
   - プロジェクトに pyproject.toml / requirements.txt があればそちらを利用してください。
   - 開発中は `pip install -e .`（プロジェクトがパッケージ化されている場合）も利用できます。

4. 環境変数の設定
   - プロジェクトルートに `.env` を作成するか、環境変数をセットします（上記参照）。

---

## 使い方（代表的な例）

以下は主要 API の利用例です。Python REPL やスクリプトから利用できます。

- DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

- J-Quants の ID トークン取得（内部で refresh token を使用）
```python
from kabusys.data import jquants_client as jq
id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
```

- 株価・財務・カレンダーの日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
result = run_daily_etl(conn)  # target_date, id_token など引数で指定可能
print(result.to_dict())
```

- RSS ニュース収集と保存（既知銘柄リストを渡して銘柄紐付け）
```python
from kabusys.data import news_collector as nc
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードセット
stats = nc.run_news_collection(conn, known_codes=known_codes)
print(stats)
```

- 品質チェックの実行
```python
from kabusys.data import quality
issues = quality.run_all_checks(conn)  # ETL 後の品質検査
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

- 監査ログスキーマの初期化（監査専用 DB）
```python
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

各関数は詳しい引数・戻り値のドキュメントがコード内に記載されています。レートリミットやリトライ挙動などの運用関連は jquants_client の実装コメントを参照してください。

---

## ディレクトリ構成

主要ファイル構成（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・settings オブジェクト
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・認証・レート制御）
    - news_collector.py
      - RSS 収集・前処理・保存・銘柄抽出
    - schema.py
      - DuckDB スキーマ定義・初期化（Raw/Processed/Feature/Execution）
    - pipeline.py
      - ETL（差分更新・backfill・品質チェック・run_daily_etl）
    - calendar_management.py
      - マーケットカレンダーの判定・夜間更新ジョブ
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py (戦略層用: 実装はプロジェクト拡張領域)
  - execution/
    - __init__.py (発注・約定管理用: 実装はプロジェクト拡張領域)
  - monitoring/
    - __init__.py (監視・メトリクス用: 実装はプロジェクト拡張領域)

---

## 運用上の注意 / トラブルシューティング

- J-Quants API のレート制限（120 req/min）を守る設計ですが、運用時の追加 API 呼び出しに注意してください。
- ネットワークエラーや 429 等を考慮した自動リトライがありますが、継続的なエラーがある場合はログを確認してください。
- news_collector は SSRF 対策や XML パース例外対処を備えていますが、未知のフィード形式には失敗することがあります（ログに警告）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行います。CI 等で無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB ファイルのパスは settings.duckdb_path でカスタマイズできます。親ディレクトリがない場合は自動作成されます。
- Python バージョンは 3.10 以上を推奨（型記法や union 演算子の使用のため）。

---

## 開発・拡張

- strategy / execution / monitoring パッケージは拡張ポイントです。実際の売買ロジック・ブローカー連携はここに実装してください。
- audit モジュールは監査ログのDDLを提供します。運用でのトレーサビリティ要件に合わせて拡張してください。

---

## ライセンス / 貢献

本 README はコードベースの説明用テンプレートです。実際のライセンス表記や貢献ルールはリポジトリの LICENSE / CONTRIBUTING.md を参照してください。

---

必要に応じて README に追加したい情報（例: 実行時のコマンド例、CI 設定、Dockerfile、より詳細な API 使用例など）があれば教えてください。README をそれに合わせて拡張します。