# KabuSys

KabuSys は日本株のデータプラットフォームとリサーチ／自動売買基盤を想定した Python パッケージです。J-Quants や kabuステーション、OpenAI を利用した ETL、データ品質チェック、特徴量（ファクター）計算、ニュース NLP、監査ログ（トレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

主な目的は日本株を対象としたデータ収集（J-Quants 等）、品質チェック、ファクター計算、ニュースからのセンチメント評価、そして売買シグナル／発注の監査トレーサビリティを提供することです。  
設計上の方針として、バックテストや統計解析でのルックアヘッドバイアスを避けるため、関数内部で安易に `date.today()` / `datetime.today()` を参照しない実装が意識されています。

主要コンポーネント
- data: ETL（J-Quants クライアント、ニュース収集、カレンダー管理、品質チェック、監査テーブル初期化など）
- research: ファクター計算・特徴量探索ユーティリティ
- ai: ニュースの NLP スコアリング、マーケットレジーム判定（OpenAI 利用）
- config: 環境変数 / .env 読み込み・設定管理

---

## 主な機能一覧

- J-Quants API クライアント（差分取得、ページネーション、トークンリフレッシュ、保存関数）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
- ETL パイプライン（差分取得、backfill、品質チェック）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- データ品質チェック
  - 欠損・重複・スパイク・日付不整合チェック（run_all_checks）
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- ニュース収集（RSS）と保存（raw_news / news_symbols）
  - fetch_rss / preprocess_text（SSRF 対策、gzip 制御、URL 正規化）
- ニュース NLP（OpenAI）
  - score_news: 銘柄ごとの ai_score を ai_scores テーブルへ書き込み
  - news NLP はバッチ処理・リトライ・レスポンス検証あり
- マーケットレジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
  - score_regime: market_regime テーブルへ書き込み
- 研究用ユーティリティ
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / zscore_normalize
- 監査ログ（トレーサビリティ）初期化
  - init_audit_schema / init_audit_db（DuckDB に監査用テーブルを作成）

---

## セットアップ手順

前提
- Python 3.10 以上
- ネットワーク接続（J-Quants / OpenAI など外部 API へアクセスする場合）

1. リポジトリをチェックアウトし仮想環境を作成
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージをインストール
   - 必要なパッケージ（例）:
     - duckdb
     - openai
     - defusedxml
   - pip でインストール:
     - pip install -e .[all]  または  pip install duckdb openai defusedxml
     （プロジェクトの pyproject.toml／setup がある場合は -e . が便利です）

3. 環境変数の設定
   - .env / .env.local をプロジェクトルートに置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN  （J-Quants のリフレッシュトークン）
     - KABU_API_PASSWORD      （kabuステーション API のパスワード）
     - SLACK_BOT_TOKEN        （Slack 通知に使用）
     - SLACK_CHANNEL_ID       （Slack チャンネルID）
     - OPENAI_API_KEY         （AI 機能を使う場合、score_news/score_regime など）
   - 任意 / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) （デフォルト development）
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) （デフォルト INFO）
     - KABU_API_BASE_URL （デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH （デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH （デフォルト: data/monitoring.db）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. データベース初期化（監査用など）
   - 監査ログ専用 DuckDB を作成する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - ETL 用の DuckDB（settings.duckdb_path を利用）:
     ```python
     from kabusys.config import settings
     import duckdb
     conn = duckdb.connect(str(settings.duckdb_path))
     ```

---

## 使い方（主要 API と実行例）

基本的には DuckDB の接続オブジェクト（duckdb.connect() の戻り）を渡して各関数を使用します。

- 設定の読み取り
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

- ETL（日次パイプライン）実行
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（OpenAI を使って銘柄ごとのスコアを ai_scores に書き込む）
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
  print("written:", written)
  ```

- レジーム判定（MA200 とマクロ記事を合成）
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（研究用）
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect(str(settings.duckdb_path))
  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  ```

- RSS 取得（ニュース収集）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

- データ品質チェック例
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

注意点
- AI 関連（score_news / score_regime）は OpenAI API の利用が前提です。API キーは引数に渡すか環境変数 OPENAI_API_KEY を設定してください。
- 多くの関数は DuckDB 内のテーブル（raw_prices, raw_financials, raw_news, ai_scores, market_regime, market_calendar など）を前提としています。ETL を先に実行してデータを用意してください。
- ETL / API 呼び出しは外部サービスへアクセスするため、ネットワークや API レート制限に留意してください。

---

## ディレクトリ構成（主要ファイル）

リポジトリは src/kabusys 以下に実装がまとまっています。主要ファイルを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                    -- 環境変数 / .env 読み込み・Settings
  - ai/
    - __init__.py
    - news_nlp.py                 -- ニュースセンチメント（score_news）
    - regime_detector.py          -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py           -- J-Quants API クライアント + 保存関数
    - pipeline.py                 -- ETL パイプライン（run_daily_etl 等）
    - etl.py                      -- ETLResult の再エクスポート
    - news_collector.py           -- RSS 収集（fetch_rss 等）
    - calendar_management.py      -- 市場カレンダー管理（is_trading_day 等）
    - stats.py                    -- 共通統計関数（zscore_normalize）
    - quality.py                  -- データ品質チェック
    - audit.py                    -- 監査ログ DDL / 初期化（init_audit_db / init_audit_schema）
    - pipeline.py                 -- ETL 実行ロジック
  - research/
    - __init__.py
    - factor_research.py          -- calc_momentum / calc_volatility / calc_value
    - feature_exploration.py      -- calc_forward_returns / calc_ic / factor_summary / rank

---

## 実運用上の注意 và ベストプラクティス

- 環境変数は機密情報を含むため .env を管理する際は適切に保護（Git 管理除外）してください。
- J-Quants のレート制限（120 req/min）を守るため、jquants_client の内部レートリミッタが実装されていますが、運用設計でも過負荷にならないよう注意してください。
- OpenAI の呼び出しはコスト・レート制限の影響を受けます。バッチサイズやリトライ設定はコード内の定数で調整可能です。
- DuckDB のファイル配置は settings.duckdb_path で管理します。クラウド運用時は永続ストレージの取り扱いに注意してください。
- ETL と品質チェックは別プロセス／ジョブに分け、監査ログを必ず保管する運用が望ましいです。

---

この README はコードベースの主要機能と使い方をまとめたものです。詳細な API 仕様や運用手順、CI/CD、モニタリング連携（Slack 通知等）はプロジェクトの運用方針に応じて別途ドキュメント化してください。質問やサンプル追加の希望があればお知らせください。