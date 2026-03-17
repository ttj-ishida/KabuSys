# KabuSys

日本株自動売買プラットフォームのコアライブラリ（読み取り専用ドキュメント）

このリポジトリは、J-Quants 等の外部データソースから市場データやニュースを収集して DuckDB に格納し、品質チェック、戦略/シグナル生成、監査ログ、発注管理までを想定した基盤モジュール群を提供します。

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコアコンポーネント群です。主に以下を目的としています。

- J-Quants API から株価・財務・マーケットカレンダーを安全に取得して保存する（差分更新・冪等保存）
- RSS フィードからニュースを収集して正規化・DB保存・銘柄紐付けを行う
- DuckDB に対するスキーマ定義・初期化を行う
- ETL パイプラインで差分取得・保存・データ品質チェックを実行する
- カレンダー管理、監査ログ（トレーサビリティ）用スキーマを提供する
- 将来的に戦略（strategy）、発注（execution）、監視（monitoring）モジュールと統合する設計

設計上のポイント（抜粋）:
- API レート制限とリトライを考慮（J-Quants は 120 req/min）
- トークン自動リフレッシュ（401 時に一回リトライ）
- Look-ahead bias 回避のため取得時刻（fetched_at）を UTC で記録
- DB への保存は冪等（ON CONFLICT 句）で実装
- RSS 収集は SSRF / XML Bomb 等の脅威を考慮した安全設計

## 主な機能一覧

- data/jquants_client.py
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（リフレッシュトークンから id_token を取得）
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）
  - 内部でレートリミッタ、再試行（指数バックオフ）、401 リフレッシュ処理を実装
- data/news_collector.py
  - RSS フィード取得（gzip 対応）、XML パース（defusedxml を使用）
  - URL 正規化・トラッキングパラメータ除去、記事ID は SHA-256（先頭32文字）
  - raw_news へのバルク保存（INSERT ... RETURNING を使用）と news_symbols（銘柄紐付け）
  - SSRF 対策（リダイレクト先・最終 URL のホスト判定）、受信サイズ上限
- data/schema.py
  - DuckDB のテーブル群（Raw / Processed / Feature / Execution レイヤ）を定義
  - init_schema(db_path)：DB 初期化と接続返却
- data/pipeline.py
  - run_daily_etl：日次 ETL の統括（カレンダー → 株価 → 財務 → 品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl（差分更新ロジック）
  - 差分取得、backfill、品質チェック（quality モジュール）をサポート
- data/calendar_management.py
  - market_calendar を管理する夜間バッチ（calendar_update_job）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供
- data/quality.py
  - 欠損・スパイク・重複・日付不整合の検出
  - run_all_checks による一括実行と QualityIssue レポート
- data/audit.py
  - 監査ログ（signal_events / order_requests / executions）スキーマの初期化
  - init_audit_schema / init_audit_db を提供
- config.py
  - 環境変数読み込みと Settings オブジェクト
  - .env, .env.local の自動読み込み（プロジェクトルート検出）、自動無効化フラグあり

（strategy/ execution/ monitoring はパッケージプレースホルダあり）

## セットアップ手順

前提:
- Python 3.10 以上（Union 型注記（A | B）を使用しているため）
- ネットワーク環境で外部 API / RSS にアクセスできること

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境の作成（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - その他、ロギングやテスト用に必要なパッケージがあれば追加でインストールしてください
   - （将来 requirements.txt を追加する想定）
4. 環境変数の設定
   - プロジェクトルートに .env を置くことで自動で読み込まれます（優先順位: OS env > .env.local > .env）。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN  : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      : kabuステーション API のパスワード
- SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       : Slack チャンネル ID

オプション／デフォルト可:
- KABUSYS_ENV            : development | paper_trading | live  (デフォルト: development)
- LOG_LEVEL              : DEBUG | INFO | WARNING | ERROR | CRITICAL (デフォルト: INFO)
- KABU_API_BASE_URL      : kabuAPI のベース URL（デフォルト localhost:18080）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            : SQLite（監視用DB）パス（デフォルト data/monitoring.db）

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## 使い方（主な例）

以下はライブラリをプログラムから利用する簡単な例です。実際はアプリケーション側でジョブをスケジューリング（cron / Airflow 等）して運用します。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # ファイルがなければ親ディレクトリを作る
```

2) 監査スキーマ初期化（監査を使用する場合）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

3) 日次 ETL を実行（J-Quants から差分取得して保存、品質チェックまで）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

4) 個別 ETL ジョブ（株価、財務、カレンダー）
```python
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl

fetched, saved = run_prices_etl(conn, target_date=date.today())
```

5) RSS ニュース収集
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄番号のセット（抽出時にマッチさせる）
known_codes = {"7203", "6758", "9432"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存数}
```

6) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

7) J-Quants クライアントを直接利用
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

token = get_id_token()  # settings.jquants_refresh_token を利用
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

注意:
- ネットワーク例外や API エラーは呼び出し元で適切にハンドリングしてください。多くの関数は内部でログ出力して例外を送出します。
- テスト時は環境変数の自動ロードを無効化して、任意の settings を注入することができます。

## ディレクトリ構成

リポジトリ内の主要ファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    -- 環境変数 / 設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py          -- J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py          -- RSS ニュース収集・保存・銘柄抽出
    - schema.py                  -- DuckDB スキーマ定義・初期化
    - pipeline.py                -- ETL パイプライン（差分取得・保存・品質チェック）
    - calendar_management.py     -- マーケットカレンダー管理・営業日判定
    - audit.py                   -- 監査ログ用スキーマ（発注トレーサビリティ）
    - quality.py                 -- データ品質チェック（欠損・スパイク等）
  - strategy/
    - __init__.py                -- 戦略モジュールプレースホルダ
  - execution/
    - __init__.py                -- 発注実行モジュールプレースホルダ
  - monitoring/
    - __init__.py                -- 監視モジュールプレースホルダ

各モジュールは責務が明確に分離されており、将来的に strategy / execution / monitoring を実装して統合できます。

## 動作設計上の注意点（運用メモ）

- API レート制限（J-Quants）を守るためモジュールレベルでスロットリングを行います。大量取得の際はレートと API 利用契約に注意してください。
- save_* 関数は冪等に設計されています（ON CONFLICT DO UPDATE / DO NOTHING）。
- RSS フィードの収集は外部ネットワークに依存するため、SSRF / XML 攻撃対策・受信サイズ制限などの保護を組み込んでいます。
- データ品質チェックは Fail-Fast ではなく、全チェックを実行して問題を列挙します。運用側で重大度に応じた対応を決定してください。
- すべてのタイムスタンプは UTC を基本に扱うよう設計されています（特に監査ログ）。

## 貢献 / 拡張

- strategy / execution / monitoring はプレースホルダです。戦略ロジック、kabuステーションとの発注実装、監視アラートを追加して統合運用を目指してください。
- DB スキーマ変更は互換性（既存データ）を考慮して行ってください。DuckDB はスキーマ変更をサポートしますが、マイグレーション手順を明確にしてください。
- テスト: ネットワーク IO 部分（_urlopen など）をモックしてユニットテストを作成することを推奨します。

---

不明点や README に追加したい内容があれば教えてください。使用例の具体的な CLI スクリプトや systemd / cron / Airflow 用のジョブ定義例なども必要であれば作成します。