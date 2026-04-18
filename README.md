KabuSys
=======

日本株自動売買システム（KabuSys）の軽量リファレンス / 開発者向け README（日本語）

概要
----
KabuSys は日本株向けの自動売買・研究用モジュール群を集めたプロジェクトです。  
主要な責務は以下の通りです。

- データパイプライン / DuckDB を用いたファクター計算（research）
- ポートフォリオ構築（選定・重み付け・サイズ算出）
- ExecutionEngine（発注管理・リスク管理） — 本番 / ペーパー取引に対応
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- AI モジュール（ニュース NLP / レジーム判定）による補助的スコアリング
- 運用補助ツール（.env ウィザード、設定検証、ペーパートレード検証レポート 等）

特徴
----
主な機能一覧（抜粋）

- 環境設定ウィザード（python -m kabusys.config_setup）
- 起動前設定検証（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db に記録
- Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - 環境にかかわらず本番監視 DB を使用して定期ポーリング
  - MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能（デフォルト 60 秒）
- 監視コンポーネント
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / Execution PID の監視
  - TradeMonitor: 発注ログ・滞留注文・約定異常の検出（trade_logs テーブル）
  - RiskMonitor: ドローダウン・ポジション上限監視、dashboard の更新
  - KillSwitch: 条件に応じて data/kill.flag を生成し ExecutionEngine に停止シグナルを送る
- AI モジュール
  - news_nlp.score_news: OpenAI (gpt-4o-mini 等) を用いたニュースセンチメント評価
  - regime_detector.score_regime: ETF のMA乖離とマクロニュースを合成して regime を判定
- 研究用モジュール
  - research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic など
- 運用支援ツール
  - tools.paper_verification_report: ペーパートレード履歴から PASS/FAIL 判定付きレポートを生成

セットアップ手順
----------------

前提
- Python 3.9+（pipenv/venv 等で仮想環境を推奨）
- 必要な追加パッケージ: duckdb, psutil, openai（AI 機能を使う場合）、PyYAML（設定検証で YAML 検査を行う場合）

例（venv + pip）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai    # 必要に応じて PyYAML などを追加

3. .env の作成（ウィザード利用推奨）
   - python -m kabusys.config_setup
     -> 対話的に .env を生成・更新します

4. 設定検証
   - python -m kabusys.validate_config
     -> 問題があれば指摘されます。--strict を付けると警告もエラー扱いになります。

主要な環境変数（要点）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 動作モード
  - KABUSYS_ENV: development / paper_trading / live
    - paper_trading: 発注は MockBroker に記録される（data/paper_trading.db）
    - live: 本番（実際に発注が行われる想定）
- データベース
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパー取引専用 DB、デフォルト: data/paper_trading.db)
- ログ
  - LOG_LEVEL (DEBUG/INFO/...)
  - LOG_DIR (デフォルト: logs/)
- AI
  - OPENAI_API_KEY (news_nlp / regime_detector を使用する場合に必要)
- 監視関連
  - PID_FILE_PATH (例: data/execution.pid)
  - KILL_FLAG_PATH (例: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1)
- その他
  - MONITOR_POLL_INTERVAL（監視スクリプトのポーリング間隔を秒で指定、デフォルト 60）

使い方（起動・運用）
--------------------

1. .env を作成し validate_config でチェックする
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config

2. 実行エンジン起動（Execution）
   - python -m kabusys.run_execution
     - 起動前に data/stop_requested.flag が存在すると起動を行いません
     - KABUSYS_ENV=paper_trading のときは paper 用 DB に記録され、本番 DB と分離されます
     - 起動時にプロセス優先度を "high" に設定します（psutil 経由。権限により失敗することがあります）
     - 停止は data/stop_requested.flag の作成（または KillSwitch により data/kill.flag が作成され ExecutionEngine.stop() が呼ばれます）

3. 監視プロセス起動（Monitoring）
   - python -m kabusys.run_monitoring
     - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒）
     - 監視は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します
     - data/stop_requested.flag を設置すると監視ループは終了します

4. Kill Switch / Stop フロー
   - KillSwitch はリスク条件を満たした場合に data/kill.flag を生成します（ExecutionEngine はこれを見て停止する設計）
   - 運用者が手動で停止するには data/stop_requested.flag を作成して run_* スクリプトが安全に終了するのを待ちます

5. ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
   - 環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定できます

ロギング
-------
- 共通ユーティリティ kabusys.utils.logging_setup.setup_logging を起動スクリプトが呼び出します
- 標準出力（stdout）へ出力しつつ、 logs/<app_name>.log に日次ローテートで保存（既定 30 世代保持）
- LOG_LEVEL / LOG_DIR 環境変数で調整可能

ディレクトリ構成（抜粋）
----------------------

以下は src/kabusys 以下の主なファイル・モジュール構成（README 作成時点の抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py          — .env 対話ウィザード（python -m kabusys.config_setup）
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — ペーパートレード検証レポート生成
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算 (select_candidates, calc_equal_weights, calc_score_weights)
    - position_sizing.py      — 発注株数算出 (calc_position_sizes)
    - risk_adjustment.py      — セクター上限・レジーム乗数
    - __init__.py
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py      — システム状態 / データ鮮度監視
    - trade_monitor.py       — (発注ログ監視等)
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （アラート送信のラッパー）
  - execution/
    - execution_engine.py    — ExecutionEngine（発注セッション管理）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）による銘柄別スコア
    - regime_detector.py     — マクロ + MA によるレジーム判定
    - __init__.py
  - research/
    - factor_research.py     — momentum/volatility/value 等
    - feature_exploration.py — IC / 将来リターン / 統計サマリ
    - __init__.py
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — psutil を用いた優先度 / CPU affinity 設定
    - __init__.py

注意事項・運用メモ
----------------
- .env は機密情報を含むためリポジトリにコミットしないでください（config_setup.py にも明記あり）。
- KABUSYS_ENV を live に設定する際は特に注意してください（validate_config は複数の注意喚起を行います）。
- OpenAI を利用する機能は API コストとレイテンシが発生します。失敗時はフォールバックや部分的なスキップが実装されていますが、運用上の監視が必要です。
- run_execution/run_monitoring は stop フラグ（data/stop_requested.flag）を確認します。自動停止や手動停止を計画する場合はこの仕組みを利用してください。
- log ディレクトリ作成に失敗した場合はファイルロギングが無効化され、標準出力のみになります（警告が出ます）。
- プロセス優先度・CPU affinity の設定は OS と権限に依存し、設定に失敗しても致命的にはなりません（警告ログのみ）。

開発者向け：よく使うコマンド
---------------------------
- .env 作成・更新:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動（デバッグ/開発）:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- AI スコア（プログラムから呼ぶ例）:
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key="...")

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。
- ライセンス情報はプロジェクトルートの LICENSE ファイル等で管理してください（ここでは記載なし）。

付記
----
この README はコードベース内の実装に基づく概要ガイドです。詳細な設計（PortfolioConstruction.md、StrategyModel.md 等）がプロジェクトに含まれる場合はそちらも参照してください。質問や追加したいドキュメントがあれば教えてください。