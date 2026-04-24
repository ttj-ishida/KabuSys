# KabuSys — 日本株自動売買システム README

このリポジトリは日本株向けの自動売買システム（KabuSys）のコアライブラリ群です。戦略の研究、ポートフォリオ構築、注文実行、監視、AI（ニュース NLP / レジーム検出）などの機能をモジュール化して提供します。本ファイルはコードベースの概要、主要機能、セットアップ方法、使い方、ディレクトリ構成を日本語でまとめた README.md です。

注意: 本 README はソースコード（src/kabusys 配下）に基づく説明です。実運用では .env による環境設定や本番/ペーパートレードの切り替えに十分注意してください。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要スクリプト・CLI の実行例）
- 環境変数（主なキーとデフォルト）
- 停止・Kill スイッチ運用
- ディレクトリ構成（主要ファイルの説明）

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能を備えたモジュール型ライブラリです。

- 市場データ（DuckDB）を用いたファクター計算・リサーチ
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 発注エンジン（ExecutionEngine）とブローカークライアント抽象化（paper/live 切替）
- 監視モジュール（System / Trade / Risk）とアラート・Kill スイッチ
- AI 補助（ニュースセンチメント、レジーム判定） — OpenAI API を利用
- CLI ユーティリティ（.env ウィザード、設定検証、検証レポート）

設計方針の一部:
- 本番用の監視ログ（monitoring）は環境に関わらず本番の sqlite パスを使うなど、実運用を意識した設計がなされています。
- Paper trading（KABUSYS_ENV=paper_trading）は発注をモック化して DB を分離します（data/paper_trading.db）。
- LLM 呼び出しはリトライ・バリデーション・スコアクリップ等のフェイルセーフを備えています。

---

## 機能一覧

主なモジュール / 機能

- kabusys.config
  - .env/.env.local の自動読み込み、Settings クラス（環境変数ラップ）
- kabusys.config_setup
  - 対話式ウィザードで .env を生成・更新
- kabusys.validate_config
  - 起動前に環境変数/設定ファイルを検証する CLI
- kabusys.run_execution
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じて実 DB / Paper 切替）
- kabusys.run_monitoring
  - SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定）
- kabusys.monitoring (system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, monitoring_db)
  - 監視・監査ログ・Kill スイッチの実装
- kabusys.portfolio (portfolio_builder, position_sizing, risk_adjustment)
  - 候補選定、重み付け、ポジションサイズ、セクター制限、レジーム乗数
- kabusys.research (factor_research, feature_exploration)
  - ファクター計算（Momentum/Value/Volatility 等）、将来リターン・IC 計算等
- kabusys.ai (news_nlp, regime_detector)
  - OpenAI を使ったニュースセンチメント付与とレジーム判定
- kabusys.tools.paper_verification_report
  - ペーパートレード DB を解析し PASS/FAIL レポートを出力
- utils（logging_setup, process_priority）
  - 統一ログ設定、プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順

前提
- Python 3.9+ を想定（DuckDB / psutil / openai 等はそれぞれ互換性のあるバージョンを使用）
- 仮想環境（venv, poetry, pipenv 等）の使用を推奨

1. リポジトリをクローンして作業ディレクトリに移動
   - git clone ... && cd <repo>

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS) / .venv\Scripts\activate (Windows)

3. 依存パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt
   - または最低限インストール例:
     - pip install duckdb psutil openai

   （PyYAML は validate_config における YAML 検証に必要。不要なら skip 可能）

4. 環境変数ファイルを作成
   - 対話式で .env を作成する:
     - python -m kabusys.config_setup
   - または .env を手動で作成（.env.example を参照）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 問題がなければ exit 0。--strict を付けると警告も失敗扱いになります。

6. 必要ディレクトリの確認
   - デフォルトの DB / ログディレクトリはプロジェクト内の data/ と logs/（自動作成されます）
   - 実行時に自動的に作成されますが、権限を確認してください。

---

## 使い方

基本的にはパッケージとして実行する形式です。いくつかの主要なコマンド例を示します。

- Execution（注文エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト data/paper_trading.db）へ記録します
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します
    - 実行中は data/execution.pid に PID を書く（設定で変更可）

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き（デフォルト 60）
      - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 注意:
    - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用して監視 DB を初期化します
    - data/stop_requested.flag の検出で監視ループを終了します

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict  （警告を fail 扱い）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI（ニュース NLP / レジーム判定）
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と API キーが必要
  - OPENAI_API_KEY を環境変数で設定するか、関数呼び出しで明示的に api_key を渡す

プロセス優先度 / ログ
- 起動スクリプトは起動直後にプロセス優先度を "high" に設定しようとします（psutil による）。権限不足の場合は警告となりスキップされます。
- ログはデフォルトで logs/<app_name>.log に日次ローテートで出力（logs/ ディレクトリを作成）。

