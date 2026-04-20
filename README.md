# KabuSys

日本株自動売買システム KabuSys のリポジトリ向け README（日本語）

概要、主要機能、セットアップ、使い方、ディレクトリ構成をまとめています。実行前に必ず `.env` を作成し、`python -m kabusys.validate_config` で設定を検証してください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。主な目的は戦略の研究・ファクター計算（Research）からポートフォリオ構築、発注（Execution）、および稼働監視（Monitoring）までを統合的にサポートすることです。DuckDB / SQLite を利用したデータ処理、OpenAI を利用したニュース NLP、監視・リスクガード、ペーパートレードの分離などの機能を備えています。

主要設計方針（抜粋）
- DuckDB（分析）とSQLite（監視・発注履歴）でデータ永続化を分離
- レジーム検出やニュースセンチメントは LLM をオプションで利用
- Paper Trading（ペーパートレード）は本番 DB と完全分離（別 SQLite）
- Kill Switch / フラグファイルにより外部から安全にエンジン停止可能

---

## 機能一覧

- Execution（ExecutionEngine）
  - 実際のブローカークライアント/モック（paper_trading）を利用した発注実行
  - リスク管理（RiskManager）、注文管理、整合性チェック（Reconciler）を備える
  - 起動時にプロセス優先度を調整し PID ファイルを管理

- Monitoring（監視）
  - SystemMonitor: CPU/MEM/DISK、プロセス生死、データ鮮度を監視
  - TradeMonitor: 注文の滞留や約定の異常を検出（trade_logs 参照）
  - RiskMonitor: ドローダウンやポジション上限の監視とリスクログ
  - KillSwitch: 条件に応じて `data/kill.flag` を書き込み ExecutionEngine を停止
  - MonitoringEngine: 上記をまとめて定期ポーリング（run_monitoring 起動スクリプト）

- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- Portfolio
  - 候補選定、等重・スコア重みの計算、セクター制限、ポジションサイズ計算（単元株調整含む）

- AI（オプション）
  - news_nlp: OpenAI を使ったニュースセンチメント集計と ai_scores への書き込み
  - regime_detector: ETF（1321）MA とマクロニュースの LLM 評価を合成して日次レジーム判定

