# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
J-Quants API などからデータを取得・永続化し、品質チェック・ニュース収集・監査ログ・ETL パイプラインを備えています。

主な設計方針は「冪等性」「トレーサビリティ」「Look‑ahead bias 回避」「堅牢なネットワーク/セキュリティ対策（SSRF 対策等）」です。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数（設定）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下の要素を持つ Python パッケージです。

- J-Quants API クライアント（株価日足 / 財務 / 市場カレンダー）
  - レートリミット制御／リトライ／トークン自動リフレッシュ対応
  - 取得時刻（fetched_at）を UTC で記録して Look‑ahead bias を防止
- DuckDB を用いたスキーマ定義・初期化モジュール
  - Raw / Processed / Feature / Execution 層でのテーブルを定義
  - 監査ログ（audit）スキーマの初期化機能
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集モジュール（RSS → raw_news）
  - URL 正規化／トラッキングパラメータ除去／SSRF 対策／gzip の安全処理
- マーケットカレンダー管理（営業日判定、次/前営業日、夜間更新ジョブ）
- データ品質チェック（欠損・重複・スパイク・日付不整合）

---

## 主な機能一覧

- データ取得
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（J-Quants）
- データ保存（冪等）
  - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB へ ON CONFLICT で保存）
- DuckDB スキーマ初期化
  - init_schema(db_path)
  - init_audit_schema(conn) / init_audit_db(db_path)
- ETL
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl（まとめて実行し品質チェックまで行う）
- ニュース収集
  - fetch_rss, save_raw_news, save_news_symbols, run_news_collection
- カレンダー管理
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- 品質チェック
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- 設定管理
  - settings オブジェクトを通して環境変数を取得（.env / .env.local の自動読み込み対応）

---

## セットアップ手順

想定 Python バージョン: 3.10+

1. リポジトリをクローン（またはパッケージを既に入手）
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要な依存パッケージをインストール
   - pip install duckdb defusedxml
   - （状況に応じて他のパッケージを追加してください。setup.py/pyproject.toml がある場合は pip install -e .）
4. 環境変数を設定
   - プロジェクトルートの `.env` または `.env.local` に設定を置くと自動読み込みされます（詳しくは「環境変数」節）
5. DuckDB スキーマを初期化
   - 下記「使い方」に例あり

注:
- 自動で .env を読み込むのはデフォルトです。テストなどで無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 簡単な使い方（コード例）

以下は最小限の利用例です。Python REPL やスクリプトで実行してください。

1) スキーマ初期化（DuckDB ファイルを作成）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH に基づく（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

2) 監査テーブルの初期化（監査用に追加）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

3) 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())  # ETLResult の内容を辞書化して表示
```

4) ニュース収集ジョブを実行（RSS → raw_news）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes を渡すと記事と銘柄の紐付けも行う
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)  # {source_name: 新規保存レコード数}
```

5) カレンダー夜間バッチ（差分同期）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved", saved)
```

6) J-Quants から直接データ取得（低レベル）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

token = get_id_token()  # settings からリフレッシュトークンを使用して id_token を取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 環境変数（設定）

kabusys.config.Settings 経由で参照される主な環境変数:

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- kabuステーション API
  - KABU_API_PASSWORD (必須) — kabu API のパスワード
  - KABU_API_BASE_URL (任意, default: http://localhost:18080/kabusapi)
- Slack
  - SLACK_BOT_TOKEN (必須) — Slack ボットトークン
  - SLACK_CHANNEL_ID (必須) — 通知用チャンネルID
- データベースパス
  - DUCKDB_PATH (任意, default: data/kabusys.duckdb)
  - SQLITE_PATH (任意, default: data/monitoring.db)
- 実行環境 / ログ
  - KABUSYS_ENV (任意, default: development) — 有効値: development, paper_trading, live
  - LOG_LEVEL (任意, default: INFO) — 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml の存在する親ディレクトリ）を探索し、`.env` を読み込みます。`.env.local` は `.env` の後に優先して読み込まれ、OS 環境変数は保護されます。
- 自動読み込みを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 注意点 / 実装上の特徴

- J-Quants クライアントはレート制限（120 req/min）を守る実装を持ち、リトライ・指数バックオフ・401時の自動リフレッシュを備えています。
- News Collector は URL 正規化（utm パラメータ除去）、SSRF 対策（リダイレクト先検査・プライベート IP 拒否）、受信サイズ制限（上限 10MB）などセキュリティ・堅牢性に配慮しています。
- DuckDB への保存は可能な限り冪等性（ON CONFLICT ... DO UPDATE / DO NOTHING）を確保しており、ETL の再実行に耐えます。
- 品質チェックは Fail‑Fast ではなく「全件収集」方式で、発見した問題を一覧として返し、呼び出し元が対応を決められる設計です。
- すべての監査タイムスタンプは UTC ベースで保存される想定です（audit.init_audit_schema は SET TimeZone='UTC' を実行します）。

---

## ディレクトリ構成

パッケージルート（src レイアウト） の主なファイル／モジュール:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存）
    - news_collector.py            — RSS ニュース収集・保存
    - pipeline.py                  — ETL パイプライン（差分更新・品質チェック）
    - schema.py                    — DuckDB スキーマ定義・初期化
    - calendar_management.py       — カレンダー管理（営業日判定・更新ジョブ）
    - audit.py                     — 監査ログスキーマ初期化
    - quality.py                   — データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（README に含まれるファイルはコードベースの抜粋に基づきます。実際のリポジトリでは追加のモジュール・ユーティリティ・ドキュメントが存在する可能性があります。）

---

## 追加のヒント

- 本パッケージをサービスやバッチで運用する場合は、KABUSYS_ENV を適切に設定（paper_trading / live）し、ログやエラーハンドリングを監視してください。
- DuckDB ファイルはローカル/共有ストレージに置けますが、運用環境ではバックアップやロック管理（同時アクセス）に注意してください。
- ニュースの銘柄抽出は正規表現で 4 桁数字を抽出する単純な方式です。独自の NLP／辞書を使って精度を高めることが可能です。
- テスト時は自動 .env ロードを無効化すると環境による副作用を回避できます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

この README はコードベースの現状（主要モジュールの実装）に基づいて作成しています。より詳細な API ドキュメント、運用手順、CI / デプロイ手順、依存関係の pin（requirements.txt / pyproject.toml）は別途整備してください。