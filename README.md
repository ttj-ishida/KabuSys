# KabuSys

日本株向け自動売買／データパイプライン基盤ライブラリ

KabuSys は J-Quants や kabuステーション 等の外部 API から市場データ・ニュース・カレンダーを取得し、DuckDB に保存・管理するためのモジュール群を提供します。ETL、データ品質チェック、監査ログ（発注→約定トレース）、ニュース収集、マーケットカレンダー管理など、システム化された自動売買プラットフォームに必要な基盤機能を含みます。

バージョン: 0.1.0

---

## 主な特徴（抜粋）

- J-Quants API クライアント
  - 日足（OHLCV）、財務指標、JPX カレンダーの取得
  - API レート制限（120 req/min）遵守（固定間隔スロットリング）
  - リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し、look‑ahead bias を抑止
  - DuckDB への冪等保存（ON CONFLICT / DO UPDATE）

- ニュース収集
  - RSS フィード取得 → 前処理 → raw_news へ冪等保存
  - URL 正規化・トラッキングパラメータ除去・SHA-256 による記事ID生成
  - SSRF 対策（スキーム検証・プライベートIPブロック）、XML の安全パース（defusedxml）
  - 大きなレスポンス防止（読み込み上限）や gzip 解凍チェック

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit の多層スキーマ定義
  - インデックスや制約を含むテーブル作成の init 関数
  - 監査ログ（signal → order_request → executions のトレース）用スキーマ

- ETL パイプライン
  - 差分更新（最終取得日からの差分取得 + backfill）
  - カレンダー先読み（lookahead）機能
  - 品質チェック（欠損・スパイク・重複・日付不整合の検出）
  - 各ステップは独立して例外処理 → 途中失敗してもできる限り継続

- マーケットカレンダー管理
  - 営業日判定、前後営業日の取得、期間内営業日の列挙
  - カレンダー差分更新ジョブ（夜間バッチ）

---

## 必要要件（例）

- Python 3.10+
- パッケージ依存（代表）
  - duckdb
  - defusedxml
  - （標準ライブラリ：urllib, datetime 等）

実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください。

---

## 環境変数（主要）

プロジェクトは .env ファイルまたは環境変数から設定を読み込みます（自動ロード機能あり）。必須の環境変数は以下の通りです。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知に利用する Bot トークン
- SLACK_CHANNEL_ID — 通知先チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

自動読み込みを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込む処理を無効化します（テスト等で利用）。

.env のパースはシェル風の書式に対応し、export プレフィクスやクォート、コメント等を扱います。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   (例: venv)
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存関係をインストール
   - pip / poetry 等を使用してください。例（最低限）:
   ```
   pip install duckdb defusedxml
   ```
   - プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください。

4. .env を準備
   プロジェクトルートに .env を置くと自動で読み込まれます（.env.local は上書き）。簡易例:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化（サンプル）
   Python REPL やスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   # 監査スキーマ追加
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)
   ```

---

## 使い方（主要ワークフロー例）

以下は代表的な操作例です。各モジュールは import して利用できます。

- J-Quants の ID トークンを取得
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使用
```

- 日次 ETL を実行（株価・財務・カレンダーの差分取得 + 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")  # 初期化して接続を取得
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブを実行
```python
from kabusys.data.news_collector import run_news_collection
conn = get_connection("data/kabusys.duckdb")

# known_codes を与えるとテキストから銘柄コード抽出して紐付けする
known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # 各ソースごとの新規保存数
```

- 市場カレンダーの夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"saved: {saved}")
```

- データ品質チェックを手動で実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)  # target_date を指定すれば絞り込み可
for i in issues:
    print(i)
```

---

## 注意点 / 設計上のポイント

- jquants_client は API レート（120 req/min）を内部で守りますが、並列プロセスからの同時実行には注意してください。
- トークンの自動リフレッシュやリトライ戦略を備えていますが、API 利用規約・レート制限を尊重してください。
- news_collector は SSRF や XML Bomb 等の脅威緩和を行いますが、外部フィードの内容は常に不確実です。取得結果の二次利用時は追加の検証を推奨します。
- DuckDB のスキーマは多くの制約やインデックスを定義しています。init_schema は冪等（既存テーブルはスキップ）です。
- 監査ログ（audit）テーブルは UTC タイムゾーンに固定されることを前提としています（init_audit_schema が SET TimeZone='UTC' を実行）。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは src 配下のパッケージ構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数・設定管理（.env 自動ロード含む）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得・保存関数）
    - news_collector.py     — RSS ニュース収集・保存・銘柄抽出
    - schema.py             — DuckDB スキーマ定義 / init_schema
    - pipeline.py           — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py— マーケットカレンダー管理
    - audit.py              — 監査ログ（signal/order_request/executions）
    - quality.py            — データ品質チェック
  - strategy/
    - __init__.py           — 戦略モジュール用エントリ
  - execution/
    - __init__.py           — 発注/約定処理用エントリ
  - monitoring/
    - __init__.py           — 監視関連モジュール（監視 DB 等）

各モジュールはさらに詳細なドキュメント（DataPlatform.md 等）を参照する設計です。

---

## 開発・拡張メモ

- strategy / execution / monitoring は拡張ポイントです。シグナル生成→リスク管理→発注フローを実装して監査ログに接続してください。
- テスト容易性のため、jquants_client._urlopen や news_collector._urlopen 等をモックしてネットワークを切り離したユニットテストが可能です。
- DuckDB を使うことでローカルで軽量にデータ操作ができます。プロダクションではバックアップやファイルロックに留意してください。

---

必要であれば README にサンプル .env.example、詳細な API 使用例（関数別の引数説明）、さらに CI / デプロイ手順（systemd / cron / Airflow 等での運用例）を追加します。どの情報を優先的に追加しますか？