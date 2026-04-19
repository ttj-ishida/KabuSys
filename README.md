KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買システムの一部を提供する Python コードベースです。本リポジトリには以下の主要機能が含まれます。

- 実行エンジン（ExecutionEngine）の起動スクリプト（本番／ペーパートレード対応）
- 監視・アラート（System / Trade / Risk monitor）および Kill Switch
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定、セクター制約）
- リサーチ（ファクター計算、特徴量探索）
- AI を使ったニュースセンチメント（OpenAI）を用いたスコアリング／レジーム判定
- 運用補助ツール（.env ウィザード、設定検証、レポート生成）
- ログ設定・プロセス優先度ユーティリティ等のユーティリティ群

主要な設計方針
- DuckDB / SQLite を使ったローカルデータ管理（分析・監視）
- Paper trading は本番 DB と完全分離（専用 SQLite を使用）
- ルックアヘッドバイアス対策（日時参照を明示的に渡す設計）
- フェールセーフ設計（API 失敗時のフォールバック、部分失敗時の DB 保護）

機能一覧
--------
- 実行関連
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使い別 DB へ記録。
  - BrokerFactory / OrderManager / RiskManager / Reconciler 等の実行コンポーネント（実行ロジックは別モジュールに分離）。
- 監視関連
  - run_monitoring.py: SystemMonitor をポーリングで回す起動スクリプト（MONITOR_POLL_INTERVAL で間隔変更可）。
  - MonitoringEngine: System/Trade/Risk モニターを束ね、KillSwitch 判定や AlertManager への通知を行う。
  - MonitoringDB: system_status, trade_logs, positions, risk_logs, dashboard テーブルを管理（マイグレーション含む）。
  - KillSwitch: リスクトリガで data/kill.flag を作成し Execution を停止させる仕組み。
- ポートフォリオ構築
  - 候補選定・スコア降順選択、等金額・スコア重みの計算
  - セクター集中抑制、レジーム乗数
  - ポジションサイズ決定（リスクベース / equal / score）、単元株丸め、aggregate cap 対応
- リサーチ
  - factor_research: Momentum / Volatility / Value の計算（DuckDB の prices_daily / raw_financials を参照）
  - feature_exploration: 将来リターン計算、IC（スピアマン）等
- AI モジュール
  - ai.news_nlp: raw_news を OpenAI に送って銘柄ごとのセンチメントスコアを ai_scores に書き込む
  - ai.regime_detector: ETF の MA とマクロニュースを LLM 評価で合成し market_regime を作成
