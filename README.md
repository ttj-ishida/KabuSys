KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的としたモジュール群です。本リポジトリは以下の主要機能を持ちます。

- シグナルに基づく発注エンジン（ExecutionEngine）
- 再起動・障害時のリコンシリエーション機能（Reconciler）
- 監視（System / Trade / Risk）とアラート（LINE push）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング）
- 研究用ファクター計算・特徴量探索（DuckDB 上の prices_daily / raw_financials を参照）
- ニュース NLP（OpenAI を用いたセンチメント評価）と市場レジーム判定
- Streamlit ベースの監視ダッシュボード

設計の要点：
- DuckDB / SQLite をデータ格納に使用（ローカルファイルベース）
- OpenAI（gpt-4o-mini）を用いた NLP 機能（API キー必須）
- paper_trading 環境では本番 DB と分離して動作（data/paper_trading.db を使用）
- 自動起動時に .env / .env.local を読み込む仕組みあり（ただし無効化可能）

主な機能一覧
-------------
- Execution
  - シグナルの読み取り → Gate（リスクチェック） → 発注（OrderManager）
  - ブローカーAPI抽象（BrokerAPIProtocol）経由での send/get/cancel
  - リコンシリエーション：OrderSent 等の不整合をブローカーと同期
  - リスク管理（Rate limit / Circuit breaker / ポジション制限 等）

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス監視、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視とダッシュボード更新
  - KillSwitch: 条件に応じて kill.flag を作成し Execution を停止させる仕組み
  - AlertManager: LINE へ一方向プッシュ（クールダウン管理あり）
  - Streamlit ダッシュボードで可視化

- Portfolio
  - 候補選別（select_candidates）
  - 等分配・スコア加重（calc_equal_weights / calc_score_weights）
  - ポジションサイジング（calc_position_sizes）
  - セクターキャップ / レジーム乗数（apply_sector_cap / calc_regime_multiplier）

- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB SQL + Python）
  - 将来リターン計算、IC（Spearman）や統計サマリー

- AI
  - news_nlp.score_news: raw_news をまとめて OpenAI に送り銘柄別センチメントを ai_scores に書き込む
  - regime_detector.score_regime: ETF（1321）MA200 とマクロニュースから市場レジームを判定・保存

セットアップ手順
----------------

1. Python 仮想環境を作成・有効化
   - 推奨: Python 3.9+（プロジェクトの pyproject.toml を参照してください）
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存関係のインストール
   - 本リポジトリに requirements.txt がある想定で:
     - pip install -r requirements.txt
   - 主な依存パッケージ（最低限）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - SQLite は標準ライブラリに含まれます。

3. 環境変数の設定 (.env)
   - プロジェクトルートに .env または .env.local を用意できます（自動ロード）。
   - 主要な環境変数（抜粋）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - KABU_API_BASE_URL (任意)
     - OPENAI_API_KEY (news/regime の利用時に必須)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート用）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
     - PAPER_FILL_MODE（instant|partial|never|reject、デフォルト instant）
     - PID_FILE_PATH, KILL_FLAG_PATH 等のパス設定
     - MONITOR_POLL_INTERVAL（監視のポーリング間隔を秒で上書き可、デフォルト 60）

   - 例 .env:
     - KABUSYS_ENV=paper_trading
     - OPENAI_API_KEY=sk-...
     - DUCKDB_PATH=data/kabusys.duckdb

4. データベース初期化
   - 監視 DB（SQLite）は起動時に自動でテーブル作成を行います（init_monitoring_db）。
   - DuckDB のテーブル（prices_daily 等）は外部の ETL/パイプラインで用意してください。

使い方
-------

- 実行バイナリ（パッケージとしてインストールした場合）
  - Monitoring（常駐ポーリング）
    - 環境変数でポーリング間隔を変更:
      - MONITOR_POLL_INTERVAL=30
    - 起動:
      - python -m kabusys.run_monitoring
    - あるいはソース直実行:
      - python src/kabusys/run_monitoring.py

    備考:
      - run_monitoring は Settings に基づき sqlite_path を開き monitoring テーブルを初期化します。
      - プロセス優先度を "high" に設定してから監視ループを開始します。

  - Execution（発注エンジン）
    - Paper trading モードで起動（本番 DB と分離）:
      - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - 通常起動（development/live）:
      - python -m kabusys.run_execution
    - 起動時の処理:
      - Broker クライアント生成（環境 KABUSYS_ENV により Mock または 実ブローカー）
      - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine を実行

  - Streamlit ダッシュボード（監視画面）
    - 起動コマンド例:
      - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    - 監視 DB を read-only モードで開いて概要・ポジション・注文・システム状態を表示します。

