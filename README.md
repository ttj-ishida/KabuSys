# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群。  
ETL（J-Quants からのデータ取得・保存）、データ品質チェック、ニュース収集・NLP（OpenAI 経由）、ファクター計算、監査ログ（発注トレース）などを含みます。

---

## 概要

KabuSys は以下の目的を持つモジュール群です。

- J-Quants API から株価・財務・カレンダー等を取得し DuckDB に差分保存する ETL パイプライン
- raw_news の収集・前処理・銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリング（銘柄別 / マクロ）
- ファクター計算（モメンタム / ボラティリティ / バリュー等）と研究用ユーティリティ
- 監査ログ（シグナル → 発注 → 約定）のスキーマ定義と初期化ヘルパー
- 環境変数／設定管理（.env 自動読み込み機能あり）

設計上の方針として、バックテストにおけるルックアヘッドバイアス回避、API の堅牢なリトライ・レートリミット制御、DuckDB への冪等保存などが考慮されています。

---

## 主な機能一覧

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - 差分取得、バックフィル、品質チェック（kabusys.data.quality）
- データ取得クライアント
  - J-Quants API クライアント（kabusys.data.jquants_client）
  - rate limiting、トークン自動リフレッシュ、ページネーション対応、DuckDB への保存ユーティリティ
- ニュース処理
  - RSS 収集と前処理（kabusys.data.news_collector）
  - OpenAI を用いた銘柄別ニューススコア（kabusys.ai.news_nlp::score_news）
  - マクロ＋ETF(1321)を用いた市場レジーム判定（kabusys.ai.regime_detector::score_regime）
- 研究用ユーティリティ
  - ファクター計算（momentum / volatility / value）（kabusys.research.factor_research）
  - 将来リターン、IC、統計サマリー等（kabusys.research.feature_exploration）
  - Zスコア正規化（kabusys.data.stats::zscore_normalize）
- 監査ログ
  - 監査テーブル DDL と初期化 helper（kabusys.data.audit::init_audit_db / init_audit_schema）
- 設定
  - 環境変数読み込みと validation（kabusys.config::settings）
  - 自動 .env ロード（プロジェクトルート検出）と無効化フラグあり

---

## 前提 / 必要環境

- Python 3.10 以上（組み込みの union 型表記や typing 機能を使用）
- 利用ライブラリ（例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
  - そのほか標準ライブラリ

（プロジェクトに含める requirements.txt または pyproject.toml に依存関係を記載する想定です）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone … && cd <repo>

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. インストール
   - pip install -U pip
   - pip install -e .          （プロジェクトを開発モードでインストール）
   - または requirements.txt / pyproject.toml に従ってインストール

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` を作成すると自動で読み込まれます（テスト時など自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数（一部）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu API パスワード（使用する場合）
     - SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
     - SLACK_CHANNEL_ID — Slack チャネル ID
     - OPENAI_API_KEY — OpenAI 呼び出しを行う場合（AI モジュールで使用）
   - 任意・デフォルトあり:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
     - KABUSYS_ENV（development, paper_trading, live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

   - 例: .env（プロジェクトルート）
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxxx
     SLACK_BOT_TOKEN=xoxb-xxxxx
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=DEBUG
     ```

5. DuckDB データベース準備（監査 DB を初期化する例）
   - Python REPL またはスクリプトから:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")  # parent ディレクトリがなければ自動作成
     ```
   - 既存接続に監査スキーマだけ追加する場合は init_audit_schema(conn, transactional=True)

---

## 使い方（よく使う API の例）

- DuckDB へ接続する（settings で指定したパスを使う例）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）をスコアリングして ai_scores テーブルへ書き込む
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY は環境変数か api_key 引数で指定
  n_written = score_news(conn, date(2026, 3, 20))
  print("書込銘柄数:", n_written)
  ```

- 市場レジーム（マクロ + ETF）スコアを計算して market_regime テーブルへ書き込む
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, date(2026, 3, 20))
  ```

- 監査ログ（発注トレース）スキーマを接続に適用
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- ファクター計算（研究用途）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  ```

注意点:
- AI を呼び出す関数（score_news / score_regime）は OPENAI_API_KEY が必要です。api_key 引数で明示的に渡すことも可能です。
- これら関数はルックアヘッド回避のため target_date を明示的に受け取り、内部で date.today()/datetime.today() を直接参照しない設計です（バックテストでの誤用を防止）。
- 自動 .env ロードはプロジェクトルート検出により行われます。テスト等で自動ロードを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## ディレクトリ構成（主なファイル）

リポジトリの主要なモジュールとファイル（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（自動 .env ロード）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（銘柄別）および関連ユーティリティ
    - regime_detector.py     — ETF + マクロから市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py            — ETL パイプラインの実装（run_daily_etl 等）
    - etl.py                 — ETLResult の再エクスポート
    - news_collector.py      — RSS 収集・前処理
    - quality.py             — データ品質チェック
    - stats.py               — 汎用統計ユーティリティ（z-score 等）
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - audit.py               — 監査ログテーブル DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / ボラティリティ / バリュー
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
  - （その他）strategy, execution, monitoring パッケージ等の設計インターフェースが想定されています

---

## 注意事項 / 開発メモ

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行います。パッケージ配布後も正しく動作するように設計されていますが、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- OpenAI 呼び出しや外部 API 呼び出しはリトライ・タイムアウト・エラーハンドリングを備えていますが、API キーやトークンの管理は利用者側で安全に行ってください。
- DuckDB に対する executemany 等で空リストを渡すと古いバージョンでエラーになることがあるため、コード中で空リストチェックを行っています。DuckDB のバージョン互換性に注意してください。
- news_collector は SSRF 回避のためにリダイレクト先検証やホストのプライベートアドレスチェック、最大レスポンスサイズ制限などを実装しています。

---

## サポート / 貢献

バグ修正・機能追加・ドキュメント改善の PR を歓迎します。  
大きな変更を提案する場合は issue を立てて議論してください。

---

以上が README の概要です。必要であれば、.env.example のより詳しいテンプレートや、CI / テスト実行手順、開発用の Docker 設定例なども追記します。どの部分を補足しますか？