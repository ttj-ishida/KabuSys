# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォームのライブラリ群です。  
データ ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログなどの機能を提供します。

バージョン: 0.1.0

---

## 概要

このパッケージは以下の責務を持ちます。

- J-Quants API を用いた株価・財務・市場カレンダーの差分 ETL（DuckDB 保存）
- RSS ベースのニュース収集、記事の前処理と銘柄紐付け
- OpenAI を使ったニュースセンチメント（銘柄別 ai_score）とマクロセンチメントの評価
- ETF の移動平均乖離とマクロセンチメントを組み合わせた市場レジーム（bull/neutral/bear）判定
- ファクター（モメンタム / バリュー / ボラティリティ等）計算と研究用ユーティリティ
- データ品質チェック・監査ログ（トレーサビリティ）用のスキーマと初期化機能

設計上のポイント:
- ルックアヘッドバイアスに注意（target_date を明示して過去データのみ参照）
- DuckDB を中心とした SQL+Python 実装
- 外部 API 呼び出しはリトライ・レート制御・安全対策を実装
- 自動 .env 読み込み機能（プロジェクトルートの .env / .env.local）あり

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch_*, save_*）
  - market calendar 管理（is_trading_day 等）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - audit（監査ログテーブル初期化）
  - news_collector（RSS 取得・前処理・保存）
  - 汎用統計（zscore_normalize）
- ai/
  - news_nlp.score_news（銘柄別ニュースセンチメントを ai_scores に書き込む）
  - regime_detector.score_regime（マクロ + ETF MA200 乖離で市場レジーム判定）
- research/
  - factor_research（calc_momentum, calc_value, calc_volatility）
  - feature_exploration（calc_forward_returns, calc_ic, factor_summary, rank）
- 設定管理
  - kabusys.config.settings（.env 自動読み込み、必須設定チェック）

---

## セットアップ手順

前提:
- Python 3.10 以上（コードは `X | Y` 型注釈等を使用）
- DuckDB を利用（ローカルファイルまたはメモリ）

1. リポジトリをチェックアウト / コピー
2. 仮想環境を作成して有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate (macOS/Linux) または .venv\Scripts\activate (Windows)
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （任意）pip install -e . でパッケージを開発モードインストール
4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（優先度: OS環境 > .env.local > .env）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必要となる主な環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API のパスワード（必須）
- OPENAI_API_KEY : OpenAI API を利用する場合に必要（ai.score 関数呼び出し時に引数で渡すことも可能）
- KABUSYS_ENV : 環境 ("development" | "paper_trading" | "live")（デフォルト "development"）
- DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH など（省略時はデフォルトパスが使われます）

.env の書き方に関して:
- export FOO=bar 形式やクォート付き、インラインコメント等に柔軟に対応します。
- .env.example を参考に作成してください（プロジェクト配布時に提供を想定）。

---

## 使い方（簡単な例）

以下は Python REPL/スクリプト内での利用例です。各関数は DuckDB 接続を受け取る設計です。

- DuckDB 接続を作る（ファイルベース）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 監査ログスキーマの初期化
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- 日次 ETL の実行（市場カレンダー取得 → 株価・財務取得 → 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコアリング（ai_scores テーブルへ書き込む）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # APIキーは引数で渡せます（None の場合は環境変数 OPENAI_API_KEY を参照）
  n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"scored {n} tickers")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- ファクター計算（例: モメンタム）
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

- ETL の細かいジョブを個別実行
  ```python
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  run_prices_etl(conn, target_date=date(2026,3,20))
  ```

注意点:
- OpenAI を利用する処理は API 呼び出しの失敗時にフェイルセーフ（スコア 0.0 を採用する等）を行いますが、API キーは必ず設定してください。
- run_daily_etl 等は内部で date.today() をデフォルトに使う箇所がありますが、各スコアリング等の関数は明示的に target_date を渡すことでルックアヘッドバイアスを防いでいます。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabu API のパスワード
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で使用）
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト "development"）
- LOG_LEVEL: "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト "INFO"）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" を設定すると .env の自動ロードを無効化

設定の読み込み:
- パッケージ起動時にプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から `.env` と `.env.local` を自動で読み込みます（OS 環境変数が優先）。
- 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主なモジュール構成（抜粋）です。

- src/kabusys/
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
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - (その他: 保存/取得ユーティリティ)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*（factor / feature 関連）
  - (将来的に) strategy/, execution/, monitoring/ などを公開する予定

各モジュールの役割:
- data/jquants_client.py: J-Quants との通信、取得・保存ロジック（レート制御・リトライ・JSON パース等）
- data/pipeline.py: 日次 ETL のオーケストレーション（品質チェック含む）
- data/news_collector.py: RSS 取得と前処理、raw_news への保存
- ai/news_nlp.py: 銘柄別ニュースを OpenAI で評価して ai_scores に保存
- ai/regime_detector.py: ETF (1321) の MA とマクロセンチメントを組み合わせて market_regime に保存
- research/*: ファクター計算、特徴量探索、IC 計算など研究向けユーティリティ

---

## 運用上の注意・ベストプラクティス

- OpenAI の API 呼び出しにはコストがかかるため、テスト時はモック化して実行してください（モジュール内部の _call_openai_api をモック可能）。
- J-Quants の API レート制限（120 req/min）を守る設計になっていますが、運用時の過剰呼び出しには注意してください。
- ETL は idempotent に保存するよう設計されています（ON CONFLICT DO UPDATE 等）。
- ニュース収集では SSRF / XML Bomb 対策（defusedxml やホストチェック）を実装していますが、運用環境のネットワークポリシーに応じた追加対策を検討してください。
- 本コードベースはバックテスト時にルックアヘッドバイアスを避ける設計が多く取り入れられています。バックテスト実行時は target_date を明示的に渡すことを推奨します。

---

## 連絡・貢献

バグ報告や機能要望は Issue を作成してください。  
プルリクエストは歓迎します。テストと静的型チェックを通した上での送付をお願いします。

---

README はこのリポジトリ内のコードの要点をまとめたものです。詳細は各モジュールの docstring を参照してください。