# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
J-Quants や RSS を用いたデータ収集、DuckDB ベースのスキーマ、特徴量・リサーチユーティリティ、ETL パイプライン、監査ログ用スキーマなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能を備えた日本株自動売買・データ基盤のための Python パッケージです。

- J-Quants API からの株価・財務・市場カレンダーの取得（レート制限・リトライ・トークン自動更新対応）
- RSS ニュース収集と記事の前処理、銘柄紐付け
- DuckDB によるデータスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- 研究／特徴量計算（モメンタム・ボラティリティ・バリュー）および IC/統計解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order → execution のトレーサビリティ）

設計方針として「本番 API に不用意にアクセスしない」「冪等性」「Look-ahead bias の防止」「最小限の外部依存」を重視しています。

---

## 主な機能一覧

- data/jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_* 系で DuckDB へ冪等保存（ON CONFLICT）
  - レートリミット管理・401 トークン自動更新・再試行ロジック
- data/news_collector
  - RSS 取得、前処理、記事ID生成（URL 正規化 + SHA-256）、DB 保存、銘柄コード抽出
  - SSRF 対策・XML 安全パーサ使用・レスポンスサイズ制限
- data/schema / data/audit
  - DuckDB の全スキーマ定義（raw_prices, prices_daily, features, signal_queue, orders, executions, audit テーブル 等）
  - init_schema / init_audit_schema で初期化
- data/pipeline
  - 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 品質チェック統合（data.quality.run_all_checks）
- data/quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
- research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
- data/stats
  - zscore_normalize（クロスセクション Z スコア正規化）

---

## セットアップ手順

前提:
- Python 3.10 以上（typing に `|` を使用しているため）
- システムに pip が利用可能

1. リポジトリをクローン / 配布パッケージを取得
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate もしくは .venv\Scripts\activate
3. 必要パッケージをインストール（例）
   - pip install duckdb defusedxml
   - （パッケージ配布用の setup/pyproject がある場合は pip install -e .）

推奨（開発用）:
- pip install -e .[dev]（もし extras が定義されていれば）

環境変数:
- .env ファイルをプロジェクトルートに置くと自動で読み込まれます（.git または pyproject.toml を基準にプロジェクトルートを検出）。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト等で使用）。

必須環境変数（config.Settings 参照）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

オプション（デフォルトあり）:
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- KABUS_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト data/monitoring.db）

例: .env（最小）
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（簡単な例）

以下は Python REPL あるいはスクリプトからの利用例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成され、テーブルが作られます
```

2) 監査ログスキーマの初期化（オプション）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

3) 日次 ETL を実行
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を渡すことも可能
print(result.to_dict())
```

4) ニュース収集ジョブ（既知銘柄セットがある場合の例）
```python
from kabusys.data.news_collector import run_news_collection
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: 新規保存数}
```

5) 研究／特徴量計算
```python
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic
from datetime import date

target = date(2024, 1, 4)
mom = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1, 5, 21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print(ic)
```

6) J-Quants データ取得（低レベル）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
financials = fetch_financial_statements()
```

テスト時のヒント:
- テスト用にメモリ上の DuckDB を使う: init_schema(":memory:")
- 自動 .env 読み込みを無効にする: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

ログレベルは環境変数 LOG_LEVEL で制御できます。

---

## ディレクトリ構成

主要ファイルのみ抜粋（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py      — RSS ニュース収集・保存
    - schema.py              — DuckDB スキーマ定義・init_schema
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - features.py            — 特徴量ユーティリティの公開インターフェース
    - calendar_management.py — マーケットカレンダー管理 / バッチ更新ジョブ
    - audit.py               — 監査ログスキーマ（signal / order / executions）
    - etl.py                 — ETLResult の再エクスポート
  - research/
    - __init__.py            — 研究用ユーティリティの公開
    - feature_exploration.py — 将来リターン計算 / IC / サマリー
    - factor_research.py     — momentum / volatility / value の計算
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

---

## 開発・運用上の注意

- 環境変数の取り扱いに注意してください。必須トークンが未設定だと起動時にエラーになります（Settings._require が検出）。
- J-Quants API のレート制限（120 req/min）を遵守する実装になっていますが、使い方によってはローカル側でスロットリングが必要な場合があります。
- DuckDB に対する DDL は幾つかの RDBMS 機能（ON DELETE CASCADE 等）を意図的に避ける実装になっています。削除プロセスはアプリ側で整合性を保つ必要があります。
- ニュース収集は外部 URL にアクセスするため、ネットワークやセキュリティ制約（プロキシ / ファイアウォール）を考慮してください。
- production（live）での実行には十分なテストとリスク管理を実施してください（KABUSYS_ENV を "live" に設定すると is_live が True になります）。

---

必要であれば README に以下を追加します:
- .env.example のサンプルファイル
- より詳細な API リファレンス（各関数の引数説明）
- CI / テスト実行方法（pytest 等）
- デプロイ手順（systemd/service, コンテナ化など）

追記希望があれば具体的に教えてください。