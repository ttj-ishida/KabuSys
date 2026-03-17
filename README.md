# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けのデータ取得・ETL・監査基盤ライブラリです。J-Quants や RSS などから市場データ・財務データ・ニュースを収集して DuckDB に保存し、品質チェックやカレンダー管理、監査ログ（発注 → 約定トレース）までをサポートします。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）に準拠する内部 RateLimiter
  - 再試行（指数バックオフ、最大 3 回）と 401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で保存し、Look-ahead Bias を抑制
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集（RSS）
  - RSS フィードから記事を収集して raw_news に保存
  - 記事ID は正規化 URL の SHA-256（先頭32字）で冪等性を担保
  - SSRF / XML Bomb / 大容量レスポンス対策（defusedxml、ホスト検査、サイズ上限など）
  - 記事と銘柄コードの紐付け（news_symbols）機能
  - 収集ジョブはソース毎にエラーハンドリング（1ソース失敗でも他を継続）

- ETL パイプライン
  - 差分更新（最終取得日からの差分のみを取得）とデフォルトで直近数日を再取得（backfill）して後出し修正を吸収
  - 市場カレンダー先読み（lookahead）
  - 品質チェック（欠損、重複、スパイク、日付不整合など）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義を提供
  - インデックス作成と初期化ユーティリティ（init_schema, init_audit_schema）

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 に至る UUID ベースのトレーサビリティ
  - 発注の冪等性（order_request_id）を設計に組み込み
  - UTC タイムゾーン固定、ステータス追跡

- データ品質チェック
  - 欠損データ、スパイク（前日比）、重複、将来日付／非営業日データの検出
  - 各チェックは QualityIssue のリストを返す（Fail-Fast ではなく全件収集）

- 設定管理
  - .env / .env.local または OS 環境変数から設定を自動ロード
  - プロジェクトルート（.git または pyproject.toml）を探索して .env を読み込む
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 前提（Prerequisites）

- Python 3.10 以上（型アノテーションの構文等を利用）
- 必要な主要ライブラリ（例）
  - duckdb
  - defusedxml

（プロジェクトの requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン（またはソースを入手）

   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成（推奨）

   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存ライブラリをインストール

   必要最低限の例:

   ```
   pip install duckdb defusedxml
   ```

   開発用にパッケージとしてインストールする場合（プロジェクトに setuptools/pyproject を用意している前提）:

   ```
   pip install -e .
   ```

4. 環境変数の準備

   プロジェクトルート（.git または pyproject.toml がある場所）に `.env`（と必要なら `.env.local`）を作成します。主な必須設定:

   - JQUANTS_REFRESH_TOKEN ・・・J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     ・・・kabuステーション API のパスワード
   - SLACK_BOT_TOKEN       ・・・Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      ・・・Slack のチャンネル ID

   オプション（デフォルト値あり）:

   - KABUSYS_ENV （development / paper_trading / live、デフォルト development）
   - LOG_LEVEL （DEBUG/INFO/...、デフォルト INFO）
   - DUCKDB_PATH （デフォルト data/kabusys.duckdb）
   - SQLITE_PATH （デフォルト data/monitoring.db）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込む処理を無効化

   .env の例（参考）:

   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本例）

以下は Python REPL やスクリプトから利用する簡単な例です。関数はライブラリ内に公開されているユーティリティを使います。

- DuckDB スキーマ初期化

```python
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")  # ファイル DB を作成して接続を返す
# または in-memory
# conn = schema.init_schema(":memory:")
```

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
# 初回は init_schema を実行してください
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブの実行

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes を渡すと記事と銘柄コードの紐付けを行う
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
stats = run_news_collection(conn, known_codes=known_codes)
print(stats)
```

- カレンダー更新ジョブ（夜間バッチに使用）

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved {saved} records")
```

- J-Quants API を直接利用（トークン取得 / データフェッチ）

```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()  # settings.jquants_refresh_token を使用して idToken を取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

- 品質チェックを個別に実行

```python
from kabusys.data.quality import run_all_checks
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn, reference_date=date.today())
for i in issues:
    print(i)
```

注意点:
- network 呼び出しを含む箇所は例外を送出する可能性があるため、運用スクリプトでは適切に try/except を配置してください。
- テスト時は設定の自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_collector の内部関数 _urlopen などはテスト用にモック可能です。

---

## 主要モジュールの説明（簡易）

- kabusys.config
  - .env / 環境変数読み込み、Settings オブジェクトを提供
  - 自動 .env ロードロジック（プロジェクトルート探索）
- kabusys.data.jquants_client
  - J-Quants API 通信、リトライ・レート制御、DuckDB 保存関数
- kabusys.data.news_collector
  - RSS 取得、正規化、SSRF 対策、raw_news / news_symbols 保存
- kabusys.data.schema
  - DuckDB のテーブル DDL と初期化ロジック（init_schema / get_connection）
- kabusys.data.pipeline
  - 差分 ETL（prices / financials / calendar）、日次 ETL のエントリポイント
- kabusys.data.calendar_management
  - 営業日判定、next/prev_trading_day、calendar_update_job
- kabusys.data.audit
  - 監査ログ用スキーマ（signal_events, order_requests, executions）初期化
- kabusys.data.quality
  - データ品質チェック（欠損・重複・スパイク・日付不整合）

---

## ディレクトリ構成

（プロジェクトルートの `src/kabusys` 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - execution/            (発注・実行関連のパッケージ（未実装ファイル群含む）)
    - __init__.py
  - strategy/             (戦略モジュールの置き場)
    - __init__.py
  - monitoring/           (監視・メトリクスモジュール)
    - __init__.py
  - data/
    - __init__.py
    - jquants_client.py   (J-Quants API クライアント、保存ロジック)
    - news_collector.py   (RSS ニュース収集、SSRF 対策、保存)
    - pipeline.py         (ETL パイプライン)
    - calendar_management.py (マーケットカレンダー管理)
    - schema.py           (DuckDB スキーマ定義と初期化)
    - audit.py            (監査ログスキーマ初期化)
    - quality.py          (データ品質チェック)

---

## 注意・運用上のポイント

- セキュリティ
  - RSS 収集は SSRF・XML 攻撃・大容量応答に対処する実装になっていますが、外部入力の URL などを安易に受け入れない運用を推奨します。
  - シークレット（API トークン等）は必ず安全に管理してください（.env を共有リポジトリに含めない等）。
- 冪等性とトレース
  - DuckDB への保存は基本的に ON CONFLICT を用いた冪等処理を行います。監査ログは削除しない前提で設計されています。
- テスト容易性
  - jquants_client の id_token 注入や news_collector._urlopen のモックなど、テストのための注入ポイントが用意されています。
- 本番モード
  - KABUSYS_ENV を `live` にすると is_live フラグが True になります。実際の発注・課金などは十分な確認のうえで行ってください。

---

## ライセンス / 貢献

本 README はコードベースの説明用です。実際のライセンス表記や貢献ガイドライン（CONTRIBUTING.md）はプロジェクトルートに合わせて追加してください。

---

必要であれば、README にサンプル .env.example、詳細な API 使用例、運用用 cron / systemd サービス例、単体テスト・モック例などを追加で作成します。どの内容を追加しますか？