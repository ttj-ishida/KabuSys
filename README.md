# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けのライブラリ群です。J-Quants や kabuステーション などの外部 API からデータを取得し、DuckDB を用いてデータ基盤（Raw / Processed / Feature / Execution / Audit 層）を構築・管理します。ETL、品質チェック、ニュース収集、マーケットカレンダー管理、監査ログなどの機能を備え、戦略層・実行層と連携するための基礎を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 必要条件 / 依存関係
- セットアップ手順
- 環境変数（.env）について
- 使い方（簡単なコード例）
- よく使うユーティリティ / 挙動のポイント
- ディレクトリ構成

---

## プロジェクト概要

このコードベースは、データ取得 -> 保存 -> 品質チェック -> 戦略用特徴量作成 -> 発注・監査までのデータプラットフォーム部分を実装しています。主要モジュールは data パッケージに集約されており、以下をサポートします。

- J-Quants API から株価・財務・カレンダーを取得（レート制限、リトライ、トークン自動更新 を実装）
- RSS からニュースを収集し前処理・DB保存（SSRF対策・サイズ制限・トラッキングパラメータ除去）
- DuckDB スキーマ定義 & 初期化
- ETL パイプライン（日次差分取得、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日の判定・翌営業日/前営業日の取得）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

---

## 主な機能一覧

- config
  - .env / .env.local をプロジェクトルートから自動読み込み（無効化可）
  - 環境変数をラップした Settings オブジェクトを提供

- data.jquants_client
  - J-Quants API クライアント
  - RateLimiter（120 req/min）
  - リトライ（指数バックオフ、最大 3 回）、401 の場合トークン自動リフレッシュ
  - fetched_at を UTC で記録
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）

- data.news_collector
  - RSS 取得・XML パース（defusedxml）
  - URL 正規化（トラッキング除去）→ SHA-256 の先頭 32 文字を記事 ID として冪等保存
  - SSRF 対策（スキーム検査、リダイレクト時のホスト検査、プライベート IP 拒否）
  - レスポンスサイズ制限（デフォルト 10MB）
  - raw_news / news_symbols の保存（チャンク挿入、トランザクション）

- data.schema
  - DuckDB テーブル定義 (Raw / Processed / Feature / Execution 層)
  - init_schema(db_path) で初期化

- data.pipeline
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - 差分取得、backfill（デフォルト 3 日）、品質チェック統合

- data.calendar_management
  - 営業日判定・next/prev_trading_day・get_trading_days
  - calendar_update_job で夜間バッチ更新

- data.audit
  - 監査用テーブル（signal_events / order_requests / executions）定義
  - init_audit_schema / init_audit_db（UTC タイムゾーン固定）

- data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - run_all_checks でまとめて実行、QualityIssue を返す

---

## 必要条件 / 依存関係

推奨 Python バージョン: 3.10+

主な依存ライブラリ（一例）
- duckdb
- defusedxml

（セットアップ時に requirements.txt や pyproject.toml を用意してください）

---

## セットアップ手順

1. リポジトリをクローン / プロジェクトルートへ移動

2. 仮想環境作成・有効化（例）
```bash
python -m venv .venv
source .venv/bin/activate
```

3. 依存関係インストール
（プロジェクトに requirements.txt/pyproject.toml がある想定）
```bash
pip install duckdb defusedxml
# または
pip install -e .
```

4. 環境変数を用意
プロジェクトルートに `.env` または `.env.local` を作成します（詳細は次節）。

5. DuckDB スキーマ初期化（例）
Python REPL やスクリプトで:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # settings.duckdb_path はデフォルト data/kabusys.duckdb
```

---

## 環境変数（.env）について

config モジュールはプロジェクトルート（.git または pyproject.toml を基準）を探索して自動的に `.env` / `.env.local` を読み込みます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — 通知対象の Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH — SQLite（監視等）パス (デフォルト: data/monitoring.db)
- KABUSYS_ENV — 環境 (development, paper_trading, live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)

例 .env
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単なコード例）

以下は典型的なワークフローの例です。

1) スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

3) ニュース収集（RSS を用いた記事収集と銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄抽出で用いる有効な銘柄コードの集合
known_codes = {"7203", "6758", "9984", ...}
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

4) カレンダー夜間バッチ更新
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("saved:", saved)
```

5) 監査ログ初期化（監査専用 DB を別ファイルに作る例）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

6) 品質チェック単体実行
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn)
for i in issues:
    print(i)
```

---

## よく使うユーティリティ / 挙動のポイント

- 自動 .env 読込
  - プロジェクトルート（.git または pyproject.toml がある場所）を起点に `.env` / `.env.local` を読み込みます。
  - .env.local の方が優先され、OS 環境変数は上書きされません（保護）。テストなどで無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

- jquants_client
  - レート制限: 120 req/min を守るためのスロットリング（固定間隔）
  - リトライ: ネットワークや 429/408/5xx に対して指数バックオフ（最大3回）
  - 401 受信時は refresh_token から id_token を再取得し 1 回リトライ
  - ページネーション対応（pagination_key）
  - DuckDB への保存関数は冪等（ON CONFLICT DO UPDATE / DO NOTHING）

- news_collector
  - defusedxml を使用し安全な XML パースを実施
  - レスポンスの読み取りサイズを制限（デフォルト 10MB）
  - リダイレクト先のスキーム・ホスト検査により SSRF を防止
  - URL を正規化してハッシュ化（記事ID生成）することで冪等性を保証

- schema.init_schema
  - 初期化は冪等（既存テーブルは保持）
  - db_path の親ディレクトリがなければ自動作成
  - ":memory:" を指定するとインメモリ DB が使える

- pipeline.run_daily_etl
  - カレンダー → 株価 → 財務 → (品質チェック) の順で実行
  - 差分更新（最終取得日から backfill 日数分を遡って再取得）
  - 各ステップは個別にエラーハンドリングされ、1 ステップ失敗でも他は継続

---

## ディレクトリ構成

主要ファイル / パッケージの概観（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                    # 環境変数 / Settings
    - execution/                   # 発注・実行関連（パッケージ）
    - strategy/                    # 戦略関連（パッケージ）
    - monitoring/                  # 監視関連（パッケージ）
    - data/
      - __init__.py
      - jquants_client.py          # J-Quants API クライアント（取得 + 保存）
      - news_collector.py          # RSS ニュース収集・保存
      - schema.py                  # DuckDB スキーマ定義 / init_schema
      - pipeline.py                # ETL パイプライン（run_daily_etl 等）
      - calendar_management.py     # マーケットカレンダー管理
      - audit.py                   # 監査ログ初期化 / テーブル定義
      - quality.py                 # データ品質チェック

---

## 開発メモ / 注意点

- 型ヒントは Python 3.10+ の構文（| を使ったユニオン）を使用しています。適切な Python バージョンを使用してください。
- ネットワークを伴う処理（J-Quants / RSS）は外部エラーに対して堅牢に設計されていますが、実行前に必要な API トークン・認証情報が正しく設定されていることを確認してください。
- テストを行う場合、news_collector._urlopen などの低レベル関数をモックするとネットワークを使わずにテストできます。
- DuckDB のトランザクションは一部関数で明示的に使用しています（トランザクション/チャンク挿入）。DDL 実行時のトランザクション管理に注意してください（audit.init_audit_schema に transactional オプションあり）。

---

必要であれば README に含めるコマンド例（Docker / systemd / crontab での定期実行例）や、より詳細な .env.example、pyproject.toml / requirements.txt のテンプレートも作成できます。どの情報を優先して追加しますか？