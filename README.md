KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システムのコンポーネント群です。  
このリポジトリには、実行エンジン（ExecutionEngine）、監視コンポーネント（Monitoring）、ポートフォリオ構築／リスク管理ロジック、リサーチ用ファクター計算、ニュース NLP を用いた AI スコアリングなどのモジュールが含まれます。  
設計方針は「実運用を意識した堅牢さ」と「テスト可能な純粋関数／明確な I/O 層」です。

主な特徴
--------
- ExecutionEngine（実注文明細管理・発注処理）および監視ループの起動スクリプトを含む。
- paper_trading（ペーパートレード）モードに対応し、実 DB と分離して動作可能。
- monitoring: システム稼働状況（CPU/メモリ/ディスク）、データ鮮度、オーダー状況、リスク監視（ドローダウン・ポジション上限）を収集・永続化。
- Kill Switch：条件を満たすと data/kill.flag を書き込み Execution を止める仕組み。
- portfolio: 候補選定、重み計算、ポジションサイジング、セクター制約、レジーム乗数等の純粋関数群。
- research: DuckDB を使ったファクター計算（モメンタム / ボラティリティ / バリュー）や IC 計算。
- ai: OpenAI を利用したニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）。
- ユーティリティ: ログ設定、プロセス優先度設定、設定ウィザード・検証 CLI、Paper Trading 検証レポート生成など。

セットアップ手順
----------------
前提
- Python 3.9+（ソースは型アノテーションを使用）
- システムに sqlite3 は標準搭載、追加で以下をインストールする想定:
  - duckdb
  - psutil
  - openai （AI 機能を使う場合）
  - PyYAML（config YAML の検証を行う場合。必須ではない）

仮想環境（例）
- venv を作成・有効化:
  - python -m venv .venv
  - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

パッケージインストール（例）
- pip install duckdb psutil openai PyYAML

ディレクトリ作成（ログ・データ保存用）
- mkdir -p data logs

環境変数設定
- 必須（起動前に設定するか .env を作成）:
  - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
  - KABU_API_PASSWORD      — kabuステーション API パスワード
- 推奨・任意:
  - KABUSYS_ENV            — 実行環境: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH            — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH            — 監視 DB デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード時の DB（デフォルト: data/paper_trading.db）
  - LOG_LEVEL              — ログレベル（DEBUG/INFO/…）
  - OPENAI_API_KEY         — OpenAI を使う機能のための API キー（ai モジュール）
  - PAPER_FILL_MODE        — paper_trading の約定モード (instant|partial|never|reject)
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする (0/1)
  - MONITOR_POLL_INTERVAL  — 監視ポーリング間隔（秒、デフォルト 60） ※ run_monitoring 用

.env の作成支援
- 対話式ウィザード:
  - python -m kabusys.config_setup
  - これにより .env を生成できます（.env は絶対に Git にコミットしないでください）。

設定検証
- 起動前に設定を検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります。

使い方（主要コマンド）
---------------------

1) 監視ループ（SystemMonitor 単体起動）
- 目的: システム状態や監視 DB への書き込みを行うデーモン的プロセス
- 実行:
  - python -m kabusys.run_monitoring
- オプション／挙動:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）。
  - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが終了します（または Ctrl+C）。
  - 監視は常に「本番」sqlite_path を使用（KABUSYS_ENV に依存しない）。

2) 実行エンジン（ExecutionEngine）
- 目的: 注文発行・注文管理を行うエンジン。paper_trading モードでは MockBrokerClient を使用してペーパートレード DB に記録。
- 実行:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB とは完全分離。
  - 実行中は data/execution.pid に PID を書きます。
  - 停止は data/stop_requested.flag を作成するか、エンジンから kill.flag を検知すると停止します。

3) Paper Trading 検証レポート
- 目的: ペーパートレード DB を解析しシステム稼働率・注文成功率・レイテンシ等をレポート化
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

