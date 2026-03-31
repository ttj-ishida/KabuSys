# KabuSys — 日本株自動売買 / データプラットフォーム

KabuSys は日本株のデータプラットフォームと戦略リサーチ／自動売買の基盤ライブラリです。  
DuckDB をデータ層に用い、J-Quants からの ETL、ニュース収集・NLP による銘柄スコアリング、マーケットレジーム判定、監査ログ（発注→約定トレース）などのユーティリティを提供します。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（日付参照に datetime.today() 等を直接使わない）
- DuckDB を中心に SQL + Python で効率的に処理
- 外部 API 呼び出しはリトライ／バックオフ・レート制御を実装
- 冪等性（ON CONFLICT / idempotent）を重視

---

## 機能一覧

- 環境設定読み込みと管理（.env 自動読み込み、Settings）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得・保存
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - レート制限・トークン自動リフレッシュ・リトライ実装
- ETL パイプライン
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース収集（RSS）と前処理（SSRF 対策、サイズ制限、URL 正規化）
- ニュース NLP（OpenAI を用いたセンチメント評価）
  - score_news: 銘柄ごとの ai_score を ai_scores テーブルへ保存
  - calc_news_window: ニュース集計ウィンドウ計算
- 市場レジーム判定（ETF 1321 の MA + マクロニュースの LLM 評価の合成）
  - score_regime: market_regime テーブルへ書き込み
- 研究向けユーティリティ（ファクター計算、将来リターン、IC 計算、Z スコア正規化）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day、カレンダー更新ジョブ）
- 監査ログ（signal_events / order_requests / executions）スキーマ初期化・管理
- 汎用統計ユーティリティ（zscore_normalize 等）

---

## 必要条件（主な依存）

- Python 3.10+
- duckdb
- openai（OpenAI の新しい SDK を使用する想定）
- defusedxml
- そのほか標準ライブラリ（urllib, json, logging, typing 等）

（プロジェクトの pyproject.toml / requirements.txt があればそちらを優先してください）

例（pip）:
```bash
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン / コピーしてパッケージをインストール
   ```bash
   git clone <repo-url>
   cd <repo>
   # 開発インストール（プロジェクトに pyproject / setup があれば）
   pip install -e .
   ```
2. 必要な Python パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   ```
3. 環境変数を設定（.env ファイルをプロジェクトルートに配置）
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN — Slack 通知に使用する場合
     - SLACK_CHANNEL_ID — Slack チャネル ID
     - KABU_API_PASSWORD — kabu API のパスワード（kabu 接続を行う場合）
     - OPENAI_API_KEY — OpenAI API を呼ぶ場合（score_news / score_regime）
   - 任意 / デフォルト
     - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG / INFO / ...（デフォルト INFO）
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=secret
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. 自動 .env 読み込みについて
   - パッケージの config モジュールはプロジェクトルート（.git または pyproject.toml のある場所）から .env を自動読み込みします。
   - テストなどで自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（主な例）

以下はライブラリ API の利用例です。実行前に必要な環境変数・DB の準備を行ってください。

共通: DuckDB 接続を作成
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # ファイルを指定、":memory:" も可
```

1) 日次 ETL 実行（J-Quants から日次差分取得 → 保存 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date None で今日
print(result.to_dict())
```

2) ニュース NLP スコアリング（指定日のニュースを集計して ai_scores に保存）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書込み銘柄数:", n_written)
```

3) 市場レジーム判定（ETF 1321 の MA とマクロニュース LLM を合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB 初期化（監査用 DuckDB を作成してスキーマ作成）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# または conn が既存なら init_audit_schema(conn)
```

5) マーケットカレンダーの判定や取得
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2026, 3, 20)
print("is_trading_day:", is_trading_day(conn, d))
print("next:", next_trading_day(conn, d))
```

6) ニュース収集（RSS 取得）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

注意点：
- score_news / score_regime は OpenAI API キーが必要です（api_key 引数または環境変数 OPENAI_API_KEY を使用）。
- J-Quants API 呼び出しは settings.jquants_refresh_token を必要とします。
- ETL・保存処理は DuckDB のテーブルスキーマを前提としています。スキーマ初期化は別モジュール（data.schema など）で行う想定です。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下の主要モジュールと主な公開関数／クラス）

- kabusys/
  - __init__.py
  - config.py
    - settings: Settings インスタンス（環境変数アクセス）
  - ai/
    - __init__.py (score_news をエクスポート)
    - news_nlp.py
      - score_news(conn, target_date, api_key=None)
      - calc_news_window(target_date)
    - regime_detector.py
      - score_regime(conn, target_date, api_key=None)
  - data/
    - __init__.py
    - calendar_management.py
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days
      - calendar_update_job
    - etl.py
      - ETLResult (再エクスポート)
    - pipeline.py
      - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
    - stats.py
      - zscore_normalize
    - quality.py
      - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
    - audit.py
      - init_audit_schema, init_audit_db
    - jquants_client.py
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
      - save_daily_quotes, save_financial_statements, save_market_calendar
      - get_id_token
    - news_collector.py
      - fetch_rss, preprocess_text, _make_article_id, など
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum, calc_value, calc_volatility
    - feature_exploration.py
      - calc_forward_returns, calc_ic, factor_summary, rank
  - monitoring/ (存在する場合は監視関連モジュール—コードベースに応じて)
  - execution/ (発注関連の実装がある場合)

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 用）
- KABU_API_PASSWORD — kabu API パスワード（発注連携用）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite モニタリング DB（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env ロードを無効化（テスト用）

config.Settings クラスを通じて環境変数を参照します。必須変数が未設定だと ValueError が投げられます。

---

## 開発・テスト時の注意

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。CI/テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして環境を明示的に注入することを推奨します。
- OpenAI 呼び出しやネットワーク IO 部分はユニットテストでモックしやすいように実装上の差し替えポイントがあります（例: kabusys.ai.news_nlp._call_openai_api を patch する等）。
- DuckDB を使ったテストは ":memory:" を渡してインメモリ DB を利用可能です。
- J-Quants クライアントはレート制御・リトライを実装しているため、実行時に過度なリクエストを行わないよう留意してください。

---

必要であれば README に以下を追加できます：
- 詳細なテーブルスキーマ（raw_prices, raw_financials, ai_scores, market_regime 等）
- CI / GitHub Actions の設定例
- 実際のワークフロー例（cron / Airflow での ETL スケジュール）
- API キーの安全な取り扱い（Vault / GitHub Secrets の例）

ご希望があれば、README をプロジェクトに合わせてさらに拡張（具体的なコマンド例、schema 初期化手順、サンプル .env.example ファイル挿入など）します。