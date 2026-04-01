# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、ファクターリサーチ、監査ログ（トレーサビリティ）、市場カレンダー管理などをモジュール化して提供します。

主な設計方針
- ルックアヘッドバイアスの排除（内部で date.today() / datetime.today() を直接参照しない）
- DuckDB を用いたローカルデータ保存（冪等保存、ON CONFLICT 等に対応）
- 外部 API 呼び出しにはリトライ・レート制御を備えフェイルセーフに設計
- テスト容易性のため設定注入・関数差し替えを想定（mock 可能）

---

## 機能一覧

- 設定管理
  - .env / .env.local / 環境変数からの設定読み込み（自動ロード、無効化可）
  - settings オブジェクト経由で各種設定にアクセス
- データ取得・ETL（kabusys.data.pipeline）
  - J-Quants API からの株価（daily_quotes）、財務データ、上場銘柄情報、マーケットカレンダー取得
  - 差分取得・バックフィル・品質チェック（quality モジュール）
  - 日次 ETL 実行エントリ run_daily_etl()
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理、raw_news への冪等保存
  - SSRF 対策、レスポンスサイズ上限、トラッキングパラメータ除去など
- NLP / AI（kabusys.ai）
  - news_nlp.score_news(): ニュースを LLM（gpt-4o-mini）で銘柄別センチメント評価 → ai_scores テーブルへ書込
  - regime_detector.score_regime(): ETF（1321）MA200 とマクロニュースの LLM 評価を合成して market_regime に書込
  - 再試行やエラー時のフォールバック実装あり（API失敗時はスコア0にフォールバック等）
- リサーチ（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター算出（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - zscore_normalize（data.stats に実装）
- 市場カレンダー管理（kabusys.data.calendar_management）
  - market_calendar を参照した営業日判定、next/prev_trading_day、calendar_update_job（J-Quants から差分取得）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル DDL と初期化補助（init_audit_schema / init_audit_db）
  - created_at / updated_at は UTC で保存する設計

---

## セットアップ手順（ローカル利用想定）

1. Python 環境を準備（推奨: 3.10+）
2. 必要パッケージをインストール（プロジェクトに requirements.txt があればそれを使用）
   - 本リポジトリに明示の requirements ファイルは含まれていませんが、少なくとも以下は必要になります:
     - duckdb
     - openai
     - defusedxml
   - 例:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     pip install duckdb openai defusedxml
     # + その他プロジェクト固有の依存があればインストール
     ```
3. リポジトリをインストール（開発モードなど）
   ```bash
   pip install -e .
   ```
4. 環境変数 / .env を用意
   - プロジェクトルート（pyproject.toml または .git を基点）に `.env` / `.env.local` を配置すると自動で読み込まれます（優先順: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テストなどで有用）。
   - 必須の環境変数（主なもの）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabu ステーション API 用パスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: 通知先チャンネル ID
     - OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用。関数呼び出し時に引数で注入可能）
   - 任意/デフォルト設定
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - LOG_LEVEL: DEBUG|INFO|...（デフォルト INFO）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

---

## 使い方（主要なユースケース）

以下は基本的な Python API の利用例です。すべて DuckDB 接続を受け取る方式なので、duckdb.connect() して渡します。

- 設定にアクセスする
```python
from kabusys.config import settings

print(settings.duckdb_path)
print(settings.is_live)
```

- ETL（日次 ETL）の実行
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# 明示的に target_date を指定することを推奨（ルックアヘッド防止）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコアリング（AI）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY を環境変数に設定しておけば api_key は省略可
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {written} codes")
```

- 市場レジーム判定（AI + ETF MA）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db

# ファイル DB を作成して監査スキーマを初期化
conn = init_audit_db("data/audit.duckdb")
```

- news_collector を用いた RSS 取得（簡易）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"])
```

注意点
- AI を呼ぶ関数は api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ETL / データ保存関数は冪等設計ですが、実行前に DuckDB のスキーマ（テーブル定義）を用意しておく必要がある箇所があるため、プロジェクトのスキーマ初期化手順を確認してください（このコードベースには各モジュールで使用するテーブル名と INSERT の仕様が記載されています）。
- DuckDB の executemany に空リストを渡すとバージョン依存で問題になるため、呼び出し側は注意が払われています（モジュール側でガード済み）。

---

## 主要モジュールと API（概要）

- kabusys.config
  - settings: Settings オブジェクト（環境変数経由で各種設定にアクセス）
- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - save_daily_quotes(conn, records)
  - fetch_financial_statements(...)
  - save_financial_statements(conn, records)
  - fetch_market_calendar(...)
  - save_market_calendar(conn, records)
  - fetch_listed_info(...)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult クラス
- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - preprocess_text(...)
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル／ディレクトリ構成（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース NLP スコアリング
    - regime_detector.py             — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント + 保存
    - pipeline.py                    — ETL パイプライン / run_daily_etl 等
    - etl.py                         — ETLResult の再エクスポート
    - news_collector.py              — RSS ニュース取得・前処理
    - quality.py                     — データ品質チェック
    - calendar_management.py         — 市場カレンダー管理
    - audit.py                       — 監査ログ（DDL / 初期化）
    - stats.py                       — 共通統計ユーティリティ（zscore_normalize 等）
  - research/
    - __init__.py
    - factor_research.py             — 各種ファクター計算
    - feature_exploration.py         — 将来リターン・IC・統計サマリー
  - ai/, data/, research/ 以下にそれぞれテスト・補助関数も存在

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY        — OpenAI API キー（AI 機能を使う場合必須）
- KABU_API_PASSWORD     — kabu API のパスワード（必要に応じて）
- KABU_API_BASE_URL     — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH           — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH           — SQLite/監視用パス（デフォルト data/monitoring.db）
- KABUSYS_ENV           — development | paper_trading | live（デフォルト development）
- LOG_LEVEL             — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（1 を設定）

---

## テスト・開発時のヒント

- 環境変数の自動ロードを無効化したい場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- AI 呼び出しやネットワーク依存箇所はモック可能に設計されています（モジュール内の _call_openai_api や _urlopen などを patch）。
- DuckDB はファイルパス（例: data/kabusys.duckdb）または ":memory:" を利用可能です。audit.init_audit_db() はディレクトリ自動作成を行います。

---

必要であれば、README に含める具体的な .env.example（推奨設定テンプレート）や、開発用の docker-compose / systemd の起動例、CI 用のテスト手順なども作成します。どの部分を詳細化しますか？