4) AI 関連
- news_nlp.score_news / regime_detector.score_regime を通じて OpenAI を使用する処理があります。
- 必要: 環境変数 OPENAI_API_KEY を設定するか、各関数呼び出し時に api_key 引数を渡す。
- 注意: API コールは料金が発生します。レート制限・エラー対策としてリトライ・フェイルセーフが実装されています（失敗時はスキップして続行）。

ファイル・ディレクトリ構成
------------------------
（省略可能なファイルは抜略、主要なモジュールを列挙）

- src/kabusys/
  - __init__.py                     — パッケージ定義（バージョン等）
  - config.py                       — 環境変数/.env ロード・Settings クラス
  - config_setup.py                 — .env 対話式ウィザード
  - validate_config.py              — 起動前設定検証 CLI
  - run_monitoring.py               — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py   — Paper Trading 検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースセンチメント取得（OpenAI）
    - regime_detector.py             — 市場レジーム判定（OpenAI + 1321 MA）
  - monitoring/
    - monitoring_db.py               — SQLite 永続化層・MonitoringDB クラス
    - system_monitor.py              — システム状態・データ鮮度監視
    - trade_monitor.py               — （取引監視、コードベースに含まれる想定）
    - risk_monitor.py                — ドローダウン・ポジション制限監視
    - kill_switch.py                 — kill.flag の管理
    - alert_manager.py               — （アラート送信管理）
    - monitoring_engine.py           — 複数モニタの統合ループ
  - execution/
    - execution_engine.py            — ExecutionEngine（起動ロジックは run_execution）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py            — 候補選定／重み計算
    - position_sizing.py              — 発注数量計算・上限・丸め
    - risk_adjustment.py              — セクター制約・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py              — モメンタム/ボラティリティ/バリュー算出
    - feature_exploration.py          — forward returns / IC / 統計サマリ
  - monitoring/monitoring_db.py etc.  — 監視 DB 周り（上記と重複あり）
  - utils/
    - __init__.py
    - logging_setup.py               — 共通ログ設定ユーティリティ
    - process_priority.py            — プロセス優先度 / CPU affinity 設定ユーティリティ

運用での注意点
--------------
- .env は絶対にリポジトリにコミットしないでください（APIキー・パスワードを含むため）。
- 本番運用時は KABUSYS_ENV=live を設定する前に validate_config で入念に確認してください（validate_config は live 時に追加警告を表示します）。
- kill.flag（data/kill.flag）を手動で作成すると ExecutionEngine に停止シグナルを送れます。起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動でクリアされますが、本番では 0 を推奨します。
- run_monitoring は監視 DB と duckdb に接続します。monitoring は常に本番 sqlite_path を使用する設計です（環境に依存しない）。
- AI 機能は API レスポンスを検証しており、失敗時はフェイルセーフでデフォルト値（例: macro_sentiment=0.0）にフォールバックしますが、APIキー管理・コストに注意してください。

開発／テスト
------------
- 自動で .env を読み込みますが、テスト時にその挙動が邪魔になる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- モジュールの設計は純粋関数化（副作用の少ない設計）を意識しているため、ユニットテストで個別関数を簡単にテストできます（外部リソースはモック可能）。

よく使うコマンドまとめ
---------------------
- .env を作る: python -m kabusys.config_setup
- 設定検証:     python -m kabusys.validate_config [--strict]
- 監視起動:     python -m kabusys.run_monitoring
- 実行エンジン: python -m kabusys.run_execution
- Paper 報告:   python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

ライセンス・貢献
----------------
このリポジトリ内のコードはそれぞれのライセンスに従ってください。外部提供のパッケージ（OpenAI, duckdb, psutil 等）は各々のライセンスに従います。貢献時はセキュリティに関わる情報（トークン・パスワード等）を含めないよう注意してください。

補足／問い合わせ
----------------
- 実行時のログは logs/ に出力されます（config: kabusys.utils.logging_setup）。
- 詳細な設計（PortfolioConstruction.md, StrategyModel.md 等）は別ドキュメントに記載される想定です。必要であれば README に追加します。

以上。README の補足や出力形式（Markdown の微調整、典型的な .env.example 追加など）を希望される場合は教えてください。