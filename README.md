KabuSys
======

日本株向けのデータプラットフォーム / リサーチ / 自動売買補助ライブラリです。  
ETL・データ品質チェック・ニュース収集・LLMによるニュース／マーケット判定・ファクター計算・監査ログ（発注トレーサビリティ）など、量的運用に必要な基盤機能を提供します。

概要
----
KabuSys は以下のような責務を持つモジュール群から構成されています。

- データ取得・ETL（J-Quants API 経由で株価・財務・カレンダーを取得、DuckDB に保存）
- データ品質チェック（欠損・スパイク・重複・日付不整合の検出）
- ニュース収集（RSS → raw_news、SSRF 対策・トラッキング除去）
- ニュース NLP（OpenAI を使った銘柄別センチメント算出）
- 市場レジーム検出（ETF MA とマクロニュースの LLM 評価の合成）
- ファクター計算 / 研究用ユーティリティ（モメンタム・ボラティリティ・バリュー等）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 設定管理（.env 自動読み込み、環境切替）

主な機能一覧
--------------
- ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
- データ品質チェック: run_all_checks / check_missing_data / check_spike / check_duplicates / check_date_consistency（kabusys.data.quality）
- ニュース収集: fetch_rss, preprocess_text, raw_news 保存ロジック（kabusys.data.news_collector）
- ニュース NLP: score_news(conn, target_date, api_key=None) — ai_scores テーブルに書込む（kabusys.ai.news_nlp）
- 市場レジーム判定: score_regime(conn, target_date, api_key=None) — market_regime テーブルに書込む（kabusys.ai.regime_detector）
- ファクター計算: calc_momentum / calc_volatility / calc_value（kabusys.research.factor_research）
- 研究支援: calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize（kabusys.research.feature_exploration / kabusys.data.stats）
- J-Quants クライアント: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / save_*（kabusys.data.jquants_client）
- 監査ログ初期化: init_audit_db / init_audit_schema（kabusys.data.audit）
- 設定管理: Settings クラス（kabusys.config） — 環境変数/.env から設定取得

セットアップ手順
----------------

前提
- Python 3.10+ を推奨（Union types, | を使用しているため）
- ネットワーク接続（J-Quants / OpenAI / RSS ソース）

1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - 実行環境に応じて追加の依存が必要になる場合があります（標準ライブラリ以外は上記が主要依存）

3. 環境変数 / .env の準備
   プロジェクトルートに .env または .env.local を置くと、自動的に読み込まれます（kabusys.config の自動ロード）。
   自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   必須（運用に応じて）:
   - JQUANTS_REFRESH_TOKEN=...           （J-Quants 用リフレッシュトークン）
   - KABU_API_PASSWORD=...               （kabuステーション API のパスワード）
   - OPENAI_API_KEY=...                  （OpenAI を使う機能を使う場合）
   任意:
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb      （デフォルト）
   - SQLITE_PATH=data/monitoring.db       （デフォルト）
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|... 

   .env のフォーマットはシェル風（export KEY=val も可）で、クォートやコメントにも対応します。

4. データディレクトリの準備
   デフォルトで data/ 配下に DB 等を置きます。必要に応じて .env でパスを変更してください。

使い方（基本例）
---------------

- DuckDB 接続を作成する例:

  from pathlib import Path
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する:

  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- ニュースセンチメントを算出して ai_scores に書き込む:

  from datetime import date
  from kabusys.ai.news_nlp import score_news
  # OPENAI_API_KEY が環境変数に設定されているか、api_key を直接渡す
  written_count = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込んだ銘柄数:", written_count)

- 市場レジームを判定して market_regime に保存する:

  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査用 DuckDB を初期化する:

  from pathlib import Path
  from kabusys.data.audit import init_audit_db
  audit_db_path = Path("data/audit.duckdb")
  audit_conn = init_audit_db(audit_db_path)
  # 初期化済みの接続が返る（必要なテーブル・インデックスが作成される）

- ファクター計算（例: モメンタム）:

  from datetime import date
  from kabusys.research.factor_research import calc_momentum
  records = calc_momentum(conn, target_date=date(2026,3,20))
  # records は各銘柄ごとの dict のリスト

設定管理のポイント
------------------
- 環境変数は優先順位: OS 環境 > .env.local > .env
- 自動読み込みはパッケージ内で行う（プロジェクトルートは .git または pyproject.toml を探索して判定）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト時に便利）

注意事項 / 運用上の注意
-----------------------
- OpenAI API 呼び出しは gpt-4o-mini を使用する設計です。API キー（OPENAI_API_KEY）が必要です。失敗時はフェイルセーフとして中立スコア（0.0）にフォールバックするロジックが組み込まれていますが、API 利用量にご注意ください。
- J-Quants API はレート制限を遵守するように RateLimiter（120 req/min）とリトライロジックを実装しています。JQUANTS_REFRESH_TOKEN が必須です。
- 日付に関する処理はルックアヘッドバイアスを避ける設計（内部で date.today() を直接参照しない関数、明示的 target_date を受け取る）になっています。バックテスト用途では特に target_date を明示的に渡してください。
- news_collector には SSRF 対策や受信バイト上限があり、安全性を考慮していますが、実運用する際は RSS ソースの制御と検証を行ってください。
- DuckDB に対する executemany の挙動（バージョン依存）を考慮した実装になっています。DuckDB のバージョンに依存する不整合が出る場合はバージョンを合わせてください。

ディレクトリ構成
-----------------
（主要ファイル / モジュールのみ抜粋）

src/kabusys/
- __init__.py
- config.py                      — 環境変数/設定管理
- ai/
  - __init__.py
  - news_nlp.py                   — ニュース NLP（銘柄別 ai_scores）
  - regime_detector.py            — 市場レジーム判定（1321 MA + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py             — J-Quants API クライアント & DuckDB 保存
  - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
  - etl.py                        — ETLResult のエクスポート
  - quality.py                    — データ品質チェック
  - news_collector.py             — RSS ニュース収集
  - calendar_management.py        — 市場カレンダー管理（営業日判定等）
  - stats.py                      — 統計ユーティリティ（zscore_normalize 等）
  - audit.py                      — 監査ログ初期化（監査テーブルDDL）
- research/
  - __init__.py
  - factor_research.py            — Momentum/Volatility/Value 等の計算
  - feature_exploration.py        — 将来リターン / IC / 統計サマリー 等

README に記載されていない実装の細部や API の使用例は、各モジュールの docstring を参照してください。各 public 関数は docstring に引数・戻り値・例外・副作用（DB 書き込みなど）を明確に記載しています。

補足：よく使う環境変数（まとめ）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- OPENAI_API_KEY — OpenAI を使う処理で必要
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト: data/monitoring.db
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — DEBUG/INFO/...

問い合わせ / 貢献
-----------------
バグ報告や機能提案は issue を立ててください。設計方針や実装上の意図は各モジュールの docstring に詳述されていますので、まずそちらを参照してください。