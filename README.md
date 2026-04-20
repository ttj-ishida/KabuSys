# KabuSys — README

このリポジトリは日本株向けの自動売買・研究・監視ツール群（KabuSys）の実装です。  
以下はコードベースを元に作成した README.md（日本語）です。セットアップ方法、使い方、主要コンポーネントの説明を含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム（ExecutionEngine）と、それを支える以下の補助機能を提供します。

- 実行エンジン（ExecutionEngine） — 発注、リスク管理、オーダー管理、照合（reconciler）
- 監視サブシステム（Monitoring） — システム状態、発注ログ、リスク監視、Kill Switch（停止フラグ）など
- ポートフォリオ構築モジュール — 候補選定、重み計算、ポジションサイズ算出、セクター制限、レジーム補正
- 研究モジュール — ファクター計算（モメンタム、バリュー、ボラティリティ等）、特徴量探索（IC、forward returns 等）
- AI連携モジュール — ニュースの NLP によるセンチメント評価、レジーム判定（OpenAI 利用）
- ツール類 — ペーパートレード検証レポート生成など
- 設定管理／ヘルパー — .env ウィザード、設定検証、ログ設定、プロセス優先度設定 等

設計の特徴：
- DB は DuckDB（分析）と SQLite（監視・発注履歴）を併用。
- Paper trading モードでは本番 DB と分離された専用 SQLite を使用。
- AI 呼び出しは OpenAI クライアントを使用（失敗時は安全側フォールバック）。
- 設定は .env / 環境変数を基本とし、README と .env.example を参照してセットアップ。

---

## 主な機能一覧

- ExecutionEngine 実行（run_execution）
  - ブローカークライアントの注入（本番 or Mock）
  - OrderManager / OrderRepository / RiskManager / Reconciler を統合
  - PID ファイル管理、停止フラグ監視（data/stop_requested.flag）
- Monitoring（run_monitoring / MonitoringEngine）
  - SystemMonitor：CPU/MEM/Disk、プロセス生存チェック、データ鮮度チェック
  - TradeMonitor：滞留注文・約定異常等の検出（trade_logs の集計）
  - RiskMonitor：ドローダウン・ポジション数監視 → リスクログ・kill.flag 出力
  - AlertManager 経由で通知（LINE など設定可能）
- Portfolio（kabusys.portfolio）
  - 銘柄候補選定、等金額・スコア加重配分、リスクベースの株数計算
  - セクターキャップ適用、レジーム乗数計算
- Research（kabusys.research）
  - モメンタム／バリュー／ボラティリティ等のファクター計算（DuckDB を利用）
  - Forward returns、IC（Spearman rank）や統計サマリー
- AI（kabusys.ai）
  - news_nlp.score_news：ニュース記事を集約して LLM に投げ、ai_scores テーブルへ格納
  - regime_detector.score_regime：ETF の MA とマクロセンチメントから日次レジーム判定
- ユーティリティ
  - config_setup：対話式 .env ウィザード（python -m kabusys.config_setup）
  - validate_config：起動前の設定検証（python -m kabusys.validate_config）
  - tools.paper_verification_report：Paper Trading の検証レポート生成

---

## 必要条件 / 推奨環境

- Python 3.9+
- 必要ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証に任意）
- OS：Linux / macOS / Windows（プロセス優先度など一部機能はプラットフォーム差異あり）

依存関係はプロジェクトの packaging（requirements.txt / pyproject）に合わせてインストールしてください。

---

## 環境変数（主要）

重要な環境変数の抜粋：

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: execution 環境（development / paper_trading / live）※デフォルト development
- DUCKDB_PATH: 分析用 DuckDB のパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時に使用）
- LOG_LEVEL, LOG_DIR
- OPENAI_API_KEY: AI 機能を利用する場合に必須（news_nlp / regime_detector）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）

必須変数は Settings クラスおよび validate_config の定義を参照してください。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Windows では .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - 要件ファイルが無い場合は少なくとも duckdb, psutil, openai を入れてください。

4. .env を作成
   - 対話式ウィザードを使用：
     - python -m kabusys.config_setup
   - あるいは手動で .env ファイルを作る（リポジトリに .env をコミットしないこと）

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにしたい場合は --strict を付与：
     - python -m kabusys.validate_config --strict

