# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ（KabuSys）のリポジトリ向け README。  
このドキュメントは、コードベース内のモジュール（データ取得・ETL・スキーマ・品質チェック・監査ログなど）に基づいて作成しています。

---

## プロジェクト概要

KabuSys は、日本株の市場データ取得・保存・品質管理・戦略実行に必要な基盤機能を提供する Python パッケージのコア部分です。主な目的は次の通りです。

- J-Quants API からの株価・財務・マーケットカレンダー取得
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution 層）の初期化・管理
- ETL（差分取得、バックフィル、保存）パイプライン
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用テーブルの初期化

設計の要点として、API のレート制限遵守・リトライ・トークン自動リフレッシュ・冪等な保存（ON CONFLICT DO UPDATE）・UTC タイムスタンプ保存などを採用しています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（リフレッシュトークンによる ID トークン取得）
  - レートリミッタ（120 req/min）、指数バックオフリトライ、401 時の自動トークンリフレッシュ
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）

- data/schema.py
  - DuckDB 用の完全なスキーマ定義（Raw / Processed / Feature / Execution）
  - テーブル作成・インデックス作成を行う init_schema 関数、既存 DB への接続 get_connection

- data/pipeline.py
  - 日次 ETL パイプライン（run_daily_etl）
  - 差分更新ロジック（最終取得日の確認、backfill の実行）
  - ETLResult クラスによる実行結果の集約
  - 個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）

- data/quality.py
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 各チェックは QualityIssue のリストを返す（重大度: error / warning）
  - run_all_checks で一括実行

- data/audit.py
  - 監査ログ用テーブル定義（signal_events / order_requests / executions）
  - init_audit_schema / init_audit_db により監査テーブルをセットアップ
  - トレーサビリティを保証する設計（UUID 連鎖、UTC、削除禁止の方針等）

- config.py
  - 環境変数読み込み・管理（Settings クラス）
  - プロジェクトルートの自動検出に基づく .env / .env.local の自動読み込み（任意で無効化可能）
  - 必須環境変数のチェック（_require）

---

## 必要条件（推奨）

- Python 3.10+
- duckdb
- （ネットワークアクセスが必要）J-Quants API を利用する場合は API 資格情報
- その他、実行環境に応じて依存パッケージを追加してください

（このリポジトリに requirements.txt / pyproject.toml がある場合はそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate.bat）
3. 必要パッケージをインストール
   - pip install duckdb
   - 追加の依存があれば pip install -r requirements.txt
4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml を基準）に `.env` を作成します。
   - 自動読み込みの挙動:
     - OS 環境変数の優先度が最も高い
     - 次に `.env`（override=False: OS 変数を上書きしない）
     - 最後に `.env.local`（override=True: `.env.local` が `.env` を上書き可能。ただし OS 環境変数は保護される）
     - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
5. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - KABUSYS_ENV: one of development / paper_trading / live（省略時 development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（省略時 INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（省略時 data/kabusys.duckdb）
   - SQLITE_PATH: 監視用途の SQLite パス（省略時 data/monitoring.db）

例 .env（最小）
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

## 使い方（基本例）

以下は Python スクリプト・REPL からの基本的な使い方例です。

1) DuckDB スキーマ初期化（初回）
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Settings から取得される Path
conn = init_schema(settings.duckdb_path)  # ディレクトリ自動作成、テーブル作成
```

2) 日次 ETL の実行（市場カレンダー・株価・財務データの差分取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
# conn は init_schema で取得した DuckDB 接続
result = run_daily_etl(conn)
print(result.to_dict())
```

3) 監査ログテーブルの初期化（監査テーブルを既存の DB に追加）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)  # conn は init_schema の接続
```

4) J-Quants の個別データ取得（テストやバッチで）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

token = get_id_token()  # settings.jquants_refresh_token を使用して ID トークンを取得
records = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,12,31))
# 保存は jquants_client.save_daily_quotes(conn, records)
```

5) 品質チェックの個別実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)
for issue in issues:
    print(issue)
```

ポイント:
- run_daily_etl は独立したステップ毎にエラーを捕捉するため、1 ステップ失敗でも他ステップを続行します。ETLResult に errors と quality_issues が格納されます。
- jquants_client は API レート制限（120 req/min）を内部で尊重します。大量取得時はこの制約に注意してください。
- get_id_token はリフレッシュトークンを用いた取得で、_request 内のロジックにより 401 発生時は自動リフレッシュを試みます。

---

## 便利な設定と注意点

- .env の自動読み込み
  - config._find_project_root() により、パッケージ内部のファイル位置に依らずプロジェクトルートを探索して `.env` / `.env.local` を自動ロードします。
  - 自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。

- 環境モード
  - KABUSYS_ENV は "development", "paper_trading", "live" のいずれかを指定。Settings.is_live / is_paper / is_dev で判定可能。

- ログレベル
  - LOG_LEVEL により内部ログ出力の閾値を制御します。デフォルトは INFO。

- DuckDB の使用
  - init_schema は :memory: を渡すとインメモリ DB を作成します（テスト用途に便利）。
  - 親ディレクトリが無ければ自動で作成されます。

- 冪等性
  - jquants_client の保存関数は ON CONFLICT DO UPDATE を使っているため繰り返し実行してもデータを更新でき、重複を排除します。

---

## ディレクトリ構成（主要ファイル）

以下はこのリポジトリ内の主要なファイル/モジュール構成です（省略化）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings
  - execution/                      — 発注関連（サブモジュール placeholder）
    - __init__.py
  - strategy/                       — 戦略関連（サブモジュール placeholder）
    - __init__.py
  - monitoring/                     — 監視関連（placeholder）
    - __init__.py
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + DuckDB 保存
    - schema.py                     — DuckDB スキーマ定義・初期化
    - pipeline.py                   — ETL パイプライン（差分更新・品質チェック）
    - audit.py                      — 監査ログテーブルの定義・初期化
    - quality.py                    — データ品質チェック

（上記に加えてテスト、ドキュメント、スクリプト等がプロジェクトルートに存在する場合があります）

---

## 開発時のヒント / FAQ

- テストで .env 自動読み込みを回避したい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してから Settings をインポートしてください。
- J-Quants トークンエラー（401）が出る場合:
  - jquants_client のロジックは 401 時にリフレッシュを試行しますが、リフレッシュトークン自体が無効な場合は get_id_token() が失敗します。JQUANTS_REFRESH_TOKEN を確認してください。
- スパイク閾値の調整:
  - pipeline.run_daily_etl / quality.run_all_checks では spike_threshold を調整できます（デフォルト 0.5 = ±50%）。

---

この README はコードリポジトリ内の実装に基づき作成しています。追加の機能や運用フロー（戦略実装、ブローカー連携、モニタリング通知など）は別モジュールとして拡張していく想定です。必要であれば、README の英訳、利用例・CI 設定・デプロイ手順なども作成します。