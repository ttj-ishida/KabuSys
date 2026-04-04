# KabuSys

日本株向けの自動売買 / データプラットフォームのコアライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・AI によるニュースセンチメント、ファクター計算、監査ログ（トレーサビリティ）、カレンダー管理など、トレーディング戦略構築に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的で設計されています。

- J-Quants API を用いたデータ取得（株価日足、財務、マーケットカレンダー）
- DuckDB を用いたデータ保存・ETL パイプライン
- RSS ベースのニュース収集と OpenAI を使ったニュースセンチメント評価
- マーケットレジーム判定（ETF 1321 の MA200 とマクロニュースの組合せ）
- ファクター計算・リサーチユーティリティ（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions）の管理と初期化

設計方針の重要な点：
- ルックアヘッドバイアス防止（内部で datetime.today() を無闘で参照しない設計）
- 冪等性（DB への保存は ON CONFLICT を使う）
- フェイルセーフ（外部 API 失敗時は安全にフォールバック）

---

## 機能一覧

- 環境設定管理（自動 `.env` 読み込み、必須変数チェック）
- J-Quants クライアント
  - fetch_daily_quotes / save_daily_quotes
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar
  - get_id_token（自動トークンリフレッシュ、レート制御、リトライ）
- ETL パイプライン
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult（処理結果の構造化）
- データ品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- ニュース収集
  - fetch_rss（SSRF 対策、トラッキング除去、XML 安全パース）
  - raw_news / news_symbols との連携を前提とした収集ロジック
- ニュース NLP（OpenAI）
  - score_news（銘柄ごとの ai_score を ai_scores テーブルに書込）
  - calc_news_window（ニュース集計ウィンドウ）
- レジーム判定（市場センチメント）
  - score_regime（ETF 1321 の MA200 乖離とマクロセンチメントの合成）
- 研究用ユーティリティ
  - calc_momentum / calc_value / calc_volatility
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（data.stats）
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- 監査ログ管理
  - init_audit_schema / init_audit_db（監査用テーブル群の初期化）

---

## セットアップ

必要な Python パッケージ（代表例）

- python >= 3.9
- duckdb
- openai
- defusedxml

（プロジェクトに requirements.txt が無い場合は上記を pip でインストールしてください）

例：
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 必要に応じて他の依存を追加
```

.env（環境変数）設定：
- プロジェクトルートに `.env` を作成すると自動で読み込まれます（読み込み順: OS 環境 > .env.local > .env）。
- 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（主なもの）：
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      : kabu ステーション API のパスワード（必須）

任意 / デフォルト値を持つ：
- KABU_API_BASE_URL      : kabu API base URL（デフォルト "http://localhost:18080/kabusapi"）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID : LINE 通知に使用する場合
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト "data/kabusys.duckdb"）
- SQLITE_PATH            : 監視 DB（デフォルト "data/monitoring.db"）
- KABUSYS_ENV            : "development" / "paper_trading" / "live"（デフォルト "development"）
- LOG_LEVEL              : "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"（デフォルト "INFO"）

注意: settings で env 値は検証され、不正な値は例外になります。

---

## 基本的な使い方

以下は代表的な利用例です。各関数は DuckDB 接続（duckdb.connect(...) の接続オブジェクト）を受け取って動作します。

設定参照例：
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

DuckDB 接続例：
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

ETL（日次パイプライン）実行例：
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュースのセンチメント評価（OpenAI 必須）：
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数で設定するか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("scored:", n_written)
```

市場レジーム判定（OpenAI 必須）：
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

監査ログ DB 初期化：
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの duckdb 接続
```

データ品質チェックの実行例：
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)  # target_date を指定可能
for i in issues:
    print(i)
```

ニュース収集（RSS を個別に取得）：
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

研究系ファクター計算の例：
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は dict のリスト: {"date","code","mom_1m","mom_3m","mom_6m","ma200_dev"}
```

OpenAI との連携について：
- score_news / score_regime は OpenAI API キーを必要とします。
- api_key 引数にキー文字列を渡すか、環境変数 OPENAI_API_KEY を設定してください。
- API 呼び出しはリトライを実装していますが、レート制限等に注意してください。

---

## ディレクトリ構成（主要ファイル）

以下はソースツリー（src/kabusys 以下）の要約です。各モジュールはさらに多くの補助関数と実装を持ちます。

- src/kabusys/
  - __init__.py
  - config.py                        # 環境変数・設定管理（.env 自動読み込み等）
  - ai/
    - __init__.py
    - news_nlp.py                    # ニュースの OpenAI スコアリング（score_news）
    - regime_detector.py             # マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              # J-Quants API クライアント（取得・保存・認証・レート制御）
    - pipeline.py                    # ETL パイプライン（run_daily_etl 等）
    - etl.py                         # ETL インターフェース（ETLResult 再エクスポート）
    - news_collector.py              # RSS ニュース収集（SSRF 対策等）
    - calendar_management.py         # マーケットカレンダー管理・判定・更新ジョブ
    - quality.py                     # データ品質チェック（欠損・スパイク等）
    - stats.py                       # 汎用統計ユーティリティ（zscore_normalize）
    - pipeline.py (上記)
    - audit.py                       # 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py             # モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py         # 将来リターン・IC・統計要約
  - monitoring/ (該当 API / 実装が将来的に配置される想定)
  - strategy/ (戦略層モジュールは別途実装)

---

## 実装上の注意点 / ヒント

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に動作します。CI やテストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB の executemany はバージョンによって空リストの扱いが異なるため、コード中で空リストの呼び出しを避ける保護ロジックがあります。
- OpenAI API 呼び出しは JSON Mode（response_format={"type":"json_object"}）で実行しますが、LLM の出力は常に検証・パースしています（フェイルセーフ: パース失敗時はスコア 0.0 等にフォールバック）。
- J-Quants API 呼び出しは内部にレートリミッタとリトライを実装しています。トークン（idToken）はモジュールキャッシュされ、401 の場合に自動的にリフレッシュされます。
- 本ライブラリの多くの関数は外部副作用（発注 API 呼び出し等）を行わない設計のため、研究・バックテスト用途で安全に利用できます。ただし、ETL や DB 書き込みは実際にデータを変更するため、実行前にバックアップやテスト DB を用いることを推奨します。

---

## サポート / 開発

- 単体テストやモックが必要な箇所（OpenAI 呼び出し、HTTP 通信など）はモジュール内で差し替え易く設計されています（例: _call_openai_api を patch）。
- 新機能追加時は既存の設計方針（ルックアヘッド抑止、冪等性、フェイルセーフ）に従って実装してください。

---

以上がこのコードベースの README.md 相当の概要と利用方法です。必要であれば、README に含めるサンプル .env.example や具体的な CLI 実行方法（スケジューラ設定、systemd サービス例、cron ジョブ例）も作成できます。どの情報を追加しましょうか？