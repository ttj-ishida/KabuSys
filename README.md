KabuSys — 日本株自動売買プラットフォーム（README）
================================

概要
----
KabuSys は日本株のデータパイプライン、特徴量/ファクター計算、ニュース系 NLP（LLM）によるセンチメント評価、監査ログ・発注監視のためのユーティリティ群を提供するライブラリです。  
設計上の特徴として「ルックアヘッドバイアス回避」「ETL の差分・冪等保存」「外部 API に対する堅牢なリトライ/レート制御」「監査証跡の完全性保持（UUID 連鎖）」等を重視しています。

主な機能
--------
- データ ETL（J-Quants API からの株価・財務・マーケットカレンダー取得）
  - 差分取得・バックフィル・品質チェックを備えた日次パイプライン（run_daily_etl）
- ニュース収集（RSS）と前処理・DB への冪等保存（news_collector）
- ニュース NLP（OpenAI を用いたセンチメント評価）
  - 銘柄ごとのセンチメントを ai_scores に書き込む score_news
  - マクロ記事を用いた市場レジーム判定 score_regime（ma200 + LLM 合成）
- 研究用ユーティリティ（ファクター計算・将来リターン・IC・統計サマリー）
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic など
- データ品質チェック（欠損、重複、スパイク、日付不整合検出）
- 監査ログスキーマ（signal_events / order_requests / executions）の初期化と DB 操作ユーティリティ
- J-Quants クライアント（認証/ページネーション/保存関数）と堅牢な HTTP リクエスト実装

セットアップ手順
--------------
1. クローン / パッケージを配置
   - リポジトリをクローンし、Python のパッケージとして利用できる状態にします。

2. 依存パッケージ（例）
   - 少なくとも以下が必要です（環境に応じて適宜 pinned してください）:
     - duckdb
     - openai
     - defusedxml
   - 例（pip）:
     pip install duckdb openai defusedxml

3. 環境変数 / .env の準備
   - プロジェクトルートに .env（および必要に応じて .env.local）を作成します。
   - 自動ロード: パッケージはインポート時にプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を探索し、.env → .env.local の順で読み込みます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必須の環境変数（主なもの）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD     : kabuステーション API 用パスワード
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID      : 通知先 Slack チャンネル ID
     - OPENAI_API_KEY        : OpenAI 呼び出しに使用（score_news / score_regime）
   - 任意 / デフォルト
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG|INFO|...) — デフォルト INFO
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db

4. データベース初期化（監査ログ）
   - 監査ログ用 DB を初期化する例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
   - または既存の DuckDB 接続にスキーマを追加:
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)

基本的な使い方
------------

共通準備: DuckDB 接続
- 多くの機能は DuckDB 接続を受け取ります。settings で指定したパスを使う例:
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

ETL（デイリー ETL）
- 日次 ETL を実行して株価・財務・カレンダーを取得し品質チェックを行う:
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  import duckdb, datetime
  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=datetime.date(2026, 3, 20))
  print(result.to_dict())

個別 ETL ジョブ
- run_prices_etl / run_financials_etl / run_calendar_etl を個別に呼べます（テストや再実行向け）。

ニュースのセンチメントスコア（LLM）
- 銘柄ごとのニュースセンチメントを ai_scores テーブルに書き込む:
  from kabusys.ai.news_nlp import score_news
  score_news(conn, target_date=datetime.date(2026, 3, 20), api_key="sk-...")  # api_key を指定するか環境変数 OPENAI_API_KEY を用いる

市場レジーム判定
- マクロ記事 + ETF(1321) の MA200 乖離で市場レジームを判定し market_regime に書き込む:
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=datetime.date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を利用

ファクター計算 / 研究用ユーティリティ
- 例: モメンタム / ボラティリティ / バリューを計算
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  mom = calc_momentum(conn, target_date)
  vol = calc_volatility(conn, target_date)
  val = calc_value(conn, target_date)

統計ユーティリティ
- Z スコア正規化:
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, ["mom_1m", "mom_3m"])

ニュース収集（RSS）
- RSS を取得して raw_news に格納するワークフローは news_collector モジュールを使用します（fetch_rss 等）。fetch_rss は外部ネットワークを扱うので SSRF 対策やサイズ制限などの安全機構が組み込まれています。

構成 / 重要な設計ポイント（注記）
--------------------------------
- 環境変数は Settings クラス経由で取得されます（kabusys.config.settings）。
- 自動 .env 読み込み: プロジェクトルート (.git / pyproject.toml) を探索して .env / .env.local を読み込みます。
- Look-ahead バイアス防止: 各モジュールは target_date 引数を明示的に受け取り、datetime.today()/date.today() を直接参照しない実装を心がけています（バックテスト向け）。
- 冪等性: DB への保存は基本 ON CONFLICT DO UPDATE / INSERT ... DO UPDATE 等で実装されています。
- 外部 API: J-Quants は固定間隔レート制御とリトライ、OpenAI 呼び出しはリトライと JSON モードを使った厳密なパースを行います。
- フェイルセーフ: LLM や API の失敗は例外にせずフォールバック（ゼロスコア等）する箇所が多く、パイプライン全体の堅牢性を高めています。

主要テーブル（データスキーマの要点）
----------------------------------
- raw_prices / raw_financials / market_calendar : J-Quants 由来の生データを保存
- raw_news / news_symbols : RSS 等からのニュース原稿と銘柄マッピング
- ai_scores : 銘柄ごとの AI によるセンチメントスコア
- market_regime : 日次の市場レジーム（score_regime により書き込み）
- signal_events / order_requests / executions : 監査ログ（監査スキーマ）

ディレクトリ構成（主なファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                         — 環境変数 / Settings
- ai/
  - __init__.py
  - news_nlp.py                      — ニュースセンチメント（score_news）
  - regime_detector.py               — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py                — J-Quants API クライアント + 保存関数
  - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
  - etl.py                           — ETLResult 再エクスポート
  - calendar_management.py           — 市場カレンダー管理 / 営業日ロジック
  - news_collector.py                — RSS 収集・前処理
  - quality.py                       — データ品質チェック
  - stats.py                         — 統計ユーティリティ（zscore_normalize）
  - audit.py                         — 監査ログスキーマ初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py               — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py           — calc_forward_returns / calc_ic / rank / factor_summary

開発・運用上の注意
----------------
- OpenAI 利用時は API レートやコストに注意してください。score_news はバッチ処理（最大バッチサイズあり）で送信する設計です。
- J-Quants API のレート制限（120 req/min）に合わせた実装済みですが、並列化などを行う場合は注意してください。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるため、モジュール内でガードされています。
- テスト時: 環境変数自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用できます。OpenAI 呼び出し等はモック可能な設計になっています。

ライセンス / コントリビューション
--------------------------------
- 本リポジトリのライセンス表記や貢献ルールはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（この README はコードベースの説明に焦点を当てています）。

問い合わせ / サポート
--------------------
- 問題や要望は Issue を立てるか、開発チームの Slack / メーリングリストへ連絡してください（Slack 通知連携機能あり: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を設定）。

以上が KabuSys の概要と利用方法のまとめです。README の内容やサンプルは環境やバージョンに応じて調整してください。必要であればセットアップスクリプト例や docker-compose の雛形も作成できます。