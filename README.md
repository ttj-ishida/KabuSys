KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買・研究・監視コンポーネント群をまとめた Python パッケージです。  
README ではプロジェクト概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめています。

概要
----
KabuSys は以下の機能を持つモジュール群から構成されます。

- 実運用用 ExecutionEngine（発注・リスク管理・オーダー管理）
- 監視サブシステム（System / Trade / Risk の定期チェック、Kill Switch）
- ポートフォリオ構築（候補選定、ウェイト計算、ポジションサイズ算出）
- リサーチ（ファクター計算、特徴量探索、将来リターン・IC）
- AI 補助（ニュースの NLP スコアリング、レジーム判定）
- 各種ユーティリティ（設定読み込み、ログ設定、プロセス優先度設定）
- ツール類（Paper Trading の検証レポート生成など）

設計方針のポイント
- 本番 / ペーパートレードを環境変数 KABUSYS_ENV で切り替え（paper_trading では発注をモックし DB を分離）
- .env と config/*.yaml を利用した設定管理（config_setup.py による対話ウィザード）
- ログはコンソール + 日次ローテートファイル出力（logs/<app>.log、30日保持）
- AI 呼び出し（OpenAI）は API キーを環境変数で渡す。呼び出し部はリトライ・フェイルセーフ実装

主な機能一覧
----------------
- Execution
  - 発注エンジン起動スクリプト: run_execution (python -m kabusys.run_execution)
  - Paper Trading モードでは MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
  - プロセス優先度設定、PID ファイル管理、停止フラグ監視

- Monitoring
  - システム監視: CPU/Memory/Disk、注文プロセスの存否、データ鮮度チェック
  - トレード監視: 滞留注文検出・約定異常の検出
  - リスク監視: ドローダウンやポジション上限の検出、kill.flag 発行
  - 監視ループ起動スクリプト: run_monitoring (python -m kabusys.run_monitoring)
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）

- Research / Portfolio
  - ファクター計算: Momentum / Volatility / Value（DuckDB を利用し prices_daily/raw_financials を参照）
  - 特徴量解析: 将来リターン計算、IC（スピアマン）計算、統計サマリ
  - ポートフォリオ構築: 候補選定、等金額・スコア加重、リスクベース配分、セクターキャップ、ポジションサイズ算出（単元丸め含む）

- AI
  - ニュース NLP: raw_news を OpenAI に渡して銘柄ごとのセンチメントを ai_scores に書き込む（kabusys.ai.score_news）
  - レジーム判定: ETF（1321）MA200 とマクロニュースセンチメントを合成して market_regime を計算（kabusys.ai.regime_detector.score_regime）
  - OpenAI API 呼び出しはリトライ、JSON バリデーション、スコアクリッピング等の堅牢化あり

- ツール
  - Paper Trading 検証レポート生成: kabusys.tools.paper_verification_report（期間指定可）

前提条件 / 依存ライブラリ
------------------------
最低限の依存（本リポジトリ内で参照されている主要パッケージ）:
- Python 3.9+（型ヒント等を用いた実装のため推奨）
- duckdb
- psutil
- openai (AI 関連機能を使う場合)
- PyYAML（config 検証機能を利用する場合に推奨）

インストール例（仮のコマンド例 — requirements.txt が無い場合は手動で）:
- 仮想環境作成:
  - python -m venv .venv
  - source .venv/bin/activate
- 必要パッケージのインストール:
  - pip install duckdb psutil openai PyYAML

セットアップ手順
----------------
1. リポジトリをクローンしてワークツリーを準備
2. Python 仮想環境を作成して有効化
3. 必要パッケージをインストール（上記参照）
4. .env を準備（対話式ウィザードを推奨）

.env の作成（対話式）
- 実行:
  - python -m kabusys.config_setup
- ウィザードが .env を生成します（J-Quants、kabuAPI、DB パス、KABUSYS_ENV などの主要設定を対話式で設定）。

設定検証
- 対応: python -m kabusys.validate_config
- オプション: --strict を付けると警告も失敗扱い（exit 1）になります。
- validate_config は必須環境変数の有無、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在、config/*.yaml の存在・パース（PyYAML 必要）等をチェックします。

主要環境変数（よく使うもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: 分析用 DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（paper_trading のときに使用、デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject、デフォルト instant）
- OPENAI_API_KEY: OpenAI を使う場合に設定
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

実行方法（サンプル）
-------------------
- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を .env または環境に設定すると、MockBrokerClient と data/paper_trading.db を使用します。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中は data/execution.pid を利用（PID 管理）、停止は stop flag 書き込みで行います。

- Monitoring 起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を環境変数で上書き可能（例: export MONITOR_POLL_INTERVAL=120）
  - 監視は常に本番用 sqlite_path（settings.sqlite_path）を使用してログを保存します。

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI / レジーム判定（プログラムから呼び出す API）
  - from kabusys.ai import score_news
  - from kabusys.ai.regime_detector import score_regime
  - OpenAI API キーは OPENAI_API_KEY 環境変数で指定

停止フラグ・Kill Switch
---------------------
- data/stop_requested.flag: run_execution / run_monitoring の外部終了シグナル（ファイルが存在するとループを抜ける / 起動を拒否）
- data/kill.flag: KillSwitch によって書き込まれる（リスク閾値超過など）。存在すると ExecutionEngine に停止を促す（外部で削除することで解除可能）
- PID ファイル: data/execution.pid（ExecutionEngine 起動で使用）

ログ
----
- ログは標準出力（stdout）とファイル（logs/<app>.log）に出力されます。
- ローテーション: 日次、30日分保持
- ログディレクトリは環境変数 LOG_DIR で指定可能。デフォルト logs/

パッケージ API（主要モジュール）
--------------------------------
- kabusys.config: Settings クラス（環境変数ラッパー）
- kabusys.run_execution: ExecutionEngine 起動スクリプト
- kabusys.run_monitoring: SystemMonitor ポーリング起動スクリプト
- kabusys.config_setup / validate_config: .env ウィザード / 設定検証
- kabusys.monitoring: MonitoringDB, SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine 等
- kabusys.portfolio: select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- kabusys.research: calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.ai: score_news（ニュース NLP）、regime_detector.score_regime（市場レジーム判定）
- kabusys.tools.paper_verification_report: ペーパートレード検証レポート生成

ディレクトリ構成
----------------
（src/kabusys 以下を抜粋して表示）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring 起動スクリプト
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py        — システム状態・データ鮮度監視
    - trade_monitor.py         — （滞留注文・約定異常等の検出）※実装参照
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag 管理
    - monitoring_engine.py     — 複数 Monitor をまとめてポーリング
    - alert_manager.py         — アラート送信（LINE など）※実装参照
  - execution/
    - execution_engine.py      — 実行エンジン（EngineConfig 等）
    - order_manager.py         — 注文管理
    - order_repository.py      — DB 経由の注文保存
    - broker_factory.py        — ブローカー選択（Mock / 実ブローカー）
    - reconciler.py            — 注文整合処理
    - risk_manager.py          — 発注前リスクチェック, RiskConfig
  - portfolio/
    - portfolio_builder.py     — 候補選定・ウェイト計算
    - position_sizing.py       — 株数・投下資金計算
    - risk_adjustment.py       — セクター上限・レジーム乗数
  - research/
    - factor_research.py       — Momentum/Value/Volatility 計算
    - feature_exploration.py   — 将来リターン・IC・統計
  - ai/
    - news_nlp.py              — ニュース NLP スコアリング（OpenAI 呼び出し・バリデーション）
    - regime_detector.py       — レジーム判定（MA200 + マクロセンチメント）
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

補足 / 運用上の注意
------------------
- 本番環境（KABUSYS_ENV=live）では必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を必ず適切に設定してください。validate_config の警告・エラーを確認してください。
- kill.flag / stop_requested.flag の取り扱いに注意してください。特に本番での自動クリアは危険（KILL_FLAG_CLEAR_ON_START を 1 にすることは避けることを推奨）。
- OpenAI 呼び出しや外部 API の失敗はフェイルセーフ設計ですが、API キーの漏洩・料金に注意してください。
- DB ファイル (DuckDB / SQLite) のバックアップ・権限管理を適切に行ってください。

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス情報が別途ある場合はそちらを参照してください（本 README には含まれていません）。

問い合わせ・貢献
----------------
バグ報告、改善提案、機能追加のプルリクエストは歓迎します。まずは issue を立ててください。

以上がこのコードベースの主要説明です。必要であれば、特定モジュール（例: ExecutionEngine の設定パラメータや RiskConfig の詳細、AI モジュールのプロンプト/バッチ処理仕様など）についての詳しいドキュメントやサンプルを追記します。どの箇所を深掘りしますか？