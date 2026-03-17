# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群。  
J-Quants 等の外部データソースから市場データ・財務データ・ニュースを取得して DuckDB に格納し、品質チェック・カレンダー管理・監査ログ等を提供します。戦略層（strategy）、発注層（execution）、監視（monitoring）との接続を想定した基盤コンポーネント群です。

---

## 主な特徴（機能一覧）

- 環境設定管理
  - `.env`, `.env.local` または環境変数から自動読み込み（プロジェクトルート検出）
  - 必須環境変数は Settings 経由で明示的に取得
- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務、JPX マーケットカレンダーの取得
  - レートリミット（120 req/min）準拠（固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回）、401 時はトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録（Look-ahead Bias 対策）
  - DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE）
- ニュース収集
  - RSS フィードから記事を収集し raw_news に保存
  - URL 正規化（トラッキングパラメータ除去）→ SHA-256 先頭32文字で記事ID生成（冪等性）
  - SSRF / XML Bomb / 大きなレスポンス対策（defusedxml, ホスト検証, サイズ制限）
  - 銘柄コード抽出（4桁コード）と news_symbols への紐付け
- ETL パイプライン
  - 差分更新（最終取得日に基づく差分取得）、バックフィルで後出し修正を吸収
  - 品質チェック（欠損、重複、スパイク、日付不整合）
  - run_daily_etl による一括処理（calendar → prices → financials → quality_checks）
- マーケットカレンダー管理
  - market_calendar を中心に営業日判定、次/前営業日の取得、期間内営業日取得などのユーティリティ
  - calendar_update_job による夜間差分更新
- 監査ログ（Audit）
  - signal → order_request → executions のトレーサビリティ用テーブル群を提供
  - 発注冪等キー（order_request_id）や broker_execution_id の一意性管理
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化 API

---

## 動作環境・依存条件

- Python 3.10+
  - 型ヒントに union operator (|) を使用しているため 3.10 以降を想定
- 必要な主要パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）や DuckDB ファイル書き込み権限が必要

必要なパッケージはプロジェクトに requirements.txt があればそちらを利用してください。無ければ最低限以下をインストールします。

pip install duckdb defusedxml

---

## 環境変数（主なもの）

必須（Settings で _require_ されるもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意／デフォルトあり:
- KABUSYS_ENV — 環境: development / paper_trading / live （デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動ロードを無効化
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用 DB）パス（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト localhost:18080）

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml を含むディレクトリ）にある `.env` と `.env.local` を自動的に読み込みます。OS 環境変数が優先され、`.env.local` は `.env` を上書きできます。自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順

1. リポジトリをクローン / プロジェクトのルートに移動
2. Python 環境を用意（推奨: 仮想環境）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows では .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install -r requirements.txt  （requirements.txt がない場合は最低限 pip install duckdb defusedxml）
4. 環境変数を設定
   - プロジェクトルートに .env を作成するか、OS 環境変数として設定します。
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
5. DuckDB スキーマ初期化
   - Python REPL または小さなスクリプトで初期化します（下の「使い方」を参照）。

---

## 使い方（主要 API と実行例）

以下は基本的な使い方サンプルです。実行はプロジェクトルートで行ってください。

- DuckDB にスキーマを作成して接続する

```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")  # 親ディレクトリを自動作成
```

- run_daily_etl を使って日次 ETL を実行する

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を渡さない場合は今日を基準
print(result.to_dict())
```

- ニュース収集ジョブを実行する

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット（任意）
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

- カレンダー更新バッチ（夜間ジョブ）を実行する

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
```

- 監査ログテーブルを追加で初期化する

```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
init_audit_schema(conn)
```

- 設定値にアクセスする

```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.is_live)
```

注意点:
- J-Quants API の認証トークン取得は get_id_token を内部で行います。`JQUANTS_REFRESH_TOKEN` を設定しておいてください。
- ニュース収集は外部 RSS に依存します。SSRF 対策やサイズ制限が組み込まれているため、外部フィードの扱いに注意してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - schema.py              — DuckDB スキーマ定義・初期化
    - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - news_collector.py      — RSS ニュース収集・保存ロジック
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログ（signal/order/execution）初期化
  - strategy/
    - __init__.py            — 戦略層（拡張ポイント）
  - execution/
    - __init__.py            — 発注層（拡張ポイント）
  - monitoring/
    - __init__.py            — 監視（拡張ポイント）

（プロジェクトルート）
- .env / .env.local           — 環境変数（任意）
- pyproject.toml or setup ... — パッケージメタ情報（存在時、config のプロジェクトルート検出に利用）

---

## 実運用上の注意と設計メモ

- API レート制限を厳守するため、J-Quants クライアントは固定間隔スロットリングとリトライを実装しています。大量リクエストを組む場合は注意してください。
- データ取得時の fetched_at（UTC）は「いつシステムがそのデータを知り得たか」を示すため、将来のバックテストやトレーニングでの Look-ahead Bias 防止に役立ちます。
- DuckDB の INSERT は基本的に ON CONFLICT を使って冪等化していますが、外部からのデータ投入やスキーマ変更には注意してください。
- news_collector は RSS の XML を解析します。外部からのフィードを扱うため、XML 関連の脆弱性対策（defusedxml）、SSRF 対策、最大受信サイズ制限を行っています。
- audit（監査）テーブル群は発注のトレーサビリティを保証するため、削除しないことを前提とした設計になっています。UTC タイムスタンプを利用してください。

---

## 貢献・拡張ポイント

- strategy/*, execution/*, monitoring/* は拡張用プレースホルダです。各自の戦略ロジック・ブローカー連携・アラート実装を追加してください。
- Slack 通知や監視アラートなどの実装は、monitoring モジュールに統合することを想定しています。
- より高度なレート制御や非同期取得（asyncio）への移行は、将来のパフォーマンス改善候補です。

---

この README はコードベースの主要機能と使い方を簡潔にまとめたものです。詳細は各モジュール（src/kabusys/data/*.py 等）の docstring を参照してください。問題や不明点があれば開発者ドキュメントに追記してください。