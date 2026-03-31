# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けに設計されたライブラリです。データ取得（J-Quants）、データ ETL/品質チェック、ニュース収集・NLP（OpenAI を利用したセンチメント）、市場レジーム判定、リサーチ（ファクター計算）および監査ログの初期化など、取引ロジックに必要な基盤機能を提供します。

主な設計方針:
- ルックアヘッドバイアスを避ける（内部で datetime.today()/date.today() に依存しない設計）
- DuckDB を用いたローカルデータレイヤ
- 冪等性と堅牢なエラーハンドリング（ETL/保存は ON CONFLICT / トランザクションを活用）
- 外部 API 呼び出しにはレート制御とリトライを実装
- テストしやすいように内部 API 呼び出しをモック可能に設計

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡易サンプル）
- 環境変数一覧
- ディレクトリ構成（主要ファイル説明）
- テスト／モックに関する注意

---

プロジェクト概要
- 日本株向けのデータプラットフォーム＋リサーチ／AI／監査ログ機能を提供する Python モジュール群。
- J-Quants API から株価・財務・カレンダー等を取得して DuckDB に保存する ETL、RSS ベースのニュース収集、ニュースの LLM ベースセンチメント評価、ETF ベースの市場レジーム判定、ファクター計算・探索、データ品質チェック、監査テーブル初期化などを含みます。

機能一覧
- データ取得 / ETL
  - J-Quants クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETL 結果を表す ETLResult
- データ品質
  - 欠損チェック、スパイク検出、重複チェック、将来日付／非営業日チェック（quality.run_all_checks）
- カレンダー管理
  - 営業日判定 / next/prev_trading_day / get_trading_days / calendar_update_job
- ニュース収集
  - RSS 取得と前処理（news_collector.fetch_rss）
  - URL 正規化、SSRF 対策、受信サイズ制限等
- ニュース NLP（OpenAI）
  - 銘柄ごとのセンチメントスコアリング（ai.news_nlp.score_news）
  - 市場レジーム判定（ai.regime_detector.score_regime）
  - API 呼び出しはリトライ・バックオフ・JSON 検証を実装
- リサーチ
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - zscore_normalize（data.stats）
- 監査ログ
  - 監査用スキーマ作成と DB 初期化（data.audit.init_audit_schema / init_audit_db）
  - signal_events, order_requests, executions テーブルとインデックス
- 設定管理
  - .env / .env.local 自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - settings オブジェクト経由で環境変数取得（kabusys.config.settings）

---

セットアップ手順（開発用）
前提:
- Python 3.10 以上（Union 型演算子 |、型注釈、match などの利用に対応したバージョン）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows PowerShell)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. パッケージをインストール（開発モード）
   - pip install -e .

5. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に .env を作成。
   - 必須変数等は下記「環境変数一覧」を参照。

自動 .env ロードについて:
- デフォルトでプロジェクトルートの .env → .env.local の順に読み込みます。
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

使い方（簡易サンプル）
- DuckDB 接続を作成して ETL を実行する例:

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")  # settings.duckdb_path で既定パスを取得可能
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントの算出:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数か api_key 引数で渡す
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"written scores: {written}")

- 市場レジーム判定:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査 DB の初期化:

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/monitoring_audit.duckdb")
  # conn をアプリケーションの監査用接続として使用する

モック／テストのヒント:
- OpenAI 呼び出しは内部で _call_openai_api を使用しているため、unit test では patch("kabusys.ai.news_nlp._call_openai_api") や patch("kabusys.ai.regime_detector._call_openai_api") で差し替え可能です。
- RSS のネットワーク取得は kabusys.data.news_collector._urlopen をモックして制御できます。

---

環境変数一覧（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants 用リフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD (必須)
  - kabu ステーション API のパスワード
- KABU_API_BASE_URL (任意)
  - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須)
  - Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須)
  - Slack チャンネル ID
- DUCKDB_PATH (任意)
  - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意)
  - 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意)
  - 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意)
  - ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY (任意)
  - OpenAI 呼び出しに使う API キー（ai.score_* 関数は api_key 引数でも渡せる）
- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意)
  - =1 にすると自動 .env 読み込みを無効化

（注意）Settings オブジェクト（kabusys.config.settings）経由でこれらの値を取得できます。必須変数が欠けていると ValueError が送出されます。

---

ディレクトリ構成（抜粋・主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - .env 自動ロード、Settings クラス（環境変数取得）
- ai/
  - __init__.py
  - news_nlp.py        — ニュースの LLM によるセンチメントスコア化（score_news）
  - regime_detector.py — ETF MA とマクロニュースを合成した市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py  — J-Quants API クライアント（取得 / 保存ロジック）
  - pipeline.py        — ETL パイプライン（run_daily_etl 等）
  - etl.py             — ETLResult 再エクスポート
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - news_collector.py  — RSS 収集と前処理（SSRF 対策等）
  - stats.py           — z-score 正規化ユーティリティ
  - quality.py         — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py           — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py — モメンタム/バリュー/ボラティリティ計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリーなど

その他:
- README.md（本ファイル）
- .env.example（プロジェクトルートに用意する想定。存在しない場合は Settings._require でエラーが出ます）

---

テスト／モックに関する注意
- ネットワーク依存部分（OpenAI / J-Quants / RSS 取得）は内部関数をモックできるよう設計されています:
  - OpenAI: kabusys.ai.news_nlp._call_openai_api / kabusys.ai.regime_detector._call_openai_api を patch してレスポンスを模擬できます。
  - RSS: kabusys.data.news_collector._urlopen を patch して HTTP レスポンスを置き換えられます。
  - J-Quants: kabusys.data.jquants_client._request をモックすると API レスポンス全体を制御できます。
- 自動 .env 読み込みはテスト時に影響することがあるため、KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化できます。

---

ライセンス / 貢献
- （リポジトリに合わせてライセンスを記載してください）

---

補足
- 本 README はコードベースの公開 API（関数名・挙動）と設計方針を要約したものです。詳細な仕様や追加のユーティリティは各モジュールの docstring を参照してください。