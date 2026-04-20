# KabuSys

日本株自動売買システムのライブラリ兼起動スクリプト群の README（日本語）。

このリポジトリは、戦略・ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、
AI を使ったニューススコアリング、研究ユーティリティ等を含むモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は日本株の自動売買（バックテスト / ペーパートレード / 本番）を支援する
モジュール群と、関連する運用スクリプトを提供します。主な機能は以下の通りです。

- 発注エンジン起動スクリプト（ExecutionEngine 起動）
- システム / 発注 / リスク監視のポーリング実行
- Paper Trading（模擬発注）向け DB 分離と検証レポート生成
- DuckDB を用いたファクター計算・リサーチユーティリティ
- OpenAI を用いたニュース NLP スコアリング（ai モジュール）
- 簡易的な設定ウィザード（.env 生成）と設定検証 CLI
- ロギング・プロセス優先度設定ユーティリティ等の共通ユーティリティ

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV による paper_trading 分離）
  - run_monitoring.py — システム監視（SystemMonitor）ポーリングループ起動

- 設定 / 検証
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — .env と config/*.yaml の事前チェック CLI

- 監視関連
  - monitoring_engine.py — 各 Monitor（System / Trade / Risk）を統合して実行
  - system_monitor.py / trade_monitor.py / risk_monitor.py — 個別監視ロジック
  - kill_switch.py — 条件に応じた停止フラグ（data/kill.flag）作成ロジック
  - monitoring_db.py — SQLite ベースの監視ログ永続化層

- 発注関連（execution 配下）
  - BrokerClientFactory（本番/モック分岐）
  - ExecutionEngine, OrderManager, OrderRepository, RiskManager, Reconciler

- ポートフォリオ構築（portfolio）
  - 銘柄選定、ウェイト計算、ポジションサイズ算出、セクター制限、レジーム乗数

- リサーチ（research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（情報係数）計算、統計サマリ

- AI（ai）
  - news_nlp: OpenAI を用いたニュースセンチメントの集約・スコア保存
  - regime_detector: MA200 とマクロニュースを合成して市場レジーム判定

- ツール
  - tools/paper_verification_report.py — Paper Trading の検証レポート生成

- ユーティリティ
  - utils/logging_setup.py — 統一ロギング設定
  - utils/process_priority.py — プロセス優先度 / CPU affinity 設定
  - config.py — 環境変数読み込み / Settings クラス（.env 自動読み込み機能含む）

---

## セットアップ手順（開発環境）

1. Python 環境を作成（推奨: venv / pyenv）
   - python 3.9+ を想定（実際の要件はプロジェクトに合わせてください）

2. 依存パッケージをインストール
   - 代表的な依存例（requirements.txt がない場合）:
     - duckdb
     - psutil
     - openai
     - PyYAML（validate_config で YAML 検証を使う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. プロジェクトルートに移動（.git または pyproject.toml を含む場所）
   - config.py はプロジェクトルートから .env / .env.local の自動ロードを行います。

4. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいは .env を手動で作成（以下にキーとデフォルト値を列挙）

5. 設定検証（オプション）
   - python -m kabusys.validate_config
   - 厳密モード（警告があれば exit(1)）:
     - python -m kabusys.validate_config --strict

6. データディレクトリの準備
   - デフォルトのパスは "data/" 以下にファイルを生成します（必要に応じて .env で上書き）。
   - ログはデフォルトで "logs/" に出力されます（LOG_DIR で変更可能）。

---

## 主要な環境変数（代表）

（秘密情報は .env に設定し、絶対に Git にコミットしないでください）

- 認証 / API
  - JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
  - KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
  - OPENAI_API_KEY — OpenAI API キー（ai モジュール使用時）

- システム / 実行
  - KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
  - LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）

- DB / ファイルパス
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — ExecutionEngine PID ファイルパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — kill.flag パス（デフォルト: data/kill.flag）

- Paper / Monitoring 固有
  - PAPER_FILL_MODE — MockBrokerClient の fill mode（instant | partial | never | reject、デフォルト: instant）
  - MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト: 60）

- 自動 .env 読み込み抑止（テスト用）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — config.py の自動 .env ロードを無効化

---

## 使い方（起動方法・コマンド例）

- ExecutionEngine を起動（Execution 用プロセス）
  - python -m kabusys.run_execution
  - 振る舞い:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。
    - _STOP_FLAG（data/stop_requested.flag）を監視し、存在すると起動を中止または実行中に停止します。
    - 起動直後にプロセス優先度を "high" に設定します（set_process_priority を使用）。
    - 実行中は PID ファイル（data/execution.pid 等）を書きます。

- Monitoring を起動（監視ポーリング）
  - python -m kabusys.run_monitoring
  - 振る舞い:
    - MONITOR_POLL_INTERVAL（秒）を環境変数で上書き可能（デフォルト: 60）。
    - 監視は常に settings.sqlite_path（本番の monitoring.db）を使用します（環境に依らず）。
    - SystemMonitor / TradeMonitor / RiskMonitor を用いてログを DB に永続化し、Kill Switch や AlertManager に通知します。
    - data/stop_requested.flag を検知するとループを終了します。

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード:
    - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- ライブラリ的に利用する関数
  - kabusys.research.calc_momentum / calc_volatility / calc_value
  - kabusys.ai.score_news(target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(...)
  - kabusys.portfolio.* の純粋関数群（選定・配分・サイズ計算）

---

## 監視・停止フローの概要

- kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）
  - KillSwitch により書き込まれる stop 指示ファイル。ExecutionEngine は起動時や稼働中にこれを参照して安全停止します。
  - kill.flag は意図的に手動で作成/削除できます。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアします（本番では注意）。

- stop_requested.flag（run_execution / run_monitoring で使用）
  - data/stop_requested.flag の存在により、run_execution/run_monitoring 側で即時終了処理を行います。
  - 通常は運用ツールやデプロイから設定されることを想定。

---

## ディレクトリ構成

（主要ファイルのみ抜粋。パッケージは src/kabusys 配下に配置されています）

- src/
  - kabusys/
    - __init__.py
    - config.py — 環境変数読み込みと Settings クラス
    - config_setup.py — 対話式 .env ウィザード（CLI）
    - validate_config.py — 設定検証 CLI
    - run_execution.py — ExecutionEngine 起動スクリプト
    - run_monitoring.py — Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート
    - ai/
      - news_nlp.py — ニュース NLP（OpenAI）スコアリング
      - regime_detector.py — 市場レジーム判定（MA200 + マクロニュース）
    - portfolio/
      - portfolio_builder.py — 候補選定・重み計算
      - position_sizing.py — 株数決定ロジック
      - risk_adjustment.py — セクターキャップ・レジーム乗数
      - __init__.py
    - research/
      - factor_research.py — ファクター計算（momentum/value/volatility）
      - feature_exploration.py — 将来リターン・IC・統計
      - __init__.py
    - monitoring/
      - monitoring_db.py — SQLite 永続化層
      - system_monitor.py — システム／データ鮮度監視
      - trade_monitor.py — 発注ログ監視（存在）
      - risk_monitor.py — ドローダウン / ポジション上限監視
      - kill_switch.py — 停止フラグ管理
      - monitoring_engine.py — 各 Monitor を束ねる実行ロジック
    - utils/
      - logging_setup.py — ロギング設定ユーティリティ
      - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
      - __init__.py

- data/ (ランタイムで生成される想定)
  - monitoring.db（デフォルト）
  - paper_trading.db（paper_trading 用）
  - kabusys.duckdb（DuckDB）
  - kill.flag / stop_requested.flag / execution.pid
- logs/
  - execution.log / monitoring.log など（TimedRotatingFileHandler による日次ローテーション）

---

## 注意事項・運用上のヒント

- 本番運用時は KABUSYS_ENV=live の設定に注意してください。validate_config は live の場合に追加警告を出します。
- .env は秘密情報を含むため絶対に Git にコミットしないでください（config_setup のヘッダにも明記）。
- Monitoring は設定に関わらず設定された monitoring.sqlite_path（デフォルト data/monitoring.db）を使う設計です。運用の分離に注意してください。
- Paper Trading は paper_trading 用 DB にデータを分離することで本番 DB と混ざらないように設計されています。
- OpenAI を使う機能は API 利用料が発生します。API キー・クォータ管理は十分に行ってください。
- ロギングディレクトリ作成に失敗した場合はファイル出力はスキップされ、コンソール出力のみで継続します。

---

## 参考コマンドまとめ

- .env を対話生成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- ExecutionEngine 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - or 指定 DB: python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

---

この README はリポジトリ内のスクリプト / モジュールの概要と運用に必要な最低限の情報をまとめたものです。詳細な振る舞いや設定は各モジュールの docstring とソースコードを参照してください。必要ならば具体的な起動例や systemd / supervisor のユニット定義例なども追加できます。希望があれば教えてください。