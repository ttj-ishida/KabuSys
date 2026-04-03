# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、ファクター計算、監査ログ（発注→約定トレーサビリティ）など、研究・運用のためのユーティリティを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要機能を提供します。

- J-Quants API を利用した株価・財務・マーケットカレンダーの差分 ETL（rate limiting・リトライ・冪等保存対応）
- RSS ベースのニュース収集と前処理（SSRF/トラッキング除去対策、冪等保存）
- OpenAI（gpt-4o-mini）を用いたニュースのセンチメント評価（銘柄別 ai_scores）およびマクロセンチメントを使った市場レジーム判定
- リサーチ用ファクター計算（モメンタム・ボラティリティ・バリュー等）と統計ユーティリティ（Zスコア等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）と初期化ユーティリティ
- 設定管理（環境変数 / .env 自動ロード）

設計方針として、バックテストでの look-ahead バイアスを避けるために日付参照の扱いに注意しており、外部 API 呼び出しは明示的に制御・フェイルセーフ化されています。

---

## 機能一覧（モジュール別ハイレベル）

- kabusys.config
  - 環境変数 / .env 自動ロード、必須設定の取得
- kabusys.data.jquants_client
  - J-Quants API クライアント（取得 / 保存 / ページネーション / 認証リフレッシュ）
- kabusys.data.pipeline
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl 等の ETL パイプライン
- kabusys.data.news_collector
  - RSS 取得、前処理、raw_news テーブルへの保存ロジック（SSRF 対策等）
- kabusys.ai.news_nlp
  - 銘柄別ニュースの LLM スコアリング（ai_scores への書き込み）
- kabusys.ai.regime_detector
  - ETF（1321）200日MA 乖離とマクロニュースセンチメントを合成した市場レジーム判定
- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary 等
- kabusys.data.quality
  - データ品質チェック（欠損・重複・スパイク・日付整合性）
- kabusys.data.audit
  - 監査スキーマ定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
- kabusys.data.calendar_management
  - 市場カレンダー管理・営業日判定ユーティリティ

---

## セットアップ手順

以下はローカルで利用するための最小手順例です。

1. リポジトリをクローン

   ```
   git clone <リポジトリURL>
   cd <repo>
   ```

2. Python 仮想環境作成（推奨）

   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール

   主要な依存（少なくとも動作に必要なもの）:
   - duckdb
   - openai
   - defusedxml

   例:

   ```
   pip install duckdb openai defusedxml
   ```

   （プロジェクトに pyproject.toml / requirements.txt があればそれを利用してください）

4. 環境変数の設定

   必須の環境変数:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 実行に必須）

   AI 関連を使う場合:
   - OPENAI_API_KEY : OpenAI API キー

   その他（オプション・デフォルト有り）:
   - KABU_API_PASSWORD
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
   - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
   - LOG_LEVEL: DEBUG | INFO | ...

   .env ファイルをプロジェクトルートに配置すると自動でロードされます（.git もしくは pyproject.toml を起点にプロジェクトルートを探索）。
   自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   推奨: .env.example（存在する場合）を参考に .env を作成してください。

5. データディレクトリ作成（必要に応じて）

   ```
   mkdir -p data
   ```

---

## 使い方（例）

以下は代表的な利用例（Python REPL / スクリプト）です。

- DuckDB 接続を作る（設定からパスを取得）

  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（J-Quants トークンは settings で取得）

  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- 株価差分 ETL（個別ジョブ）

  ```python
  from kabusys.data.pipeline import run_prices_etl
  from datetime import date

  fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
  print(f"fetched={fetched}, saved={saved}")
  ```

- ニュース NLP スコアリング（前日 15:00 JST ～ 当日 08:30 JST のウィンドウを対象）

  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  count = score_news(conn, target_date=date(2026,3,20))
  print(f"scored {count} codes")
  ```

- 市場レジーム判定

  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ DB 初期化（監査専用 DB）

  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- ファクター計算・解析

  ```python
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

  m = calc_momentum(conn, date(2026,3,20))
  fwd = calc_forward_returns(conn, date(2026,3,20))
  ic = calc_ic(m, fwd, "mom_1m", "fwd_1d")
  print(ic)
  ```

ログレベルや env によって挙動が変わるため `settings.log_level` / `settings.env` を確認してください。`settings.is_live` でライブモード判定ができます。

---

## 注意点・運用上のヒント

- API キーやシークレットは .env 或いは環境変数で安全に管理してください。`.env` を誤ってコミットしないよう .gitignore に追加してください。
- OpenAI 呼び出しは再実行や失敗時のフォールバックを実装していますが、API 利用料金が発生します。テスト時はモック化することを推奨します（コード内でモック対象の private 関数が明記されています）。
- DuckDB に対する executemany の空リスト渡しは一部バージョンでエラーになることがあるため、コード側で空チェックを行っています。独自にスクリプトを書く際も留意してください。
- news_collector では SSRF・XML 攻撃対策を行っていますが、RSS ソースの信頼性の確認や取得時のタイムアウト設定は適切に行ってください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
  - パッケージ公開 API の定義（data, strategy, execution, monitoring などを __all__ に含める）
- config.py
  - 環境変数管理、.env 自動ロード、settings オブジェクト
- ai/
  - __init__.py
  - news_nlp.py : 銘柄別ニュースの LLM スコアリング（score_news）
  - regime_detector.py : マクロセンチメント + ETF MA を合成した市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py : J-Quants API クライアント + 保存ロジック
  - pipeline.py : ETL パイプライン（run_daily_etl など）、ETLResult
  - etl.py : ETLResult の再エクスポート
  - news_collector.py : RSS 取得・前処理・raw_news 保存
  - calendar_management.py : market_calendar と営業日判定・calendar_update_job
  - stats.py : zscore_normalize 等の統計ユーティリティ
  - quality.py : データ品質チェック
  - audit.py : 監査ログスキーマと初期化ユーティリティ（init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py : Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py : 将来リターン計算、IC、統計サマリー
- research/*（補助ユーティリティ）
- その他（strategy, execution, monitoring）についてはパッケージの __all__ に含まれており、将来の戦略・約定・監視実装と連携することを想定しています。

---

## 開発・テスト時の便利な環境変数

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - パッケージインポート時の .env 自動ロードを無効化（ユニットテスト等で使用）
- KABUSYS_ENV=development|paper_trading|live
  - 動作モード切替（settings.is_live / is_paper / is_dev の判定に使われます）

---

以上が本リポジトリの README です。  
実際の運用・デプロイ時は、機密情報の取り扱い（API キー・トークン）、DB のバックアップ・マイグレーション、監査ログの保全などにご注意ください。必要であればインストール用の pyproject.toml / requirements.txt、CI 設定、運用手順（runbook）を別途作成することを推奨します。