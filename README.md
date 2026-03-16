# KabuSys

日本株向けの自動売買プラットフォーム基盤ライブラリです。データ取得、スキーマ管理、監査ログ、データ品質チェック、設定管理など、自動売買システムの基盤（Data Platform / Execution Platform）を提供します。

主な設計方針:
- データのトレーサビリティ（fetched_at / UTC タイムスタンプ／監査ログ）
- 冪等性（DuckDB への ON CONFLICT / 冪等キー）
- API レート制御とリトライ（J-Quants クライアント）
- データ品質チェックを組み込み

バージョン: 0.1.0

---

## 機能一覧

- 設定管理（環境変数 / .env 自動読み込み）
  - 自動でプロジェクトルート（`.git` または `pyproject.toml`）を探索して `.env` / `.env.local` を読み込み
  - 必須環境変数チェックを提供（Settings クラス）
- データ取得（J-Quants API クライアント）
  - 日次株価（OHLCV）のページネーション取得
  - 財務データ（四半期 BS/PL）の取得
  - JPX マーケットカレンダーの取得
  - レート制限（120 req/min）、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化（冪等）
  - インデックスの作成
- 監査ログ（Audit）
  - シグナル → 発注 → 約定 のトレーサビリティテーブル（UUID を用いたチェーン）
  - 発注要求に冪等キー (order_request_id) を付与
  - UTC タイムスタンプ保存、FK による参照整合性
- データ品質チェック（Quality）
  - 欠損データ検出（OHLC 欄）
  - スパイク（前日比）検出
  - 重複チェック（主キー重複）
  - 日付不整合（未来日付／非営業日データ）検出
- （骨組み）strategy / execution / monitoring パッケージのプレースホルダ

---

## 必要条件

- Python 3.10+（型注釈に union | を使用）
- 依存パッケージ（例）
  - duckdb
- 標準ライブラリ（urllib, json, logging, datetime 等）

※ 実行環境に合わせて requirements.txt を整備してください（本リポジトリには含まれていない場合があります）。

例:
```
pip install duckdb
```

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成して依存をインストール
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install duckdb
   ```
3. 環境変数を設定
   - プロジェクトルート（`.git` または `pyproject.toml` がある場所）に `.env` / `.env.local` を配置すると自動で読み込まれます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（Settings により参照）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャネル ID

任意／デフォルト値あり:
- KABUS_API_BASE_URL — デフォルト: `http://localhost:18080/kabusapi`
- DUCKDB_PATH — デフォルト: `data/kabusys.duckdb`
- SQLITE_PATH — デフォルト: `data/monitoring.db`
- KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト: `development`）
- LOG_LEVEL — `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト: `INFO`）

例 `.env`（テンプレート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（クイックスタート）

（1）DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数に基づくデフォルトパスを返します
conn = init_schema(settings.duckdb_path)
```

（2）J-Quants から日次株価を取得して保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
from kabusys.data.schema import get_connection
from kabusys.config import settings

# 必要であれば明示的に ID トークンを取得
id_token = get_id_token()  # 省略可：モジュールキャッシュを利用

# データを取得（例: 特定銘柄・期間）
records = fetch_daily_quotes(id_token=id_token, code="7203", date_from=None, date_to=None)

# DuckDB に保存
conn = get_connection(settings.duckdb_path)
saved = save_daily_quotes(conn, records)
print(f"保存レコード数: {saved}")
```

主な API 振る舞い:
- _request はレート制限（120 req/min）を固定間隔スロットリングで守り、リトライ（最大 3 回、指数バックオフ）を行います。
- 401 エラー時は自動でリフレッシュトークンから ID トークンを再取得し一度だけリトライします。
- fetch_* 系関数はページネーションに対応し、結果を全件取得します。

（3）監査ログスキーマ初期化（既存の DuckDB 接続に追加）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)  # conn は init_schema で取得した接続
```

（4）データ品質チェックの実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
```

---

## 主要モジュール解説

- kabusys.config
  - Settings クラスを通して環境変数を取得。必須変数未設定時は ValueError を投げる。
  - .env 自動ロード: プロジェクトルートを探索し `.env` → `.env.local`（上書き）を読み込む。
- kabusys.data.jquants_client
  - J-Quants API とのやり取り、レート制御、リトライ、トークン管理、DuckDB 保存用ユーティリティを提供。
- kabusys.data.schema
  - DuckDB の全テーブル（Raw/Processed/Feature/Execution）とインデックスを作成する init_schema を提供。get_connection で接続を取得。
- kabusys.data.audit
  - 監査ログ用テーブル（signal_events, order_requests, executions）および関連インデックスを初期化。
- kabusys.data.quality
  - データ品質チェック（欠損、重複、スパイク、日付不整合）を実装。run_all_checks でまとめて実行可能。
- kabusys.strategy / kabusys.execution / kabusys.monitoring
  - パッケージプレースホルダ。戦略ロジック、発注実行、監視（Slack 等）を実装する場所。

---

## ディレクトリ構成

リポジトリの主要ファイル／ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py            - パッケージ設定（バージョン、エクスポート）
  - config.py              - 環境変数／設定管理（.env 自動ロード、Settings）
  - data/
    - __init__.py
    - jquants_client.py    - J-Quants API クライアント（取得・保存ロジック）
    - schema.py            - DuckDB スキーマ定義と初期化
    - audit.py             - 監査ログ（トレーサビリティ）定義と初期化
    - quality.py           - データ品質チェック
  - strategy/
    - __init__.py          - 戦略関連モジュール（拡張ポイント）
  - execution/
    - __init__.py          - 発注・ブローカー連携（拡張ポイント）
  - monitoring/
    - __init__.py          - モニタリング／アラート（拡張ポイント）

---

## 運用上の注意

- 環境変数の管理は慎重に行ってください。`.env.local` はローカル専用の上書きに使いますが、機密情報をリポジトリに含めないでください。
- DuckDB ファイルはデフォルトで `data/kabusys.duckdb` に作成されます。バックアップ・持ち出しポリシーを決めてください。
- J-Quants API にはレート制限があります。本クライアントは固定間隔スロットリングで制御しますが、大量の並列プロセスで呼ぶと制限を超える恐れがあります。
- 監査ログ（audit）は削除しない前提で設計されています。データの整合性を保つため、FK 制約は ON DELETE RESTRICT を採用しています。
- すべての TIMESTAMP は UTC を使用する設計です（監査ログ初期化時に TimeZone を UTC に設定します）。

---

## 開発／拡張ガイド（簡略）

- 戦略実装:
  - kabusys.strategy パッケージに戦略モジュールを追加し、signal_events テーブルへシグナルを書き出す
- 発注実装:
  - kabusys.execution パッケージで証券会社 API（kabuステーション等）とのやり取りを行い、order_requests → executions の流れを実装
- 通知／監視:
  - kabusys.monitoring に Slack 通知等を実装。Settings から SLACK_BOT_TOKEN / SLACK_CHANNEL_ID を利用

---

必要であれば README にサンプル .env.example、requirements.txt、テスト実行方法（pytest 等）や CI 設定のテンプレートを追加できます。どの情報を補足したいか教えてください。