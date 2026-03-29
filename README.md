# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants 経由）→ データ品質チェック → 特徴量・ファクター計算 → ニュースNLP / レジーム判定 → 監査ログ（発注トレーサビリティ）を含む一連の基盤機能を提供します。

主な設計方針：
- ルックアヘッドバイアス防止（内部で date.today() を不用意に参照しないなど）
- DuckDB をデータレイヤ（ローカル分析用）に利用
- API 呼び出しに対してリトライ / レート制御 / フェイルセーフを実装
- 冪等性と監査トレーサビリティを重視

---

## 機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック（settings オブジェクト）
- データ取得（J-Quants クライアント）
  - 株価日足（OHLCV）、財務データ、上場情報、マーケットカレンダー取得（ページネーション・認証管理・リトライ）
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新・バックフィル対応
  - ETL 実行結果を ETLResult で返却
- データ品質チェック
  - 欠損データ、重複、スパイク（前日比）、将来日付／非営業日データ検出
  - QualityIssue による詳細報告
- ニュース収集 / 前処理
  - RSS フィード取得（SSRF 対策、サイズ制限、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存（記事ID は正規化 URL のハッシュ）
- ニュース NLP（OpenAI を利用）
  - 銘柄ごとにニュースを集約し LLM でセンチメントを算出して ai_scores に格納（バッチ処理・リトライ）
  - レスポンスのバリデーションとスコアクリッピング
- 市場レジーム判定
  - ETF 1321 の MA200 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次で bull/neutral/bear を判定
  - market_regime へ冪等書き込み
- 研究（research）
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン算出、IC（Spearman）計算、ファクターサマリ、Z-score 正規化ユーティリティ
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査スキーマを初期化・管理
  - 監査 DB 初期化ユーティリティ（init_audit_db、init_audit_schema）

---

## 要件（推奨）

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai（OpenAI SDK）
  - defusedxml
  - （ネットワーク I/O のため標準ライブラリの urllib 等を使用）

※ 実際のインストール要件はプロジェクトの pyproject.toml / requirements.txt を参照してください（本コードスニペットには manifest が含まれていません）。

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成してアクティベート（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. インストール（開発モード）
   - pyproject.toml / setup.py がある場合:
     ```bash
     pip install -e .
     ```
   - 必要パッケージを個別にインストールする場合:
     ```bash
     pip install duckdb openai defusedxml
     ```

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動的にロードされます（デフォルトで OS 環境 > .env.local > .env の順で優先）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（主にテスト用）。

   代表的な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabu API パスワード（必須）
   - KABU_API_BASE_URL : kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
   - OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector などで使用）
   - DUCKDB_PATH : duckdb ファイルのパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH : sqlite path（監視等で使用。デフォルト: data/monitoring.db）
   - KABUSYS_ENV : 開発環境（development / paper_trading / live、デフォルト: development）
   - LOG_LEVEL : ログレベル（DEBUG/INFO/...、デフォルト: INFO）

   .env の例（簡易）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   OPENAI_API_KEY=sk-xxxx...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABU_API_PASSWORD=your_kabu_password
   ```

---

## 使い方（基本的な例）

以下は Python から各主要機能を呼び出す例です。

- DuckDB 接続を作って日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（OpenAI が必要）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # 環境変数 OPENAI_API_KEY が設定されていれば api_key 引数は省略可
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {n_written}")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマ初期化（監査専用 DB を生成）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- RSS フィード取得（news_collector のユーティリティ）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  url = DEFAULT_RSS_SOURCES["yahoo_finance"]
  articles = fetch_rss(url=url, source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

注意点：
- OpenAI を使う処理（news_nlp, regime_detector）は API キーが必要です。api_key 引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- J-Quants API を利用する ETL は JQUANTS_REFRESH_TOKEN が必須です（settings.jquants_refresh_token により取得）。

---

## よく使うモジュール（API サマリ）

- kabusys.config
  - settings: 環境変数読み込み・検証を行うシングルトン
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.data.news_collector
  - fetch_rss, preprocess_text, _make_article_id (ユーティリティ)
- kabusys.ai.news_nlp
  - score_news (銘柄別ニュースセンチメントを ai_scores に保存)
- kabusys.ai.regime_detector
  - score_regime (MA200 と マクロニュース LLM を組み合わせた市場レジーム判定)
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.audit
  - init_audit_schema, init_audit_db

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル・モジュール構成の概略です（src/kabusys 配下）。

- src/
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
      - etl.py
      - news_collector.py
      - quality.py
      - stats.py
      - calendar_management.py
      - audit.py
      - pipeline.py
      - etl.py
      - audit.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/__init__.py
    - ai/__init__.py

（上記は主要なモジュールを抜粋しています。実際のディレクトリにはさらに補助モジュールやテスト等が存在する場合があります。）

---

## 運用上の注意

- 環境変数の自動ロード:
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索して `.env` / `.env.local` を読み込みます。テスト時などで自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- リトライ / フェイルセーフ:
  - 外部 API 呼び出し（J-Quants / OpenAI）はリトライ・バックオフを実装しています。LLM 呼び出し失敗時はスコアを中立（0）にフォールバックする等、フェイルセーフな設計です。
- 監査データ:
  - 監査テーブルは削除しない前提で設計されています。init_audit_db でスキーマを初期化してください。
- DuckDB バージョン依存:
  - 一部の executemany / 型バインドなどで DuckDB のバージョン差異に注意（コード内に互換性ワークアラウンドあり）。

---

## サポート / 貢献

バグ報告や機能要望は Issue を立ててください。プルリクエストは歓迎します。コードの設計方針やルックアヘッドバイアス対策に関する変更提案は特に慎重にレビューします。

---

必要なら、この README に以下を追加できます：
- pyproject.toml / requirements.txt に基づく正確なインストール手順
- 各テーブル（raw_prices, raw_financials, market_calendar, ai_scores, market_regime, signal_events 等）のスキーマ定義
- 運用例（cron / Airflow / GitHub Actions での ETL スケジュール例）
- テスト実行手順

どれを追加しますか？