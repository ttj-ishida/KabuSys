# KabuSys

日本株向け自動売買用ライブラリ / 小規模フレームワーク

このリポジトリは、日本株市場データ取得、DuckDB スキーマ管理、監査ログなどを備えた自動売買基盤の一部実装です。J-Quants API からのデータ取得や、取得データの DuckDB への永続化、監査ログ（発注 → 約定の追跡）を行うためのユーティリティを提供します。

---

## 主な特徴

- J-Quants API クライアント
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得
  - ページネーション対応
  - レートリミッティング（120 req/min）を厳守
  - リトライ（指数バックオフ、最大 3 回）と 401 の自動トークンリフレッシュ対応
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層にまたがるテーブル定義
  - 冪等なテーブル作成（CREATE IF NOT EXISTS）・インデックス作成
  - init_schema() で DB 初期化、get_connection() で接続取得

- 監査（Audit）
  - signal_events / order_requests / executions を使った完全なトレース機構
  - order_request_id を冪等キーとして二重発注防止
  - TIMESTAMP は UTC 保存（init_audit_schema が SET TimeZone='UTC' を実行）

- 環境変数設定管理
  - .env / .env.local / OS 環境変数から設定を自動ロード（プロジェクトルート検出）
  - 必須キーの取得用 Helpers（settings オブジェクト）
  - 自動ロードを無効化するフラグあり（KABUSYS_DISABLE_AUTO_ENV_LOAD）

---

## 必要条件

- Python 3.10+
- 主要依存: duckdb
  - pip install duckdb

（パッケージ化・配布方法により追加依存がある場合があります。プロジェクトルートの pyproject.toml / requirements.txt を参照してください。）

---

## セットアップ手順

1. リポジトリをクローン / 作業ディレクトリへ移動
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)
3. 依存パッケージをインストール
   - pip install duckdb
   - （他に必要なライブラリがある場合は追加でインストール）
4. 環境変数設定
   - プロジェクトルートに .env を用意します（.env.local を作ると上書きされます）。
   - 自動ロードの仕組み:
     - OS 環境変数 > .env.local > .env の優先度で読み込み
     - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
5. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - 省略可能:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB 保存先（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: sqlite 用監視 DB（デフォルト: data/monitoring.db）

例 .env 内容:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単なコード例）

以下は主要機能の利用例です。実際はエラーハンドリングやログ設定、リソース管理を適宜追加してください。

- DuckDB スキーマ初期化（ファイル DB）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # 親ディレクトリを自動作成して接続を返す
```

- J-Quants から日足を取得して DuckDB に保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = fetch_daily_quotes(code="7203")  # 例: トヨタのコード
n = save_daily_quotes(conn, records)
print(f"{n} 件保存しました")
```

- 財務データ・カレンダーの取得と保存
```python
from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements, fetch_market_calendar, save_market_calendar

fin = fetch_financial_statements(code="7203")
save_financial_statements(conn, fin)

cal = fetch_market_calendar()
save_market_calendar(conn, cal)
```

- ID トークンを直接取得する（通常は自動で refresh されるため明示的に呼ぶ必要は少ない）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を利用
```

- 監査スキーマを既存接続に追加
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)  # conn は init_schema() の戻り値など
```

---

## 設計上の注意 / 実装メモ

- レート制限
  - J-Quants の最大 120 req/min を守るため、モジュール内で固定間隔スロットリング（_RateLimiter）を実装しています。短時間に大量リクエストを送ると自動的に待機します。

- リトライとエラーハンドリング
  - 408 / 429 / 5xx を対象に指数バックオフで最大 3 回リトライします。
  - 429 の場合は Retry-After ヘッダを優先して待機時間を決定します。
  - 401 の場合は 1 回のみトークンを自動リフレッシュして再試行します（無限再帰を避けるため get_id_token 呼び出し中は自動リフレッシュを無効化）。

- Look-ahead bias 対策
  - データ保存時に fetched_at を UTC ISO タイムスタンプで記録します。これにより「いつシステムがそのデータを知り得たか」を明確にできます。

- 冪等性
  - DuckDB への INSERT は ON CONFLICT DO UPDATE を利用して重複を吸収します（raw_prices / raw_financials / market_calendar 等）。

- 環境変数自動読み込み
  - パッケージ初期化時に .env を自動でプロジェクトルートからロードします（.git または pyproject.toml を基準にルートを探索）。
  - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

---

## ディレクトリ構成

以下はこのコードベースの主要なファイル・モジュール構成です。

- src/kabusys/
  - __init__.py
    - パッケージのメタ情報（バージョン、エクスポート）。
  - config.py
    - .env 自動ロード、Settings クラス（settings オブジェクト）を提供。
    - 主要設定: jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level 等。
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得関数、保存関数、トークン取得、レート制御、リトライ）。
    - schema.py
      - DuckDB スキーマの DDL 定義および init_schema / get_connection。
    - audit.py
      - 監査ログ用 DDL と init_audit_schema / init_audit_db。
    - (その他) audit.py では監査用テーブルとインデックス群を定義。
  - strategy/
    - __init__.py
    - （戦略ロジックを配置する想定のパッケージ）
  - execution/
    - __init__.py
    - （発注・ブローカー連携ロジックを配置する想定のパッケージ）
  - monitoring/
    - __init__.py
    - （監視用モジュールを配置する想定）

---

## 今後の拡張ポイント（例）

- kabuステーション等ブローカー連携の実装（execution 層）
- Strategy 層の実装とシグナル生成パイプライン
- Slack 通知・監視用ジョブ（monitoring 層）
- 単体テスト / CI 設定、型チェック（mypy）など

---

## ライセンス・貢献

この README はコードからの抜粋と利用方法の説明に基づいて作成しています。実際のライセンスや貢献フローはリポジトリの LICENSE / CONTRIBUTING を参照してください。

---

何か特定の使い方（たとえば戦略のサンプル、DuckDB クエリ例、CI 用の設定など）を README に追加したい場合は、用途を教えてください。必要に応じて例やコードスニペットを拡張します。