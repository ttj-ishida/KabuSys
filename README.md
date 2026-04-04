# KabuSys

日本株向けの自動売買／データ基盤ユーティリティ集です。  
DuckDB を用いたデータパイプライン、J-Quants API クライアント、ニュース NLU / LLM を用いたスコアリング、研究用ファクター計算、監査（トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、以下を目的とした Python パッケージです。

- J-Quants API からの差分 ETL（株価・財務・市場カレンダー）
- ニュース収集と LLM（OpenAI）を用いた銘柄 / マクロセンチメントのスコアリング
- ファクター計算・特徴量探索（研究用途）
- 監査ログ（signal → order → execution のトレーサビリティ）テーブル初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）

設計上の特徴:
- ルックアヘッドバイアスを回避するため、内部で date.today() を不用意に参照しない実装方針
- DuckDB をメインのストレージとして利用（軽量で SQL ベース）
- API 呼び出しに対するリトライ／レート制御・フェイルセーフを備えた実装
- 環境変数 / .env による設定管理（自動ロード機能あり）

---

## 主な機能一覧

- 環境設定管理: kabusys.config.Settings（.env 自動読み込み、保護キー対応）
- J-Quants クライアント: kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - トークン自動リフレッシュ、レートリミット、リトライ実装
- ETL パイプライン: kabusys.data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
  - ETLResult による実行結果集約、品質チェック呼び出し
- データ品質チェック: kabusys.data.quality
  - 欠損 / スパイク / 重複 / 日付不整合 の検出
- ニュース収集: kabusys.data.news_collector
  - RSS 取得、前処理、raw_news への保存（冪等）
  - SSRF 対策、XML セキュリティ対策（defusedxml）
- AI（LLM）関連:
  - kabusys.ai.news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores に書き込み
  - kabusys.ai.regime_detector.score_regime: ETF（1321）MA とマクロニュースを合成して市場レジームを market_regime に書き込み
  - OpenAI 呼び出しは JSON Mode を利用し、レスポンスパース・バリデーションを行う
- 研究ユーティリティ: kabusys.research
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（kabusys.data.stats）によるクロスセクション正規化
- 監査ログ初期化: kabusys.data.audit.init_audit_db / init_audit_schema
  - signal_events / order_requests / executions テーブルとインデックスを作成

---

## セットアップ手順

1. リポジトリをクローン（例）
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. Python 仮想環境作成（推奨）
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   - 最低限必要なライブラリ:
     - duckdb
     - openai
     - defusedxml
   - 開発環境では pip install -e .（プロジェクトに setup/pyproject がある前提）
   例:
   ```
   pip install duckdb openai defusedxml
   pip install -e .
   ```

4. 環境変数 / .env の設定
   - プロジェクトは自動的にプロジェクトルート（.git または pyproject.toml）を探して `.env` / `.env.local` を読み込みます。
     優先順位: OS 環境変数 > .env.local > .env
   - 自動読み込みを無効化したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数（代表的なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に必要）
     - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH: デフォルト "data/monitoring.db"
     - KABUSYS_ENV: one of ("development", "paper_trading", "live")（デフォルト development）
     - LOG_LEVEL: one of ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト INFO）

   .env のサンプルは .env.example を参照してください（プロジェクトに含めてください）。

5. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（基本例）

以下は Python REPL / スクリプトから呼び出す簡単な例です。事前に必要な環境変数（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）を設定してください。

- DuckDB 接続の作成（デフォルト path は settings.duckdb_path）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（市場カレンダー・株価・財務を差分取得）:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（LLM）で銘柄スコアを生成:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY が環境変数にある場合、api_key 引数は不要
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written {n_written} scores")
  ```

- 市場レジーム判定（ETF 1321 の MA とマクロニュースの合成）:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化:
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブルが作成される
  ```

- ニュース RSS を取得（単体）:
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles[:5]:
      print(a["datetime"], a["title"])
  ```

注意点 / ヒント:
- OpenAI API 呼び出しはレート制御・リトライを備えていますが、API キーやコストに注意して実行してください。
- テスト時は kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api をモックして LLM 呼び出しを差し替えられます。
- ETL の run_daily_etl は個々のステップでエラーハンドリングされ、ETLResult にエラー情報や品質チェック結果を保持します。

---

## 設定（settings）について

kabusys.config.Settings 経由で設定を参照できます。主なプロパティ:

- jquants_refresh_token  (JQUANTS_REFRESH_TOKEN)
- kabu_api_password      (KABU_API_PASSWORD)
- kabu_api_base_url      (KABU_API_BASE_URL, default: http://localhost:18080/kabusapi)
- line_channel_access_token, line_user_id
- duckdb_path (デフォルト data/kabusys.duckdb)
- sqlite_path (監視用 DB, デフォルト data/monitoring.db)
- pid_file_path / kill_flag_path / 閾値系 CPU/MEM/DISK
- env / log_level / is_live / is_paper / is_dev

.env の取り込みは自動で .env → .env.local の順で行います（OS 環境変数を上書きしない）。自動読み込みを抑制するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成（概要）

以下は主要モジュール／ファイルの一覧（src/kabusys 以下）です。実装は各ファイルの docstring を参照してください。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — 銘柄別ニュースセンチメント（LLM）
    - regime_detector.py           — マクロ + ETF MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント & DuckDB 保存
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETLResult の再エクスポート
    - news_collector.py            — RSS 収集・前処理・保存
    - calendar_management.py       — 市場カレンダー判定・更新ジョブ
    - quality.py                   — データ品質チェック
    - stats.py                     — zscore_normalize 等汎用統計
    - audit.py                     — 監査ログ（テーブル DDL / 初期化）
  - research/
    - __init__.py
    - factor_research.py           — momentum / value / volatility 等
    - feature_exploration.py       — forward returns, IC, summary, rank
  - execution/ (インタフェース層、発注処理に関するモジュールを想定)
  - monitoring/ (監視・プロセス管理ユーティリティを想定)
  - その他ユーティリティ群

---

## 開発・テスト時の注意

- LLM / 外部 API 呼び出しは外部依存なので、ユニットテストでは HTTP / OpenAI 呼び出しをモックしてください。内部では _call_openai_api の差し替えが想定されています。
- DuckDB を使うため、テストでは ":memory:" を使ってインメモリ DB を初期化できます（例: init_audit_db(":memory:")）。
- .env 読み込みロジックはプロジェクトルートを __file__ の親から探索するため、テスト実行時のカレントディレクトリに依存しません。自動ロードを無効にする環境変数も用意しています。

---

## ライセンス / 貢献

この README の末尾にプロジェクトのライセンスや貢献ガイドを記載してください（本サンプルでは省略）。

---

この README はコードベースの主要機能と使い方の概要をまとめたものです。各モジュールのより詳しい仕様やパラメータは、該当するソースファイルの docstring を参照してください。