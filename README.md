# KabuSys

日本株向けのデータプラットフォーム／自動売買基盤のライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース NLP（LLM を用いたセンチメント）、市場レジーム判定、研究用ファクター計算、監査ログ（注文→約定トレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール集合です。

- J-Quants API からの差分 ETL（株価日足・財務・マーケットカレンダー）
- RSS ベースのニュース収集と LLM を用いた銘柄センチメントスコアリング
- ETF とニュースを組み合わせた市場レジーム判定（bull / neutral / bear）
- 研究用ファクター（モメンタム・バリュー・ボラティリティ等）と評価ユーティリティ
- データ品質チェック、マーケットカレンダー管理
- 監査ログ（signal → order_request → execution）のスキーマ初期化と管理
- 設定は .env / 環境変数で管理。自動ロード機能あり（プロジェクトルートを自動検出）

設計上の特徴として、ルックアヘッドバイアスを避けるために内部で現在日時を直接参照しない（関数に target_date を明示的に渡す）点、DuckDB を用いたローカル永続化と SQL ベース処理、LLM 呼び出しに対する堅牢なリトライ/フォールバックなどがあります。

---

## 機能一覧

- 環境設定管理
  - .env/.env.local 自動ロード（プロジェクトルート検出）
  - 必須環境変数チェック（settings オブジェクト）
- データ ETL（kabusys.data.pipeline）
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - J-Quants クライアント（rate-limit、リトライ、トークン自動リフレッシュ）
  - DuckDB への冪等保存（ON CONFLICT 対応）
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合チェック
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、テキスト前処理、SSRF 対策、トラッキングパラメータ除去、raw_news への冪等保存
- ニュース NLP（kabusys.ai.news_nlp）
  - LLM（gpt-4o-mini）を用いた銘柄別センチメントスコア算出（ai_scores テーブルへ書き込み）
  - バッチ／トリミング／リトライ実装
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離 + マクロニュースセンチメントを合成して日次レジーム判定
- 研究モジュール（kabusys.research）
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize（kabusys.data.stats）を利用した正規化
- 監査ログ初期化（kabusys.data.audit）
  - signal_events, order_requests, executions のテーブル定義とインデックス作成
  - init_audit_db / init_audit_schema

---

## 必要条件（開発環境）

- Python 3.10 以上（構文で `|` 型合併を使用）
- 推奨ライブラリ（主要な実装依存）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib, json 等を使用

requirements.txt がプロジェクトにある場合はそれを利用してください。ない場合は最低限次をインストールします:

```
pip install duckdb openai defusedxml
```

※ OpenAI SDK のバージョンにより API 呼び出しインタフェースが変わる場合があります。実際の環境では SDK の互換性を検証してください。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   ```
   requirements.txt がない場合は上記の必須パッケージを individually にインストールしてください。

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を用意すると自動で読み込まれます（自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN（J-Quants のリフレッシュトークン）
     - OPENAI_API_KEY（OpenAI API キー）
     - SLACK_BOT_TOKEN（Slack 通知を使う場合）
     - SLACK_CHANNEL_ID（Slack 通知を使う場合）
     - KABU_API_PASSWORD（必要時）
   - オプション:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - KABU_API_BASE_URL（kabu API のベースURL、デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（データベースファイルのパス、デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 SQLite パス、デフォルト: data/monitoring.db）

5. .env の例（プロジェクトルートに .env を作成）
   ```
   # .env (例)
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
   SLACK_CHANNEL_ID=C0123456789
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主要な関数／ワークフロー）

以下はライブラリの主要な使い方の例です。関数は DuckDB 接続（duckdb.connect(...) の返り値）を受け取る設計が多いです。

- DuckDB 接続を開く（ファイル DB）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# API キーを環境変数で設定していれば api_key=None で可
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定を実行して market_regime テーブルへ書き込む
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records: list of dict with keys "date", "code", "mom_1m", "mom_3m", "mom_6m", "ma200_dev"
```

- 監査ログ用 DB を初期化する（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブルとインデックスが作成されます
```

- .env 自動ロードを無効化する（テスト時など）
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

注意点:
- OpenAI 呼び出しは料金が発生するため、テスト環境ではモックや環境変数の無効化を検討してください。
- J-Quants API はレート制限と認証（リフレッシュトークン）を使用します。設定されたトークンの権限を確認してください。
- ETL 関数は例外を内部で捕捉して処理を継続する設計ですが、結果オブジェクト（ETLResult）でエラー・品質問題を確認してください。

---

## ディレクトリ構成（抜粋）

以下はリポジトリ内の主要ファイルとモジュールのツリー（抜粋）です。実際のリポジトリに合わせて微調整してください。

- src/kabusys/
  - __init__.py
  - config.py                              # 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                           # ニュース NLP（score_news 等）
    - regime_detector.py                    # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                     # J-Quants API クライアント（fetch/save）
    - pipeline.py                           # ETL パイプライン（run_daily_etl 等）
    - etl.py                                # ETL 公開インターフェース
    - news_collector.py                     # RSS 収集（fetch_rss 等）
    - calendar_management.py                # マーケットカレンダー管理
    - stats.py                              # 汎用統計ユーティリティ（zscore_normalize）
    - quality.py                            # データ品質チェック
    - audit.py                              # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py                    # ファクター計算（mom/value/volatility）
    - feature_exploration.py                # 将来リターン・IC・統計サマリー
  - monitoring/ (未掲載ファイルにつづく可能性あり)
  - execution/  (未掲載ファイルにつづく可能性あり)
  - strategy/   (未掲載ファイルにつづく可能性あり)

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- OPENAI_API_KEY (必須 for LLM functions) — OpenAI の API キー
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知に必要
- KABU_API_PASSWORD — kabuAPI（必要な機能を使う場合）
- KABUSYS_ENV — development | paper_trading | live（デフォルト development）
- LOG_LEVEL — ログレベル（デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite ファイルパス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化するには 1 を設定

---

## 開発・テストに関する注意

- LLM 呼び出し（OpenAI）や外部 API（J-Quants）はネットワーク依存のため、単体テストではモック（unittest.mock）による差し替えを推奨します。コード内でもテスト差し替え用に内部呼び出しを関数に切り出している箇所があります（例: _call_openai_api を patch）。
- DuckDB を用いた SQL 処理は SQL 文の互換性に依存します。ローカルで DuckDB のバージョンを合わせてください。
- ETL 実行は idempotent を目指していますが、運用前にバックアップと小規模のドライランで動作確認してください。

---

必要であれば README を拡張して、CI、フォーマット/リンティング、より詳細な API リファレンス（各関数の引数/返り値例）、実運用のワークフロー（cron / Airflow での運用例）などを追加します。どの部分を詳しくしたいか教えてください。