# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
ETL・ニュース収集・AIによるニュースセンチメント評価・市場レジーム判定・研究（ファクター計算）・監査ログ等の機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ収集 -> 品質チェック -> ファクター計算 -> シグナル生成 -> 発注監査までを想定したコンポーネント群です。  
主な設計方針は次のとおりです：

- Look-ahead バイアスを避ける（実行時点の現在日時を安易に参照しない）
- DuckDB を用いたローカルデータレイク（raw_prices, raw_financials, raw_news, market_calendar 等）
- J-Quants API を用いたデータ取得（差分更新・ページネーション対応・再試行・レート制御）
- OpenAI（gpt-4o-mini 等）を用いたニュースの NLP 処理（JSON Mode 利用）
- 冪等性・監査性を重視（監査テーブル、order_request_id の冪等キー等）
- 外部への直接発注コードはこのコードベースには含まれていない（監査・実行層の基盤を提供）

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数チェック（settings オブジェクト）
- データ ETL（kabusys.data.pipeline）
  - J-Quants から株価・財務・カレンダーを差分取得して DuckDB に保存
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - rate limit 制御、リトライ、トークン自動更新、DuckDB への冪等保存
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、SSRF 対策、トラッキングパラメータ除去、raw_news 保存
- 市場カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日取得、カレンダーの夜間更新ジョブ
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等のテーブル定義と初期化関数
- AI モジュール（kabusys.ai）
  - ニュースセンチメントスコア（score_news）
  - 市場レジーム判定（score_regime） — ETF 1321 の MA200 とマクロニュースの合成
- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（momentum, volatility, value）、forward returns、IC、統計サマリ
- 汎用統計ユーティリティ（kabusys.data.stats）
  - zscore_normalize 等

---

## セットアップ手順

以下は動作に必要な基本手順です。プロジェクトの仮想環境作成と依存パッケージのインストールを行います。

1. Python のインストール（推奨: 3.10+）
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール

推奨パッケージ（requirements.txtがない場合の例）:
- duckdb
- openai
- defusedxml

例:
```
pip install duckdb openai defusedxml
```

パッケージをローカル開発用にインストールする場合:
```
pip install -e .
```
（プロジェクトが setuptools/pyproject を持つ場合）

4. 環境変数の設定
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）から .env / .env.local を自動読み込みします。
- 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（一部）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（必要なら）
- SLACK_BOT_TOKEN — Slack 通知に使用
- SLACK_CHANNEL_ID — Slack 通知先チャンネル
任意/デフォルト:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/...
- DUCKDB_PATH — データベース (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH — 監視 DB (デフォルト: data/monitoring.db)
- OPENAI_API_KEY — OpenAI を使う機能で利用（各関数に api_key 引数で注入可）

.env の例:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
OPENAI_API_KEY=sk-xxxx...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## 使い方（代表的な例）

以下はライブラリをプログラムから呼び出す基本的な例です。いずれも Python スクリプト・REPL で実行できます。

- DuckDB 接続の作成例:
```python
import duckdb
from pathlib import Path
from kabusys.config import settings

db_path = settings.duckdb_path  # Path オブジェクト
conn = duckdb.connect(str(db_path))
```

- 日次 ETL を実行する（run_daily_etl）:
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# conn は duckdb 接続
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメントスコアを生成（score_news）:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# APIキーを明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {count} codes")
```

- 市場レジーム判定（score_regime）:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査 DB の初期化:
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_db = init_audit_db(Path("data/audit.duckdb"))  # 初期化済み接続を返す
```

- market calendar の夜間更新ジョブ（calendar_update_job）:
```python
from kabusys.data.calendar_management import calendar_update_job
from datetime import date

saved = calendar_update_job(conn, lookahead_days=90)
print("saved:", saved)
```

注意点:
- OpenAI 呼び出しを含む機能はネットワーク・API レート制限の影響を受けます。テスト時はモック（unittest.mock.patch）で `_call_openai_api` を差し替えられるよう設計されています。
- ETL 実行や保存はトランザクションで管理されますが、部分的に成功した結果が残る場合があります。ETLResult の内容を確認してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールと代表的な関数・クラスの一覧です。

- kabusys/
  - __init__.py
  - config.py
    - settings (Settings)
    - 自動 .env ロード機能（.git / pyproject.toml を基準にプロジェクトルート検出）
  - ai/
    - __init__.py
    - news_nlp.py
      - score_news(conn, target_date, api_key=None)
      - calc_news_window(target_date)
    - regime_detector.py
      - score_regime(conn, target_date, api_key=None)
  - data/
    - __init__.py
    - jquants_client.py
      - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
      - save_daily_quotes / save_financial_statements / save_market_calendar
      - get_id_token 等
    - pipeline.py
      - ETLResult dataclass
      - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
    - news_collector.py
      - fetch_rss / preprocess_text など RSS 収集・前処理・SSRF 対策
    - calendar_management.py
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
      - calendar_update_job
    - quality.py
      - QualityIssue dataclass
      - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
    - stats.py
      - zscore_normalize
    - audit.py
      - init_audit_schema / init_audit_db
    - etl.py
      - ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_volatility / calc_value
    - feature_exploration.py
      - calc_forward_returns / calc_ic / factor_summary / rank

---

## 開発・テストに関するメモ

- OpenAI 呼び出し・ネットワーク I/O 部分はユニットテストでモック化することを想定しています（モジュール内の `_call_openai_api` や jquants_client の `_request` などを patch）。
- .env の自動ロードはプロジェクトルート検出に依存するため、テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定するか、環境変数を直接注入してください。
- DuckDB のバージョン差異（executemany の空リストなど）に注意した実装になっています。テスト時は実際の DuckDB 接続（:memory:）を使うと良いです。
- ロギングは各モジュールで行っているため、ローカルでの実行前に適切にロガーを設定してください（LOG_LEVEL や logging.basicConfig 等）。

---

## よく使う環境変数一覧（まとめ）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- OPENAI_API_KEY (必須 for AI functions) — OpenAI API キー（score_news / score_regime）
- KABU_API_PASSWORD — kabuステーション API パスワード（必要に応じて）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知設定
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みの無効化（1=無効）

---

もし README に追加したい具体的な使用例（例: ETL の Cron 設定、Slack 通知の利用方法、戦略実行フローのサンプル）や CI/CD 用の手順があれば教えてください。必要に応じて追記します。