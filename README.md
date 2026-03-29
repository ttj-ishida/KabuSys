KabuSys — 日本株向けデータプラットフォーム & 自動売買基盤
====================================

概要
----
KabuSys は日本株向けのデータ収集（ETL）・品質管理・特徴量生成・ニュース NLP・市場レジーム判定・監査ログ（トレーサビリティ）などを含む汎用ライブラリ群です。  
主に以下用途を想定しています：

- J-Quants API からの株価／財務／市場カレンダーの差分取得と DuckDB への保存
- ニュース記事の収集／前処理と OpenAI を用いた銘柄別センチメントスコア算出
- ETF やマクロセンチメントを組み合わせた市場レジーム判定
- ファクター（モメンタム、ボラティリティ、バリュー等）計算および探索的解析（IC 等）
- ETL 品質チェック（欠損・スパイク・重複・日付不整合）
- 発注／約定までの監査ログ（監査テーブル初期化ユーティリティ）

主な機能一覧
--------------
- 環境変数・設定管理（自動 .env 読み込み、Settings オブジェクト）
- J-Quants API クライアント（レート制限・リトライ・トークン自動リフレッシュ）
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- Data 品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
- ニュース収集（RSS 取得・前処理・SSRF 対策・記事ID生成）
- ニュース NLP（OpenAI を用いた銘柄別センチメントスコアリング: score_news）
- 市場レジーム判定（ETF MA とマクロニュースを合成: score_regime）
- 研究用ユーティリティ（ファクター計算、forward returns、IC、z-score 正規化など）
- 監査ログ（audit スキーマ作成・監査 DB 初期化）

前提条件 / 必要なライブラリ
-------------------------
- Python 3.10+
- 主要依存（例）
  - duckdb
  - openai
  - defusedxml
  - その他: 標準ライブラリ（urllib, datetime, json, logging など）

（実際の requirements.txt / pyproject.toml がある場合はそちらを参照してください）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - またはパッケージ化されていれば: pip install -e .

4. 環境変数の設定
   - プロジェクトルートの .env / .env.local を用意します（パッケージ起動時に自動で読み込まれます）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...
     - KABU_API_PASSWORD=...
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi  （必要に応じて）
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...
   - 自動ロードを無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DB 用ディレクトリ作成（必要に応じて）
   - mkdir -p data

使い方（基本例）
----------------

Python REPL / スクリプトから直接呼び出す例をいくつか示します。すべて Look-ahead バイアス対策のため target_date を明示して呼び出す設計です。

- DuckDB 接続の作成例
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL の実行（市場カレンダー・株価・財務・品質チェック）
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースセンチメントスコアの生成（score_news）
  - from datetime import date
  - from kabusys.ai.news_nlp import score_news
  - cnt = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxx")
  - print(f"scored {cnt} codes")

- 市場レジーム判定（score_regime）
  - from datetime import date
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026,3,20), api_key="sk-xxx")

- 監査ログスキーマの初期化 / 監査 DB の作成
  - from kabusys.data.audit import init_audit_db, init_audit_schema
  - audit_conn = init_audit_db("data/audit.duckdb")
  - # または既存 conn に対して
  - init_audit_schema(conn, transactional=True)

- ファクター計算 / 研究用ユーティリティ
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
  - moments = calc_momentum(conn, target_date=date(2026,3,20))

運用/スケジューリング
---------------------
- ETL やニュース収集、ニューススコアリング、レジーム判定などは日次バッチとして cron / Airflow / Prefect 等でスケジュールする想定です。  
- 各関数は例外を適切にログ出力しつつ部分的に続行する設計になっているため、監視（ログ・Slack 通知等）を組み合わせることを推奨します。

環境設定の挙動（自動 .env ロード）
-------------------------------
- kabusys.config モジュールはプロジェクトルート（.git または pyproject.toml を探索）を基準に .env と .env.local を自動で読み込みます。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時など）。

ディレクトリ構成（主要ファイル）
-------------------------------
以下はコードベースから抽出した主要モジュールの構成（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py               — 環境設定管理
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースセンチメントスコアリング（score_news）
    - regime_detector.py    — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント・保存ロジック
    - pipeline.py           — ETL 実行ロジック（run_daily_etl 等）
    - etl.py                — ETL 公開インターフェース（ETLResult）
    - news_collector.py     — RSS 取得 / ニュース前処理
    - calendar_management.py— 市場カレンダー管理（is_trading_day 等）
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - quality.py            — 品質チェック（QualityIssue / run_all_checks）
    - audit.py              — 監査テーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py    — ファクター計算（momentum/value/volatility）
    - feature_exploration.py— forward returns / IC / 統計サマリー
  - research/*、ai/* などから便利関数をエクスポート
- pyproject.toml / setup.cfg / README.md（本ファイル）

設計上の注意点 / 運用上の注意
----------------------------
- Look-ahead バイアスへの配慮
  - 多くの関数は内部で date.today() を参照せず、常に target_date 引数を要求または使用しており、バックテストでのルックアヘッドを防止する設計です。
- OpenAI / J-Quants の API 呼び出しはリトライやフェイルセーフ（失敗時はゼロスコア等）を備えていますが、APIキー管理・レート制限には十分注意してください。
- DuckDB の executemany に関する注意（空パラメータの扱い等）はコード内にも配慮がありますが、使用する DuckDB バージョンでの挙動確認を推奨します。
- ニュース収集では SSRF 対策／XML パース安全化（defusedxml）を行っていますが、運用環境でのネットワークポリシー設定も重要です。

よく使う API のまとめ（リファレンス的に）
-----------------------------------
- Settings（設定取得）
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env, settings.is_live など

- ETL / Data
  - run_daily_etl(conn, target_date, id_token=None, ...)
  - run_prices_etl(conn, target_date, id_token=None, ...)
  - get_last_price_date(conn) / get_last_calendar_date(conn)

- News / AI
  - score_news(conn, target_date, api_key=None)
  - score_regime(conn, target_date, api_key=None)

- Research
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(conn, target_date, horizons=[1,5,21])

- Audit
  - init_audit_db(path) → DuckDB 接続（監査用DB初期化）
  - init_audit_schema(conn, transactional=True)

サポート / 貢献
----------------
- バグ報告・改善提案は issue を作成してください。  
- 大きな設計変更や API 変更は事前に議論の場（issue / PR）で合意をお願いします。

付録: 例 .env（サンプル）
-------------------------
以下は必須・代表的なキーの例（実運用では secrets を安全に管理してください）:

- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=...
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

以上。必要があれば README に追記したい点（例: 実際のコマンド例、CI 設定、サンプル cron、より詳細な API リファレンス）を教えてください。