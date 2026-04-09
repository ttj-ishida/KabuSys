# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ。ETL（J-Quants からのデータ取り込み）、ニュース収集・NLP（OpenAI を利用したセンチメント解析）、リサーチ（ファクター/特徴量探索）、監査ログ（発注〜約定トレーサビリティ）、マーケットカレンダー管理などを含むモジュール群を提供します。

主な設計方針は「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ（外部API障害時に例外を投げずに継続可能）」です。

---

## 機能一覧

- データ取得 / ETL
  - J-Quants から株価日足（OHLCV）、財務データ、マーケットカレンダーを差分取得・保存（duckdb）
  - ETL パイプライン（run_daily_etl）と個別ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - 品質チェック（欠損・スパイク・重複・日付不整合検出）

- ニュース収集・NLP
  - RSS 取得と前処理（URL 正規化、SSRF 対策、受信サイズ制限）
  - ニュースと銘柄を紐付け raw_news/news_symbols → ai_scores へ書き込み
  - OpenAI（gpt-4o-mini, JSON mode）を使った銘柄別センチメント集計（score_news）
  - マクロニュース + ETF（1321）MA200乖離を合成して市場レジーム判定（score_regime）

- 研究（Research）
  - ファクター計算: momentum / value / volatility 等（calc_momentum / calc_value / calc_volatility）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - Z スコア正規化ユーティリティ（zscore_normalize）

- 監査ログ（Audit）
  - signal_events / order_requests / executions を含む監査用スキーマ作成（init_audit_schema / init_audit_db）
  - 発注トレーサビリティ（冪等キー、ステータス遷移管理）

- カレンダー管理
  - market_calendar の取得・更新（calendar_update_job）
  - 営業日判定・次営業日/前営業日取得・期間内営業日取得など（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）

- 設定管理
  - .env 自動読み込み（プロジェクトルート基準）、環境変数経由の設定（kabusys.config.settings）

---

## セットアップ手順

前提:
- Python 3.9 以上（typing の union 表記・型ヒントを使用）
- DuckDB、OpenAI SDK 等が必要（requirements を用意している場合はそちらに従ってください）

例（開発環境）:

1. リポジトリをチェックアウトしてパッケージをインストール（編集可能インストール推奨）
   ```
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   ```

2. 環境変数（.env）を用意する
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants API のリフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — 監視等に使用する SQLite のパス（デフォルト: data/monitoring.db）
     - PAPER_FILL_MODE — paper_trading 用のモック約定モード（instant/partial/never/reject）
     - PAPER_TRADING_SQLITE_PATH — paper トレード用 SQLite パス（デフォルト: data/paper_trading.db）
     - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
     - LOG_LEVEL — "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"

3. 必要な DB の初期化（監査ログ用など）
   - 監査ログ専用 DB を初期化して接続を得る例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # conn は duckdb 接続オブジェクト
     ```

4. OpenAI を使用する場合は OPENAI_API_KEY を設定してください。
   - テスト時は関数内部の _call_openai_api をモックして API 呼び出しを差し替えられます。

---

## 使い方（代表的な例）

- 日次 ETL 実行（DuckDB 接続を作成して run_daily_etl を呼ぶ）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア付け（OpenAI API キーが必要）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定（ETF 1321 MA200 とマクロセンチメントの合成）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- ファクター計算（研究用）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  ```

- 監査スキーマの初期化（既存接続へ）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- ニュース収集（RSS フェッチ）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

注意点:
- score_news / score_regime は OpenAI API の結果を JSON mode で期待します。API 障害時はフォールバックロジックにより 0（中立）等で継続しますが、API キーは必須です。
- ETL は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar 等）に依存します。初期スキーマは別途用意するか、ETL スクリプトにスキーマ初期化処理を組み合わせてください。

---

## よく使う設定・ファイルパス（デフォルト）

- DuckDB データベース: data/kabusys.duckdb（settings.duckdb_path）
- 監視用 SQLite: data/monitoring.db（settings.sqlite_path）
- Paper trading SQLite: data/paper_trading.db（settings.paper_sqlite_path）
- 監査ログ PID / フラグ: data/execution.pid / data/kill.flag（settings.pid_file_path / settings.kill_flag_path）

.env の自動読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml を探索）を基準として `.env` と `.env.local` を自動読み込みします。
- テスト等で自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義（version 等）
- config.py — 環境変数 / 設定管理（settings）
- ai/
  - __init__.py
  - news_nlp.py — ニュース NLP（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダー管理
  - etl.py — ETL 公開インターフェース（ETLResult）
  - pipeline.py — 日次 ETL パイプラインと個別 ETL ジョブ
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - quality.py — データ品質チェック
  - audit.py — 監査ログ（スキーマ初期化 / init_audit_db）
  - jquants_client.py — J-Quants API クライアント（取得 / 保存）
  - news_collector.py — RSS 収集・前処理
- research/
  - __init__.py
  - factor_research.py — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 特徴量探索（forward returns, IC, summary）
- (その他) strategy/, execution/, monitoring/ などが __all__ に含まれる想定（必要に応じて追加）

---

## 開発・テストノート

- OpenAI 呼び出しやネットワーク依存処理はテストでモックしやすいよう設計されています（内部の _call_openai_api / _urlopen 等を patch 可能）。
- DuckDB はインメモリモード(":memory:") でテストが可能です（init_audit_db なども対応）。
- ETL・データ保存関数は冪等（ON CONFLICT）で設計されているため再実行が安全です。

---

問題報告・貢献:
- バグ報告や機能要望はリポジトリの Issue を利用してください。Pull Request は歓迎します。

ライセンス:
- （ここにライセンス情報を追記してください）

以上。必要に応じて README の具体的なコマンドや .env.example のテンプレートを追加できます。どの情報を詳細化したいか教えてください。