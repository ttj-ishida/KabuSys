# KabuSys

日本株向け自動売買システムの一部（ライブラリおよび起動スクリプト群）。

このリポジトリには、以下の主要機能を提供するモジュール群が含まれます：
- 実行エンジン（ExecutionEngine）起動スクリプト
- 監視（Monitoring）ポーリングエンジン
- ポートフォリオ構築・ポジションサイズ計算
- ファクター計算・リサーチユーティリティ（DuckDB ベース）
- ニュース NLP / レジーム判定（OpenAI を利用）
- 設定ウィザードおよび設定検証ツール
- ペーパートレード検証レポート生成スクリプト

README の目的：プロジェクト概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成をまとめます。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の要素を提供する Python ベースのモジュール集合です。

- データ解析（DuckDB）に基づくファクター計算・リサーチ
- ポートフォリオ構築とリスク制御（等重配分・スコア重み・リスクベース等）
- 注文管理・発注ラッパ（本番 / ペーパー切替可能）
- 監視（システム稼働、データ鮮度、注文状況、ドローダウン）と Kill Switch
- ニュースの LLM（OpenAI）によるセンチメント評価とレジーム判定
- 実運用を想定したログ設定・プロセス優先度設定ユーティリティ

設計方針として、DB は DuckDB（分析用）と SQLite（監視・履歴用）で分離され、ペーパートレード時は専用の SQLite を使って本番 DB と隔離する仕組みがあります。

---

## 主な機能一覧

- 設定管理
  - .env 対話式ウィザード（kabusys.config_setup）
  - 起動前の設定検証 CLI（kabusys.validate_config）

- 実行・監視スクリプト
  - run_execution.py: ExecutionEngine の起動（KABUSYS_ENV による挙動切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動

- 監視機能
  - SystemMonitor: CPU/Mem/Disk、プロセス生存、データ鮮度チェック
  - TradeMonitor: 発注・約定ログの監視（滞留注文、異常約定等）
  - RiskMonitor: ドローダウン・ポジション上限監視（kill flag と連動）
  - MonitoringEngine: 各 Monitor の統合とアラート発行ルール

- ポートフォリオ構築（純粋関数）
  - 候補選定（select_candidates）
  - 重み計算（等重・スコア重み）
  - ポジションサイズ計算（risk_based / equal / score）
  - セクターキャップ適用、レジーム乗数

- リサーチ / ファクター
  - モメンタム、ボラティリティ、バリュー等の計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI（OpenAI）連携
  - ニュース NLP（ai.news_nlp.score_news）: 記事集合のセンチメント集計・ai_scores への保存
  - レジーム判定（ai.regime_detector.score_regime）: MA + マクロセンチメントの合成判定

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

- ユーティリティ
  - ログ統一設定（kabusys.utils.logging_setup）
  - プロセス優先度設定 / CPU affinity（kabusys.utils.process_priority）
  - 監視 DB の初期化と永続化層（kabusys.monitoring.monitoring_db）

---

## セットアップ手順

以下はローカル開発（および簡単な運用確認）の手順例です。

1. リポジトリをクローンしてワークディレクトリへ移動
   - プロジェクトルートには pyproject.toml か .git が存在する想定です（設定自動ロードの基準）。

2. Python 環境の準備
   - 推奨: Python 3.9+
   - 仮想環境を作成して有効化し、必要パッケージをインストールしてください。
     - 主要依存例: duckdb, psutil, openai, sqlite3（標準）、PyYAML（設定検証に任意）
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install duckdb psutil openai pyyaml

3. .env の作成（対話式ウィザード推奨）
   - 実行:
     - python -m kabusys.config_setup
   - ウィザードで J-Quants トークン、kabu API パスワード、DB パス等を設定してください。
   - 重要: .env は Git にコミットしないでください（ウィザードの注記あり）。

