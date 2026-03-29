# KabuSys

日本株向けの自動売買・データプラットフォーム。  
データ取得（J-Quants）、ニュース収集・NLP（OpenAI）、研究用ファクター計算、ETL パイプライン、監査ログ（DuckDB）などを統合したライブラリ群です。

主な特徴
- J-Quants API 経由の株価・財務・カレンダー取得（ページネーション・リトライ・レート制御対応）
- RSS ベースのニュース収集（SSRF対策、URL正規化、トラッキング除去）
- OpenAI を用いたニュースセンチメント（銘柄別）とマクロセンチメント判定
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- ファクター計算（モメンタム / バリュー / ボラティリティ等）と統計ユーティリティ
- 監査ログ用スキーマ（signal → order_request → execution のトレーサビリティ）
- Look-ahead バイアス対策や堅牢なエラーハンドリング設計

---

## 主な機能一覧（モジュール別）
- kabusys.config
  - .env 自動ロード（プロジェクトルート検出）、環境変数ラッパー（Settings）
- kabusys.data
  - jquants_client: API 取得・DuckDB への保存（raw_prices / raw_financials / market_calendar 等）
  - pipeline: run_daily_etl 等の ETL エントリポイント、ETLResult
  - news_collector: RSS 取得・正規化・raw_news への登録ロジック
  - calendar_management: 営業日判定 / next/prev_trading_day / calendar_update_job
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news(conn, target_date, api_key=None): 銘柄別ニュースセンチメントを ai_scores に書込
  - regime_detector.score_regime(conn, target_date, api_key=None): ma200 とマクロニュースを合成して market_regime を記録
- kabusys.research
  - calc_momentum / calc_value / calc_volatility：ファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank：特徴量探索・IC 計算

---

## 前提・要件
- Python 3.10+
- 必須ライブラリ（概略）
  - duckdb
  - openai
  - defusedxml
- J-Quants API のリフレッシュトークン、kabu API パスワード、OpenAI API キー等が必要

（実際のインストールでは pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作る
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. パッケージと依存をインストール
   - editable インストール（開発）
     ```bash
     pip install -e ".[dev]"  # または最小で pip install -e .
     ```
   - 必要パッケージを手動で入れる場合（例）
     ```bash
     pip install duckdb openai defusedxml
     ```

3. 環境変数（.env）を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 最低必要な環境変数（例）
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     OPENAI_API_KEY=sk-...
     KABUSYS_ENV=development    # development | paper_trading | live
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     ```
   - 注意: Settings クラスは必須環境変数が不足している場合 ValueError を送出します。

4. データベース用ディレクトリ作成
   ```bash
   mkdir -p data
   ```

---

## 基本的な使い方（コード例）

- DuckDB 接続を作って ETL を走らせる
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを評価して ai_scores に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY が環境変数に設定されていれば api_key は省略可
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote {written} scores")
  ```

- マーケットレジーム判定（ma200 + マクロニュース）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマ初期化（監査用 DB を分ける例）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # これで signal_events, order_requests, executions テーブルが作られる
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(momentum), "records")
  ```

---

## よく使う API（抜粋）
- data.pipeline.run_daily_etl(conn, target_date, id_token=None, ...)
  - 日次 ETL のエントリポイント（カレンダー・株価・財務・品質チェック）
- data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - 生 API 取得関数（主に内部使用）
- data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
  - DuckDB に保存（冪等）
- data.news_collector.fetch_rss / preprocess_text
  - RSS 取得・前処理
- ai.news_nlp.score_news(conn, target_date, api_key=None)
  - 銘柄別ニュースセンチメントを ai_scores に書き込む
- ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 市場レジーム（bull/neutral/bear）を market_regime に書き込む
- data.audit.init_audit_schema(conn, transactional=False) / init_audit_db(path)
  - 監査ログスキーマ初期化

---

## 注意事項 / 設計上のポイント
- Look-ahead バイアス防止:
  - 多くのモジュールは内部で datetime.today()/date.today() を直接参照せず、必ず target_date を引数で受け取る設計です。
  - prices_daily 取得やニュースウィンドウは target_date より先のデータを参照しないように注意されています。
- 自動環境変数読み込み:
  - パッケージインポート時にプロジェクトルート（.git または pyproject.toml）を探索し .env / .env.local を自動読み込みします。
  - テスト等で無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI / J-Quants / 外部 API 呼び出し:
  - API 呼び出しはリトライやバックオフ、フェイルセーフ（失敗時のフォールバック）を備えていますが、APIキーやレート制限の管理は運用側で行ってください。
- DuckDB の executemany 空リスト問題:
  - 一部の実装は DuckDB のバージョン特性を考慮しており、executemany に空リストを渡さない工夫があります。

---

## ディレクトリ構成（主要ファイル）
src/kabusys/
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
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - etl.py (トップレベル公開)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/*（factor/feature 関数）
- その他: strategy / execution / monitoring の名前は __all__ に含まれているがここでは主に data/ai/research を中心に実装済み

（各モジュールの詳細と設計意図はソースコード内の docstring を参照してください）

---

## デバッグ・開発ヒント
- ログレベルは環境変数 LOG_LEVEL で制御（DEBUG|INFO|WARNING|ERROR|CRITICAL）。
- 自動 .env 読み込みの挙動やロード順は config.py を確認。順序は OS 環境 > .env.local > .env。
- テスト時は外部 API 呼び出しをモックし、OpenAI クライアント呼び出しや HTTP 接続を差し替えてください（モジュール設計はモック差替えを想定）。
- DuckDB のスキーマ初期化・監査ログ作成は data.audit.init_audit_schema / init_audit_db を利用してください。

---

この README はコードベースの主な使い方と設計意図をまとめたものです。詳細な API や実運用向けの設定（監視・リトライ設定・実発注ロジック等）は各モジュールの docstring を参照し、環境に合わせて運用ルールを整備してください。質問や追加のチュートリアルが必要であれば教えてください。