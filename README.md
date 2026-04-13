# KabuSys

KabuSys は日本株の自動売買・バックテスト・監視を目的とした軽量な Python プロジェクトです。市場データの集計（DuckDB）、注文管理（SQLite / ブローカー API）、監視・アラート（LINE）、および AI を用いたニュースセンチメント評価を含むモジュール群を提供します。

以下は、このリポジトリの概要、機能、セットアップ・使い方、ディレクトリ構成のまとめです。

---
目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（起動コマンド・オプション）
- 環境変数（主な設定）
- 典型的なワークフロー
- ディレクトリ構成

---

プロジェクト概要
- 日本株自動売買システムのコア機能（シグナル→ポートフォリオ構築→注文 → リコンシリエーション）と、監視・レポート・研究用ユーティリティを備えたモジュール群。
- DuckDB を使った時系列/ファクター計算、SQLite による監視ログ・注文ログの永続化、OpenAI API を使ったニュース NLP、LINE でのアラート通知などを含む。
- KABUSYS_ENV により挙動を切り替えられる（development / paper_trading / live）。

機能一覧
- execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカー抽象化（BrokerClientFactory）により paper_trading では MockBroker を使い本番 DB と分離
  - OrderManager / OrderRepository / Reconciler による起動時の自動リコンシリエーション
  - RiskManager（ポジション上限・ドローダウン等）
- monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス存否・データ鮮度の監視
  - TradeMonitor: 注文滞留・約定異常価格の検出
  - RiskMonitor: ドローダウン監視・ポジション数監視（kill flag 生成も含む）
  - MonitoringEngine: これらを周期実行して Alert（LINE）や kill flag を発動
  - SQLite ベースの monitoring DB 初期化/読み書き（monitoring_db.py）
  - Streamlit ベースの監視ダッシュボード起動スクリプト
- research
  - ファクター計算（momentum, volatility, value）と特徴量探索（forward returns, IC）
  - DuckDB 接続を受け取り SQL / Python で計算
- portfolio
  - 候補選定・重み計算（等分・スコア加重）
  - セクター上限適用、レジーム乗数、ポジションサイズ計算（単元丸め・aggregate cap）
- ai
  - news_nlp: raw_news を集約して OpenAI API でセンチメントを計算し ai_scores に書き込む
  - regime_detector: ETF (1321) MA200 乖離 + マクロニュースセンチメントを合成して market_regime を判定
- tools
  - paper_verification_report: Paper Trading DB を解析して稼働率 / 注文成功率 / レイテンシ等の検証レポートを CLI 出力

セットアップ手順（概略）
1. Python の準備
   - 推奨: Python 3.10+（型注釈やマッチングは現代的な機能を想定）
   - 仮想環境の作成:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（必要なもの）
   - duckdb
   - psutil
   - requests
   - streamlit (監視ダッシュボード利用時)
   - openai (AI 機能利用時)
   例:
     pip install duckdb psutil requests streamlit openai

3. 環境変数 / .env の準備
   - プロジェクトルートに .env または .env.local を置くことで自動ロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須（実行する機能に依存）:
     - JQUANTS_REFRESH_TOKEN（research 等で必要）
     - KABU_API_PASSWORD（kabuステーション API を使う場合）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - その他主要設定（デフォルト値はコード内 Settings に記載）:
     - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
     - DUCKDB_PATH（例 data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定モード）
     - LOG_LEVEL
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信）
     - PID_FILE_PATH / KILL_FLAG_PATH（実行プロセス管理）
     - MONITOR_POLL_INTERVAL（監視ループのポーリング間隔、秒。既定 60）

   .env の一例:
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=...
     LINE_CHANNEL_ACCESS_TOKEN=...
     LINE_USER_ID=...

使い方（起動コマンド）
- ExecutionEngine（取引実行）
  - 環境変数で KABUSYS_ENV を切り替える（paper_trading では MockBroker を使用しデータは data/paper_trading.db に記録される）
  - 実行:
      python -m kabusys.run_execution
  - 注意:
    - process priority を high に設定するため権限が必要な場合があります。
    - 起動時に kill_flag_clear_on_start を有効にしておくと、既存の kill.flag を自動で削除する挙動があります（Settings.kill_flag_clear_on_start）。

