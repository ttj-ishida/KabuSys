# KabuSys

日本株自動売買システムのコアライブラリ（KabuSys）。  
データ収集（J-Quants）、データ永続化（DuckDB）、監査ログ、発注フロー基盤を提供するモジュール群を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買プラットフォーム向けに設計された内部ライブラリです。  
主な目的は以下です。

- 外部データソース（J-Quants）からの市場データ取得とロバストな通信（レートリミット・リトライ・トークンリフレッシュ）
- 取得データの DuckDB への永続化（冪等的な INSERT / ON CONFLICT 更新）
- DuckDB によるデータスキーマ（Raw / Processed / Feature / Execution レイヤー）の提供と初期化
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）を記録する監査スキーマ
- 環境変数管理（.env 自動読み込み・明示的設定）と設定ラッパー

設計上の留意点として、Look-ahead Bias を避けるために取得時刻（UTC）を保存すること、API レート制限（120 req/min）を守ること、監査ログは削除しない前提で設計されていることなどがあります。

---

## 機能一覧

- 環境変数 / 設定:
  - .env / .env.local をプロジェクトルートから自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須設定に対する検証（未設定時は ValueError）
  - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL の検証

- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - 固定間隔レートリミッタ（120 req/min）
  - リトライ（指数バックオフ、最大 3 回、408/429/5xx 等に対応）
  - 401 発生時の自動トークンリフレッシュ（1 回）
  - ページネーション対応
  - DuckDB への保存関数（save_daily_quotes 等）は冪等（ON CONFLICT DO UPDATE）

- DuckDB スキーマ（kabusys.data.schema）
  - Raw / Processed / Feature / Execution レイヤーを含む多くのテーブル DDL を提供
  - インデックス定義、外部キーを考慮した作成順序
  - init_schema(db_path) で初期化および接続取得

- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions テーブルを提供
  - 監査用インデックス、UTC タイムゾーン設定
  - init_audit_schema(conn) / init_audit_db(path) を提供

- その他モジュールプレースホルダ:
  - strategy, execution, monitoring パッケージ（拡張用エントリポイント）

---

## 必要条件 / 依存関係

- Python 3.10 以上（パイプライン型注釈（A | B）を使用しているため）
- duckdb パッケージ

インストール例:
```
pip install duckdb
```

プロジェクトを開発環境としてインストールする場合（ソースツリーのルートで）:
```
pip install -e .
```
（pyproject.toml / setup.py が存在する前提です）

---

## 環境変数（主なもの）

必須（アプリケーション起動前に設定するか .env を作成）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API 用パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意 / デフォルトあり:

- KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL （デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env 読み込みを無効化（テスト時など）

.env のサンプル（プロジェクトルートに .env.example を置くことを想定）を作成してください。

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. Python 3.10+ 環境を用意（venv 推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb
   ```
   （プロジェクトで requirements.txt / pyproject.toml があればそれを利用）

4. 環境変数を設定（.env をプロジェクトルートに置く）
   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB スキーマの初期化（Python REPL やスクリプトで実行）
   ```
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   ```
   これにより必要な全テーブルとインデックスが作成されます。

6. （任意）監査ログを追加で初期化する場合:
   ```
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)
   ```

---

## 使い方（簡単な例）

- J-Quants から日足を取得して DuckDB に保存する例:

```
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema
from kabusys.config import settings

# DB 初期化または接続
conn = init_schema(settings.duckdb_path)

# 例: 特定銘柄または全銘柄（code=None）
records = fetch_daily_quotes(code="7203")  # トヨタ例
# または date 範囲で取得
# from datetime import date
# records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))

# 保存（冪等）
n = save_daily_quotes(conn, records)
print(f"saved {n} rows")
```

- 財務データ取得 → 保存:

```
from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements

records = fetch_financial_statements(code="7203")
save_financial_statements(conn, records)
```

- マーケットカレンダー取得 → 保存:

```
from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar

calendar = fetch_market_calendar()
save_market_calendar(conn, calendar)
```

- id_token を直接取得（通常は自動で管理される）:
```
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

注意点:
- API リクエストは内部でレートリミットとリトライを行います。
- 401 エラー発生時は自動的にリフレッシュし 1 回リトライします（無限ループ回避あり）。
- DuckDB への保存関数は ON CONFLICT DO UPDATE を使用しているため同一キーの重複登録は更新されます（冪等性）。

---

## ディレクトリ構成

プロジェクトの主要ファイル構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py               # 環境変数・設定管理（.env 自動読み込み含む）
    - data/
      - __init__.py
      - jquants_client.py     # J-Quants API クライアント（取得・保存ロジック）
      - schema.py             # DuckDB スキーマ定義・初期化
      - audit.py              # 監査ログ（signal_events, order_requests, executions）
      - audit.py
    - strategy/                # 戦略ロジック用パッケージ（拡張ポイント）
      - __init__.py
    - execution/               # 発注・ブローカー連携（拡張ポイント）
      - __init__.py
    - monitoring/              # 監視・メトリクス（拡張ポイント）
      - __init__.py

その他:
- .env.example（存在すれば）: 環境変数サンプル
- pyproject.toml / setup.cfg / setup.py（プロジェクト配布設定: 存在する場合）

---

## 設計上の重要なポイント / 注意事項

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。CWD に依存しないため、パッケージ配布後も正しく動作します。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定してください。
- DuckDB の初期化（init_schema）は冪等であり、既存テーブルは上書きされません。初回のみ実行してください。
- 監査ログは削除を前提としないため、FK は ON DELETE RESTRICT 等で保護されています。監査テーブルは必ず UTC タイムゾーンで保存されます（init_audit_schema は SET TimeZone='UTC' を実行します）。
- Python バージョンは 3.10 以上を想定しています（型注釈に A | B を使用）。

---

## 今後の拡張案（参考）

- strategy / execution / monitoring モジュールの実装（シグナル生成→発注→モニタリングのフルワークフロー）
- SLACK 通知連携による運用アラート
- パフォーマンス計測・バックテスト用ツールの追加
- 単体テスト・統合テスト、CI 設定

---

## サポート / コントリビュート

内部ライブラリのため、利用・拡張を行う場合はまずローカル環境で DuckDB を作成し、安全なテスト環境（KABUSYS_ENV=paper_trading）で動作確認してください。プルリクエストや問題報告の際は、再現手順とログ（LOG_LEVEL を DEBUG にして得られる詳細）を添えてください。

---

README は以上です。必要であれば、README にサンプル .env.example、より詳細な API 使用例、あるいは contribution ガイド（CONTRIBUTING.md）を追加しますか？