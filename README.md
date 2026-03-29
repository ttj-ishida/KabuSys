# KabuSys

日本株向けのデータプラットフォーム & 自動売買支援ライブラリです。ETL、ニュース収集・NLP、ファクター計算、研究用ユーティリティ、監査ログ、J-Quants / kabuステーション / OpenAI を使った連携機能などを提供します。

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants）、データ品質チェック、特徴量（ファクター）計算、ニュースの NLP スコアリング、マーケットレジーム推定、監査ログ（トレーサビリティ）などを統合したソフトウェアコンポーネント群です。バックテストや運用パイプラインの土台として利用できる設計になっています。

設計方針の主なポイント：
- ルックアヘッドバイアス防止（内部で date.today() を不用意に参照しない等）
- DuckDB を主なデータストアとして使用（軽量かつ高速な分析 DB）
- API 呼び出しは冪等化・リトライ・レート制御を備えた実装
- 品質チェックや監査ログ等で運用の安全性を重視

---

## 機能一覧（主なモジュール）

- kabusys.config
  - 環境変数／.env 読み込み・設定管理（自動ロード機能あり）
- kabusys.data
  - ETL パイプライン（J-Quants からの prices / financials / calendar 取得）
  - J-Quants クライアント（認証・ページネーション・保存関数）
  - カレンダー管理（営業日判定、next/prev trading day、calendar 更新ジョブ）
  - ニュース収集（RSS → raw_news、SSRF 対策・トラッキング除去）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（signal / order_request / executions のテーブル定義・初期化）
  - 統計ユーティリティ（zscore 正規化 等）
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM(OpenAI) でセンチメント化して ai_scores に格納
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュースで市場レジーム判定
- kabusys.research
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: forward returns / IC / ファクターサマリー等
- kabusys.audit / execution / monitoring（監査・実行・監視周りが入る想定）

---

## セットアップ手順

※以下は一般的なセットアップ手順の例です。実行環境（OS / Python バージョン等）に応じて調整してください。

1. リポジトリをクローン
   ```
   git clone <repo_url>
   cd <repo_root>
   ```

2. Python 仮想環境を作成・有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate    # Windows
   ```

3. 必要なパッケージをインストール
   - 本リポジトリには requirements.txt を同梱していない想定なので、最低限必要なパッケージをインストールしてください:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発時には `pip install -e .`（パッケージとしてインストール）を推奨：
     ```
     pip install -e .
     ```

4. 環境変数 (.env) を用意
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可）。
   - 必須環境変数（主要）：
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN: Slack 通知を使う場合のボットトークン
     - SLACK_CHANNEL_ID: Slack 通知先チャンネルID
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
   - 任意／デフォルト：
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単なサンプル）

以下は Python REPL / スクリプトから主要機能を呼び出す例です。必要に応じて import 部分をプロジェクト名に合わせてください。

- DuckDB 接続の作成例（設定の duckdb_path を利用）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（市場カレンダー取得 → prices / financials 保存 → 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # target_date を指定。None の場合は今日が対象
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコア付与（OpenAI APIキーが環境変数 OPENAI_API_KEY に必要）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（OpenAI を使用）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB の初期化（監査用 DuckDB を別ファイルで用意）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # 監査テーブルが作成され、UTC タイムゾーンが設定されます
  ```

- カレンダー関連ユーティリティ
  ```python
  from kabusys.data.calendar_management import (
      is_trading_day,
      next_trading_day,
      prev_trading_day,
      get_trading_days,
      calendar_update_job
  )
  from datetime import date

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  days = get_trading_days(conn, date(2026,1,1), date(2026,1,31))
  ```

- ニュース RSS 取得（news_collector.fetch_rss）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

注: AI 関連の関数（score_news, score_regime）は OpenAI API を利用します。API 呼び出しの料金と利用制限に注意してください。API エラー時はフェイルセーフ（ゼロスコア等）で継続する設計になっていますが、キー未設定の場合は ValueError を投げます。

---

## よく使うモジュールと API（一覧）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env, settings.log_level など
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl, ETLResult
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.data.news_collector
  - fetch_rss, preprocess_text, 他ユーティリティ
- kabusys.ai.news_nlp.score_news
- kabusys.ai.regime_detector.score_regime
- kabusys.research.factor_research
  - calc_momentum, calc_volatility, calc_value
- kabusys.research.feature_exploration
  - calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.audit
  - init_audit_schema, init_audit_db

---

## 環境変数まとめ（主要）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
- OPENAI_API_KEY (AI 機能利用時 必須): OpenAI API キー
- SLACK_BOT_TOKEN (必要に応じて)
- SLACK_CHANNEL_ID (必要に応じて)
- KABU_API_PASSWORD (kabuステーション API 用)
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みを無効化

---

## ディレクトリ構成

以下はパッケージ内の主要ファイル / モジュールの概要（src/kabusys 配下）です：

- __init__.py
  - パッケージのバージョンと公開モジュール定義
- config.py
  - 環境変数・.env 読み込み、設定取得用 Settings クラス
- ai/
  - news_nlp.py: ニュースを LLM で評価して ai_scores に書き込む
  - regime_detector.py: ETF MA とマクロニュースを合成して市場レジーム判定
- data/
  - __init__.py
  - pipeline.py: ETL パイプラインのエントリポイント（run_daily_etl 等）
  - jquants_client.py: J-Quants API クライアント（取得・保存）
  - calendar_management.py: 市場カレンダー管理、営業日判定、calendar_update_job
  - news_collector.py: RSS 取得・前処理・raw_news 保存補助
  - quality.py: データ品質チェック
  - stats.py: zscore 正規化等の統計ユーティリティ
  - audit.py: 監査ログテーブル定義と初期化
  - etl.py: ETLResult の再公開
- research/
  - __init__.py
  - factor_research.py: Momentum / Value / Volatility 等の計算
  - feature_exploration.py: forward returns / IC / summary 等
- research/feature_exploration.py, research/factor_research.py（上記）

（上記に挙げたモジュールは主要なものです。細かなサブモジュールやユーティリティも多数含まれます）

---

## 運用時の注意 / ベストプラクティス

- 環境（KABUSYS_ENV）を正しく設定して、実運用（live）と検証（paper_trading / development）を区別してください。
- DuckDB ファイルは定期的にバックアップ・スナップショットを取得してください。
- OpenAI や J-Quants の API キーは適切に管理し、ログやリポジトリにコミットしないでください。
- ETL は夜間バッチとしてスケジュールし、run_daily_etl の戻り値（ETLResult）で品質問題の有無を監視してください。
- ニュース収集時の外部アクセス（RSS）の安全性対策（SSRF、gzip/Bomb 等）は組み込まれていますが、信頼できる環境で実行してください。

---

必要な追加情報（インストール手順の詳細、CI 設定例、デプロイ手順、サンプル SQL スキーマ、.env.example ファイル等）を希望される場合は、どの項目を優先して書けばよいか教えてください。