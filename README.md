# KabuSys

日本株自動売買システムのコアライブラリ（リポジトリ内の一部）。  
この README はソースコード（src/kabusys/*）に基づく簡潔な導入・利用ガイドです。

※ 本リポジトリはパッケージ内部向けのモジュール群を含み、実運用には別途外部設定（.env）や依存ライブラリのインストールが必要です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。  
主な機能は以下の通りです。

- 注文発行 / 発注管理（ExecutionEngine、OrderManager、RiskManager 等）
- システム監視（SystemMonitor、MonitoringEngine）
- リスク監視（ドローダウン監視、ポジション上限）
- ペーパートレード分離（KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用）
- ファクター計算・リサーチ（momentum, volatility, value など）
- ニュース NLP によるセンチメント解析（OpenAI API を使用）
- Paper Trading 検証レポート生成ツール
- 環境設定ウィザード・設定検証ツール（.env の作成／検証）

---

## 主な機能一覧

- 実行系
  - run_execution.py: ExecutionEngine 起動スクリプト（本番/ペーパー切替）
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定可）

- 監視系
  - MonitoringEngine: 各モニタ（System/Trade/Risk）をまとめて定期実行
  - SystemMonitor: CPU/メモリ/ディスク/プロセス・データ鮮度チェック
  - RiskMonitor: ドローダウン・ポジション上限の検出、ダッシュボード更新
  - KillSwitch: 条件達成で data/kill.flag を書き込むことで Execution を停止

- ポートフォリオ構築
  - 銘柄選定（score / equal）
  - 重み計算、ポジションサイズ計算（単元株丸め、aggregate cap）

- リサーチ
  - factor_research: momentum / volatility / value 等のファクター計算（DuckDB 接続で動作）
  - feature_exploration: 将来リターン / IC /統計サマリ等

- AI（外部 API）
  - news_nlp: raw_news を OpenAI に送り銘柄ごとのセンチメントを ai_scores テーブルへ登録
  - regime_detector: ETF（1321）MA とニュースセンチメントを合成して市場レジームを判定・保存

- ツール
  - config_setup.py: .env を対話式に作成／更新するウィザード
  - validate_config.py: .env / config/*.yaml 等の起動前検証
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポートを生成

---

## 必要条件 / 依存

- Python 3.10+
- 主な Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config.yaml のパース確認に必要、なくても動作する箇所あり）

実行環境によってはさらに依存があります（例えば broker クライアント等）。requirements.txt がある場合はそちらを使用してください。

---

## 環境変数（重要）

必須（少なくとも起動検証でチェックされる）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

代表的な任意 / 推奨:
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
  - paper_trading の場合、MockBroker と別 DB（data/paper_trading.db）が使用されます
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 等で使用）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

Kill / Stop フラグ:
- data/stop_requested.flag: run_execution / run_monitoring が監視している停止フラグ（存在するとループを終了）
- data/kill.flag: KillSwitch が書き込む停止シグナル（ExecutionEngine 停止要求）

設定ファイルの自動読み込み:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env / .env.local があれば自動で読み込まれます。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## セットアップ手順（推奨）

1. リポジトリをチェックアウト
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - 実運用では broker クライアント等の追加依存が必要になる場合があります
4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参照）
5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告を厳格に扱いたい場合は --strict を付ける
6. データディレクトリとログディレクトリの作成（自動作成されることが多いが事前に準備しておくと良い）
   - mkdir -p data logs

> 注意: run_monitoring/run_execution はそれぞれ起動時に DB テーブルの初期化（監視用テーブルなど）を呼びます。

---

## 使い方（主要コマンド例）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading モードでは MockBrokerClient が使われ、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録されます
  - 停止は data/stop_requested.flag を作成するか、プロセスを終了する（Ctrl+C）

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変える:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - run_monitoring は常に本番 sqlite_path（Settings.sqlite_path）を使って監視テーブルを記録します
  - 停止は data/stop_requested.flag を作成するか、Ctrl+C

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- プログラムからの利用（例）
  - AI スコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="xxxx")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, date(2026,4,1), api_key="xxxx")
  - リサーチ / ファクター計算:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value
    - 各関数に DuckDB 接続と target_date を渡して利用

---

## 停止・Kill フラグの挙動

- run_execution/run_monitoring はプロジェクトルート下の data/stop_requested.flag を監視しており、存在検出で安全にループを終了します。
- KillSwitch（リスク超過時）は data/kill.flag を作成し、これを見て ExecutionEngine 停止などのアクションを行います（kill フラグの自動クリアは環境変数 KILL_FLAG_CLEAR_ON_START で制御）。
- PID ファイル（data/execution.pid）を使用してプロセス管理を行う箇所があります。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理
  - config_setup.py              — .env 対話ウィザード
  - validate_config.py           — 設定検証スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py           — ログ設定ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py           — SQLite 永続化層（監視）
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py
    - kill_switch.py
    - alert_manager.py (※存在想定)
  - execution/
    - execution_engine.py (※存在想定)
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/ (実行時生成)
    - monitoring.db (デフォルト)
    - paper_trading.db (ペーパートレード用)
    - kill.flag, stop_requested.flag, execution.pid
  - logs/ (デフォルトのログ出力先)

（実際の追加ファイル / 依存モジュールはリポジトリ内の全ファイルを参照してください）

---

## 運用上の注意

- KABUSYS_ENV を `live` にセットする際は非常に注意してください。validate_config の結果や LINE 通知設定などを十分に確認してください。
- .env ファイルは決してリポジトリにコミットしないでください（config_setup でも注意書きがあります）。
- OpenAI API を利用する機能は API キーが必要であり、利用量に応じて課金されます。レート制限やエラー処理（リトライ）は実装されていますが、運用時のコストと遅延を考慮してください。
- 監視・停止フラグ（kill.flag / stop_requested.flag）や PID ファイルによる運用設計が組み込まれています。運用ルール（誰がフラグを立てる/消すか）を明確にしてください。

---

## 問い合わせ・拡張

- リサーチ機能や AI モジュールは外部データ（prices_daily / raw_financials / raw_news 等）を前提としています。DuckDB に必要なテーブルが存在することを確認してください。
- テスト／CI で自動的に設定を差し替えたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して .env 自動読み込みを抑制できます。

---

以上がこのコードベース（src/kabusys/*）の概要と導入・利用手順です。追加で README に記載したい実行例や、各モジュールの詳細ドキュメント（API 仕様、設定項目の詳細など）が必要であればお知らせください。