- ツール
  - config_setup: 対話式 .env ウィザード（.env を生成）
  - validate_config: .env と config/*.yaml の事前検証 CLI
  - paper_verification_report: ペーパートレード DB から検証レポート生成

- ユーティリティ
  - logging_setup: 共通ログ設定（stdout + 日次ローテートファイル）
  - process_priority: Windows/Linux の差を吸収した優先度 / cpu affinity 設定

---

## 必要条件（主な依存パッケージ）

- Python 3.10+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（validate_config で YAML 内容検証を行う場合）

例（最小インストール）:
pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt がない場合は上記を参考にしてください）

---

## 環境変数（重要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意/設定:
- KABUSYS_ENV: execution モード（development / paper_trading / live） (default: development)
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring.db）パス（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading.db）
- PAPER_FILL_MODE: paper_trading の fill モード（instant/partial/never/reject）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
- その他: PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEM/DISK の閾値等

.env の自動読み込み:
- プロジェクトルートに `.env` / `.env.local` があると自動で読み込まれます（OS 環境変数優先）。
- 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

推奨手順:
1. `python -m kabusys.config_setup` で対話的に `.env` を作成
2. `python -m kabusys.validate_config` で検証

---

## セットアップ手順

1. リポジトリをクローンし、作業ディレクトリをプロジェクトルート（pyproject.toml または .git が存在する場所）にする。

2. Python 仮想環境を作成・有効化（任意）:
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール:
   pip install duckdb psutil openai PyYAML

4. 環境変数 (.env) を準備:
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - あるいは `.env` を手動で作成（.env.example を参照）

5. 設定検証:
   python -m kabusys.validate_config
   - 必須環境変数が未設定だとエラーになります。
   - --strict を付けると警告も失敗扱いになります。

6. 初回実行前に data ディレクトリ等を作成しておくと安全です（多くの起動処理が自動作成するようになっていますが、権限などで失敗する場合があるため）:
   mkdir -p data logs

---

## 使い方（起動 / CLI）

主要な起動スクリプトは Python モジュールとして提供されています。プロジェクトルートで以下を実行します。

- Execution Engine を起動（常用）:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、`data/paper_trading.db`（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動時に `data/execution.pid`（PIDファイル）を扱います。
  - 外部停止: `data/stop_requested.flag` （存在すると起動せず/停止させる挙動）

- Monitoring を起動（定期監視）:
  python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60）。
  - Monitoring は KABUSYS_ENV に関わらず production の sqlite_path を使用して監視テーブルへ記録します。
  - 停止チェック: リポジトリルートの `data/stop_requested.flag` を監視。作成されるとループを終了します。

- 設定ウィザード（.env 作成）:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: environment で指定された PAPER_TRADING_SQLITE_PATH または `data/paper_trading.db`

- その他ユーティリティ:
  - 監視の単発実行やモジュール関数はユニットテストやスクリプトから呼び出せます（例: MonitoringEngine.run_once など）。

停止シグナル / Kill Switch
- Execution 側を即座に停止させたい場合は監視側の条件（ドローダウン、ポジション上限等）で `data/kill.flag` が書かれます（KillSwitch）。`run_execution` は `stop_requested.flag` を見て安全に停止します。
- 手動で安全に停止したい場合は `data/stop_requested.flag` を作成してください（Monitoring と Execution の両ループはこれを参照して終了します）。
- `KillSwitch.clear()` を呼ぶか、`data/kill.flag` を手動で削除してから Execution を再起動してください。

ログ
- ログは標準出力（stdout）とファイル（logs/<app_name>.log）に出力されます。ログディレクトリは `LOG_DIR` 環境変数で上書き可能。ログレベルは `LOG_LEVEL` で制御します。

---

## 重要な挙動メモ

- run_monitoring は常に（KABUSYS_ENV に関係なく）production 用の sqlite_path を使用して監視データを書きます（コードの意図によりこう設計されています）。
- run_execution は `KABUSYS_ENV=paper_trading` のとき `paper_sqlite_path`（PAPER_TRADING_SQLITE_PATH）を使用してペーパートレード DB を分離します。
- .env の自動読み込みはプロジェクトルートが見つからないとスキップされます。また KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- OpenAI を使う機能（news_nlp, regime_detector）には `OPENAI_API_KEY` が必要です。API エラー時はフェイルセーフ（0.0 等）で継続する設計です。

---

## 開発者向け: 主要ファイル・ディレクトリ構成

（src/kabusys 以下の主要ファイルを抜粋）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py          (実装ファイル群)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py          (アラート送信ロジック)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - ai/
    - news_nlp.py
    - regime_detector.py

（上記は抜粋です。実際のファイル一覧と依存関係はプロジェクト内を参照してください）

---

## よくある運用フロー（例）

1. `.env` を作成（config_setup）
2. validate_config で検証
3. データ収集・DuckDB 準備（別プロセスで pipeline 実行）
4. Monitoring を常時起動:
   python -m kabusys.run_monitoring
5. 発注エンジンを起動（毎営業日やスケジューラ経由）:
   python -m kabusys.run_execution
6. ペーパートレード評価:
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## トラブルシューティング / 注意点

- ログディレクトリや data ディレクトリに書き込み権限がないとファイルハンドラ作成に失敗します（その場合はコンソールログのみで継続します）。
- OpenAI など外部 API はネットワーク・レート制限により失敗することがあります。AI モジュールはリトライとフェイルセーフを実装していますが、API キーとレートに注意してください。
- .env を絶対に VCS（Git）にコミットしないでください（config_setup でも注意喚起あり）。
- プロダクションでの Kill Switch の設定は慎重に（KILL_FLAG_CLEAR_ON_START の扱いに注意）。

---

この README はコードベースのエントリポイント、設定、実行フローをまとめた入門ドキュメントです。詳細な設計（アルゴリズムの理論・パラメータ）や運用手順は各ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）・config/*.yaml を参照してください。必要であれば README を拡張し、起動例スクリプトや systemd / supervisor のユニット例も追加できます。