4. 設定検証
   - 起動前に検証:
     - python -m kabusys.validate_config
     - 厳格モード（警告もエラー扱い）: python -m kabusys.validate_config --strict
   - PyYAML が無い場合、config/*.yaml のパース検証はスキップされます（警告）。

5. データディレクトリとログディレクトリ
   - デフォルトの SQLite / DuckDB / ログディレクトリは以下です（.env で上書き可能）。
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_DIR: logs/
   - ログディレクトリは自動作成されますが、作成に失敗するとコンソール出力のみで継続します。

6. OpenAI を使う機能
   - OPENAI_API_KEY 環境変数を設定するか、関数呼び出しで渡してください（ai.score_news / score_regime）。

---

## 使い方（コマンド例）

- .env の作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録して本番 DB と分離されます。
    - 起動時に data/stop_requested.flag が存在する場合は起動を行いません。
    - 実行中、data/stop_requested.flag が作成されるとエンジン停止処理を行います。
    - 実行時は PID を data/execution.pid に書きます（設定で変更可能）。

- 監視（Monitoring）ループ起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - SystemMonitor をポーリングして監視ログ（SQLite）へ記録します。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）。
    - run_monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を使用して監視 DB を初期化します。
    - 停止は data/stop_requested.flag を作成すると検知して終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を使うか、PAPER_TRADING_SQLITE_PATH 環境変数で指定

- ライブラリ関数の利用（例）
  - ニューススコアリング（プログラム内から呼ぶ）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

- ログ設定
  - 全起動スクリプトは kabusys.utils.logging_setup.setup_logging を呼び出します。
  - LOG_LEVEL（デフォルト INFO）や LOG_DIR を .env で設定できます。

---

## 主要環境変数（代表）

- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ格納ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI を使う機能向けの API キー
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

補足:
- 自動で .env をロードする機能はプロジェクトルート（.git または pyproject.toml を基準）を探索します。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 停止・Kill Switch

- 停止フラグ（停止要求）
  - data/stop_requested.flag: run_execution / run_monitoring の外部停止用（スクリプトはこのファイルの存在を確認して終了します）
- Kill Switch（自動停止判定）
  - KillSwitch は監視結果（ドローダウン超過、ポジション上限等）に応じて data/kill.flag を書き込み、ExecutionEngine に停止を促します。
  - kill.flag のパスは Settings.kill_flag_path で設定（デフォルト data/kill.flag）されます。
  - Settings.KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動的に kill.flag をクリアします（本番では推奨されません）。

---

## 典型的な運用フロー（簡易）

1. .env を作成（kabusys.config_setup）。
2. 設定検証（kabusys.validate_config）。
3. データ投入 / DuckDB 準備（prices_daily, raw_financials 等をロード）。
4. ExecutionEngine を開始（本番/ペーパーに応じて起動）。
5. Monitoring を別プロセスで開始して継続監視。
6. 必要に応じて Kill Switch による自動停止や LINE 通知等で対応。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主なファイル・モジュール（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py            # .env 対話式ウィザード
  - validate_config.py        # 起動前設定検証 CLI
  - run_execution.py          # ExecutionEngine 起動スクリプト
  - run_monitoring.py         # SystemMonitor ポーリング起動スクリプト
  - utils/
    - __init__.py
    - logging_setup.py        # ログ設定ユーティリティ
    - process_priority.py     # プロセス優先度/CPU affinity
  - monitoring/
    - monitoring_db.py        # SQLite 永続化層（監視ログ）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (参照)
  - execution/
    - execution_engine.py     # ExecutionEngine（推定）
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
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
  - tools/
    - paper_verification_report.py

（上記に含まれない補助モジュールや設定ファイルがプロジェクトに存在する場合があります）

---

## 注意事項 / トラブルシューティング

- .env を自動ロードしない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動で環境変数を管理してください。
- validate_config で警告が出た場合は内容を確認してください。特に KABUSYS_ENV=live の場合は設定ミスが重大な事故につながります。
- OpenAI を使う機能は API 使用量・遅延に注意し、API キーの管理を徹底してください。
- DuckDB / SQLite ファイルは場所と権限を確認してください。親ディレクトリが存在しない場合は警告が出ますが、起動時に作成されることがあります。
- run_monitoring の MONITOR_POLL_INTERVAL は 1 秒以上の正の整数を指定してください。不正な値はデフォルト 60 秒にフォールバックします。
- psutil によるプロセス優先度設定や CPU affinity は環境（OS, 権限）依存で失敗することがあります。失敗した場合は警告ログが出ます。

---

この README はコードベースの主要箇所を要約したものです。各モジュールの詳細な仕様・アルゴリズムはソースコード内のドキュメント文字列（docstring）やコメントを参照してください。必要であれば、運用手順書やデプロイ手順の追加ドキュメントを作成します。