# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
DuckDB を利用したデータ基盤、J-Quants API によるデータ取得、ニュースの NLP スコアリング、ファクター計算、ETL パイプライン、監査ログ（トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、日本株を対象とした研究・運用プラットフォームのコアライブラリです。主な目的は次の通りです。

- J-Quants API からの株価・財務・カレンダー取得（差分ETL）
- DuckDB をバックエンドにしたデータ保存と品質チェック
- ニュース収集・NLP（OpenAI）を用いたセンチメント算出
- マーケットレジーム判定（MA200 + マクロニュース）
- ファクター（モメンタム・バリュー・ボラティリティ等）計算と特徴量解析
- 監査ログテーブル（シグナル→発注→約定のトレーサビリティ）
- ユーティリティ（マーケットカレンダー、統計ユーティリティ等）

設計方針として、ルックアヘッドバイアスの防止、冪等性（ON CONFLICT / idempotent 保存）、外部API呼び出しのリトライ・バックオフ、テストしやすさ（モック可能な内部呼び出し）を重視しています。

---

## 機能一覧

主な公開機能（抜粋）

- 環境設定
  - kabusys.config.settings：環境変数/`.env` から設定取得、自動ロード機能
- データ取得・保存（J-Quants）
  - kabusys.data.jquants_client.get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）
- ETL パイプライン
  - kabusys.data.pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult（実行結果のデータクラス）
- データ品質チェック
  - kabusys.data.quality.run_all_checks / check_missing_data / check_spike / check_duplicates / check_date_consistency
- ニュース収集・NLP
  - kabusys.data.news_collector.fetch_rss（RSS 収集、安全対策実装）
  - kabusys.ai.news_nlp.score_news（OpenAI で銘柄ごとのニュースセンチメントを ai_scores に書込）
  - kabusys.ai.regime_detector.score_regime（MA200 とマクロニュースで市場レジーム判定）
- 研究用ユーティリティ
  - kabusys.research.calc_momentum / calc_value / calc_volatility
  - kabusys.research.feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - kabusys.data.stats.zscore_normalize
- マーケットカレンダー
  - kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- 監査ログ（トレーサビリティ）
  - kabusys.data.audit.init_audit_db / init_audit_schema（signal_events, order_requests, executions 等のテーブルを作成）

注意: 一部のサブパッケージ（strategy, execution, monitoring）はパッケージエクスポート対象に含まれていますが、このリポジトリ内の該当実装は別途存在する可能性があります。

---

## セットアップ手順

依存ライブラリ（代表例）
- Python 3.9+
- duckdb
- openai
- defusedxml
- （標準ライブラリで多く実装しています）

インストール例（仮の requirements）
pip install duckdb openai defusedxml

パッケージを開発インストールする例:
pip install -e .

環境変数 / .env
- プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（ただしテストなどで無効化可能）。
- 自動ロードを無効にする: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

主要な環境変数（設定モジュール `kabusys.config.settings` に記載）:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知に使うボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視データなど）パス（例: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視関連設定
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/...
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）

例（.env）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

DB 初期化（監査ログ）
- 監査ログ専用 DB を初期化する:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  もしくは既存の DuckDB 接続へ:
  from kabusys.data.audit import init_audit_schema
  conn = duckdb.connect(settings.duckdb_path)
  init_audit_schema(conn, transactional=True)

注意点
- OpenAI など外部 API を利用する関数は API キーを引数で上書き可能。テストでは内部の _call_openai_api をモックする想定。
- news_collector は SSRF/圧縮サイズ/XML インジェクション対策が組み込まれています。

---

## 使い方（簡単な例）

Python レベルでの基本的な利用例をいくつか示します。

1) DuckDB 接続を開く
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースのスコアリング（OpenAI API キーは env か引数で）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key=None (環境変数 OPENAI_API_KEY を利用)
count = score_news(conn, target_date=date(2026,3,20))
print("scored:", count)
```

4) マーケットレジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

5) ファクター計算・研究ユーティリティ
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

moms = calc_momentum(conn, target_date=date(2026,3,20))
vols = calc_volatility(conn, target_date=date(2026,3,20))
values = calc_value(conn, target_date=date(2026,3,20))

fwd = calc_forward_returns(conn, target_date=date(2026,3,20), horizons=[1,5,21])
ic = calc_ic(moms, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

6) RSS フィード取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

7) marketplace calendar ヘルパー
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2026, 3, 20)
print("is trading:", is_trading_day(conn, d))
print("next trading:", next_trading_day(conn, d))
```

---

## テスト / モックに関するヒント

- OpenAI 呼び出しは内部関数 `_call_openai_api` を通して行われます。ユニットテストでは `unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")` や同様に regime_detector のものをパッチして固定レスポンスを返すことで外部 API を呼ばずにテストできます。
- news_collector のネットワーク部分は `_urlopen` をモック可能です（`kabusys.data.news_collector._urlopen` を差し替え）。
- 自動 .env ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください（テスト環境で便利です）。

---

## ディレクトリ構成

（主要ファイル・モジュールの一覧）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - pipeline.py
    - etl.py
    - jquants_client.py
    - news_collector.py
    - stats.py
    - quality.py
    - audit.py
    - (その他データ関係モジュール)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research や ai 以下に研究・解析用のユーティリティがまとまっています。
- その他:
  - README.md（本ファイル）
  - pyproject.toml / setup.cfg / requirements.txt（存在する場合）

各モジュールの責務はファイル冒頭の docstring に詳述されています。特に ETL / data / news / audit に関する処理は DB スキーマ・冪等性・ロギング・例外処理に留意して実装されています。

---

## 注意事項 / 補足

- 本ライブラリは実運用（特に live 環境での発注・約定処理）に使用する前に、環境変数・認証情報・DuckDB スキーマ・監査ログの初期化・十分なテストを必ず行ってください。
- OpenAI / J-Quants / 証券 API など外部サービスのレート制限や料金に留意してください。
- 時刻・タイムゾーンの扱いに敏感なアルゴリズム（ニュースウィンドウ、fetched_at、ETLの対象日など）はルックアヘッドバイアス回避を意識して設計されています。バックテストでこれらの関数を呼ぶ際は対象日指定を明示することを推奨します。

---

必要ならば README にサンプル .env.example や初期 SQL スキーマ（raw_prices 等の CREATE TABLE 文）、または CI / ローカルデバッグ手順を追加できます。追加希望があれば教えてください。