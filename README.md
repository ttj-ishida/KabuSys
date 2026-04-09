# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（約定トレース）などを提供します。

バージョン: 0.1.0

---

## 主要ポイント（プロジェクト概要）

- DuckDB を中心としたデータ格納・分析基盤（prices_daily、raw_news、raw_financials、market_calendar 等）。
- J-Quants API からの差分取得・保存（レート制御・リトライ・トークン自動リフレッシュ対応）。
- ニュース収集（RSS）とニュースの前処理、OpenAI を用いた銘柄別センチメント（ai_scores）集計。
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成）。
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）と統計ユーティリティ（Zスコアなど）。
- データ品質チェックモジュール（欠損・重複・スパイク・日付不整合）。
- 監査ログ（signal_events, order_requests, executions）スキーマ初期化ユーティリティ。
- .env または環境変数から設定を読み込む自動ロード機能（必要に応じて無効化可能）。

---

## 機能一覧

- データ取得・保存
  - J-Quants: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への冪等保存: save_daily_quotes / save_financial_statements / save_market_calendar
- ETL
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - run_daily_etl: 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - ETL 結果を表す ETLResult
- ニュース
  - RSS 取得と前処理（SSRF 対策、トラッキング除去、size cap）
  - score_news(conn, target_date, api_key=None): OpenAI による銘柄別ニュースセンチメント集約
- AI（市場レジーム）
  - score_regime(conn, target_date, api_key=None): MA200 と LLM のマクロセンチメントを合成して市場レジームを算出・保存
- 研究（research）
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize
- データ品質
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job（J-Quants からの差分更新）
- 監査ログ（audit）
  - init_audit_schema / init_audit_db（監査用 DuckDB 初期化）
- 設定管理
  - kabusys.config.settings: 環境変数をラップして提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等）

---

## セットアップ手順（開発マシンでの例）

前提: Python 3.10+ を想定（型アノテーションに union 表記などを使用）。

1. リポジトリをクローンし、仮想環境を作成・有効化:

   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール（プロジェクトに requirements.txt がある想定。無い場合は主要依存を一覧）:

   例: requirements.txt がない場合の最低依存
   ```bash
   pip install duckdb openai defusedxml
   ```

   またはパッケージを編集してローカルインストール:
   ```bash
   pip install -e .
   ```

3. 環境変数 / .env を準備

   - 自動的にプロジェクトルートの `.env` / `.env.local` がロードされます（OS 環境変数が優先）。
   - 自動ロードを無効化したい場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

   推奨設定（.env 例）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=your_password
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

   - 注意: 必須項目は Settings のプロパティ参照時にチェックされます（例: JQUANTS_REFRESH_TOKEN が未設定だと ValueError）。

4. データディレクトリを作成（デフォルトパスを使用する場合）:
   ```bash
   mkdir -p data
   ```

---

## 使い方（主な API/ユーティリティの例）

以下は Python REPL / スクリプトでの利用例です。

- 設定と DuckDB 接続

  ```python
  import duckdb
  from kabusys.config import settings

  db_path = str(settings.duckdb_path)  # settings.duckdb_path は Path
  conn = duckdb.connect(db_path)
  ```

- 日次 ETL を実行（target_date を指定することでルックアヘッドバイアスを防止）:

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI API キーは env または api_key 引数で指定）:

  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定:

  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査専用の DB を作成）:

  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/monitoring_audit.duckdb")
  ```

- 研究用ファクター計算:

  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  ```

- データ品質チェックの実行:

  ```python
  from kabusys.data.quality import run_all_checks

  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

- RSS 取得（news_collector のユーティリティ）:

  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  ```

注意点:
- OpenAI 呼び出しは gpt-4o-mini を想定し、JSON mode を利用して厳密な JSON を期待しています。API 応答が不正な場合はフェイルセーフでスコアを 0 にする等の扱いが組まれています。
- ETL / AI 処理は target_date を外部引数で与えており、内部で date.today() を参照しない設計（バックテストでのルックアヘッド防止）。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須：J-Quants API を使う場合）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector が必要とする）
- KABU_API_PASSWORD: kabuステーション API 用パスワード
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG" | "INFO" | ...)
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_FILL_MODE: Paper Trading の Fill 動作 ("instant"|"partial"|"never"|"reject")
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

settings モジュールからはこれらを便利に参照できます:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

---

## ディレクトリ構成（主要ファイル）

src/kabusys 以下の主要モジュール：

- kabusys/
  - __init__.py
  - config.py                -- 環境変数 / .env 読み込み
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュースセンチメント（銘柄別）
    - regime_detector.py     -- 市場レジーム判定（MA200 + マクロ NLT）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（取得・保存）
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - etl.py                 -- ETL 公開インターフェース（ETLResult 再エクスポート）
    - quality.py             -- データ品質チェック
    - stats.py               -- 統計ユーティリティ（zscore_normalize）
    - calendar_management.py -- 市場カレンダー管理（is_trading_day 等）
    - news_collector.py      -- RSS 収集・前処理
    - audit.py               -- 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py     -- calc_momentum / calc_value / calc_volatility
    - feature_exploration.py -- calc_forward_returns / calc_ic / factor_summary / rank
  - research/... (その他)

（上記は抜粋です。詳細はコードツリーを参照してください）

---

## 実運用上の注意 / ベストプラクティス

- 機密情報（API キー等）は .env や CI のシークレットに安全に保管してください。リポジトリに含めないでください。
- OpenAI・J-Quants の API レートや料金に注意してください。テスト環境では paper_trading を使い、PAPER_FILL_MODE を設定して模擬約定を制御してください。
- ETL の実行は cron やスケジューラで夜間に行い、run_daily_etl の戻り値（ETLResult）を監視・ログ保管してください。
- DuckDB のファイルはバックアップや権限管理に注意してください（運用環境でのロック・同時接続の扱い等）。
- テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用すると .env の自動読み込みを抑えられます。

---

## 参考・拡張ポイント

- CLI やデーモンラッパー（ETL定期実行、監視、発注実行など）の実装はこのライブラリをベースに追加してください。
- 監査ログ（audit）スキーマは初期化済みの DuckDB 接続へ追加可能です（init_audit_schema / init_audit_db）。
- 研究モジュールは pandas 等に依存せずスタンドアローンで動くため、外部可視化・解析ツールにデータを吐き出して使うのがおすすめです。

---

必要に応じて README を補足（例: requirements.txt、CI 設定、デプロイ手順、実行サンプルスクリプト等）します。どの部分を詳しく書きたいか教えてください。