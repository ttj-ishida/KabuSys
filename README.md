# KabuSys

KabuSys は日本株のデータ収集・品質管理・ファクター計算・ニュース NLP・市場レジーム判定・監査ログまでを含む、自動売買・リサーチ向けの共通ライブラリ群です。本リポジトリは主に ETL → データ品質 → 研究 → シグナル生成 → 発注／監視 に必要なユーティリティを提供します。

## 主な特徴
- J-Quants API 連携による株価・財務・マーケットカレンダーの差分 ETL（レートリミット・リトライ対応、冪等保存）
- DuckDB を利用したローカルデータベース保存と SQL ベースのデータ処理
- ニュース収集（RSS）と前処理、LLM（OpenAI）を使ったニュースごとの銘柄センチメント算出（ai_scores テーブルへの書き込み）
- マクロニュースと ETF（1321）の MA 乖離を組み合わせた市場レジーム判定（bull / neutral / bear）
- ファクター計算（Momentum / Volatility / Value 等）と特徴量探索（将来リターン・IC・統計サマリー）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログスキーマ（signal_events / order_requests / executions）と初期化ユーティリティ
- セキュリティ考慮（RSS の SSRF 防止、defusedxml による XML パース保護、外部 API 呼び出しのフェイルセーフ設計）

---

## 必要条件
- Python 3.10 以上（型ヒントで `X | None` 形式を使用）
- 主な Python パッケージ:
  - duckdb
  - openai
  - defusedxml

（プロジェクトによって他に必要な依存がある場合があります。環境に合わせて追加してください。）

---

## 環境変数 / 設定
KabuSys は .env または環境変数から設定を読み込みます（自動読み込みはプロジェクトルートの `.git` または `pyproject.toml` を基準に行われます）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行監視向け設定
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

設定は `kabusys.config.settings` 経由でアクセスできます（例: `from kabusys.config import settings`）。

---

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （任意）pip install -e . などパッケージ化されている場合は適宜

4. 環境変数を設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成して値を設定
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=あなたのリフレッシュトークン
     OPENAI_API_KEY=sk-...
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     ```

5. DuckDB の初期スキーマ／監査 DB を必要に応じて初期化
   - 監査テーブルを作るには:
     ```
     from kabusys.config import settings
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db(settings.duckdb_path)
     ```

---

## 使い方（主要なユースケース例）

基本的に各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。以下は簡単な利用例です。

- 共通インポート例
  ```
  import duckdb
  from datetime import date
  from kabusys.config import settings
  ```

- ETL（日次パイプライン）の実行
  ```
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（OpenAI API キー必須）
  ```
  from kabusys.ai.news_nlp import score_news

  # api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定
  written_count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written_count}")
  ```

- 市場レジーム判定
  ```
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（研究用）
  ```
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  volatility = calc_volatility(conn, target_date=date(2026, 3, 20))
  value = calc_value(conn, target_date=date(2026, 3, 20))
  ```

- 将来リターン / IC / 統計サマリー
  ```
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary

  fwd = calc_forward_returns(conn, target_date=date(2026, 3, 20))
  ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
  summary = factor_summary(factor_records, columns=["mom_1m", "mom_3m"])
  ```

- カレンダー操作
  ```
  from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

  is_trading = is_trading_day(conn, date(2026, 3, 20))
  nxt = next_trading_day(conn, date(2026, 3, 20))
  days = get_trading_days(conn, start_date, end_date)
  ```

- RSS フィード取得（ニュース収集の一部）
  ```
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  ```

注意点:
- LLM 呼び出し（score_news / score_regime）は OpenAI の JSON mode を想定しています。レスポンスのパースで失敗した場合はフェイルセーフでスコア 0 を使ったり、該当銘柄をスキップしたりする設計です。
- J-Quants API を使う関数は `JQUANTS_REFRESH_TOKEN` を必要とします（`kabusys.data.jquants_client.get_id_token` で使用）。

---

## ディレクトリ構成（主要ファイルと役割）
以下は `src/kabusys` 以下の主要モジュールと簡単な説明です。

- __init__.py
  - パッケージのバージョンと公開モジュール宣言

- config.py
  - 環境変数 / .env の読み込み、アプリ設定（settings オブジェクト）

- ai/
  - __init__.py
  - news_nlp.py : ニュースから銘柄ごとのセンチメントを OpenAI で評価し ai_scores に保存
  - regime_detector.py : ETF（1321）MA 乖離 × マクロニュースセンチメントで市場レジーム判定

- data/
  - __init__.py
  - jquants_client.py : J-Quants API クライアント（取得 + DuckDB への保存）
  - pipeline.py : ETL パイプライン（run_daily_etl 等）と ETLResult
  - etl.py : ETL の公開インターフェース（ETLResult 再エクスポート）
  - calendar_management.py : マーケットカレンダー管理（営業日判定等）
  - news_collector.py : RSS 取得と前処理（SSRF 対策、XML 安全）
  - stats.py : zscore_normalize 等、汎用統計関数
  - quality.py : データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py : 監査ログスキーマ定義・初期化（signal_events / order_requests / executions）

- research/
  - __init__.py
  - factor_research.py : Momentum / Volatility / Value 等のファクター算出
  - feature_exploration.py : 将来リターン計算、IC、統計サマリー、ランク関数

その他、各モジュール内に多くの補助関数・設計方針コメントが含まれており、実運用向けの堅牢性（冪等性、フェイルセーフ、ログ・監査）に配慮しています。

---

## 開発 / テストに関するメモ
- config の自動 .env ロードはプロジェクトルートの検出に基づき行われます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。
- OpenAI 呼び出しはモジュール内部でラップされており、ユニットテストでは `_call_openai_api` をモックして応答を差し替えることが想定されています。
- DuckDB の `executemany` に空リストを渡すとエラーになるバージョンがあるため、該当コードでは空チェックが入っています。テスト環境でも実運用に近い DuckDB バージョンを使うことを推奨します。

---

## ライセンス / コントリビューション
（この README では省略 — 実際のリポジトリに合わせて追記してください）

---

README の内容はコードベースのコメント・関数仕様に基づいてまとめています。追加で「使い方の具体的なスクリプト」や「デプロイ手順（systemd / コンテナ）」などが必要であれば、利用シーンに合わせて追記します。