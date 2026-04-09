# KabuSys

日本株向け自動売買・データプラットフォーム（ライブラリ）

軽量な ETL、データ品質チェック、ニュース NLP（OpenAI 経由）、市場レジーム判定、リサーチ用ファクター計算、監査ログなどを含む日本株システム基盤のモジュール群です。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への格納（ETL）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集・前処理・OpenAI を使った銘柄別センチメントスコア算出（ai.news_nlp）
- マクロニュースとETFの MA を組み合わせた市場レジーム判定（ai.regime_detector）
- 研究用のファクター計算（research.*）および統計ユーティリティ（data.stats）
- 発注・約定トレーサビリティ用の監査（data.audit）
- J-Quants クライアント（data.jquants_client）: レート制限・リトライ・トークン自動更新を実装

設計上のポイント：
- ルックアヘッドバイアスを避けるため、内部で `date.today()` 等を不用意に参照しない実装方針
- ETL / 保存処理は冪等（ON CONFLICT で上書き）で実装
- 外部 API 呼び出しにはレート制限・リトライ・フォールバックを備える
- DuckDB を主体としたローカルデータ管理

---

## 主な機能一覧

- ETL
  - 日次 ETL（prices / financials / market calendar）: `kabusys.data.pipeline.run_daily_etl`
  - 差分取得、バックフィル、品質チェック
- データ品質
  - 欠損チェック、主キー重複、スパイク検出、日付整合性チェック: `kabusys.data.quality`
- ニュース
  - RSS 収集・前処理・SSRF 対策: `kabusys.data.news_collector`
  - OpenAI を用いた銘柄別ニュースセンチメント: `kabusys.ai.news_nlp.score_news`
- 市場レジーム判定
  - ETF (1321) の 200 日 MA とマクロニュースの LLM スコアを組み合わせた日次判定: `kabusys.ai.regime_detector.score_regime`
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算: `kabusys.research.*`
  - 将来リターン計算、IC 計算、統計サマリー
- 監査（Audit）
  - signal → order_request → execution を辿れる監査テーブルの初期化: `kabusys.data.audit.init_audit_db` / `init_audit_schema`
- J-Quants クライアント
  - レート制限、トークン自動リフレッシュ、ページネーション、DuckDB への保存ユーティリティ

---

## セットアップ手順

前提:
- Python 3.10+（ソースで型ヒントの union `|` を利用）
- DuckDB を利用可能（Python パッケージ duckdb）
- OpenAI API を利用する場合は API キー
- J-Quants のリフレッシュトークン（データ ETL に必須）

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   - リポジトリに requirements.txt があることを想定：
     ```
     pip install -r requirements.txt
     ```
   - 開発中は editable install:
     ```
     pip install -e .
     ```

4. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（自動読み込みはデフォルトで有効）。
   - 主要な環境変数（最低限必要なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
     - KABU_API_PASSWORD: kabu ステーション API のパスワード（必要時）
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
     - その他（任意）:
       - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
       - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
       - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
       - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH
       - KABUSYS_ENV（development / paper_trading / live）
   - 自動 .env ロードを無効化するには:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. データベースディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（代表的な例）

以下は Python スクリプトや REPL からモジュールを呼ぶ例です。各関数は DuckDB の接続オブジェクト（duckdb.connect() が返す接続）を受け取ります。

- 日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニュースセンチメントをスコアリングして ai_scores に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数か api_key 引数で指定
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", n_written)
  ```

- 市場レジーム（market_regime テーブル）を算出する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB を初期化する（監査用 DuckDB を別ファイルで作る例）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/monitoring_audit.duckdb")
  ```

- RSS を取得する（ニュース収集の一部）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  url = DEFAULT_RSS_SOURCES["yahoo_finance"]
  articles = fetch_rss(url, source="yahoo_finance")
  for a in articles[:5]:
      print(a["datetime"], a["title"])
  ```

注意点:
- OpenAI 呼び出しはネットワーク障害・レート制限等に対してリトライやフォールバック（失敗時は中立スコア 0.0）を行う設計です。
- ETL・保存処理は冪等化されているため同一データの再投入で上書きされます。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須 for ETL）
- KABU_API_PASSWORD: kabu API パスワード（発注等で必要）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE: paper trading の埋め込み挙動（instant | partial | never | reject）
- PAPER_TRADING_SQLITE_PATH: Paper trading 用 SQLite パス
- KABUSYS_ENV: environment（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

設定はプロジェクトルートにある `.env` / `.env.local` または環境変数から読み込まれます。プロジェクトルートの判定は .git または pyproject.toml を基準に行われます。

---

## ディレクトリ構成（主要ファイル）

リポジトリの `src/kabusys` 配下がライブラリ本体です。主要モジュールを抜粋すると:

- src/kabusys/
  - __init__.py
  - config.py                          — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                       — ニュースセンチメント（ai_scores 書込）
    - regime_detector.py                — 市場レジーム判定（market_regime 書込）
  - data/
    - __init__.py
    - jquants_client.py                 — J-Quants API クライアント（fetch/save）
    - pipeline.py                       — ETL パイプライン（run_daily_etl 等）
    - etl.py                            — ETL 型の公開インターフェース（ETLResult）
    - quality.py                        — データ品質チェック
    - news_collector.py                 — RSS 収集 / 前処理
    - calendar_management.py            — 市場カレンダー操作（is_trading_day 等）
    - stats.py                          — 統計ユーティリティ（zscore_normalize）
    - audit.py                          — 監査ログテーブル初期化
  - research/
    - __init__.py
    - factor_research.py                — Momentum/Value/Volatility 等
    - feature_exploration.py            — forward returns / IC / summary 等

（上記以外に execution / strategy / monitoring 等のサブパッケージが想定されていますが、本リストはコード内に含まれる主要モジュールに基づく抜粋です。）

---

## 設計上・運用上の注意点

- Look-ahead bias の排除:
  - 各 AI / リサーチ関数は対象日より未来のデータ参照を明示的に防ぐ実装になっています（例: SQL では date < target_date などの条件を使用）。
- 冪等性:
  - DuckDB への保存は ON CONFLICT を用いた upsert（更新）を基本とします。ETL の再実行が安全になるよう設計されています。
- 外部 API 安全性:
  - J-Quants クライアントはレート制限（120 req/min）を尊重し、401 時のトークン自動リフレッシュやリトライを備えています。
  - news_collector は SSRF 対策、受信上限、XML パースの安全処理を行います。
- OpenAI 使用:
  - LLM 呼び出しは JSON Mode を想定し、レスポンスの検証とフォールバック（失敗時は中立スコア）を行っています。
  - テスト時に内部 API 呼び出し関数をモック可能な設計です。
- トランザクション:
  - 重要な書き込みは BEGIN/COMMIT/ROLLBACK を用いた処理を行い、失敗時にロールバックします（ただし一部 DDL は transactional フラグに注意）。

---

## よくある利用フロー（例）

1. `.env` に JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY をセット
2. 日次 ETL をスケジューラ（cron 等）で実行 → prices / financials / market_calendar を更新
3. ETL 後に `kabusys.data.quality.run_all_checks` を呼んでデータ品質を確認
4. ニュース収集を走らせ、`score_news` で ai_scores を更新
5. `score_regime` を日次で実行して market_regime を算出
6. 研究用に `kabusys.research` の関数を用いてファクター分析

---

もし README に追加したい内容（例: requirements.txt の正確な中身、CI / テスト実行方法、具体的な CLI サンプルなど）があれば教えてください。必要に応じて README を拡張します。