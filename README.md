# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリセット。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、研究用ファクター計算、監査ログ（トレーサビリティ）、市場カレンダー管理、kabu ステーション連携のための設定・ユーティリティ群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータパイプラインとアルゴリズム研究、AI ベースのニュースセンチメント評価、監査ログを含む自動売買システムの基盤コンポーネント群です。  
主な目的は以下:

- J-Quants API からの差分取得と DuckDB への冪等保存（ETL）
- RSS ベースのニュース収集と OpenAI による記事／マクロセンチメント評価
- ファクター（モメンタム／バリュー／ボラティリティ等）計算、将来リターンや IC の分析補助
- 市場カレンダー管理（営業日判定、SQ判定等）
- 監査ログ（signal → order_request → execution）用スキーマ初期化
- 設定管理（.env / 環境変数自動読み込み）

設計方針として、ルックアヘッドバイアスを避ける実装、外部 API のリトライ & フェイルセーフ、DuckDB による効率的な SQL 処理、冪等性を意識した保存ロジックが取られています。

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（認証・取得・保存）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS -> raw_news 保存、SSRF 対策、トラッキングパラメータ除去）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp: ニュース記事の銘柄別センチメント評価（OpenAI）
  - regime_detector: ETF（1321）の MA とマクロニュースを合成した市場レジーム判定
- research
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（forward returns / IC / summary / rank）
- config
  - .env / 環境変数の読み込み、アプリ設定オブジェクト (`settings`)
  - 自動 .env 読み込み（プロジェクトルートを .git / pyproject.toml で探索）
- auditing / execution / monitoring（監査・発注・監視用ユーティリティ群の基礎）

---

## 必要条件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

実行環境やバージョンにより追加で必要になるパッケージがあります。pyproject.toml / requirements.txt を用いる運用を推奨します。

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール（プロジェクトに requirements があればそれを利用）
   ```
   pip install duckdb openai defusedxml
   # または
   pip install -e .
   ```

4. 環境変数 / .env を準備  
   プロジェクトルートに `.env`（と必要に応じて `.env.local`）を置くと、パッケージ import 時に自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能）。

   例: `.env`
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

   注意:
   - `JQUANTS_REFRESH_TOKEN` と `OPENAI_API_KEY` は必須（機能による）。設定がない場合、各関数は ValueError を投げます。
   - 自動ロードはパッケージ import 時にプロジェクトルート（.git または pyproject.toml）を基準に行われます。

---

## 使い方（主要な例）

以下は Python REPL / スクリプトから使う例です。DuckDB 接続を作成して関数を呼び出します。

- ETL（日次 ETL の実行）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコアリング（銘柄別 ai_scores への書き込み）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY は環境変数に設定済みである想定
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- ファクター計算 / 研究用ユーティリティ
  ```python
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  date0 = date(2026, 3, 20)
  mom = calc_momentum(conn, date0)
  vol = calc_volatility(conn, date0)
  val = calc_value(conn, date0)
  ```

---

## 設定（主な環境変数）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合は必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（発注等で必要）
- KABU_API_BASE_URL: kabu ステーションのベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知に使用する場合
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_ENV: environment（development / paper_trading / live）

備考: config モジュールは .env/.env.local を自動読み込みします。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

（主要なファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  # ニュース NLP（銘柄別スコアリング）
    - regime_detector.py           # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            # J-Quants API クライアント（取得・保存）
    - pipeline.py                  # ETL パイプライン / run_daily_etl 等
    - etl.py                       # ETL 再エクスポート（ETLResult）
    - news_collector.py            # RSS ニュース収集
    - calendar_management.py       # 市場カレンダー
    - quality.py                   # データ品質チェック
    - stats.py                     # 統計ユーティリティ（zscore_normalize）
    - audit.py                     # 監査ログ（スキーマ初期化）
  - research/
    - __init__.py
    - factor_research.py           # ファクター計算（momentum/value/volatility）
    - feature_exploration.py       # 将来リターン、IC、統計サマリー等
  - research/*.py
  - その他（execution / monitoring / strategy 等のサブパッケージ想定）

ファイルは機能別に整理されており、DuckDB を中心に SQL + Python のハイブリッド実装で効率よく処理を行います。

---

## 開発・運用上の注意

- ルックアヘッドバイアス回避のため、モジュール内の各関数は内部で `date.today()` を安易に参照しない設計です。バックテストなどでは明示的に target_date を渡してください。
- OpenAI / J-Quants 呼び出しにはリトライやフェイルセーフが組み込まれていますが、API キーやレート制限は運用側で管理してください。
- DuckDB の executemany に関する制約（バージョン差）を考慮して一部実装は空リストチェック等を行っています。DuckDB の互換性・バージョンアップ時は注意してください。
- news_collector では SSRF 対策、XML インジェクション対策（defusedxml）等のセキュリティ考慮がされています。RSS ソースを増やす場合は信頼できるソースを登録してください。

---

もし README に含めたい追加の利用例（kabu ステーション連携、監視ジョブの起動方法、CI/CD での ETL スケジュール例など）があればお知らせください。それに合わせて README を拡張します。