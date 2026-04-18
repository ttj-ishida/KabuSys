README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部を実装した Python パッケージです。本リポジトリには以下の主要機能が含まれます。

- 実行エンジン（ExecutionEngine）および監視プロセス（Monitoring）
- ペーパートレード対応（本番 DB と分離）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- 研究用ファクター計算・特徴量探索（DuckDB ベース）
- ニュース NLP / レジーム判定（OpenAI を用いたセンチメント評価）
- 監視ログ永続化（SQLite）およびアラート／Kill Switch 機構
- ユーティリティ：設定ウィザード、設定検証、ペーパートレード検証レポート 等

主な特徴
--------
- モジュール化された設計：monitoring, execution, portfolio, research, ai, utils などに分割
- DuckDB を用いた解析処理（prices_daily, raw_financials 等のテーブル参照）
- OpenAI（gpt-4o-mini 想定）との統合（ニュースセンチメント・マクロセンチメント）
- ペーパートレード時は MockBroker を利用し、data/paper_trading.db に記録して本番 DB と分離
- .env による環境設定管理と対話式ウィザード（config_setup.py）
- 日次ローテーションのログ出力（logs/<app>.log）

セットアップ
----------
前提
- Python 3.10 以上（型注釈で | 演算子を使用）
- SQLite（標準ライブラリ）、その他以下の外部パッケージ：

推奨インストール例
1. 仮想環境を作る（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb openai psutil
   - 解析用に PyYAML があると config/*.yaml の検証が可能: pip install PyYAML

3. data / logs ディレクトリが自動作成されますが、権限に注意してください。

環境変数（必須 / 主要）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合は必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時に使用、デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR）
- LOG_DIR — ログ保存先ディレクトリ（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）
- その他: PAPER_FILL_MODE（ペーパートレードの約定挙動: instant|partial|never|reject）、MONITOR_POLL_INTERVAL（監視ポーリング秒数を上書き）など

.env の作成/更新
- 対話式ウィザードを使用:
  - python -m kabusys.config_setup
- 生成後、設定を検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります

使い方
-----
起動スクリプト
- 監視プロセスを起動（本番監視・Kill Switch 等）:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
  - 注意: monitoring は KABUSYS_ENV にかかわらず sqlite_path（本番用）を使用します

- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と完全に分離）

ツール / ユーティリティ
- ペーパートレード検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH を指定して DB を切り替え可能

AI 関連
- ニュースセンチメント（ai.news_nlp.score_news）やレジーム判定（ai.regime_detector.score_regime）は OpenAI API を使用します。OPENAI_API_KEY を設定してください。
- LLM 呼び出しはリトライや JSON 検証を実装しており、失敗時は安全側のフォールバック（例: スコア=0.0）で継続します。

ログ / フラグ
- ログ:
  - デフォルトは logs/<app_name>.log（TimedRotatingFileHandler：日次ローテーション、30 日保持）
  - コンソールは stdout に出力されます
- Kill Switch:
  - data/kill.flag に理由テキストを書き込むことで ExecutionEngine に停止シグナルを送ります
  - KillSwitch は drawdown 超過やポジション上限超過等の条件で flag を書き込みます
  - 実行開始時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされますが、本番では無効（0）を推奨します
- 停止フラグ:
  - data/stop_requested.flag を監視プロセスや ExecutionEngine が検知すると優雅に停止します

実装上の注意点 / 挙動
- run_monitoring は常に Settings.sqlite_path（監視 DB）を使用します。環境にかかわらず監視ログは同一 DB に保存されます。
- run_execution は KABUSYS_ENV に応じて本番 DB または PAPER_TRADING_SQLITE_PATH を使用します（ペーパートレードは分離）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- process 優先度設定や CPU affinity は utils/process_priority.py に抽象化されています。権限がない場合は警告を出してスキップします。

主要コマンドまとめ
- .env 作成: python -m kabusys.config_setup
- 設定確認: python -m kabusys.validate_config [--strict]
- 監視起動: python -m kabusys.run_monitoring
- 実行エンジン起動: python -m kabusys.run_execution
- ペーパーレポート: python -m kabusys.tools.paper_verification_report [--from] [--to] [--db]

ディレクトリ構成（主要ファイル）
--------------------------------
（src/ 以下がパッケージルート）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 読み込み・Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （実装ファイル群）注文滞留・約定異常監視（この README に含まれない実装ファイルも存在）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - kill_switch.py         — kill.flag 操作
    - alert_manager.py       — （アラート送信ロジック）
  - execution/
    - execution_engine.py    — 実行エンジン本体 (EngineConfig, run_session など)
    - broker_factory.py      — ブローカークライアント生成（Mock / 実ブローカー）
    - order_manager.py       — 注文管理
    - order_repository.py    — DB 永続化（orders）
    - reconciler.py          — 差分解決（実行状態と DB の同期）
    - risk_manager.py        — 発注前のリスク制御
  - portfolio/
    - portfolio_builder.py   — 候補選定・スコア順ソート
    - position_sizing.py     — 株数算出・aggregate cap ロジック
    - risk_adjustment.py     — セクター上限・レジーム乗数
  - research/
    - factor_research.py     — momentum/value/volatility ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py            — ニュースの LLM ベースセンチメント集計（ai_scores 書込）
    - regime_detector.py     — マクロセンチメント + MA200 によるレジーム判定
  - data/                    — 実行時に使用する DB / flag / pid 等を配置（data/monitoring.db, data/paper_trading.db, data/kill.flag, data/execution.pid, data/stop_requested.flag）
  - logs/                    — ログファイル出力先（デフォルト）

追加情報 / 推奨運用
------------------
- 本番環境では KABUSYS_ENV=live / KILL_FLAG_CLEAR_ON_START=0 を必ず確認してください。
- OpenAI を使用する機能を有効にする場合は API キーの管理（環境変数・シークレット管理）に注意してください。呼び出しはリトライやレート制限対策を含みますがコストとレートに留意してください。
- DuckDB のテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）は外部 ETL・パイプラインで準備することを想定しています。
- 監視ループや実行エンジンはデーモン化するか、systemd / docker / Kubernetes 等でプロセス監視を行うことを推奨します。

ライセンス / バージョン
----------------------
- パッケージのバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。
- ライセンス情報はリポジトリルートの LICENSE ファイルを参照してください（存在する場合）。

お問い合わせ
----------
実装の詳細や運用に関する質問があれば、リポジトリのイシューや担当者にお問い合わせください。