- Monitoring（監視ループ）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き（デフォルト: 60）
  - 実行:
      python -m kabusys.run_monitoring
  - 監視は常に production の sqlite_path（Settings.sqlite_path）を参照します（KABUSYS_ENV に依存しません）。

- Streamlit ダッシュボード（監視 UI）
  - 実行:
      streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 既存の DB を読み取り専用で開きます（存在しない場合はエラー表示）。

- Paper Trading 検証レポート
  - 実行:
      python -m kabusys.tools.paper_verification_report
    オプション:
      --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で指定可）

- AI 機能
  - OpenAI API を使う機能（kabusys.ai.news_nlp.score_news / regime_detector.score_regime）は OPENAI_API_KEY を環境変数か引数で渡す必要があります。
  - API 呼び出しはリトライ・バックオフを含むが、失敗時は安全にフォールバック（スコア 0.0 やスキップ）する実装です。

主要な環境変数（Settings 参照）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY
- LINE_CHANNEL_ACCESS_TOKEN
- LINE_USER_ID
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db)
- PAPER_FILL_MODE (instant|partial|never|reject)
- KABUSYS_ENV (development|paper_trading|live)
- LOG_LEVEL
- PID_FILE_PATH (デフォルト data/execution.pid)
- KILL_FLAG_PATH (デフォルト data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (1 で起動時クリア)

典型的なワークフロー（例）
1. .env を用意し DuckDB と（必要なら）paper_trading 用 SQLite を作成・初期化する。
2. 研究・ファクター計算: research モジュールの関数を呼び出して DuckDB 上で分析。
3. PaperTrading（検証）:
   - KABUSYS_ENV=paper_trading を設定
   - python -m kabusys.run_execution を実行（data/paper_trading.db に発注ログが残る）
   - python -m kabusys.tools.paper_verification_report --from ... --to ... で検証レポートを生成
4. 本番運用:
   - KABUSYS_ENV=live を設定して python -m kabusys.run_execution をデーモンとして起動
   - 監視は python -m kabusys.run_monitoring を別プロセスで常時実行
   - streamlit ダッシュボードで監視状況を確認
   - 重大リスク発生時は monitoring が kill.flag を書き、ExecutionEngine 側で停止処理をトリガーする設計

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数/設定ロード
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - data/                       — （未表示）データ取り込み / pipeline 等（DuckDB 関連）
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - execution/
    - order_manager.py
    - reconciler.py
    - （broker_factory 等、ブローカ抽象）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
    - streamlit_dashboard.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - process_priority.py

トラブルシューティング（よくある注意点）
- 権限エラー: process priority の設定や pid ファイル書き込みに関して権限が必要な場合があります（特に高優先度設定）。
- DB ロック: SQLite を複数プロセスで更新する場合は注意。monitoring DB は監視用、orders DB は別ファイルで分離されています。
- OpenAI API のレート制限: news_nlp / regime_detector はリトライとフォールバックを備えていますが、API キーと使用量に注意してください。
- Streamlit で DB を読み取り専用で開く際、URI に ?mode=ro を付けています（ファイルが存在しない場合は start 失敗）。MonitoringEngine を先に起動して DB を作成してください。
- MONITOR_POLL_INTERVAL に 0 や負値を設定すると警告が出てデフォルト（60秒）にフォールバックします。

ライセンス・貢献
- このリポジトリにライセンス表記が含まれていない場合、利用・配布前に作者方針を確認してください。機能追加・修正は PR を歓迎します。

以上が README の要約です。必要であれば、各モジュール（ExecutionEngine、Broker 実装、DuckDB スキーマ、テスト手順など）に対する詳細なドキュメントや、Systemd / Docker での運用方法サンプルも作成します。どの部分の詳細が欲しいか教えてください。