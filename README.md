# KabuSys

KabuSys は日本株向けのデータプラットフォーム / リサーチ / 自動売買の基盤ライブラリです。J-Quants・RSS・OpenAI 等と連携してデータ収集（ETL）、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、監査ログ（トレーサビリティ）などを一貫して扱えるよう設計されています。

この README はリポジトリ内の主要モジュール群と基本的なセットアップ・利用方法を日本語でまとめたものです。

## 主な特徴

- データ収集（J-Quants API 経由の株価・財務・マーケットカレンダー）
  - ページネーション、レート制限、トークン自動リフレッシュ、指数バックオフ対応
- ETL パイプライン（差分取得・バックフィル・品質チェック）
  - run_daily_etl による日次 ETL 実行
- ニュース収集（RSS）と前処理（SSRF 対策・トラッキング除去）
- ニュース NLP（OpenAI）による銘柄別センチメント算出（ai.score_news）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントを合成）
  - ai.score_regime
- リサーチ用ファクター計算・特徴量解析
  - momentum / volatility / value / forward returns / IC / summary
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions を追跡するテーブル群の初期化ユーティリティ）
- 環境変数 / .env の自動読み込みと集中設定管理（kabusys.config）

---

## 機能一覧（モジュール別の概要）

- kabusys.config
  - .env ファイルまたは環境変数から設定を読み込み、Settings クラスでアクセス可能
  - 自動読み込みの優先度: OS 環境 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化
- kabusys.data
  - jquants_client: J-Quants API の取得 / DuckDB への保存（save_*）
  - pipeline: ETL 実行（run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl）
  - calendar_management: JPX カレンダーの判定 / 次営業日取得等
  - news_collector: RSS 取得・前処理・raw_news 保存用ユーティリティ
  - quality: データ品質チェック（欠損/スパイク/重複/日付不整合）
  - stats: zscore_normalize 等の統計ユーティリティ
  - audit: 監査ログテーブルの初期化（init_audit_schema / init_audit_db）
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースの LLM によるセンチメント算出と ai_scores テーブルへの書き込み
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュースの LLM スコアを合成して market_regime テーブルへ書き込み
- kabusys.research
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
- 監視・実行（設定項目として pid_file_path / kill_flag 等をサポート）

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（型アノテーションに union | を使用）
- システムに DuckDB が利用可能であれば良い（pip install duckdb で利用可）

1. リポジトリをクローンし、開発インストール（もしくはパッケージ化インストール）
   - 開発インストール例:
     - pip install -e .
   - 必要な依存パッケージ（代表例）:
     - duckdb
     - openai
     - defusedxml
     - （標準ライブラリ: urllib, logging 等は不要）
   - 例:
     - pip install duckdb openai defusedxml

2. 環境変数 / .env の準備
   - プロジェクトルート（pyproject.toml または .git があるディレクトリ）に `.env` / `.env.local` を配置すると自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN（J-Quants のリフレッシュトークン）
     - KABU_API_PASSWORD（kabuステーション API パスワード — 発注周りを使う場合）
   - 任意（機能に応じて）:
     - OPENAI_API_KEY（OpenAI API キー。ai モジュールを使う場合）
     - KABU_API_BASE_URL（kabu API のベース URL。デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用）
     - DUCKDB_PATH（データベースファイル、デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用 sqlite、デフォルト data/monitoring.db）
     - KABUSYS_ENV（development/paper_trading/live）
     - LOG_LEVEL（DEBUG/INFO/...）
   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

3. データベース初期化（監査ログ用）
   - 監査ログテーブルは kabusys.data.audit.init_audit_db / init_audit_schema で初期化できます。
   - 例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

注意:
- 他のスキーマ（raw_prices / raw_financials / market_calendar / raw_news / ai_scores / prices_daily 等）はプロジェクト内のスキーマ定義（別スクリプトやマイグレーション）で作成する想定です（この README のコード一覧では audit 用の初期化ユーティリティが提供されています）。

---

## 使い方（代表的な例）

以下は Python API を直接呼ぶ基本例です。実行前に .env を整え、依存パッケージをインストールしておいてください。

