# KabuSys

日本株向けの自動売買／データ基盤ユーティリティ集です。  
データ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログ（監査テーブル）など、バックテスト・本番運用に必要な基盤処理を提供します。

---

## 概要

KabuSys は次のような用途を想定したモジュール群を提供します。

- J-Quants API を用いた株価・財務・カレンダーなどの差分取得と DuckDB への冪等保存（ETL）
- RSS ベースのニュース収集と銘柄紐付け
- OpenAI を使ったニュースセンチメント分析（ai.news_nlp）と市場レジーム判定（ai.regime_detector）
- 研究用のファクター計算（research.*）と統計ユーティリティ（data.stats）
- データ品質チェック（data.quality）
- 監査ログテーブル定義・初期化（data.audit）
- 市場カレンダー管理・営業日ロジック（data.calendar_management）

設計方針として、ルックアヘッドバイアス回避、冪等性、堅牢なリトライとフェイルセーフを重視しています。

---

## 主な機能一覧

- ETL
  - run_daily_etl: 市場カレンダー、株価、財務の差分取得・保存・品質チェックを一括実行
  - 個別 ETL: run_prices_etl / run_financials_etl / run_calendar_etl
- J-Quants クライアント（data.jquants_client）
  - fetch_* / save_* の一貫インターフェース（rate limiting, retry, token refresh）
- ニュース収集（data.news_collector）
  - RSS から記事取得、前処理、raw_news への冪等保存
- ニュース NLP（ai.news_nlp）
  - 指定ウィンドウのニュースをバッチで OpenAI に送り、ai_scores に書き込み
- 市場レジーム判定（ai.regime_detector）
  - ETF 1321 の MA200 とマクロニュースセンチメントを合成して日次レジーム判定
- 研究用（research）
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank
- データ品質（data.quality）
  - 欠損・重複・将来日付・スパイク検出などのチェック群
- 監査ログ（data.audit）
  - signal_events / order_requests / executions の DDL と初期化ユーティリティ

---

## 必要条件

- Python 3.10 以上（型記法および union 型の使用）
- 推奨パッケージ（主な依存）
  - duckdb
  - openai
  - defusedxml

（実際の運用では別途 requests 等が必要になる箇所があり得ます。プロジェクトの requirements.txt または pyproject.toml を参照してください。）

---

## セットアップ手順

1. リポジトリをクローン / パッケージをインストール

   仮想環境を作成してからインストールすることを推奨します。

   bash:
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb openai defusedxml
   # (プロジェクト配下に setup があれば) pip install -e .
   ```

2. 環境変数 / .env を用意する

   ルートに `.env`（および必要に応じて `.env.local`）を置くと自動で読み込まれます。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（ai 関連で必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注系で使用）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/...
   - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH: data/monitoring.db（デフォルト）
   - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（監視用）
   
   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=secret
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. データベース場所の準備（必要に応じて）
   - DuckDB をファイルで使う場合、親ディレクトリを作成するか、data ディレクトリを作成してください。
     ```
     mkdir -p data
     ```

---

## 使い方（主要な利用例）

※ ここでは簡単な Python スニペットを示します。logging の設定や例外処理は適宜追加してください。

1. 日次 ETL を実行する

   ```
   from datetime import date
   import duckdb
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

2. ニューススコアリング（ai.news_nlp）

   ```
   from datetime import date
   import duckdb
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect("data/kabusys.duckdb")
   count = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY が必要
   print("scored:", count)
   ```

3. 市場レジーム判定（ai.regime_detector）

   ```
   from datetime import date
   import duckdb
   from kabusys.ai.regime_detector import score_regime

   conn = duckdb.connect("data/kabusys.duckdb")
   score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY が必要
   ```

4. 監査ログスキーマ初期化

   ```
   import duckdb
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db("data/audit.duckdb")  # parent dir を自動作成
   ```

5. 市場カレンダー判定ユーティリティ

   ```
   from datetime import date
   import duckdb
   from kabusys.data.calendar_management import is_trading_day, next_trading_day

   conn = duckdb.connect("data/kabusys.duckdb")
   d = date(2026, 3, 20)
   print(is_trading_day(conn, d))
   print(next_trading_day(conn, d))
   ```

6. RSS フィード取得（ニュース収集の一部）

   ```
   from kabusys.data.news_collector import fetch_rss

   articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
   for a in articles[:5]:
       print(a["datetime"], a["title"])
   ```

---

## 環境変数と設定（要点）

- 自動 .env 読み込み
  - パッケージはプロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動で読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - 自動ロードを無効にする: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- 主要設定は `kabusys.config.settings` から参照できます。例:
  - settings.jquants_refresh_token
  - settings.duckdb_path
  - settings.env / settings.is_live / settings.log_level

---

## ディレクトリ構成（主要ファイル）

サンプルツリー（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py  — 環境変数と設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースを OpenAI でスコアリング（ai_scores）
    - regime_detector.py — MA200 とニュースで市場レジーム判定（market_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API client（fetch/save）
    - pipeline.py             — ETL パイプライン / ETLResult
    - etl.py                  — ETL 再エクスポート（ETLResult）
    - news_collector.py       — RSS 収集 / 前処理
    - calendar_management.py  — 市場カレンダー / 営業日ユーティリティ
    - quality.py              — データ品質チェック群
    - stats.py                — zscore_normalize 等統計ユーティリティ
    - audit.py                — 監査ログ DDL / init_audit_schema / init_audit_db
  - research/
    - __init__.py
    - factor_research.py      — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py  — calc_forward_returns / calc_ic / factor_summary / rank

（詳細は各モジュールの docstring を参照してください。各関数に利用例と設計上の注意が含まれています。）

---

## 開発・運用上の注意

- ルックアヘッドバイアス対策:
  - 多くの処理は internal において date 引数ベースで動作し、`datetime.today()` や `date.today()` に依存しない設計になっています。バックテスト用途でも安全に使えるように配慮されています。
- OpenAI / J-Quants 呼び出し:
  - API 呼び出しの失敗に対してはリトライとフェイルセーフ（ゼロスコア、スキップ等）を行いますが、API キーの設定は必須です（該当処理を呼ぶ前に環境変数を設定してください）。
- DuckDB の互換性:
  - 一部の executemany 空リストの扱いなど DuckDB バージョン依存の注意があります。DuckDB バージョンと合わせて動作確認を行ってください。
- セキュリティ:
  - news_collector は SSRF 対策（リダイレクト検査 / プライベートホスト拒否）や XML パースのハードニング（defusedxml）を実装しています。

---

## 参考（トラブルシュート）

- 環境変数が読み込まれない:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認。または .env/.env.local の位置（プロジェクトルート判定は .git または pyproject.toml ベース）を確認してください。
- OpenAI 呼び出しでエラーが出る:
  - OPENAI_API_KEY の設定を確認してください。AI モジュールは API レスポンスの JSON 構造を厳密に期待しています。想定外の出力がある場合はログを確認し、モデル設定をチェックしてください。
- J-Quants API の 401 が発生する:
  - JQUANTS_REFRESH_TOKEN を確認。jquants_client は自動リフレッシュを試みますが、最初のトークンが誤っていると失敗します。

---

詳細は各モジュールの docstring（ソース内コメント）を参照してください。必要であれば README に追加記載（CI 流れ、運用スクリプト、例外ハンドリング方針など）を追記します。