# KabuSys — 日本株自動売買システム (README)

このリポジトリは、日本株向けの自動売買システムのコアライブラリ群です。戦略・ポートフォリオ構築、発注実行、監視、研究（ファクター計算）や AI を使ったニュース評価などの機能を含みます。

以下はプロジェクトの概要、主要機能、セットアップ手順、使い方、ディレクトリ構成のまとめです。

---

## プロジェクト概要

- 名前: KabuSys
- 目的: 日本株自動売買に必要なコンポーネント（シグナル生成・ポートフォリオ構築・注文実行・監視・ログ保存・解析）を提供するライブラリ群。
- 設計方針:
  - モジュール化された純粋関数と状態管理コンポーネントを分離
  - DB は DuckDB（分析）と SQLite（監視/履歴）を利用
  - Paper Trading と Live を分離（ペーパートレードは専用 SQLite に記録）
  - 環境変数/.env による設定管理（config_setup による対話式ウィザード、validate_config による検証）
  - OpenAI（gpt-4o-mini 等）を使ったニュース NLP / レジーム判定機能（オプション）

---

## 主な機能一覧

- 設定管理
  - .env 自動ロード（プロジェクトルートの .env/.env.local）
  - 対話式の .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）

- 実行（Execution）
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper Trading サポート（KABUSYS_ENV=paper_trading で MockBroker を使用し専用 DB に記録）
  - プロセス優先度設定、PID ファイル管理、停止フラグ検出

- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（run_monitoring.py）
  - Monitoring DB（SQLite）へのログ保存（system_status, trade_logs, positions, risk_logs, dashboard）
  - Kill Switch：条件に応じて data/kill.flag を書き込み、ExecutionEngine 停止をトリガー
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）

- ポートフォリオ構築
  - 候補選定、等配分/スコア加重配分、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元株丸め・集約上限処理・スケーリング）

- 研究/分析
  - DuckDB を用いたファクター計算モジュール（モメンタム / バリュー / ボラティリティ 等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（オプション）
  - ニュース記事のセンチメントを OpenAI でスコアリング（news_nlp）
  - マクロニュースと ETF MA を合成した市場レジーム判定（regime_detector）
  - OpenAI API の利用は環境変数 OPENAI_API_KEY が必要

- ツール
  - Paper Trading の検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 環境変数（主なもの）

（多くは .env に記載する想定。対話式ウィザードで設定可能）

必須（最低限）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意/設定:
- KABUSYS_ENV: execution 環境（development | paper_trading | live）。デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト: INFO
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring で利用。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（'1' でクリア）

ログ:
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）

その他:
- PID_FILE_PATH, KILL_FLAG_PATH 等は Settings から指定可能（デフォルトは data/ 以下）

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - （requirements.txt がある想定。なければ下記を参考に必要ライブラリをインストール）
   - pip install duckdb psutil openai
   - オプション: PyYAML（config 検証で YAML パースを有効にする場合）: pip install pyyaml

4. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または .env.example を参考に手動で作成

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い: python -m kabusys.validate_config --strict

6. DB・ログディレクトリ作成（自動で作成されることが多いですが、権限等で失敗する場合は手動）
   - mkdir -p data logs

注意:
- 自動で .env を読み込む機能はプロジェクトルート（.git または pyproject.toml のある場所）を起点にしています。テストで自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（主要コマンド）

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
    - PID ファイルを data/execution.pid（設定による）へ書きます。
    - data/stop_requested.flag が存在すると起動をスキップまたは停止します。

- 監視ループ（Monitoring）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視は本番用 sqlite_path（Settings.sqlite_path）を使用してログを保存します（KABUSYS_ENV に依存しない）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- AI 機能（ニューススコアリング / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY）。
  - kabusys.ai.news_nlp.score_news や kabusys.ai.regime_detector.score_regime を呼び出して利用。

停止・Kill Switch:
- 監視コンポーネントは条件（ドローダウンやポジション上限等）に応じて data/kill.flag を書き込むことがあります。ExecutionEngine は kill.flag を検知して安全停止する仕組みです。
- 強制停止用に run_monitoring/run_execution が参照する stop_requested.flag（data/stop_requested.flag）を使う実装があるため、運用ではこれらのファイルの存在に注意してください。

ログ:
- ログは標準出力に出力され、また指定ディレクトリ（デフォルト logs/）へ日次ローテーションで保存されます（kabusys.utils.logging_setup）。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル・モジュールと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ情報（バージョン等）
  - config.py — 環境変数 / .env 読み込みロジックと Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト

  - portfolio/
    - portfolio_builder.py — 候補選定・配分計算（等配分/スコア加重）
    - position_sizing.py — 株数決定・集約キャップ・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - __init__.py

  - monitoring/
    - monitoring_db.py — SQLite 監視 DB 作成/読み書き
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 発注ログの整合性・滞留注文監視（存在）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch（flag ファイル書き込み）
    - monitoring_engine.py — 各 Monitor を束ねる実行エンジン
    - alert_manager.py — アラート送信（LINE 等、実装に依存）
  
  - execution/
    - execution_engine.py — ExecutionEngine（注文発行フロー）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py — 発注周り実装
  
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン計算、IC 計算、統計サマリー
    - __init__.py

  - ai/
    - news_nlp.py — ニュース記事を OpenAI でスコアリング
    - regime_detector.py — マクロ + ETF MA を使ったレジーム判定
    - __init__.py

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
    - __init__.py

- data/ (ランタイムで使用する想定のディレクトリ)
  - monitoring.db（既定: data/monitoring.db）
  - paper_trading.db（ペーパートレード用: data/paper_trading.db）
  - stop_requested.flag, kill.flag, execution.pid, ...（運用用フラグ/PID）

---

## 運用上の注意点 / トラブルシューティング

- .env ファイルは機密情報を含むため絶対に Git にコミットしないでください。
- 開発時に .env の自動読み込みを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- run_execution/run_monitoring はプロセス優先度を上げる処理を行いますが、権限がないと警告が出ます（AccessDenied をキャッチして続行します）。
- OpenAI を利用する AI 機能は API エラー・タイムアウトに対してリトライやフォールバックを実装していますが、API キーの有無は事前に確認してください。
- DuckDB / SQLite のファイルパスは Settings で指定できます。複数プロセスから同じ SQLite を書き込む際はロックに注意してください（設計上は監視 DB と発注 DB を分離することが推奨されています）。

---

## 開発者向け補足

- ロギングは kabusys.utils.logging_setup.setup_logging をアプリ起動時に呼び出して統一してください。
- config.Settings クラスはプロパティベースで環境変数を読み取ります。必須値は _require() でチェックされ未設定時は ValueError となります。
- DB マイグレーション（monitoring_db.init_monitoring_db）は起動時に冪等に実行され、テーブルやカラムの追加 (例: latency_ms や peak_value) を行います。
- AI 関連は外部 API に依存する処理が多いため、テストでは _call_openai_api 等をモックすることが容易になるよう設計されています。

---

この README はコードベースの主要な操作と構成を概説しています。各モジュールの詳細な利用方法や API は該当ソースファイルの docstring / コメントを参照してください。必要があれば各コンポーネントの詳細手順（デプロイ手順や systemd/cron での起動例など）を追加します。