- DuckDB 接続と設定取得例
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（run_daily_etl）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（ai.score_news）
  - OpenAI API キーは引数で渡すか、環境変数 OPENAI_API_KEY に設定しておきます。
  ```python
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
  print("書き込み件数:", n_written)
  ```

- 市場レジーム判定（ai.score_regime）
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY から取得
  ```

- ファクター計算 / リサーチ
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  momenta = calc_momentum(conn, date(2026, 3, 20))
  vols = calc_volatility(conn, date(2026, 3, 20))
  values = calc_value(conn, date(2026, 3, 20))
  ```

- 監査 DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # テーブルが作成され、UTC タイムゾーンが設定されます（SET TimeZone='UTC'）
  ```

- RSS フィード取得（ニュース収集ユーティリティ）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES['yahoo_finance'], source='yahoo_finance')
  ```

注意点:
- ai モジュールは OpenAI の JSON mode を利用する想定です。API 制限や課金に注意してください。
- ETL / API 呼び出しはネットワーク・API レート制限に依存します。ログやリトライ設定を確認してください。
- run_daily_etl() は ETLResult を返し、品質チェックの結果（quality_issues）や errors を含みます。停止判断は呼び出し側で行ってください。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注や接続に必要）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで利用）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト development）
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env ロードを無効化

.env のパースはシェル風の export KEY=val 形式やコメント、クォート、エスケープに対応しています。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py            # ニュースの LLM スコアリングと関連ユーティリティ
  - regime_detector.py     # 市場レジーム判定（1321 MA とマクロセンチメントの合成）
- src/kabusys/data/
  - __init__.py
  - jquants_client.py      # J-Quants API クライアント（fetch / save / auth / rate limiter）
  - pipeline.py            # ETL パイプライン（run_daily_etl 等）
  - etl.py                 # ETLResult の公開（再エクスポート）
  - calendar_management.py # 市場カレンダー管理（営業日判定 / calendar_update_job）
  - news_collector.py      # RSS 取得・前処理・保存ユーティリティ
  - quality.py             # データ品質チェック
  - stats.py               # 統計ユーティリティ（zscore_normalize）
  - audit.py               # 監査ログ（テーブル DDL / init_audit_db）
- src/kabusys/research/
  - __init__.py
  - factor_research.py     # Momentum / Value / Volatility 計算
  - feature_exploration.py # 将来リターン / IC / summary / rank
- その他: strategy / execution / monitoring パッケージが宣言されているが実装はプロジェクト内の別ファイル等に依存します。

---

## ログ・監視・運用メモ

- KABUSYS_ENV により is_live / is_paper / is_dev を判定できます（settings.is_live 等）。
- PID ファイル / kill flag 等の設定があり、長時間実行プロセスの監視をサポートする設計です（設定: PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START）。
- リトライやフォールバックを多用しており、外部 API の一時障害に対してフェイルセーフ（デフォルトスコアやスキップ）で継続する方針です。
- ETL の品質チェックは fail-fast ではなく問題を収集して結果を返します。呼び出し側で Alert / 停止判断を実装してください。

---

## 開発・テスト時のヒント

- 自動 .env 読み込みを無効化して独立した環境を作る場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- ai モジュールや外部 API をテストする場合は、内部の _call_openai_api などを unittest.mock.patch で差し替える工夫がコード中で想定されています。
- news_collector のネットワーク呼び出しは _urlopen をモック化してテスト可能です。
- DuckDB による executemany の空パラメータに関する仕様（バージョン依存）を考慮しているため、本番と同等のバージョンで動作確認してください。

---

## ライセンス・貢献

- このドキュメントではライセンス情報は省略しています。実際のリポジトリの LICENSE ファイルを参照してください。
- バグ報告・機能追加は Pull Request ベースでお願いします。外部 API キー等は共有しないでください。

---

以上が KabuSys の概要と基本的な使い方です。より詳細な API やテーブルスキーマ、運用手順（マイグレーション、DB スキーマ初期化スクリプト等）はプロジェクト内の追加ドキュメント・設計書（DataPlatform.md / StrategyModel.md 等）を参照してください。必要であれば README をさらに拡張してセットアップスクリプトや CLI 例、運用 runbook を追加します。