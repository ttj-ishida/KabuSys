# KabuSys

日本株自動売買システムのリポジトリ（ライブラリ的コア）。  
本 README はソースツリー（src/kabusys 以下）に基づく概要・セットアップ・使い方の説明です。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・運用監視を行うためのモジュール群です。主な機能は以下の通り：

- 戦略研究（ファクター計算、特徴量解析、IC 計算）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算）
- 実行エンジン（ExecutionEngine：ブローカー連携、リスク管理、発注管理）
- 監視（System / Trade / Risk モニタ、Kill Switch、アラート）
- Paper Trading 用検証ツール・レポート生成
- ニュース NLP / レジーム判定（OpenAI を用いたセンチメント評価）
- 環境設定ウィザード / 設定検証 CLI

設計方針の一例：
- DuckDB を分析向け DB として利用、SQLite を監視・発注ログ用に利用
- 環境変数 / .env による設定管理（自動読み込みあり）
- 本番／ペーパートレードで DB を分離可能
- LLM（OpenAI）呼び出しはフェイルセーフ設計（失敗時はスキップやデフォルト値）

---

## 主な機能一覧

- kabusys.config: 環境変数 / .env の読み込みと Settings 抽象化
- config_setup.py: 対話式 .env 作成ウィザード
- validate_config.py: 起動前設定検証 CLI（--strict オプションあり）
- run_execution.py: ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じてペーパートレード分離）
- run_monitoring.py: SystemMonitor をポーリングする監視プロセス起動スクリプト（MONITOR_POLL_INTERVAL で間隔設定可能）
- monitoring.*: MonitoringDB、System/Trade/Risk モニタ、KillSwitch、MonitoringEngine、アラート連携
- portfolio.*: 候補選定、重み付け、ポジションサイズ計算、セクター上限・レジーム乗数
- research.*: ファクター計算（モメンタム・バリュー・ボラティリティ）、特徴量探索、IC / サマリ
- ai.news_nlp / ai.regime_detector: OpenAI を利用したニュースセンチメント評価・市場レジーム判定
- tools.paper_verification_report: Paper Trading の検証レポート生成

---

## 必要条件（依存ライブラリ）

（プロジェクトの requirements.txt が別途あるはずですが、ソースから読み取れる主な依存は下記です）

- Python 3.9+
- duckdb
- psutil
- openai
- （任意）PyYAML — validate_config が YAML 検証を行う場合
- 標準ライブラリ: sqlite3, threading, datetime, logging など

インストール例:
```
pip install duckdb psutil openai pyyaml
```

---

## 環境変数と設定（主なもの）

必須（起動前に .env を用意するか環境変数を設定してください）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

代表的なオプション/挙動を左右する環境変数:
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading: Execution は MockBrokerClient を使用し、data/paper_trading.db に記録
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- PAPER_FILL_MODE: ペーパートレードでの約定挙動（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 本番での Kill Flag 自動クリア（0 推奨）

.env 自動ロード:
- デフォルトでプロジェクトルートの `.env` と `.env.local` を自動読み込みします（OS 環境変数が優先）。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## セットアップ手順（推奨）

1. リポジトリをクローンして Python 仮想環境を準備
   ```
   git clone <repo>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # もし存在する場合
   pip install duckdb psutil openai pyyaml
   ```

2. .env を生成（対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   ウィザード実行後、`.env` が作成されます。作成後に:
   ```
   python -m kabusys.validate_config
   ```
   で設定の妥当性を検証してください。--strict を付けると警告も失敗扱いになります。

3. データディレクトリ/ログディレクトリの作成（通常は自動で作られますが確認しておくと安心です）
   - data/
   - logs/

4. 必要な DB ファイルは最初の起動時に自動で初期化される箇所があります（monitoring DB 等）。ただし DuckDB 用の初期データは別途準備が必要な場合があります。

---

## 使い方（主要スクリプト）

- 環境設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動（本番 / ペーパーに応じて .env の KABUSYS_ENV を設定）
  ```
  python -m kabusys.run_execution
  ```
  動作概要:
  - 起動時にプロセス優先度を "high" に設定し、SQLite / DuckDB に接続します。
  - KABUSYS_ENV=paper_trading の場合は paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し MockBroker を使います。
  - data/stop_requested.flag が存在すると起動しない／停止します。
  - 実行中は data/execution.pid を利用します（PID ファイルのパスは Settings.pid_file_path）。

- 監視プロセス起動
  ```
  python -m kabusys.run_monitoring
  ```
  オプション/挙動:
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用します（環境にかかわらず）。
  - data/stop_requested.flag を検知すると監視ループを終了します。

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  DB 指定:
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```
  デフォルトは 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 系機能（ニューススコアリング / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY）。
  - 直接の CLI エントリはなく、モジュール関数（kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）を呼び出して使います。ユニットやスクリプトから呼び出して運用してください。

---

## Kill / Stop フラグ

- data/kill.flag: KillSwitch が書き込むファイル。ExecutionEngine に対する停止シグナルとして利用。
- data/stop_requested.flag: run_* スクリプトの外部停止トリガー（run_monitoring, run_execution が検出して停止します）。
- Execution 起動時に KILL_FLAG_CLEAR_ON_START が 1 の場合は自動的に kill.flag をクリアします（本番では 0 推奨）。

---

## ログ設定

- 共通ユーティリティ kabusys.utils.logging_setup.setup_logging を使用してログ管理を行います。
- stdout（StreamHandler）と日次ローテーションファイル（TimedRotatingFileHandler）をルートロガーに設定します。
- 環境変数:
  - LOG_DIR: ログディレクトリ（デフォルト logs/）
  - LOG_LEVEL: ログレベル（例: INFO）

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数管理 / Settings
- config_setup.py — 対話式 .env ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト
- tools/
  - paper_verification_report.py — ペーパー用検証レポート生成
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py
  - regime_detector.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py
- execution/ (発注関連実装)
  - execution_engine.py
  - broker_factory.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- utils/
  - logging_setup.py
  - process_priority.py
- data/ (実行時に利用するファイル群：DB、pid、flag など) — プロジェクトルート直下に想定

（実装ファイルのうち一部は上記説明で触れられていないが、リポジトリ内で役割を持ちます）

---

## 注意事項 / 運用上のヒント

- KABUSYS_ENV は重要です。`live` を設定すると本番動作となるため設定値・アクセス権・通知設定を慎重に確認してください（validate_config に本番時チェックあり）。
- .env を絶対に Git にコミットしないでください（config_setup でも明示されています）。
- OpenAI 利用部分は API 呼び出しに失敗した場合に安全側のデフォルト（スコア 0.0 など）で継続する設計になっていますが、API レート制限やコストに注意して運用して下さい。
- 監視は monitoring DB（SQLite）にログを永続化します。monitoring の DB は run_monitoring が初期化します。
- run_execution / run_monitoring の停止制御はフラグファイル（data/stop_requested.flag）と kill.flag によって行われます。運用時はこれらの存在・削除が起動/停止に影響することを理解しておいてください。
- DuckDB のデータ（prices_daily, raw_financials 等）は別途データパイプラインで準備する必要があります（research, ai モジュールは DuckDB 内の該当テーブルを参照します）。

---

この README はソース内の実装・ドキュメント文字列に基づいて作成しました。実際の環境固有の準備（証券口座接続、データ投入、運用監視設定など）は別途手順に従ってください。必要であれば、各モジュールの詳細な使い方や API 仕様の README を追加で作成できます。