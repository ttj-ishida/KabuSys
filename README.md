# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、カレンダー管理、監査ログなどの基盤機能を提供します。

---

## プロジェクト概要

KabuSys は、J-Quants 等から取得した市場データを DuckDB に蓄積し、ETL パイプライン・品質チェック・ニュース収集・カレンダー管理・監査ログ等の機能を一元的に提供するライブラリです。  
設計上の主な特徴：

- データ取得はレート制限・リトライ・トークン自動リフレッシュに対応
- DuckDB を使った冪等な保存（ON CONFLICT / INSERT … RETURNING を利用）
- News RSS 収集は SSRF 対策・XML 攻撃対策（defusedxml）・受信サイズ制限を実装
- データ品質チェック（欠損・スパイク・重複・日付不整合）を提供
- 監査ログ（シグナル→発注→約定 のトレースを UUID 連鎖で保持）

パッケージバージョン: 0.1.0

---

## 機能一覧

- 環境設定管理（.env 自動読み込み・必須チェック）
  - 環境: development / paper_trading / live
- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務、マーケットカレンダー取得
  - レート制御（120 req/min）・リトライ・トークン自動リフレッシュ
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution 層のテーブル群を作成
- ETL パイプライン
  - 差分更新（最終取得日ベース）・バックフィル機能・品質チェック統合
- ニュース収集（RSS）
  - URL 正規化・記事 ID（SHA-256 短縮）による冪等保存、銘柄コード抽出
  - SSRF・gzip爆弾・XML攻撃対策
- マーケットカレンダー管理
  - 営業日判定、前後の営業日の探索、夜間更新ジョブ
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出と報告
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルを含む監査用スキーマ

---

## 前提・依存関係

- Python 3.10 以上（型ヒントの union 型 `X | Y` を使用）
- 必要なパッケージ（代表例）:
  - duckdb
  - defusedxml
- 標準ライブラリのみで動作する部分もありますが、実運用では上記ライブラリをインストールしてください。

例（pip）:
```bash
python -m pip install "duckdb" "defusedxml"
# またはプロジェクト内にrequirements.txt があればそれを使う
```

---

## セットアップ手順

1. リポジトリをクローンして、パッケージをインストール（開発モード推奨）
   ```bash
   git clone <repo_url>
   cd <repo_root>
   python -m pip install -e .
   ```

2. 環境変数を設定
   - ルートに `.env` / `.env.local` を置くと自動読み込みされます（ただしテスト時などは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
   - 必須の環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu API のパスワード（kabu ステーション利用時）
     - SLACK_BOT_TOKEN: Slack 通知に使う Bot トークン（必要に応じて）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必要に応じて）
   - オプション:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると自動 .env 読み込みを無効化
     - DUCKDB_PATH（例: data/kabusys.duckdb）、SQLITE_PATH（監視用 DB）

   例（.env の最小例）:
   ```
   JQUANTS_REFRESH_TOKEN=～YOUR_TOKEN～
   KABU_API_PASSWORD=～YOUR_PASS～
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから初期化します:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   # またはインメモリ: init_schema(":memory:")
   ```

4. 監査ログスキーマの追加（必要な場合）
   ```python
   from kabusys.data.schema import get_connection
   from kabusys.data.audit import init_audit_schema
   conn = get_connection("data/kabusys.duckdb")
   init_audit_schema(conn)
   ```

---

## 使い方（代表的な例）

- J-Quants の ID トークン取得（通常はライブラリ内部で自動処理されますが、明示的に取得する場合）:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を利用
```

- 日次 ETL（株価・財務・カレンダー・品質チェック）
```python
from kabusys.data.schema import get_connection, init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")  # まだ初期化していない場合
result = run_daily_etl(conn)  # target_date を指定可
print(result.to_dict())
```

- ニュース収集ジョブ（RSS から記事を取得して保存し、既知銘柄で紐付け）
```python
from kabusys.data.schema import get_connection, init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄コードのセット（例: {'7203','6758'}）。ない場合は紐付けをスキップ。
res = run_news_collection(conn, known_codes={'7203','6758'})
print(res)  # {source_name: saved_count, ...}
```

- カレンダーの夜間バッチ更新
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection, init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved: {saved}")
```

- データ品質チェックを個別に実行
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

注意:
- J-Quants API 呼び出しは内部でレート制御・リトライ・トークン更新を行います。API レートや認証情報は設定次第で変わるため、実行時はログを確認してください。
- News RSS の取得は外部 HTTP を行うため、ネットワーク・セキュリティのポリシーに注意してください（SSRF 等の対策は実装済みですが周辺環境によって制約があります）。

---

## 環境設定の自動ロードについて

- パッケージはデフォルトでプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、`.env` と `.env.local` を読み込みます。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには環境変数を設定:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py                (パッケージメタ情報)
  - config.py                  (環境変数・設定管理)
  - data/
    - __init__.py
    - jquants_client.py        (J-Quants API クライアント)
    - news_collector.py        (RSS ニュース収集)
    - pipeline.py              (ETL パイプライン)
    - schema.py                (DuckDB スキーマ初期化)
    - calendar_management.py   (カレンダー管理・ユーティリティ)
    - audit.py                 (監査ログテーブル初期化)
    - quality.py               (データ品質チェック)
  - strategy/
    - __init__.py              (戦略インタフェース: 空のパッケージ)
  - execution/
    - __init__.py              (注文実行関連: 空のパッケージ)
  - monitoring/
    - __init__.py              (監視関連: 空のパッケージ)

この README はコードベースの主要モジュール構成と使い方のサンプルを簡潔にまとめたものです。各モジュールの詳細はソースコードの docstring や関数説明を参照してください。必要であれば、CLI やサービス化（systemd / cron / Airflow 等）に関する運用手順のテンプレートも追加できます。