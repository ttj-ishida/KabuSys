# KabuSys

日本株向けの自動売買／データプラットフォーム用 Python ライブラリ群です。  
ETL（J-Quants 経由の株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、リサーチ用ファクター計算、監査ログ（発注→約定トレーサビリティ）などを備えたモジュール群を提供します。

## 主要な目的
- J-Quants API からのデータ取得と DuckDB への冪等保存（ETL）
- RSS ニュース収集と LLM による銘柄センチメント評価（news_nlp）
- 市場レジーム判定（ETF + マクロ記事の合成スコア）
- ファクター計算 / 特徴量探索（リサーチ用途）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 監査ログ（signal → order_request → execution のトレース可能化）

---

## 機能一覧（抜粋）

- 環境設定管理
  - .env / .env.local をプロジェクトルートから自動ロード（必要時に無効化可能）
  - 必須の環境変数取得（不足時は例外）
- データ ETL（kabusys.data.pipeline）
  - run_daily_etl: 市場カレンダー、株価、財務データの差分取得 → 保存 → 品質チェック
  - 個別ジョブ: run_prices_etl / run_financials_etl / run_calendar_etl
- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch_*/save_* 系関数（ページネーション・リトライ・レートリミット対応）
  - get_id_token（リフレッシュトークン → idToken）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・前処理・raw_news への冪等保存（SSRF 回避、サイズ制限、トラッキングパラメータ除去）
- ニュース NLP（kabusys.ai.news_nlp）
  - score_news: 銘柄ごとに記事を集約して LLM（gpt-4o-mini）でセンチメントを算出し ai_scores に保存
- レジーム判定（kabusys.ai.regime_detector）
  - score_regime: ETF(1321) の 200 日 MA 乖離とマクロ記事の LLM スコアを合成して market_regime に保存
- リサーチ（kabusys.research）
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（kabusys.data.stats）
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合検査
- 監査ログ（kabusys.data.audit）
  - init_audit_schema / init_audit_db による監査テーブル初期化（UUID によるトレーサビリティ）

---

## セットアップ手順

前提:
- Python 3.10+（型注釈で | 型を使うため）
- pip, virtualenv 推奨

1. リポジトリをクローンして仮想環境を作成・有効化
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows (PowerShell 等)
   ```

2. 依存パッケージをインストール（例）
   requirements.txt がなければ最低限以下を入れてください:
   ```bash
   pip install duckdb openai defusedxml
   ```
   プロジェクト配布用に setuptools/poetry があれば `pip install -e .` を使う想定です。

3. 環境変数 / .env ファイルの準備
   - プロジェクトルート（.git か pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込みます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   代表的な環境変数 (.env.example)
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key      # score_news / score_regime に必要
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   SLACK_BOT_TOKEN=your_slack_token
   SLACK_CHANNEL_ID=your_channel_id
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development   # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

4. DuckDB ファイル/ディレクトリが必要な場合は自動で作成される箇所もありますが、事前にディレクトリを作ると安全です。
   ```bash
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下は Python REPL / スクリプトから主要機能を呼ぶ例です。

- ETL（日次パイプライン）を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのスコアリング（AI）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY が設定されていれば api_key 引数は不要
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI キーは環境変数 or api_key 引数で指定
  ```

- 監査ログ DB 初期化（別 DB を使う場合）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は DuckDB 接続、テーブルが作成される
  ```

- J-Quants から直接データ取得（テスト・デバッグ）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  id_token = get_id_token()  # JQUANTS_REFRESH_TOKEN が環境変数に必要
  records = fetch_daily_quotes(id_token=id_token, date_from=date(2026,1,1), date_to=date(2026,1,31))
  ```

---

## 知っておくべき挙動・設計方針

- Look-ahead バイアス防止:
  - 多くの関数は内部で datetime.today()/date.today() を直接参照せず、target_date を明示的に渡すことを想定しています。
- 自動環境読み込み:
  - プロジェクトルートの `.env`（優先度低）→ `.env.local`（優先度高）を自動でロードします。OS の環境変数はそれらより優先されます。
  - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し:
  - gpt-4o-mini を利用する設計です。API 呼び出しはリトライ・バックオフやレスポンス検証を行います。テスト時は内部の _call_openai_api をモックできます。
- J-Quants API:
  - レート制限（120 req/min）に合わせて RateLimiter を実装しています。401 受信時は自動でリフレッシュを試みます。
- DuckDB 互換性:
  - executemany の空リストバインド回避など DuckDB のバージョン差に配慮した実装になっています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースセンチメント（LLM）
    - regime_detector.py             — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（fetch/save）
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETLResult 再エクスポート
    - news_collector.py              — RSS 収集・整形
    - calendar_management.py         — 市場カレンダー管理（営業日判定）
    - stats.py                       — zscore_normalize 等
    - quality.py                     — データ品質チェック
    - audit.py                       — 監査ログテーブル初期化
  - research/
    - __init__.py
    - factor_research.py             — momentum/value/volatility 等
    - feature_exploration.py         — forward_returns, IC, summary, rank
  - ai/*、research/* のユーティリティ群

（上記は抜粋です。実際のリポジトリに他のモジュールやユーティリティが含まれる場合があります。）

---

## テスト・デバッグのヒント

- 外部 API 呼び出し（OpenAI / HTTP）をモックできるよう、モジュール内の小さなラッパー関数（_call_openai_api、_urlopen 等）に差し替えポイントを用意しています。ユニットテストではこれらを patch して副作用を抑えてください。
- DuckDB を ":memory:" にして単体テストを実行可能です（例: init_audit_db(":memory:")）。
- ETL 実行の副作用（DB 書き込み）があるため、テスト用 DB を用意して囲い込みテストを行ってください。

---

## ライセンス・貢献

（ここにライセンス情報 / 貢献ガイドを追記してください。プロジェクト配布時に適切なライセンスファイルを追加してください。）

---

この README はコードベースの主要機能と使い方の概要を記載しています。詳細な API 使用法や運用手順はプロジェクト内のドキュメント（Design / DataPlatform / Strategy 等の仕様書）に従ってください。必要があれば、特定の利用シナリオ向けの利用例や運用チェックリストを追記します。