- ツール
  - config_setup.py: 対話式で .env を生成・更新するウィザード
  - validate_config.py: .env と config/*.yaml の整合性チェック（--strict オプションあり）
  - tools.paper_verification_report: Paper Trading の検証レポート生成

前提／推奨環境
--------------
- Python 3.10 以上（PEP 604 の union 型表記などを使用）
- 必要な主要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証を行う場合）
- SQLite は標準ライブラリで利用可

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - pip install duckdb psutil openai pyyaml
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

4. .env を準備
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいはテンプレートをコピーして編集（.env.example があれば参照）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - （OpenAI を使う場合）OPENAI_API_KEY
   - 主な環境変数（省略時はデフォルトを使用）
     - KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - PAPER_FILL_MODE: instant | partial | never | reject  (default: instant)
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
     - KILL_FLAG_CLEAR_ON_START: 0 | 1
     - PID_FILE_PATH, KILL_FLAG_PATH 等（デフォルトは data 以下）

5. 設定検証
   - python -m kabusys.validate_config
   - 厳密モード: python -m kabusys.validate_config --strict

使い方
------
- 実行エンジン（ExecutionEngine）を起動
  - 本番 / ペーパートレードの挙動は KABUSYS_ENV に依存
  - コマンド:
    - python -m kabusys.run_execution
  - 特徴:
    - 起動時にプロセス優先度を "high" に設定（set_process_priority）
    - Paper trading の場合は settings.paper_sqlite_path を使用して本番 DB と分離
    - 停止方法: プロジェクトルートの data/stop_requested.flag を作成するとエンジン停止処理が行われる

- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - 特徴:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒指定（デフォルト 60 秒）
    - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存せず本番 DB を監視）
    - stop は data/stop_requested.flag で検出してループ終了

- Kill Switch（監視 → 実行停止）
  - RiskMonitor が閾値超過などを検知し、KillSwitch が data/kill.flag に理由を記載して書き込むと ExecutionEngine 側で停止を検知できる
  - 起動時の KILL_FLAG_CLEAR_ON_START=1 により kill.flag を自動でクリアする挙動を有効化できる（本番では 0 を推奨）

- ログ
  - ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution" など)
  - デフォルトログディレクトリ: logs/
  - 日次ローテーション、30 日保持
  - コンソールは stdout に出力

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db or 環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数）
  - ニューススコアリング:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - API 呼び出しはリトライ・バックオフやレスポンス検証などの安全機構を持つ

運用上の注意
-------------
- KABUSYS_ENV=live の場合は本番扱いになるため、LINE 通知や kill フラグ設定など全設定を十分に確認してください。
- .env は絶対にリポジトリへコミットしないでください（config_setup のヘッダにも注意書きあり）。
- データベースファイル（DuckDB / SQLite）はデフォルトで data/ 配下に保存されます。必要に応じて環境変数で変更してください。
- プロセス停止フロー:
  - graceful stop: data/stop_requested.flag を作成すると run_execution / run_monitoring が検出して終了します
  - kill flag: KillSwitch が data/kill.flag を作成すると ExecutionEngine 側で停止がトリガされます
- ログディレクトリ作成に失敗した場合はファイル出力が無効化され、コンソール出力のみとなります（警告ログあり）

ディレクトリ構成
----------------
（src/kabusys 配下の主要ファイル / モジュールを抜粋）

- src/kabusys/
  - __init__.py                       — パッケージ定義（__version__ = "0.1.0"）
  - config.py                         — 環境変数 / Settings 管理（.env 自動ロード、Defaults、検証）
  - config_setup.py                   — 対話式 .env ウィザード
  - validate_config.py                — 起動前設定検証 CLI
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - run_monitoring.py                 — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py    — ペーパー検証レポート生成ツール
  - utils/
    - __init__.py
    - logging_setup.py                — ログ初期化ユーティリティ
    - process_priority.py             — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py                — SQLite テーブル初期化・永続化層
    - monitoring_engine.py            — 各 Monitor を束ねるエンジン
    - system_monitor.py               — システム状態・データ鮮度監視
    - trade_monitor.py                — （注文監視ロジック）※実装参照
    - risk_monitor.py                 — ドローダウン・ポジション上限監視
    - kill_switch.py                  — kill.flag 制御
    - alert_manager.py                — （アラート送信管理）※実装参照
  - execution/
    - execution_engine.py             — ExecutionEngine 本体（起動/セッション管理）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py            — 候補選定・重み付け
    - position_sizing.py              — 発注株数計算
    - risk_adjustment.py              — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py              — ファクター計算（Momentum/Volatility/Value）
    - feature_exploration.py          — 将来リターン・IC・統計サマリー
    - __init__.py
  - ai/
    - news_nlp.py                     — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py              — 市場レジーム判定（MA + マクロセンチメント）
    - __init__.py

よくある操作例
---------------
- .env を作る（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告を FAIL 扱い）
    - python -m kabusys.validate_config --strict

- 監視を起動（コンソール実行）
  - python -m kabusys.run_monitoring

- 実行エンジンを起動（コンソール実行）
  - python -m kabusys.run_execution

- Paper Trading レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

補足
----
- YAML の検証は PyYAML がインストールされている場合のみ実施されます（validate_config）。
- DuckDB / OpenAI を使った処理は対象テーブル（prices_daily, raw_news, raw_financials 等）が必要です。データ投入や ETL は別モジュール（kabusys.data.pipeline 等）を参照してください。
- 本 README はコード内の docstring / コメントに基づいて作成しています。実運用時は本 README をプロジェクトの実態に合わせて更新してください。

ライセンス・バージョン
---------------------
- パッケージバージョン: src/kabusys/__init__.py の __version__ を参照してください（現在: 0.1.0）

問題報告・貢献
---------------
バグ報告や修正提案は issue / pull request を通じて受け付けてください。README の改善提案も歓迎します。