停止・Kill 操作
- 実行エンジンを外部から停止させるにはプロジェクトルートの data/stop_requested.flag を作成します（run_execution はこのフラグ検出で正常に停止）。
- Kill Switch（自動停止基準）:
  - risk_monitor 等が条件に合致した場合、data/kill.flag を書き込み ExecutionEngine に停止を指示できます（KillSwitch クラス）。
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨（自動クリアは危険）。

---

## 主な環境変数（抜粋）

- KABUSYS_ENV
  - 値: development / paper_trading / live
  - デフォルト: development
- JQUANTS_REFRESH_TOKEN
  - 必須（J-Quants API 用）
- KABU_API_PASSWORD
  - 必須（kabuステーション API 用）
- KABU_API_BASE_URL
  - デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH
  - デフォルト: data/kabusys.duckdb
- SQLITE_PATH
  - 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH
  - paper_trading 用 DB（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE
  - PaperTrade の約定挙動（instant | partial | never | reject）、デフォルト: instant
- LOG_LEVEL
  - デフォルト: INFO
- LOG_DIR
  - ログ保存先。デフォルト logs/
- OPENAI_API_KEY
  - AI モジュールで使用
- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング秒数（デフォルト 60）
- KILL_FLAG_CLEAR_ON_START
  - 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

自動 .env ロード
- プロジェクトルートにある .env / .env.local は自動でロードされます（OS 環境変数が優先）。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 停止・Kill スイッチ運用

- 手動停止（外部）:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring は次のループで停止します。
- 自動停止（Kill Switch）:
  - RiskMonitor がドローダウンやポジション上限を検出した場合、KillSwitch が data/kill.flag を書き込みます。ExecutionEngine は起動時に kill.flag をチェックし、書き込みがあれば起動を拒否または停止処理を行います。
- kill.flag のクリア:
  - KillSwitch.clear() を呼ぶか、ファイルを削除してください（本番では自動クリアを無効にすることを推奨）。

---

## ディレクトリ構成（主なファイルの説明）

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス、.env 自動ロード、環境変数検証ユーティリティ
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper/live 切替）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py : SQLite ベースの監視ログ層（初期化・読み書き）
    - system_monitor.py : CPU/メモリ/Disk/プロセス/データ鮮度監視
    - trade_monitor.py : （ソース中に存在）発注ログ監視（滞留注文等、コード参照）
    - risk_monitor.py : ドローダウン・ポジション上限監視
    - kill_switch.py : Kill スイッチの判定・ファイル書き込み
    - monitoring_engine.py : 各 Monitor を束ねる（run_once / run）
    - alert_manager.py : （通知・LINE 等の実装箇所）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
      - 発注エンジン、注文管理、リスク管理、ブローカ抽象化
  - portfolio/
    - portfolio_builder.py : 候補選定・重み付け
    - position_sizing.py : 株数決定・スケールダウン処理
    - risk_adjustment.py : セクター制限・レジーム乗数
  - research/
    - factor_research.py : Momentum/Value/Volatility ファクター計算（DuckDB）
    - feature_exploration.py : 将来リターン・IC・summary
  - ai/
    - news_nlp.py : ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py : ETF MA + マクロニュースでレジーム判定、DB 書き込み
  - tools/
    - paper_verification_report.py : ペーパートレード DB を解析して検証レポート出力
  - utils/
    - logging_setup.py : 一貫したログ設定（stdout + 日次ファイルローテーション）
    - process_priority.py : プロセス優先度/CPU affinity のプラットフォーム互換ヘルパ

プロジェクトルート（例）
- .env, .env.local (環境設定)
- data/ (DB, PID, stop/kill フラグ等)
  - monitoring.db (デフォルト)
  - paper_trading.db (paper_trading 用)
  - stop_requested.flag, kill.flag, execution.pid
- logs/
  - execution.log, monitoring.log, ...

---

補足・運用上の注意
- 本システムは実際に発注を行うため、KABUSYS_ENV=live の設定時はすべての設定を慎重に確認してください（validate_config には live ガードチェックあり）。
- OpenAI API を使用する機能は API コスト・レイテンシ・エラー耐性を考慮して実装されていますが、営業時間中の過剰な呼び出しや認証情報漏洩には注意してください。
- SQLite / DuckDB ファイルのバックアップやアクセス権限、ログローテーション先のディスク容量を監視することを推奨します。

---

この README はソースコードに基づく概要です。各モジュールの詳細な使い方や設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）がリポジトリにある場合はそちらも参照してください。必要であれば、特定モジュールの API 使用例や設計意図を追記します。