6. データディレクトリの確認
   - デフォルトでは data/ 以下に DB やフラグファイルを作成します。必要に応じてパスを環境変数で変更してください。

---

## 基本的な使い方

- ExecutionEngine を起動（通常の実行）：
  - python -m kabusys.run_execution
  - 実行時、KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_sqlite_path（デフォルト data/paper_trading.db）に記録します。
  - 停止は data/stop_requested.flag にファイルを作成するか、CTRL+C（KeyboardInterrupt）。

- Monitoring を起動：
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - Monitoring は常に本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを記録します。

- Paper Trading 検証レポートの生成：
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
  - --db を指定しない場合、環境変数 PAPER_TRADING_SQLITE_PATH またはデフォルト path が使用されます。

- .env の作成・更新：
  - python -m kabusys.config_setup

- 設定検証：
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いになります。

---

## ログと PID / Stop ファイル

- ログ:
  - setup_logging により stdout とファイル（logs/<app_name>.log）に出力されます。ログディレクトリは LOG_DIR/env/default を参照。
  - 日次ローテート（30 日保持）。

- PID / フラグファイル:
  - ExecutionEngine は data/execution.pid（Settings.pid_file_path）を使用して PID 管理。
  - 停止要求は data/stop_requested.flag（run_* スクリプトで参照）を作ることで行えます。
  - Kill Switch（監視が検出した深刻なリスク）は data/kill.flag を書き込み、ExecutionEngine 側はこれを検出して安全停止します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では推奨しません）。

---

## 主要ディレクトリ構成（抜粋）

リポジトリ（src/kabusys）内の主要ファイルと簡単な説明：

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数の読み込み／Settings クラス
- src/kabusys/config_setup.py
  - .env 対話式ウィザード
- src/kabusys/validate_config.py
  - 設定検証 CLI
- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト
- src/kabusys/run_monitoring.py
  - Monitoring 起動スクリプト

- src/kabusys/execution/
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
  - 発注・照合・リスク管理の実装（エンジン本体）

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite ストレージ層
  - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py
  - 監視ロジックと Kill Switch、アラート管理

- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - 銘柄選定、重み、ポジションサイズ、セクター制限等の純粋関数

- src/kabusys/research/
  - factor_research.py, feature_exploration.py
  - DuckDB を用いたファクター計算、IC 計算、統計サマリー

- src/kabusys/ai/
  - news_nlp.py — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading の集計・判定レポート

- src/kabusys/utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度・CPU affinity 設定

- data/
  - デフォルトの DB / フラグファイル 等が置かれる想定ディレクトリ
  - 例: data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag

---

## 運用・注意点

- KABUSYS_ENV を適切に設定すること（development / paper_trading / live）。live では本番 API を使用するため設定ミスは重大です。
- .env は絶対にリポジトリにコミットしないでください（シークレット情報含む）。
- OpenAI API 呼び出しを行う部分は API キーと料金に留意してください。失敗時はフォールバック動作を行いますが、外部 API 依存部分があることを理解してください。
- monitoring は本番 sqlite_path を常に使用して監視する設計です（run_monitoring は環境にかかわらず監視 DB を参照）。
- paper_trading モードは本番 DB と完全分離されるよう paper_sqlite_path を使用します。
- process priority / CPU affinity 設定はプラットフォーム差があり、権限不足で設定に失敗することがあります。その場合はログで警告が出ます。

---

## 開発者向けメモ

- DuckDB 接続を受け取る関数（research, ai modules）は副作用を持たず、テストが容易な設計です。
- DB マイグレーション（簡易）: monitoring_db.init_monitoring_db は既存 DB へカラム追加等を行います（冪等処理）。
- 単体テストにおいては環境変数の自動ロードを無効化できます:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

README は上記の通りです。リポジトリ内の個別モジュール（execution_engine、order_manager、risk_manager、news_nlp、regime_detector など）に関する詳細な API ドキュメントや使用例が必要であれば、対象モジュールを指定して下さい。必要に応じてコマンド例やユースケース別の運用手順（本番切替手順、バックアップ運用など）も追加します。