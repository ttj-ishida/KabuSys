KabuSys — 日本株自動売買基盤 (README)
====================================

概要
----
KabuSys は日本株のデータ取得（ETL）・品質チェック・ニュース NLP・市場レジーム判定・ファクター計算・監査ログなどを含む、自動売買／リサーチ基盤用の Python モジュール群です。主要な設計方針は「ルックアヘッドバイアスの排除」「冪等性」「フォールバックによる頑健性」「外部 API 呼び出しのリトライ・保護」です。

主な機能
--------
- データ取得（J-Quants）
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPXカレンダー等の差分取得・保存（jquants_client）
  - レート制限・認証トークン自動リフレッシュ・リトライ対策を実装
- ETL パイプライン（pipeline）
  - run_daily_etl を中心とした日次差分 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - ETLResult により結果・品質問題を集約
- データ品質チェック（data.quality）
  - 欠損、重複、スパイク、日付不整合などの検出
  - QualityIssue に結果を返す（error / warning）
- カレンダー管理（data.calendar_management）
  - market_calendar を基に営業日判定 / next/prev_trading_day / get_trading_days / SQ 判定 等
  - DB 未取得時は曜日ベースでフォールバック
- ニュース収集（data.news_collector）
  - RSS 取得、安全対策（SSRF 防止・受信サイズ制限・トラッキング除去）
  - raw_news / news_symbols への冪等保存（ID は正規化 URL の SHA-256）
- ニュース NLP（ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント算出、ai_scores への保存
  - バッチ化、リトライ、レスポンス検証を実装
- 市場レジーム判定（ai.regime_detector）
  - ETF(1321) の 200 日 MA 乖離（70%）とマクロニュースセンチメント（30%）を合成して日次で bull/neutral/bear を判定
  - OpenAI 呼び出しのリトライ・フェイルセーフ設計
- 研究ユーティリティ（research）
  - momentum/value/volatility 等のファクター計算
  - forward returns、IC（Spearman rank）、factor summary、zscore_normalize 等
- 監査ログ（data.audit）
  - signal → order_request → executions を辿れる監査テーブルを DuckDB に作成・初期化
  - init_audit_db / init_audit_schema を提供

セットアップ
-----------
前提（例）
- Python 3.10+（型ヒントに Union 表記等を利用）
- system に duckdb, openai, defusedxml などをインストール可能であること

例: 開発環境構築手順
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存関係をインストール
   - pip install -r requirements.txt
     （本リポジトリに requirements.txt がない場合は最低限以下を入れてください）
     - pip install duckdb openai defusedxml
4. 環境変数設定
   - プロジェクトルートに .env を置くと自動で読み込まれます（.env.local は上書き）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（.env に記載する例）
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=your_openai_api_key
     - KABU_API_PASSWORD=your_kabu_api_password
     - SLACK_BOT_TOKEN=your_slack_bot_token
     - SLACK_CHANNEL_ID=your_slack_channel_id
     - DUCKDB_PATH=data/kabusys.duckdb         (デフォルト)
     - SQLITE_PATH=data/monitoring.db         (デフォルト)
     - PID_FILE_PATH=data/execution.pid       (デフォルト)
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...（デフォルト INFO）
5. DuckDB 初期化（監査DB 例）
   - Python REPL やスクリプトで:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

使い方（サンプル）
-----------------
- 簡単な ETL 実行（日次）
  - Python スクリプト例:
    from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニューススコアリング
  - from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect(str(settings.duckdb_path))
    written = score_news(conn, target_date=date(2026,3,20))
    print(f"wrote {written} scores")

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026,3,20))

- 研究用ファクター計算
  - from kabusys.research import calc_momentum, calc_value, calc_volatility
    records = calc_momentum(conn, target_date=date(2026,3,20))

- 監査スキーマ初期化
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")

設定（settings）に関する注意
---------------------------
- 環境変数は .env / .env.local から自動読み込みされます（プロジェクトルートは .git または pyproject.toml で探索）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます（テスト用）。
- Settings で取得できる主なプロパティ:
  - settings.jquants_refresh_token
  - settings.kabu_api_password
  - settings.kabu_api_base_url (デフォルト "http://localhost:18080/kabusapi")
  - settings.slack_bot_token / settings.slack_channel_id
  - settings.duckdb_path / settings.sqlite_path / settings.pid_file_path
  - settings.env (development|paper_trading|live)
  - settings.log_level

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                       : 環境変数・設定管理（.env ロードロジック含む）
- ai/
  - __init__.py
  - news_nlp.py                    : ニュース NLP（銘柄ごとのセンチメント）
  - regime_detector.py             : 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py              : J-Quants API クライアント（取得・保存関数）
  - pipeline.py                    : ETL パイプライン（run_daily_etl 等）
  - etl.py                         : ETLResult の再エクスポート
  - quality.py                     : データ品質チェック
  - calendar_management.py         : 市場カレンダー管理
  - stats.py                       : 統計ユーティリティ（zscore_normalize 等）
  - news_collector.py              : RSS ニュース収集・前処理
  - audit.py                       : 監査ログ（テーブル作成・初期化）
- research/
  - __init__.py
  - factor_research.py             : momentum/value/volatility 等
  - feature_exploration.py         : forward returns, IC, factor_summary
- その他: strategy/, execution/, monitoring/（パッケージ公開予定、__all__ に含む）

データベース（テーブル）概要
---------------------------
（各モジュールの docstring に依存するが主要テーブルは以下）
- raw_prices / raw_financials / stocks / market_calendar
- raw_news / news_symbols / ai_scores
- prices_daily / market_regime
- audit 系: signal_events, order_requests, executions

セキュリティ・運用上の注意
------------------------
- OpenAI・J-Quants の API キーは秘匿情報です。.env を git 管理しないでください。
- news_collector は SSRF 対策（リダイレクト検証・プライベートアドレス除外）を実装していますが、本番導入時はネットワーク制御（ファイアウォール）で二重防御してください。
- ETL・API 呼び出しは外部サービスに負荷をかけるため、rate limit と retry の設定を維持してください。
- settings.env による is_live/is_paper/is_dev フラグを参照して本番と検証環境の挙動を切替えてください。

開発・テスト
------------
- モジュール内の外部 API 呼び出し（OpenAI / urllib / jquants_client._request 等）はテスト中にモック可能な設計です（モジュール内の小さなラッパー関数に注入しているため）。
- news_nlp と regime_detector は _call_openai_api を差し替えてユニットテスト可能です。

ライセンス・貢献
----------------
- 本 README はコードベースの説明用です。ライセンスやコントリビューションルールはリポジトリの LICENSE / CONTRIBUTING を参照してください。

補足（よくある質問）
-------------------
- .env のパースは config._parse_env_line によりシングル/ダブルクォート・エスケープ・コメントを適切に処理します。
- 自動 .env 読み込みはプロジェクトルートが特定できない場合（配布後など）にはスキップされます。

以上。必要であれば README の英語版、サンプル .env.example、requirements.txt、簡易起動スクリプト（CLI）テンプレートの追加も作成できます。どれを優先しますか？