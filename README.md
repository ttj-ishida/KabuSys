# KabuSys — 日本株自動売買システム (README)

このリポジトリは日本株向けの自動売買・研究・監視ユーティリティ群をまとめたライブラリ / アプリ群です。  
本READMEはコードベースの主要機能、セットアップ方法、使い方、ディレクトリ構成を日本語でまとめたものです。

注意: 実際の運用では API キーやパスワードを含む .env を絶対に公開しないでください。

---

## プロジェクト概要

KabuSys は以下目的を持つコンポーネント群を含みます。

- 発注・実行エンジン（ExecutionEngine）
- 監視コンポーネント（System / Trade / Risk Monitor）
- Kill Switch（リスク条件に応じた発注停止）
- ポートフォリオ構築・ポジションサイジング・リスク調整の純粋関数群
- 研究向けファクター計算・特徴量探索
- AI を用いたニュースセンチメント評価（OpenAI 利用）
- 各種 CLI ユーティリティ（.env ウィザード、設定検証、レポート生成）

設計方針の例:
- DB は DuckDB（分析）・SQLite（監視/発注ログ）を併用
- Paper Trading は本番 DB と分離（専用 SQLite）
- できるだけ副作用を抑えた純粋関数を研究/ポートフォリオ系で提供
- OpenAI 呼び出しはフェイルセーフにして部分失敗時に他データを保護

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
  - 対話式で .env を作成 / 更新
