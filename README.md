# KabuSys

日本株向け自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（オーダー/約定トレース）などの機能を提供します。

主な設計方針は「バックテスト時のルックアヘッドバイアス回避」「冪等性」「フェイルセーフ（API障害時はスキップ/デフォールト継続）」です。

---

## 機能一覧

- data
  - J-Quants API クライアント（fetch / save）
  - 日次 ETL パイプライン（run_daily_etl）
  - 市場カレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
  - ニュース収集（RSS → raw_news）
  - データ品質チェック（欠損 / 重複 / スパイク / 日付不整合）
  - 監査ログ用スキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュースセンチメント（score_news） — OpenAI（gpt-4o-mini）を用いたJSON出力モード
  - マクロ + テクニカル合成による市場レジーム判定（score_regime）
  - ニュースウィンドウ計算（calc_news_window）
- research
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 特徴量探索（forward returns, IC, 統計サマリー, ランク）
- audit / monitoring
  - シグナル → 発注 → 約定 をトレースする監査テーブルの定義・初期化
- 設定管理
  - 環境変数 / .env 自動ロード（パッケージルートから .env, .env.local を読み込み）

---

## 必要な環境変数（主なもの）

以下はライブラリが参照する主な環境変数です。プロジェクトルートに `.env` / `.env.local` を用意することを推奨します。

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

自動で .env を読み込む挙動は、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットすると無効化できます（テスト時に利用）。

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（推奨）
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate   # macOS / Linux
     .venv\Scripts\activate      # Windows
     ```

2. 必要パッケージをインストール  
   （リポジトリに pyproject.toml / requirements.txt がない場合は、以下の最低依存をインストールしてください）
   ```
   pip install duckdb openai defusedxml
   ```
   - 実運用では HTTP/SSL 等に依存するため環境に応じた追加パッケージが必要になる場合があります。

3. 環境変数を設定  
   プロジェクトルートに `.env` を作成するか、環境に直接設定してください。例の最小構成:
   ```
   JQUANTS_REFRESH_TOKEN=xxx
   OPENAI_API_KEY=sk-xxx
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-xxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```
   - `.env.local` は `.env` より優先して読み込まれ（上書き）、OS 環境変数は最優先です。

4. データベース初期化（監査ログなど）
   - 監査 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 既存の DuckDB 接続に監査スキーマを追加する:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_schema
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn, transactional=True)
     ```

---

## 使い方（主な例）

以下は基本的な利用例です。各 API は duckdb 接続（DuckDBPyConnection）を受け取る設計です。

- DuckDB 接続を作る（ファイルまたは ":memory:"）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定（省略時は今日）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントを生成（OpenAI API キーは環境変数 OPENAI_API_KEY）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"ai_scores に書き込んだ銘柄数: {n_written}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数か引数で渡す
  ```

- ファクター計算 / 研究ユーティリティ
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary

  target = date(2026, 3, 20)
  momentum = calc_momentum(conn, target)
  volatility = calc_volatility(conn, target)
  value = calc_value(conn, target)
  forwards = calc_forward_returns(conn, target, horizons=[1,5,21])
  ic = calc_ic(momentum, forwards, "mom_1m", "fwd_1d")
  summary = factor_summary(momentum, ["mom_1m", "mom_3m", "ma200_dev"])
  ```

- ニュース RSS を直接取得（news_collector）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])
  ```

注意:
- score_news / score_regime は OpenAI の JSON Mode（厳密な JSON 出力）を前提とし、API 失敗時はフェイルセーフ動作（該当コードはスキップまたはスコア0.0）します。
- 各関数はルックアヘッドバイアス回避のため、内部で date.today()/datetime.today() を不用意に参照しない設計になっています（target_date を明示して利用してください）。

---

## ディレクトリ構成

主要ファイル/モジュール（src/kabusys 配下）:

- __init__.py
- config.py — 環境変数 / .env 自動読み込み / 設定オブジェクト（settings）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント（score_news）
  - regime_detector.py — マクロ + MA200 による市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント + DuckDB 保存関数
  - pipeline.py — ETL パイプライン（run_daily_etl, run_prices_etl, ...）
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS 取得・前処理
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - quality.py — データ品質チェック
  - stats.py — zscore_normalize 等
  - audit.py — 監査ログスキーマ / 初期化（init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py — calc_momentum, calc_value, calc_volatility
  - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank
- research パッケージは data.stats を再利用しており、外部ライブラリに依存しない実装を志向しています。

---

## 開発・運用時の注意事項

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。テスト時には `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効にできます。
- J-Quants API の呼び出しはレートリミット（120 req/min）とリトライ処理を含みます。ID トークンの自動リフレッシュ機構あり。
- OpenAI 呼び出しはリトライやバックオフ処理を行いますが、料金や使用制限に注意してください。
- DuckDB に対する executemany の扱いや一部バージョン固有の挙動（空パラメータリスト不可など）を考慮した実装がなされています。
- 監査ログ（order_requests / executions 等）は削除せず永続化する前提で設計されています。order_request_id は冪等キーとして動作します。

---

README に不足している情報（例: pyproject.toml、テスト手順、CI 設定、具体的な SQL スキーマの初期化スクリプトなど）がある場合は、追加情報を提供してください。README をそれに合わせて拡張します。