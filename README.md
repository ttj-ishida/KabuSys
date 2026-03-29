# KabuSys — 日本株自動売買プラットフォーム (README)

概要
----
KabuSys は日本株のデータ取得・品質管理・ファクター研究・AI ニュース分析・市場レジーム判定・監査ログなどを含む、自動売買／リサーチ用途の共通ライブラリ群です。ETL（J-Quants からのデータ取得）→ 品質チェック → ファクター算出 → シグナル／監査記録というワークフローを想定しており、DuckDB を主要なローカルストレージとして利用します。

主な設計方針（抜粋）
- ルックアヘッドバイアス防止（内部で datetime.today()/date.today() を不用意に参照しない）
- DB への保存は冪等（ON CONFLICT / DO UPDATE 等）
- 外部 API 呼び出しはリトライ・レートリミット対策を実装
- テスト容易性のため注入・モック用フックを用意

機能一覧
--------
- 環境設定管理
  - .env / .env.local 自動ロード（無効化可）
  - 必須環境変数の取得（設定不足時に明確な例外）
- データ ETL
  - J-Quants API からの株価日足 / 財務 / 市場カレンダー取得（ページネーション対応）
  - 差分更新・バックフィル・品質チェックのパイプライン（run_daily_etl）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合の検出（QualityIssue を返す）
- ニュース収集
  - RSS フィードの安全な収集（SSRF 対策、gzip 上限、XML デフューズ）
  - raw_news / news_symbols への冪等保存
- ニュース NLP（AI）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント算出（score_news）
  - レスポンスのバリデーション、スコアのクリップ、チャンク化・リトライ実装
- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離とマクロニュースセンチメントを合成して日次レジーム算出（score_regime）
  - LLM 呼び出しのフェイルセーフ実装（失敗時は 0.0）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査用テーブル DDL の初期化（init_audit_schema / init_audit_db）
- 研究用ユーティリティ
  - モメンタム・ボラティリティ・バリュー等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリ、Z スコア正規化

セットアップ手順
----------------
前提
- Python 3.10+（typing の Union 省略記法等を利用）
- DuckDB が利用できる環境
- OpenAI Python SDK（openai）を利用する処理は API キーが必要
- defusedxml（RSS パースの安全化）

1. リポジトリをクローン（src レイアウトを想定）
   - 例: git clone <repo-url>

2. 依存パッケージをインストール
   - 推奨: 仮想環境を作成してから
   - 例:
     python -m venv .venv
     source .venv/bin/activate
     pip install -e .           # パッケージ化されている場合
     pip install duckdb openai defusedxml

   ※ プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください。

3. 環境変数の設定
   - プロジェクトルートに .env を用意（.env.example を参考に作成）
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL）
     - KABU_API_PASSWORD — kabuステーション API パスワード（注文連携など）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — 通知（必要に応じて）
     - OPENAI_API_KEY — OpenAI 呼び出し（news_nlp / regime_detector）
   - オプション:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 SQLite、デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/...）
   - 自動ロードを無効にする場合:
     - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. データベースファイルの配置ディレクトリを作成（必要に応じて）
   - 例: mkdir -p data

使い方（例）
------------

基本的な DB 接続（DuckDB）と ETL 実行例:
- Python スクリプト例:
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

ニュース（AI）スコア取得:
- OpenAI API キーを環境変数に設定してから呼び出すか、api_key 引数を渡す:
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # None → 環境変数 OPENAI_API_KEY を使用
  print("書き込み銘柄数:", n_written)

市場レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key=None)

監査ログ DB 初期化:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn 上で order_requests 等のテーブルが作成されます

研究用ファクター計算:
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  # records は各銘柄ごとの dict のリスト

注意点・運用メモ
----------------
- OpenAI 呼び出しはモデル（gpt-4o-mini）を想定。API レートやコストに注意してください。
- LLM 呼び出しの失敗は各モジュールでフェイルセーフが実装されており、完全停止せずにデフォルト値で継続する設計です（例: macro_sentiment=0.0）。
- ETL は差分更新とバックフィル（デフォルト 3 日）を行います。run_daily_etl の引数で挙動を制御できます。
- DuckDB の executemany に空リストを渡すとエラーとなるバージョンがあるため、内部で空チェックを行っています。
- テスト時は各モジュールの _call_openai_api などの内部関数をパッチして外部呼び出しをモックできます。
- すべてのタイムスタンプは基本的に UTC を使用する設計（監査ログ等で明文化）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / .env 自動ロードロジックと Settings クラス
- ai/
  - __init__.py
  - news_nlp.py            — ニュースセンチメント算出（score_news）
  - regime_detector.py     — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント（fetch / save）
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - etl.py                 — ETLResult の再エクスポート
  - news_collector.py      — RSS 取得・前処理・保存
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - quality.py             — データ品質チェック
  - stats.py               — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py               — 監査ログ DDL / 初期化
- research/
  - __init__.py
  - factor_research.py     — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン / IC / summary / rank
- monitoring/ (※コードベースに含まれる想定の監視用モジュール群はプロジェクトで拡張)
- strategy/ (戦略層のインターフェースは別途実装想定)
- execution/ (注文送信ロジックは別途実装想定)

依存・推奨ライブラリ
-------------------
- duckdb
- openai (OpenAI Python SDK / または OpenAI の互換クライアント)
- defusedxml
- その他標準ライブラリ（urllib, json, datetime, logging 等）

ライセンス・貢献
----------------
リポジトリに含まれる LICENSE を参照してください。バグ報告・機能提案は Issues にお願いします。

最後に
------
この README はコードベースの公開されているモジュール群を元に作成しています。実際の運用では API キーやパスワード等の取り扱いに注意し、ステージング・ペーパートレード環境で十分にテストした上でライブ運用へ移行してください。README の補足やサンプルスクリプトが必要であれば、用途（ETL Cron、定期ジョブ、戦略デプロイ等）を教えてください。