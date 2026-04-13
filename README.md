KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買（Execution）とその運用監視（Monitoring）・研究（Research）・AI（ニュース NLP）用ユーティリティを含む小規模なコードベースです。  
本リポジトリは、発注処理・リスク管理・監視ログ保存・Paper Trading（モックブローカー）・ファクター計算・ニュースセンチメント評価などのコンポーネントを含みます。

主な特徴
--------
- 実行（Execution）
  - Broker クライアントの抽象化（本番と Paper Trading を切替可能）
  - 注文の状態管理、再起動時のリコンシリエーション
  - リスク管理（発注上限・ドローダウンなど）
- 監視（Monitoring）
  - システム資源（CPU/Memory/Disk）、実行プロセス稼働、データ鮮度のポーリング監視
  - 注文滞留・約定異常価格検出
  - Kill Switch（flag ファイル）による外部停止トリガー
  - LINE によるプッシュ通知（AlertManager）
  - Streamlit ダッシュボード（read-only）
- 研究（Research）
  - DuckDB 上の価格データからファクター（Momentum / Volatility / Value 等）を計算
  - 将来リターン、IC（Information Coefficient）計算、統計サマリ
- AI（ニュース NLP）
  - OpenAI を用いたニュースセンチメント評価（銘柄別）
  - マクロニュースを使った市場レジーム判定
- ユーティリティ
  - process priority / CPU affinity 設定ユーティリティ
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）

セットアップ手順
----------------
1. Python（推奨: 3.10+）を用意する。

2. リポジトリをクローンして作業ディレクトリへ移動:
   - git clone <repo>
   - cd <repo>

3. 仮想環境を作成・有効化:
   - python -m venv .venv
   - (Linux/macOS) source .venv/bin/activate
   - (Windows) .venv\Scripts\activate

4. 依存パッケージをインストール（requirements.txt がある場合はそちらを利用。無い場合の例）:
   - pip install duckdb psutil openai requests streamlit

5. データディレクトリを作成:
   - mkdir -p data

6. 環境変数の設定:
   - プロジェクトルートに .env を置くと自動で読み込まれます（.env.local は上書き）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 主要な環境変数（抜粋）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
     - KABUSYS_ENV — 実行環境: development / paper_trading / live （デフォルト: development）
       - paper_trading を指定すると MockBrokerClient を利用し、Paper Trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します
     - PAPER_FILL_MODE — paper_trading 時の約定モード（instant/partial/never/reject）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading DB（デフォルト: data/paper_trading.db）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視ログ SQLite（デフォルト: data/monitoring.db）
     - PID_FILE_PATH, KILL_FLAG_PATH — Execution の PID / kill flag ファイルパス
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
   - 実行時に一時的に環境変数を渡す例:
     - KABUSYS_ENV=paper_trading OPENAI_API_KEY=xxx python -m kabusys.run_execution

使い方
------

- 実行エンジン（ExecutionEngine）起動
  - 本番想定:
    - 設定を整え（KABUSYS_ENV=live 等）、PID ファイル/認証情報を用意して次を実行:
      - python -m kabusys.run_execution
  - Paper Trading（モックブローカー）:
    - KABUSYS_ENV=paper_trading をセットすると paper 用 DB（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。
    - 例:
      - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 監視ループ起動（SystemMonitor ポーリング）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒数を指定（デフォルト 60）。
  - python -m kabusys.run_monitoring
  - 監視は常に本番の sqlite_path（SQLITE_PATH）を使用します（環境にかかわらず）。

- Streamlit ダッシュボード（監視）
  - 起動例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは read-only で監視 DB を参照します。DB は MonitoringEngine によって作成・更新されます。

- Paper Trading 検証レポート生成ツール
  - 使用例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db で SQLite ファイルパスを上書きできます。既定は data/paper_trading.db。

- AI / NLP 機能
  - ニューススコア付け（ai.news_nlp.score_news）やレジーム判定（ai.regime_detector.score_regime）は DuckDB 接続と target_date を渡して呼び出します。OpenAI API キー（OPENAI_API_KEY）が必要です。
  - これらはスクリプトから直接呼ぶか、スケジューラから呼び出して ai_scores / market_regime テーブルへ書き込みます。

- Kill Switch（外部停止）
  - risk_monitor / kill_switch によりドローダウンやポジション上限を検知すると data/kill.flag を書き込み Execution 側に停止を促します。
  - Execution 起動時に kill flag をクリアする設定（KILL_FLAG_CLEAR_ON_START）が利用できます。

注意点 / 運用メモ
------------------
- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から .env → .env.local を順に読み込みます。
  - OS 環境変数は保護され、.env.local の override は OS 環境変数を上書きしません。
- プロセス優先度の設定:
  - 起動スクリプトは set_process_priority("high") を呼びます。psutil によって OS 別に処理されますが、権限不足などで設定できない場合は警告が出てスキップされます。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は冪等でテーブル・インデックスを作成し、既存 DB に対する簡単なカラム追加（マイグレーション）も含みます。
- ロギング:
  - 各スクリプトは logging.basicConfig(level=logging.INFO) をデフォルトで使用します。環境変数 LOG_LEVEL で設定可能。

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py — パッケージ情報（__version__）
  - config.py — 環境変数 / 設定読み込みユーティリティ（.env 自動読み込み、Settings クラス）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - execution/
    - order_manager.py — 注文の状態遷移・Broker との同期ロジック
    - reconciler.py — 起動時のリコンシリエーション（Order / Position 同期）
    - ...（ブローカー抽象・リポジトリ等）
  - monitoring/
    - monitoring_db.py — SQLite テーブル定義・永続化ラッパー（MonitoringDB）
    - system_monitor.py — システム資源・データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — LINE Push 通知
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ベースのダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算・上限・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等の計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュースを OpenAI でスコア化して ai_scores に書き込む
    - regime_detector.py — マクロニュース + ETF MA200 でレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成ツール
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

貢献 / テスト
--------------
- ユニットテストや CI は本 README に含まれていませんが、モジュール設計は純粋関数レイヤ（portfolio, research 等）と I/O レイヤ（monitoring_db, broker 等）を分離しているため、依存を差し替えれば単体テストが容易です。
- OpenAI 呼び出し等外部 API はテスト時にモック（unittest.mock）で差し替えることを想定しています（コード内に patch 用の記述あり）。

ライセンス / 免責
----------------
この README はコードベースの仕様説明を目的としています。実際の運用では金融商品取引に関する法令やブローカーの利用規約に従ってください。本ソフトウェア利用による損害については責任を負いません。

以上。必要があれば実行例コマンドや .env.example のサンプルを追記します。ご希望の出力形式（Markdown/HTML/短縮版など）があれば教えてください。