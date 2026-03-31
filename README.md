# KabuSys

KabuSys は日本株向けのデータ基盤・研究・自動売買補助ライブラリです。  
DuckDB を中心としたデータETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ファクター算出、品質チェック、監査ログなどの機能を提供します。

主な目的は「データ収集 → 品質チェック → ファクター算出 → シグナル／監査」のワークフローを安全に実行できる基盤を提供することです。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要API例）
- 環境変数（.env）一覧
- ディレクトリ構成（主要ファイル説明）
- 運用・テスト時の注意点

---

プロジェクト概要
- 日本株のデータプラットフォームと研究用ユーティリティの集合。
- J-Quants API から株価/財務/カレンダーを取得し DuckDB に格納する ETL パイプラインを持つ。
- RSS ニュース収集と OpenAI を使った銘柄別・マクロセンチメントのスコアリング（JSON mode）を提供。
- 研究用ファクター（Momentum/Volatility/Value 等）や将来リターン、IC（Information Coefficient）等の解析ユーティリティを提供。
- 発注フローの監査ログ（signal/order_request/executions）用スキーマ初期化機能あり。

---

機能一覧
- データ取得 / ETL
  - J-Quants API クライアント（rate limit・リトライ・トークン自動リフレッシュ対応）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- データ品質チェック
  - 欠損（OHLC）、重複、スパイク（前日比閾値）、日付不整合（未来日付 / 非営業日データ）
- ニュース関連（News Collector & NLP）
  - RSS 収集（SSRF対策、トラッキングパラメータ除去、前処理）
  - GPT ベースのニュースセンチメント（ai.news_nlp.score_news）
  - マクロセンチメント合成による市場レジーム判定（ai.regime_detector.score_regime）
- 研究ユーティリティ
  - ファクター計算（momentum, volatility, value）
  - 将来リターン、IC（ランク相関）、ファクター統計サマリ
  - Zスコア正規化ユーティリティ
- 監査ログ（Audit）
  - 監査用スキーマ初期化（init_audit_schema / init_audit_db）
  - signal_events / order_requests / executions の設計とインデックスを備える
- 設定管理
  - 環境変数 / .env 自動読み込み（プロジェクトルート検出、.env / .env.local 取り込み）

---

セットアップ手順（最小）
前提: Python 3.10+（`X | Y` の型注釈、match-free union 表記などを使用）を推奨します。

1. リポジトリをクローンしてインストール（開発環境）
   - (プロジェクトルートに pyproject.toml がある想定)
   - pip editable インストール例:
     ```
     pip install -e .
     ```
2. 必要パッケージ（代表例）
   ```
   pip install duckdb openai defusedxml
   ```
   - 実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。
3. 環境変数設定
   - プロジェクトルートの .env または .env.local に必要な設定を記述します。
   - 自動ロードはデフォルトで有効（OS 環境変数 > .env.local > .env）。
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
4. DuckDB ファイル用ディレクトリ作成
   - 設定で指定したパス（例: data/kabusys.duckdb）の親ディレクトリを作成してください（init_audit_db は自動で親ディレクトリ作成しますが、運用時は権限等に注意）。

---

環境変数（主要）
Settings クラスで参照される必須/主要変数:

必須（値がないと ValueError を投げます）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD : kabu ステーション API のパスワード（発注等に使用）
- SLACK_BOT_TOKEN : Slack 通知で使用
- SLACK_CHANNEL_ID : Slack チャンネル ID

任意 / デフォルトあり
- KABUSYS_ENV : "development" | "paper_trading" | "live" （デフォルト "development"）
- LOG_LEVEL : "DEBUG"|"INFO"|"WARNING"|"ERROR"|"CRITICAL"（デフォルト "INFO"）
- KABU_API_BASE_URL : kabu API ベース URL（デフォルト "http://localhost:18080/kabusapi"）
- DUCKDB_PATH : duckdb ファイルパス（デフォルト "data/kabusys.duckdb"）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト "data/monitoring.db"）
- PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT

.env の自動読み込み
- OS 環境変数 > .env.local > .env の順で読み込まれます。
- プロジェクトルートは .git または pyproject.toml を基準に自動検出されます。
- テストや特別な実行時に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます。

---

使い方（主要 API／スニペット）

- DuckDB 接続作成
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI API キー必要）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY は環境変数か api_key 引数で渡す
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("written:", written)
  ```

- 市場レジーム判定（ETF 1321 とマクロニュースの合成）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査DB 初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # init_audit_db は UTC タイムゾーン固定・DDL を作成します
  ```

- ファクター計算 / 研究ユーティリティの利用例
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

  moment = calc_momentum(conn, target_date=date(2026,3,20))
  vol = calc_volatility(conn, target_date=date(2026,3,20))
  value = calc_value(conn, target_date=date(2026,3,20))

  forward = calc_forward_returns(conn, target_date=date(2026,3,20), horizons=[1,5,21])
  ic = calc_ic(moment, forward, factor_col="mom_1m", return_col="fwd_1d")
  ```

- RSS フィード取得（ニュースコレクター）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  ```

---

ディレクトリ構成（主要ファイルと役割）
- src/kabusys/
  - __init__.py — パッケージ初期化（version等）
  - config.py — 環境変数/.env 読み込みと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py — 記事レベルの NLP スコアリング（OpenAI）
    - regime_detector.py — マクロ + ETF MA による市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py — ETL パイプライン（run_daily_etl など）
    - etl.py — ETL API の再エクスポート（ETLResult）
    - jquants_client.py — J-Quants API クライアント（取得・保存）
    - news_collector.py — RSS 収集 / 前処理 / 保存ロジック
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付整合性）
    - stats.py — 共通統計ユーティリティ（zscore_normalize）
    - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
    - audit.py — 監査ログスキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py — Momentum/Volatility/Value などの計算
    - feature_exploration.py — 将来リターン calc / IC / summary / rank
  - ai/、research/、data/... などのサブモジュールが機能別に分離されています。

---

運用・テスト時の注意点
- Look-ahead バイアス対策
  - モジュール内で datetime.today() / date.today() を不用意に参照しない設計の関数が多くあります。target_date を明示的に与えてバックテスト可能性を保ってください。
- OpenAI 呼び出し
  - news_nlp / regime_detector は OpenAI の JSON mode を利用します。API の失敗時はフェイルセーフ（0.0 でフォールバック）するよう設計されていますが、レート制限やレスポンス形式の違いには注意してください。
- .env 自動読み込み
  - パッケージはプロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動で読み込みます。テスト時や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をアサインすると環境の汚染を避けられます。
- DuckDB executemany の仕様
  - DuckDB 0.10 の executemany は空リストを渡すと失敗する箇所があるため、コード内で空チェック済みです。DB バージョンに注意してください。
- セキュリティ
  - news_collector は SSRF 対策、受信サイズ制限、defusedxml による XML パース保護などを行っていますが、本番での運用ではネットワーク方針・プロキシ・ACL を必ず適切に設定してください。

---

ライセンス / 貢献
- このリポジトリのライセンス情報はプロジェクトのルートにある LICENSE / pyproject.toml 等を参照してください。
- コントリビューションは issue / pull request を通じて歓迎します。テストケースとドキュメントを添えてください。

---

問い合わせ
- 実行上の疑問やバグ報告は issue を作成してください。README にある設定値や使用例に従って最小の再現コードを添えると対応が早くなります。

以上。