- 設定検証 CLI（python -m kabusys.validate_config）
  - .env / config/*.yaml の基本チェック（--strict で警告も FAIL）
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading のときは MockBroker を使い paper_trading.db に記録
  - プロセス優先度設定・PID ファイル管理・停止フラグ対応
- Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - 定期ポーリングで System/Trade/Risk を監視、監視ログを SQLite に永続化
  - MONITOR_POLL_INTERVAL で間隔上書き可能（デフォルト 60 秒）
- Kill Switch
  - ドローダウン・ポジション上限等の条件を検出したら data/kill.flag を作成して Execution を停止
- Paper Trading 検証レポート（python -m kabusys.tools.paper_verification_report）
  - ペーパートレード DB のログを集計し Pass/Fail 判定（稼働率、注文成功率、P95 レイテンシ等）
- AI モジュール
  - kabusys.ai.news_nlp: raw_news を OpenAI に送って銘柄ごとのセンチメントスコア生成・書き込み
  - kabusys.ai.regime_detector: ETF マクロ指標 + LLM による市場レジーム判定
- 研究モジュール
  - kabusys.research: ファクター計算（momentum / volatility / value）、将来リターン、IC 計算 等
- ポートフォリオ構築
  - 候補選定、等比率 / スコア重み、ポジションサイズ計算、セクターキャップ/レジーム乗数適用 等
- 共通ユーティリティ
  - ログ設定（TimedRotatingFileHandler + stdout）
  - プロセス優先度 / CPU affinity 設定

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン:
   - git clone ...

2. Python 仮想環境を作成・有効化（例: venv）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール：
   - requirements.txt が無ければ少なくとも以下をインストールしてください:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML — validate_config の YAML 検証に必要
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env を作成:
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または .env.example を参考に手動作成。
   - 自動ロードはプロジェクトルート（.git または pyproject.toml のある場所）を基準に行われます。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データディレクトリ等の初期化:
   - data ディレクトリや logs ディレクトリは自動作成されますが、必要に応じて手動で作成してください。

6. 設定検証（推奨）:
   - python -m kabusys.validate_config
   - 問題がある場合は修正して再実行。--strict で警告を失敗にできます。

---

## 環境変数（主なもの）

- 必須（運用時）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: Execution は paper_trading 用 DB に記録（SQLITE 分離）
    - live: 実際に発注されるため注意

- DB / ファイルパス
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: 監視用デフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
  - PID_FILE_PATH / KILL_FLAG_PATH / LOG_DIR なども指定可能

- その他
  - LOG_LEVEL: DEBUG/INFO/...
  - PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動）
  - OPENAI_API_KEY: OpenAI を使う機能で必要
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番アラート用（任意）
  - MONITOR_POLL_INTERVAL: 監視ループの秒数（run_monitoring 用、デフォルト 60）

---

## 使い方（主要スクリプト / コマンド）

- 環境ウィザード（.env の作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も FAIL）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB に書き込み（本番 DB と分離）
  - 起動前に data/stop_requested.flag が存在すると起動をスキップ
  - 停止: data/stop_requested.flag を書くことで起動中スレッドに停止シグナルを送る

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒数で上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - monitoring は設定に関わらず sqlite_path（監視 DB）を使用してログ保存

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI / 研究機能はライブラリ関数として利用:
  - kabusys.ai.score_news(...)
  - kabusys.ai.regime_detector.score_regime(...)
  - kabusys.research.calc_momentum(...), calc_volatility(...), calc_value(...)

ログ:
- setup_logging が共通のログ設定を行います。ログは stdout と logs/<app_name>.log（日次ローテーション）へ出力されます。

停止・Kill Switch:
- Kill Switch は条件を満たすと data/kill.flag を作成します。ExecutionEngine は kill.flag を監視して停止できます（Settings.kill_flag_path を参照）。
- 明示的に停止したい場合は data/stop_requested.flag を作成すると起動スクリプトが検知して終了します。

---

## 動作上の注意点 / 運用ノウハウ

- Paper Trading と Live の DB は分離してください（デフォルト設計は分離済み）。
- OpenAI API を使う機能は API キーが必須です。失敗時はフェイルセーフな挙動（スコア 0 やスキップ）を取る設計ですが、API レートや費用に注意してください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを強く推奨します（自動クリアは危険）。
- validate_config は起動前に必ず実行して設定漏れやディレクトリ問題を検出すると良いです。
- ログディレクトリへの書き込み権限がないとファイルハンドラが無効化され、コンソール出力のみになります。

---

## ディレクトリ構成（主要ファイル・概要）

（プロジェクトルート / src/kabusys を想定）

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py
    - 環境変数の読み込み / Settings クラス / 自動 .env ロードロジック
  - config_setup.py
    - .env 対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py
    - 起動前チェック CLI（python -m kabusys.validate_config）
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - Monitoring ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
      - ペーパートレードログの集計・PASS/FAIL レポート
  - ai/
    - __init__.py
    - news_nlp.py
      - raw_news を OpenAI で評価して ai_scores に書き込む
    - regime_detector.py
      - ETF MA + マクロ NLP を組合せて market_regime を判定
  - research/
    - __init__.py
    - factor_research.py
      - momentum / volatility / value 等のファクター計算（DuckDB）
    - feature_exploration.py
      - forward returns / IC / 統計サマリ等
  - portfolio/
    - __init__.py
    - portfolio_builder.py
      - 候補選定・スコアソート
    - position_sizing.py
      - 単元丸め、allocation（risk_based / equal / score）
    - risk_adjustment.py
      - セクターキャップ、レジーム乗数
  - monitoring/
    - monitoring_db.py
      - SQLite テーブル作成 / MonitoringDB 操作用 API
    - system_monitor.py
      - システム状態・データ鮮度のチェック
    - risk_monitor.py
      - ドローダウン・ポジション上限監視
    - trade_monitor.py (参照あり)
    - kill_switch.py
      - data/kill.flag を書き込む Kill Switch
    - monitoring_engine.py
      - Monitor を束ねる実行ループ（テスト用 run_once / 実行用 run）
    - alert_manager.py (参照あり)
  - execution/
    - execution_engine.py (参照あり)
    - broker_factory.py (参照あり)
    - order_manager.py (参照あり)
    - order_repository.py (参照あり)
    - reconciler.py (参照あり)
    - risk_manager.py (参照あり)
  - utils/
    - __init__.py
    - logging_setup.py
      - 共通のログ設定（stdout + 日次ローテーション）
    - process_priority.py
      - Windows / POSIX を吸収する優先度設定・CPU affinity ユーティリティ
  - data/  (実行時に使用される)
    - monitoring.db (デフォルト: SQLITE_PATH)
    - kabusys.duckdb (デフォルト: DUCKDB_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kill.flag / stop_requested.flag / execution.pid などのフラグ・PID ファイル
  - logs/  (デフォルト)
    - execution.log, monitoring.log, ...（日次ローテーション）

---

## サンプルワークフロー

1. .env を作成（ウィザード）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config

3. 研究やデータ準備（DuckDB に prices_daily / raw_financials 等をロード）

4. Execution のテスト起動（paper_trading）
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

5. 監視の起動
   - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

6. Paper Trading レポート作成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

何か追加したいセクション（例: API ドキュメント、ユニットテストの実行方法、具体的な設定例など）があれば教えてください。README を利用目的に合わせて拡張して作成します。