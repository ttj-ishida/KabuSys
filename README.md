# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、ファクター計算、監査ログ（約定トレーサビリティ）、市場カレンダー管理などの機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的で設計された Python パッケージです。

- J-Quants API から株価/財務/カレンダー等を差分取得して DuckDB に保存する ETL。
- RSS ニュース収集と OpenAI（gpt-4o-mini 等）を用いた銘柄別ニュースセンチメントの評価（ai_scores）。
- ETF（1321）を用いた市場レジーム判定（MA200 とマクロニュースの合成スコア）。
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析ユーティリティ。
- データ品質チェック（欠損、スパイク、重複、日付整合性）。
- 監査ログテーブル（signal_events / order_requests / executions）と初期化ユーティリティ。
- 市場カレンダー管理（営業日判定、next/prev_trading_day など）。

設計上の重要点:
- ルックアヘッドバイアスの防止（内部で date.today() を直接参照しない・ETL/スコアリングで対象日を明示）。
- DuckDB を用いたローカル分析環境との親和性。
- API 呼び出しに対する堅牢なリトライ/バックオフやレート制御（J-Quants 側）。
- 冪等性を意識した DB 書き込み（ON CONFLICT / DELETE→INSERT 等）。

---

## 主な機能一覧

- data
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, get_id_token
  - 保存関数: save_daily_quotes / save_financial_statements / save_market_calendar
  - ニュース収集: fetch_rss, ニュース前処理、SSRF 対策
  - カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - 品質チェック: run_all_checks（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化: init_audit_schema / init_audit_db
  - 統計ユーティリティ: zscore_normalize

- ai
  - score_news: 銘柄毎ニュースセンチメントの算出と ai_scores への保存（OpenAI 使用）
  - score_regime: ETF（1321）MA200 乖離とマクロニュース（LLM）を合成して market_regime に保存

- research
  - ファクター計算: calc_momentum / calc_value / calc_volatility
  - 特徴量解析: calc_forward_returns / calc_ic / factor_summary / rank

- config
  - Settings: 環境変数から設定を読み込み、.env 自動ロードをサポート（.env / .env.local）

---

## セットアップ手順

以下は開発環境での最低限のセットアップ例です。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要なパッケージをインストール
   現在のコードベースで想定される外部依存（例）:
   - duckdb
   - openai
   - defusedxml

   インストール例:
   ```
   pip install duckdb openai defusedxml
   ```

   （プロジェクトが packaging されている場合は `pip install -e .` や requirements.txt を使うことを推奨）

4. 環境変数を設定
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）が検出されると、
   自動で `.env` → `.env.local` の順に環境変数がロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

   主要な環境変数（必須／任意）:
   - JQUANTS_REFRESH_TOKEN (必須: jquants のリフレッシュトークン)
   - OPENAI_API_KEY (AI 機能を使う場合は必須)
   - KABU_API_PASSWORD (kabuステーション API を使う場合)
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (通知連携など)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)

   .env の例（最小）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   ```

5. データディレクトリの準備（必要に応じて）
   デフォルトで `data/` 配下に DuckDB や PID ファイルが作られます。必要なら作成しておいてください。
   ```
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下は代表的な API の使い方の例です（DuckDB を使用）。

- DuckDB 接続を作成して ETL を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI API キーが必要）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote {n_written} ai_scores")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

注意点:
- AI 関連関数（score_news, score_regime）は OPENAI_API_KEY が環境変数または api_key 引数で指定されている必要があります。
- J-Quants へのアクセスは JQUANTS_REFRESH_TOKEN を設定しておく必要があります（get_id_token で使用）。
- ETL / API 呼び出しはネットワークや API レート制限の影響を受けます。ログ出力やリトライ設計に従い運用してください。

---

## 設定 (.env と自動ロード)

- パッケージは実行時にプロジェクトルート（.git または pyproject.toml を起点）を探索し、`.env` と `.env.local` を自動で読み込みます（OS 環境変数を上書きしないよう保護されます）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `config.Settings` クラスを通じて構成値にアクセスできます（例: `from kabusys.config import settings; settings.jquants_refresh_token`）。
- `config._require()` は必須環境変数が未設定の場合にエラーを投げます。README に示した主要な環境変数は設定してください。

---

## ディレクトリ構成（主なファイル）

以下はコードベースの主要モジュール構成（src/kabusys）です:

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py (ETLResult 再エクスポート)
    - news_collector.py
    - calendar_management.py
    - stats.py
    - quality.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research パッケージはデータ分析・ファクター研究用ユーティリティを提供

（ソースは `src/kabusys` 配下に配置されています）

---

## ログ・監視・運用上の注意

- 設定 `settings.log_level` でログレベルを制御できます（環境変数 `LOG_LEVEL`）。
- デフォルトではいくつかの閾値（CPU/MEM/DISK）や pid/kill flag 用のファイルパスが `config.Settings` に定義されています。
- J-Quants クライアントは 120 req/min のレート制限を守るように設計されています。大量のページネーションやバッチ実行時は注意してください。
- AI 呼び出し（OpenAI）はレスポンスのバリデーションやリトライ処理を行いますが、API 制限や料金にも配慮して運用してください。

---

## 貢献・拡張

- 新しいニュースソース追加、研究用指標の追加、注文執行層の実装などの拡張が想定されています。
- テスト時には API 呼び出し部分（OpenAI / ネットワーク）をモックすることを推奨します（コード中にモックポイントが明示されています）。

---

必要であれば、README にサンプル .env.example、より詳しい API リファレンス（関数引数・戻り値の詳細）、運用手順（cron / systemd の設定例）などを追加します。どの情報を優先的に追加しますか?