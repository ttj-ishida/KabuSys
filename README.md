# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants / RSS 等から市場データ・ニュースを収集し、DuckDB に蓄積、品質チェックや戦略層への特徴量供給、監査ログ（発注→約定のトレーサビリティ）を提供します。

主な設計方針：
- データの冪等性（ON CONFLICT）とトレーサビリティ重視
- API レート制御・リトライ・トークン自動更新
- SSRF 対策や XML 脆弱性対策（defusedxml 等）
- DuckDB を使った軽量な分析・ETL 基盤

バージョン: 0.1.0

---

## 機能一覧

- J-Quants クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レートリミット制御、リトライ、401 時のトークン自動リフレッシュ
  - DuckDB に対する冪等保存関数（save_*）
- ETL パイプライン
  - 差分取得（バックフィル対応）、市場カレンダー先読み、品質チェック実行
  - 日次 ETL のエントリ（run_daily_etl）
- データスキーマ / 初期化
  - Raw / Processed / Feature / Execution 層を含む DuckDB スキーマ定義
  - init_schema および監査用 init_audit_schema / init_audit_db
- ニュース収集（RSS）
  - RSS 取得・前処理・記事ID（URL 正規化→SHA-256）生成・DuckDB 保存
  - SSRF 対策、受信サイズ上限、gzip 解凍制御
  - 記事と銘柄コードの紐付け（extract_stock_codes, save_news_symbols）
- マーケットカレンダー管理
  - 営業日判定、前後の営業日取得、カレンダー夜間更新ジョブ
- 品質チェック
  - 欠損データ、スパイク（前日比）、重複、日付不整合の検出
  - QualityIssue オブジェクトで問題を集計
- 監査ログ（Audit）
  - signal_events, order_requests, executions を通した発注〜約定の完全トレーサビリティ

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の union 型表記 (|) を使用）
- Git 等（プロジェクトルート検出用に .git または pyproject.toml を推奨）

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - (Windows) .venv\Scripts\activate
   - (macOS/Linux) source .venv/bin/activate

2. 依存パッケージをインストール
   - 必須（代表例）:
     - duckdb
     - defusedxml
   - pip install duckdb defusedxml
   - （開発時は他の依存が追加される可能性があります。pyproject.toml / requirements.txt があればそれに従ってください）

3. パッケージをインストール（開発モード）
   - リポジトリルートで:
     - pip install -e .

4. 環境変数の設定
   - プロジェクトルートに .env または .env.local を配置できます。  
     config モジュールは自動で .env → .env.local をロードします（環境変数優先、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD：kabu ステーション API 用パスワード
     - SLACK_BOT_TOKEN：Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID：通知先 Slack チャンネル ID
   - オプション / デフォルト:
     - KABUSYS_ENV：development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL：DEBUG, INFO, WARNING, ...（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD：1 にすると .env の自動ロードを無効化
     - KABU_API_BASE_URL：kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH：DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH：監視用 SQLite パス（デフォルト data/monitoring.db）

例 (.env)
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=xxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

以下は Python から直接利用する際の例です。スクリプトやバッチから呼び出して ETL・ニュース収集等を実行します。

1. DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

2. 監査ログテーブルの初期化（既存 conn に追加）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

3. 日次 ETL 実行（全 ETL + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

4. ニュース収集ジョブ実行
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄抽出に使う有効コードの集合（省略すると紐付けをスキップ）
res = run_news_collection(conn, known_codes={"7203","6758"})
print(res)  # {source_name: saved_count, ...}
```

5. カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

6. J-Quants の認証トークン取得（必要に応じて）
```python
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を使用
```

注意点：
- run_daily_etl 等は内部で API 呼び出し・ファイル I/O を行います。ログを適切に設定して実行してください。
- 自動 .env ロードは config モジュールが行います。テスト時に無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

下記はパッケージ内の主要ファイル/モジュール構成です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動ロード、Settings）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS ニュース収集・前処理・保存
    - schema.py              — DuckDB スキーマ定義・init_schema
    - pipeline.py            — ETL パイプライン（差分更新、品質チェック）
    - calendar_management.py — マーケットカレンダー関連ユーティリティ / バッチ
    - audit.py               — 監査ログ（signal_events / order_requests / executions）
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — 戦略層（将来的に拡張）
  - execution/
    - __init__.py            — 発注実行層（ブローカー連携等）
  - monitoring/
    - __init__.py            — 監視・メトリクス（将来的に拡張）

各モジュールはドキュメント文字列とログを備え、DuckDB の SQL はパラメータバインドを用いる等、安全性に配慮しています。

---

## 開発・運用上の補足

- ロギング: settings.log_level によりログレベルを制御します。デプロイ先で環境変数 LOG_LEVEL を設定してください。
- テスト性: pipeline 等は id_token を引数で注入できる設計のため、モックトークンでの単体テストが可能です。
- セキュリティ:
  - RSS 取り込みでは defusedxml を使い XML Bomb を防ぎます。
  - リダイレクト時やホスト解決時にプライベートアドレスを検出して SSRF 対策を実施します。
  - .env ファイル読み込み時に OS 環境変数を保護するオプションがあります。
- データ整合性: DuckDB への保存は可能な限り ON CONFLICT（DO UPDATE / DO NOTHING）で設計されています。

---

README に記載のない詳細実装や追加のユーティリティ（Slack 通知、kabu ステーションの具体的な注文実装等）は各モジュールに実装予定／拡張可能です。必要であればサンプルスクリプトや CLI ラッパーの追加を提案できます。