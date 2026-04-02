KabuSys — 日本株自動売買プラットフォーム
=================================

概要
----
KabuSys は日本株のデータ収集・品質管理・特徴量計算・ニュース NLP（LLM）を用いたセンチメント評価、
市場レジーム判定、監査ログ管理、ETL パイプライン等を備えたライブラリ群です。
バックテストや自動売買システムのデータ基盤／リサーチ／戦略モジュールとして利用できます。

主な設計方針
- DuckDB を中心としたローカル DB でデータを管理（Look-ahead bias を避ける実装思想）
- J-Quants API からの差分 ETL（レート制限・リトライ対応）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（JSON Mode）
- 冪等性重視（DB 書き込みは ON CONFLICT 等で上書き）
- テストしやすい設計（API 呼び出し箇所はモック差替えが容易）

機能一覧
--------
- データ ETL
  - J-Quants からの株価（日足）・財務データ・市場カレンダー取得（fetch_* / save_*）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- データ品質チェック
  - 欠損・重複・スパイク・日付不整合検出（quality.run_all_checks）
- ニュース収集
  - RSS 取得・前処理・raw_news へ保存（news_collector.fetch_rss 等）
  - SSRF 対策・サイズ上限・URL 正規化など安全対策を実装
- ニュース NLP（LLM）
  - 銘柄ごとのニュースをまとめて OpenAI に投げ、ai_scores に保存（ai.news_nlp.score_news）
  - レート制限・バッチ処理・レスポンス検証・スコアクリップ
- 市場レジーム判定
  - ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime を生成（ai.regime_detector.score_regime）
- 研究用ユーティリティ
  - ファクター計算（momentum/value/volatility）や将来リターン、IC 計算、統計サマリ（research パッケージ）
  - z-score 正規化など共通統計ユーティリティ（data.stats）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ（data.audit.init_audit_db / init_audit_schema）

セットアップ手順
--------------
前提
- Python 3.10 以上（| 型ヒントなどを使用しているため）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. リポジトリのクローン（パッケージ配布がある場合は pip インストール可）
   - ローカル開発:
     python -m venv .venv
     source .venv/bin/activate
     pip install -U pip

2. 依存パッケージのインストール（例）
   pip install duckdb openai defusedxml

   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

3. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml がある場所）に .env / .env.local を置くと自動で読み込まれます。
   - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   必須（最低限）環境変数例:
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - OPENAI_API_KEY=...  （score_news / score_regime 実行時に引数で渡しても可）

   任意（デフォルト有り）:
   - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (default: data/kabusys.duckdb)
   - SQLITE_PATH (default: data/monitoring.db)
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - KABUSYS_ENV, LOG_LEVEL

   .env の書式は shell 形式（KEY=VALUE、export KEY=VALUE も可）です。

4. データベース初期化（監査ログ等）
   監査用 DB を用意する例:
   python
   >>> import duckdb
   >>> from kabusys.data.audit import init_audit_db
   >>> conn = init_audit_db("data/audit.duckdb")
   >>> # conn を使って追加の初期化や確認が可能

使い方（主要 API サンプル）
-----------------------

1) DuckDB 接続の作成
   from kabusys.config import settings
   import duckdb
   conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())

3) ニュースセンチメント（LLM）を使ったスコアリング
   from kabusys.ai.news_nlp import score_news
   from datetime import date
   n = score_news(conn, target_date=date(2026, 3, 20))
   print(f"書込み銘柄数: {n}")

   - OPENAI_API_KEY が環境変数にない場合は api_key 引数に渡してください。
   - ログ・リトライはモジュールで制御されます。

4) 市場レジーム判定
   from kabusys.ai.regime_detector import score_regime
   from datetime import date
   score_regime(conn, target_date=date(2026, 3, 20))

5) ファクター計算 / 研究用関数
   from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
   records = calc_momentum(conn, target_date=date(2026,3,20))
   # z-score 正規化
   from kabusys.data.stats import zscore_normalize
   normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "ma200_dev"])

6) データ品質チェック
   from kabusys.data.quality import run_all_checks
   issues = run_all_checks(conn, target_date=date(2026,3,20))
   for i in issues:
       print(i)

7) RSS フィード取得（ニュース収集）
   from kabusys.data.news_collector import fetch_rss
   articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
   # 取得した NewsArticle（TypedDict）を加工して DB に保存する処理を行う

注意点 / 運用のヒント
- OpenAI 呼び出しは外部 API に依存するため課金・レート制限に注意してください。
- ETL 実行は定期バッチ（夜間）で行うことを想定しています。run_daily_etl は Look-ahead bias を避ける実装です。
- news_nlp / regime_detector は API エラー時にフェイルセーフで 0（中立）寄りのスコアにフォールバックしますが、ログを監視してください。
- DuckDB の executemany にはバージョン差異があるため（空リスト不可等）モジュール側で対処されていますが、運用時は DuckDB バージョンを合わせることを推奨します。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                   — ニュースの LLM スコアリング（ai_scores へ保存）
  - regime_detector.py            — 市場レジーム判定（ma200 + マクロニュース）
- data/
  - __init__.py
  - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
  - etl.py                        — ETL の公開型再エクスポート（ETLResult）
  - jquants_client.py             — J-Quants API クライアント（fetch / save）
  - news_collector.py             — RSS 取得／前処理／SSRF 対策
  - quality.py                    — 品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py                      — 統計ユーティリティ（z-score 正規化）
  - calendar_management.py        — マーケットカレンダー管理（営業日判定 / 更新ジョブ）
  - audit.py                      — 監査ログ（signal/order/execution テーブル・初期化）
- research/
  - __init__.py
  - factor_research.py            — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py        — 将来リターン / IC / 統計サマリ

ライセンス / 貢献
----------------
- 本プロジェクトのライセンス情報（LICENSE）やコントリビュート方法はリポジトリのトップに従ってください。

よくある質問
------------
Q: .env の自動読み込みを無効にしたい
A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Q: OpenAI API キーを渡す方法は？
A: OPENAI_API_KEY 環境変数に設定するか、score_news/score_regime の api_key 引数に明示的に渡してください。

Q: DuckDB の DB ファイルを別パスにしたい
A: 環境変数 DUCKDB_PATH を設定してください（絶対/相対パス可）。

補足
----
ここで示したのはライブラリ API の概要と基本的な利用手順です。運用や本番環境ではログ設定、ジョブスケジューラ（cron / systemd / Airflow 等）、シークレット管理、監視（Slack 通知等）を組み合わせてお使いください。

不明点や追加で README に載せたいコマンド・ワークフローがあれば教えてください。必要に応じて実際の .env.example や運用手順（systemd ユニット、cron 例）も追記します。