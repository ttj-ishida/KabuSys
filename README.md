# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）のリポジトリ向け README（日本語）。

この README はコードベースに含まれる主要モジュールに基づき、プロジェクトの概要・機能・セットアップ手順・使い方・ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株のデータ収集・ETL・品質チェック・監査ログ・マーケットカレンダー管理・ニュース収集・監視などを想定した自動売買プラットフォームの基盤ライブラリです。主に以下を提供します。

- J-Quants API を用いた株価・財務・カレンダー取得クライアント（レートリミット・リトライ・トークン自動更新対応）
- DuckDB を用いたスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL パイプライン（差分更新・バックフィル、品質チェック連携）
- ニュース収集モジュール（RSS 取得・正規化・SSRF対策・トラッキング除去・DuckDB保存）
- マーケットカレンダー管理（営業日判定・前後の営業日検索）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定までのトレーサビリティ）

設計上の特徴として、API のレート制限遵守、冪等性（ON CONFLICT を用いた保存）、Look-ahead バイアス防止のための fetched_at 記録、SSRF や XML 攻撃への対策などが組み込まれています。

---

## 機能一覧

- data/jquants_client.py
  - J-Quants API クライアント
  - レートリミット（120 req/min）、指数バックオフリトライ、401 時のトークン自動リフレッシュ
  - 株価日足、財務（四半期）、マーケットカレンダーの取得および DuckDB への保存関数

- data/schema.py
  - DuckDB 用 DDL 定義（Raw / Processed / Feature / Execution）
  - init_schema() / get_connection() を提供

- data/pipeline.py
  - ETL パイプライン（run_daily_etl、個別 ETL）
  - 差分更新、バックフィル、品質チェックの統合

- data/news_collector.py
  - RSS フィード取得、前処理、記事ID生成（URL 正規化 + SHA-256）、保存（冪等）
  - SSRF・Gzip/size 限度・defusedxml による安全な XML パース

- data/calendar_management.py
  - market_calendar の差分更新ジョブ
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day

- data/quality.py
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks による一括検査、QualityIssue レポート生成

- data/audit.py
  - 監査用テーブル（signal_events / order_requests / executions）と索引の初期化
  - init_audit_schema / init_audit_db を提供

- config.py
  - .env 自動読み込み（プロジェクトルート検出）
  - 環境変数アクセス用 settings オブジェクト
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動読み込みを無効化可能

---

## セットアップ手順（開発環境）

以下は最小限のセットアップ手順です。実際のプロジェクトでは requirements.txt や Poetry 等を用意してください。

前提
- Python 3.10 以上（型注釈に union 型（|）などを使用）
- Git（プロジェクトルート検出に使用）

1. リポジトリをクローン / 作業ディレクトリへ移動

2. 仮想環境を作成して有効化（例）
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

3. 必要パッケージをインストール
   - 最低依存（例）:
     - duckdb
     - defusedxml
   - pip 例:
     - pip install duckdb defusedxml

   実際のプロジェクトでは他にも要求パッケージ（Slack クライアント等）がある可能性があります。requirements.txt/pyproject.toml を用意している場合はそれに従ってください。

4. パッケージを編集可能モードでインストール（プロジェクトに setup/pyproject がある場合）
   - pip install -e .

5. 環境変数の準備
   - プロジェクトルートに `.env`（または `.env.local`）を作成してください。
   - 主に必要な環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH           : SQLite（監視等）パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL             : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - テストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを無効化できます。

---

## 使い方（主な API / 例）

以下はライブラリ内 API の簡単な使用例です。実行前に環境変数と依存ライブラリの準備を行ってください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は Path オブジェクト
```

2) 日次 ETL 実行（デフォルト: 今日を対象）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

3) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection

# known_codes: 銘柄コードの集合（抽出に使用）。無ければ紐付けはスキップ可能
known_codes = {"7203", "6758", "9984"}
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

4) カレンダー管理 / 営業日判定
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2025, 1, 1)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

5) 監査ログ初期化
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)  # 既存の DuckDB 接続に監査テーブルを追加
```

6) J-Quants のトークン取得（必要に応じて）
```python
from kabusys.data.jquants_client import get_id_token

token = get_id_token()  # settings.jquants_refresh_token を使用して idToken を取得
```

7) 品質チェックを個別に実行
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn)
for i in issues:
    print(i)
```

注意:
- jquants_client の API 呼び出しはレート制限やリトライ、401 の自動リフレッシュなどを内部で処理します。
- news_collector は SSRF 対策、XML の安全パース、レスポンスサイズ制限、gzip 解凍上限などのセキュリティ対策が適用されています。

---

## 設定・環境変数

主要な環境変数と意味：

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite ファイルパス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると config の .env 自動ロードを抑制

config モジュールはプロジェクトルート（.git または pyproject.toml を基準）から `.env`/.env.local を自動読み込みします。`.env.local` は `.env` を上書きします。

---

## ディレクトリ構成

リポジトリ内の主要ファイルとディレクトリ（抜粋）：

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - schema.py
      - calendar_management.py
      - quality.py
      - audit.py
    - strategy/
      - __init__.py
      (戦略関連モジュールを配置)
    - execution/
      - __init__.py
      (発注・ブローカー連携等を配置)
    - monitoring/
      - __init__.py
      (監視用モジュールを配置)

- その他:
  - .env.example (想定)
  - pyproject.toml / setup.py（存在する場合、インストール設定）

上記はコードベースから抽出した構成です。戦略・実行・監視に関する詳細実装は各サブパッケージに追加実装されることを想定しています。

---

## 実運用上の注意

- 環境（KABUSYS_ENV）に応じた挙動差（paper/live）をコード側で実装してください。settings.is_live / is_paper / is_dev を利用できます。
- 実際の発注・決済処理は慎重にテストし、冪等性・監査ログの適切な記録を保証してください。
- 外部 API キーや認証情報は秘匿して管理し、`.env` をソース管理しないようにしてください。
- DuckDB は単一ファイル DB で軽量ですが、マルチプロセスや並列アクセスの運用要件については検討してください。
- ニュース収集や外部データ取得は第三者サイトへの負荷や利用規約に配慮してください。

---

この README はコードベースの現状から自動的にまとめたドキュメントです。実際の利用・配布時には以下を整備することを推奨します。

- requirements.txt / pyproject.toml による依存管理
- .env.example の明記（必須環境変数とサンプル）
- 運用手順書（デプロイ、スケジューリング、監視）
- より具体的な API リファレンス（関数引数と戻り値の詳細）

必要であれば、README をプロジェクトの方針や導入手順に合わせて追記・調整します。どの部分を詳しく書きたいか指示してください。