- AI 機能（スクリプトから利用）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続（DuckDBPyConnection）を渡して実行。api_key 未指定で環境変数 OPENAI_API_KEY を参照。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF（1321）の MA とマクロニュース評価を合成し market_regime テーブルへ書き込み。

- 監視関連注意
  - KillSwitch は条件が成立すると KILL_FLAG_PATH（デフォルト data/kill.flag）に理由を書き込みます。ExecutionEngine は起動時・ループ内でこれを検知して安全終了する設計です。
  - Settings.kill_flag_clear_on_start を 1 にすると ExecutionEngine 起動時に kill.flag を自動削除できます（注意して使用してください）。

設定（Settings）で利用可能な主要項目
------------------------------------
Settings クラスが .env / 環境変数から読み取る代表的なキー：

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（任意）
- OPENAI_API_KEY（AI 機能で必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート）
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
- PAPER_FILL_MODE（instant|partial|never|reject）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV（development|paper_trading|live）
- LOG_LEVEL

ディレクトリ構成
----------------
主要ファイル・ディレクトリと簡単な説明：

- src/kabusys/
  - __init__.py — パッケージ定義（__version__）
  - config.py — 環境変数 / .env 自動ロード / Settings クラス
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト

  - ai/
    - news_nlp.py — ニュースを OpenAI で評価して ai_scores に保存
    - regime_detector.py — マクロ + ETF MA200 で市場レジーム判定
    - __init__.py

  - monitoring/
    - monitoring_db.py — SQLite 用の永続化層（テーブル作成 + MonitoringDB クラス）
    - system_monitor.py — CPU/プロセス/データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン・ポジション上限チェック
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — LINE push 経由アラート送信
    - monitoring_engine.py — 各 Monitor を束ねたポーリングエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード

  - execution/
    - execution_engine.py — Signal-pull 型の発注エンジン（主ロジック）
    - order_manager.py — 発注ワークフロー（create / send / sync / cancel）
    - reconciler.py — 再起動時の自動復旧・照合
    - order_repository.py, order_record.py, broker_api.py, broker_factory.py など（発注・DB 操作関連）

  - portfolio/
    - portfolio_builder.py — 候補選定・スコアソート
    - position_sizing.py — 株数算出・スケールダウン・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py — 将来リターン計算・IC・統計サマリ
    - __init__.py

  - monitoring/, execution/（上記）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py

注意事項・運用上のヒント
-----------------------
- paper_trading 環境は本番 DB と完全に分離されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI API 呼び出しは料金とレート制限があるため、API キーやリトライ設定に注意してください。news_nlp / regime_detector は 429・タイムアウト等をバックオフしてリトライしますが、完全成功を保証しません（失敗時は安全側フォールバック）。
- PID ファイル / kill.flag の管理を通じて ExecutionEngine と Monitoring の協調を行っています。運用スクリプトで起動順（monitoring 先に／execution 先に）やクリーンアップを考慮してください。
- DuckDB の prices_daily / raw_financials 等のテーブルは別途 ETL で用意すること（Research / AI モジュールが依存）。

開発・テスト
-------------
- Settings の自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テストで便利）。
- AI 呼び出し箇所は各モジュールで _call_openai_api を分離しているため、ユニットテスト時はモックで置換しやすくなっています（unittest.mock.patch を使用）。

ライセンス / 貢献
-----------------
- 本 README にライセンス情報は含めていません。実際の配布時は LICENSE ファイルを追加してください。
- バグ報告・改善提案は Issue を立ててください。大きな変更は設計理念（フェイルセーフ・ローカル DB 第一）を尊重ください。

以上がこのコードベースの概要・セットアップ・使い方・ディレクトリ構成です。必要であれば .env.example のテンプレートや requirements.txt の具体的な内容、デプロイ手順（systemd ユニット例など）を追記します。どれを優先して追加しましょうか？