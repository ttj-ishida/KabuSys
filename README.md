# KabuSys

日本株自動売買システム（KabuSys）のコードベース README（日本語）

この README はリポジトリ内の主要な機能、セットアップ手順、起動方法、ディレクトリ構成を簡潔にまとめたものです。開発・運用に必要な最低限の手順と利用方法を記載しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を行うためのモジュール群を備えたシステムです。主な目的は以下：

- 戦略に基づく銘柄選定・配分・株数計算（portfolio）
- 発注・注文管理・リスク管理を担当する ExecutionEngine（execution）
- システム稼働監視・リスク監視・アラート（monitoring）
- DuckDB を用いたファクター計算・リサーチ機能（research）
- ニュースを LLM（OpenAI）で解析してスコア化する AI コンポーネント（ai）
- 開発支援ツール（設定ウィザード・設定検証・検証レポート等）

設計方針として、データベースや外部 API（kabuステーション、J-Quants、OpenAI 等）へのアクセスはモジュールごとに分離され、紙上の検証（paper_trading）用の DB 分離やフェイルセーフの実装が行われています。

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み / Settings クラス（kabusys.config）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 起動前設定検証 CLI（python -m kabusys.validate_config）

- 実行エンジン（Execution）
  - Broker クライアントの抽象化（本番 / ペーパートレード切替）
  - OrderManager / OrderRepository / RiskManager / Reconciler 組み合わせによる発注フロー
  - ExecutionEngine の起動スクリプト（python -m kabusys.run_execution）
  - ペーパートレード時は専用 SQLite（data/paper_trading.db）へ記録

- 監視（Monitoring）
  - SystemMonitor（CPU/メモリ/ディスク/プロセス存在チェック / データ鮮度）
  - TradeMonitor（注文滞留・約定異常などの検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件に応じた停止フラグ生成）
  - MonitoringEngine（ポーリングループ）
  - 監視起動スクリプト（python -m kabusys.run_monitoring）
  - 監視ログ永続化（SQLite、monitoring_db.py）

- ポートフォリオ構築（portfolio）
  - 候補選定（select_candidates）
  - 重み計算（等分 / スコア加重）
  - セクターキャップ適用、レジーム乗数
  - 株数決定・集約上限・単元株丸め（calc_position_sizes）

- リサーチ（research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算・IC（Information Coefficient）等の統計処理
  - DuckDB を利用したデータ処理

- AI（ai）
  - ニュース NLP による銘柄センチメントスコア（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
  - OpenAI クライアント呼び出し、リトライ・レスポンス検証実装あり

- ツール
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

- ユーティリティ
  - 統一的なログ設定（kabusys.utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（kabusys.utils.process_priority）
  - DB 初期化 / マイグレーションユーティリティ（monitoring_db.init_monitoring_db）

---

## セットアップ手順（開発・ローカル）

以下は一般的なローカルセットアップ手順の例です。環境に応じて適宜読み替えてください。

前提
- Python 3.10+（実際の互換バージョンはプロジェクトポリシーに従ってください）
- SQLite は標準で利用可能
- 以下の Python パッケージが必要（pip インストール）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証を行う場合に推奨）
  - （その他、実行環境に応じて追加）

例:
1. 仮想環境を作る
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

   （requirements.txt がある場合は pip install -r requirements.txt を使用）

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに .env を作成
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - 推奨: OPENAI_API_KEY（AI 機能を利用する場合）

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

5. データディレクトリの作成（必要に応じて）
   - data/（デフォルトの SQLite / PID / フラグファイルがここに置かれます）
   - logs/（ログファイル保存先）

---

## 環境変数（主なもの）

（.env に設定する代表的なキー）
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- OPENAI_API_KEY — OpenAI を使う場合に必須
- KABUSYS_ENV — execution 動作モード（development / paper_trading / live）
  - paper_trading の場合、ExecutionEngine は MockBrokerClient を使い data/paper_trading.db に記録
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログファイル保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（1=yes、0=no）

必須環境変数は validate_config でチェックされます。

---

## 使い方（主要コマンド）

- .env を作成 / 更新（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 監視の起動（デーモン / systemd 等から起動）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止方法:
    - Graceful stop: プロジェクトルート/data/stop_requested.flag を作成するとループが検知して終了します

- 実行エンジンの起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い paper_trading DB に書き込みます
  - 起動時に data/stop_requested.flag が既に存在すると起動を中止します
  - 停止方法:
    - プロジェクトルート/data/stop_requested.flag を作成すると実行中のエンジンを停止します
    - KillSwitch は conditions に応じて data/kill.flag を書き込み ExecutionEngine に停止を促します

- Paper Trading 検証レポート（CSV/標準出力）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db path/to/paper_trading.db

- AI スコア / レジーム評価（ライブラリ API）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - 実行は DuckDB 接続を渡して行います（外部スクリプト化して運用することを推奨）

---

## 停止 / Kill Switch / フラグファイル

- Graceful stop for run_monitoring/run_execution:
  - data/stop_requested.flag を作ることで起動ループは終了します（run_monitoring.py / run_execution.py が検知）
- KillSwitch:
  - monitoring 側で条件を満たすと data/kill.flag を書き込み、ExecutionEngine を停止するために使用されます
  - ExecutionEngine の Settings.kill_flag_clear_on_start が 1 の場合、起動時に kill.flag を自動クリアします（本番では 0 推奨）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 起動前検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py             — ログ設定ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py             — SQLite テーブル初期化・永続化層
    - system_monitor.py
    - trade_monitor.py             — （存在する想定の監視ロジック）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py             — （アラート送信ロジックを想定）
  - execution/
    - execution_engine.py          — 実行エンジン本体
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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
  - tools/
    - paper_verification_report.py

（実際のファイルはリポジトリを参照してください。ここに挙がっていない補助的なモジュールも存在します）

---

## ログ / DB / その他のデフォルトパス

- ログディレクトリ: logs/ （kabusys.utils.logging_setup で作成）
- DuckDB（分析用）: data/kabusys.duckdb（環境変数 DUCKDB_PATH で変更可）
- Monitoring SQLite: data/monitoring.db（環境変数 SQLITE_PATH で変更可）
- Paper Trading SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で変更可）
- PID / フラグ: data/execution.pid, data/stop_requested.flag, data/kill.flag

---

## 開発・運用上の注意

- KABUSYS_ENV が `live` の場合は本番運用モードです。validate_config は警告を出します。設定・権限を十分に確認してください。
- .env は機密情報を含むため絶対にバージョン管理にコミットしないでください（config_setup.py の出力にもその旨の注意書きがあります）。
- OpenAI など外部 API は失敗時にフェイルセーフ（スコア 0 など）で継続するよう実装されていますが、API キーの漏洩・コストには注意してください。
- モジュールの多くは DuckDB / SQLite のスキーマに依存します。DB マイグレーションは monitoring_db.init_monitoring_db のように冪等的に行われますが、手動バックアップを推奨します。
- process_priority はプラットフォーム依存の API を利用します（psutil）。権限不足で警告が出ることがありますが重大な障害ではありません。

---

## 参考コマンド一覧

- 仮想環境作成
  - python -m venv .venv
  - source .venv/bin/activate

- パッケージインストール
  - pip install duckdb psutil openai pyyaml

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視起動
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- 実行エンジン起動
  - python -m kabusys.run_execution

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば「導入手順（systemd unit ファイルや Docker のサンプル）」「各モジュールの API ドキュメント」「DB スキーマ詳細」「テストの実行方法」などの追加ドキュメントを作成します。どの部分を優先して詳細化したいか教えてください。