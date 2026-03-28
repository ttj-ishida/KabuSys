# KabuSys

KabuSys は日本株向けのデータプラットフォーム & 自動売買基盤のライブラリ群です。  
DuckDB をデータレイクとして用い、J-Quants からのデータ取得（OHLCV / 財務 / カレンダー）、RSS ニュース収集、LLM を使ったニュースセンチメント評価、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）などを提供します。

主な目的は「データ取得 → 品質検査 → 特徴量生成 → シグナル → 発注（監査）」の一連処理を支える共通ユーティリティ群をライブラリ化することです。

----

## 主な機能一覧

- 環境変数・設定読み込み（.env の自動ロード、settings オブジェクト）
- J-Quants API クライアント
  - 日次株価（OHLCV）/ 財務データ / 上場銘柄情報 / マーケットカレンダーの取得
  - レートリミット管理・再試行・トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン（run_daily_etl / 個別 ETL）
  - 差分取得、バックフィル、品質チェックの実行
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）と前処理、安全対策（SSRF 防止、gzip・サイズチェック）
- ニュース NLP（OpenAI）による銘柄別センチメントスコアリング（ai_scores への書込）
- マクロニュース + ETF MA200 を用いた市場レジーム判定（bull / neutral / bear）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、統計サマリー、Z-score 正規化）
- 監査ログスキーマ初期化 / 監査 DB 作成（監査テーブル: signal_events, order_requests, executions）
- マーケットカレンダー管理（営業日判定・次営業日/前営業日取得・カレンダー更新ジョブ）

----

## セットアップ手順

前提:
- Python 3.10+
- DuckDB が利用できる環境
- OpenAI API キー（ニュース NLP / レジーム判定で使用）
- J-Quants リフレッシュトークン（データ取得用）
- Slack 等（任意機能）のトークン（通知）

1. リポジトリをクローンしてインストール（開発用）
   ```
   git clone <repo-url>
   cd <repo>
   pip install -e .
   ```

2. 必要パッケージ（一例）
   ```
   pip install duckdb openai defusedxml
   ```
   README の依存に合わせて requirements を整備してください。

3. 環境変数を設定（.env をプロジェクトルートに置くと自動ロードされます）
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数（例）
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     KABU_API_PASSWORD=your_kabu_api_password
     SLACK_BOT_TOKEN=your_slack_bot_token
     SLACK_CHANNEL_ID=your_slack_channel_id
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development   # development | paper_trading | live
     LOG_LEVEL=INFO
     ```
   - .env のパースはシェル風の key=value、クォートやコメントにも対応しています。

4. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data
   ```

----

## 使い方（代表的な操作例）

以下は簡単な Python スクリプト例です。実運用ではログ設定やエラーハンドリングを追加してください。

- DuckDB 接続例（settings を利用）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（データ取得・品質チェック含む）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- RSS ニュース取得と保存（news_collector.fetch_rss を呼んで raw_news に保存する処理はプロジェクト側でラップしてください）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  # 取得した記事を DB に挿入する処理を実装してください（raw_news テーブルへの保存）
  ```

- ニュースセンチメントスコア計算（OpenAI を利用）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {written} codes")
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査用 DuckDB の初期化（監査ログ用データベース）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/kabusys_audit.duckdb")
  # テーブルが作成され、UTC タイムゾーンがセットされます
  ```

- 研究用: ファクター計算 / 正規化 / IC 計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic

  conn = duckdb.connect("data/kabusys.duckdb")
  t = date(2026, 3, 20)
  momentum = calc_momentum(conn, t)
  volatility = calc_volatility(conn, t)
  value = calc_value(conn, t)

  # z-score 正規化例
  norm = zscore_normalize(momentum, ["mom_1m", "mom_3m", "ma200_dev"])

  # 将来リターン
  fwd = calc_forward_returns(conn, t, horizons=[1, 5, 21])
  ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  ```

----

## .env の例（.env.example 的な内容）
プロジェクトルートに .env を置くと自動でロードされます（CWD ではなくソース位置からプロジェクトルートを探索します）。

例:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx

# OpenAI
OPENAI_API_KEY=sk-....

# kabuステーション API
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678

# DB paths (相対パス可)
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

----

## 実装上の注意点 / 設計方針（抜粋）

- ルックアヘッドバイアス防止:
  - 内部処理では datetime.today() / date.today() を直接参照せず、target_date を明示して処理します。バックテストや再現性を保つための配慮です。
- 冪等性:
  - J-Quants から取得したデータの DB 保存は ON CONFLICT DO UPDATE（冪等）で実装。
  - 監査ログの order_request_id は冪等キーとして想定。
- フェイルセーフ:
  - LLM 呼び出し失敗時は 0.0（中立）にフォールバック、例外を投げずにログ出力して処理継続する方針。
- セキュリティ:
  - news_collector で SSRF 防止、gzip サイズ上限、XML の defusedxml 使用などの対策を実装。
- 再試行 / レート制御:
  - J-Quants クライアントは固定間隔のスロットリング（120 req/min）と指数バックオフを実装。
  - OpenAI 呼び出しにもリトライロジックを実装（429/接続断/5xx 等）。

----

## ディレクトリ構成（主要ファイル）

以下はプロジェクトの主要なソースツリー（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境設定・.env 自動ロード
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py            — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult 再エクスポート
    - news_collector.py             — RSS 収集・前処理
    - calendar_management.py        — マーケットカレンダー管理 / 営業日判定
    - quality.py                    — データ品質チェック
    - stats.py                      — 共通統計ユーティリティ（z-score 等）
    - audit.py                      — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py            — Momentum/Value/Volatility 等の計算
    - feature_exploration.py        — 将来リターン / IC / 統計サマリー
  - research/（上記ファイル群）
- pyproject.toml / setup.cfg 等（プロジェクトルートで管理）

----

## 開発・運用上のヒント

- テスト時に .env 自動ロードを無効化する:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 呼び出しやネットワーク I/O 部分はユニットテストでモック可能なように設計されています（_call_openai_api の差し替え等）。
- DuckDB の executemany は空リストを受け付けないバージョンがあるため、コード中で空チェックを行っています（互換性配慮）。
- 監査 DB は UTC タイムゾーンで TIMESTAMP を保存するように初期化されます。

----

もし README に追加したい「実行スクリプト」「CI 設定」「具体的なスキーマ定義（DDL）」「運用手順（cron 例）」などがあれば、目的に合わせて追記します。どの部分をより詳しく書くか指定してください。