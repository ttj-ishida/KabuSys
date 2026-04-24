# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム「KabuSys」のコアモジュール群です。
シグナル生成・ポートフォリオ構築・発注エンジン・監視・AI を使ったニュース解析などの機能を含みます。

以下はこのコードベースの README.md（日本語）です。

---

## プロジェクト概要

KabuSys は日本株自動売買のためのモジュール群です。主な設計方針は以下です。

- 戦略・ポートフォリオ構築はメモリ内の純粋関数で実装（副作用を限定）
- 実行エンジン（ExecutionEngine）はブローカー抽象化を通して発注を行う
- 監視（Monitoring）は別プロセスで稼働し、監視ログは SQLite に保存
- Paper Trading（ペーパートレード）モードは本番 DB と完全分離
- ニュースの NLP やレジーム判定には OpenAI（LLM）を利用（オプション）
- ロギングは統一的にセットアップ（stdout + 日次ローテートファイル）

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカーファクトリによる実ブローカー / MockBroker 切替（KABUSYS_ENV）
  - 発注ログ / positions の永続化（SQLite）
  - Stop / Kill Switch による安全停止機構（ファイルフラグ）

- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor による継続監視
  - MonitoringEngine によるポーリングループ
  - 監視データ保存（SQLite）と簡易アラート発行（AlertManager 経由）
  - KillSwitch（条件を満たすと data/kill.flag を作成）

- Portfolio（銘柄選定・配分）
  - 候補選択、等金額／スコア加重、リスクベース位置決め
  - セクター上限制御、レジーム乗数の適用

- Research / Tools
  - ファクター計算（momentum, volatility, value）
  - 特徴量探索（IC 計算、forward returns、統計サマリー）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

- AI（オプション）
  - ニュース記事を LLM でスコアリング（ai/news_nlp.py）
  - マクロニュース + ETF MA を組み合わせた市場レジーム判定（ai/regime_detector.py）

- 共通ユーティリティ
  - 設定管理（config.py）: .env の自動読込をサポート
  - 対話型 .env 作成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ログ設定ユーティリティ（utils/logging_setup.py）
  - プロセス優先度／CPU affinity 設定ユーティリティ（utils/process_priority.py）

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（型注釈の union 演算子 `|` を使用）
- Git で管理されたプロジェクトルートを想定（.env 自動検出のため）

1. 仮想環境の作成（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows PowerShell
   ```

2. 依存ライブラリのインストール（例）
   必要なパッケージ（主なもの）:
   - duckdb
   - psutil
   - openai (AI 機能を使う場合)
   - PyYAML (validate_config が YAML 検証を行う場合に任意)
   インストール例:
   ```bash
   pip install duckdb psutil openai PyYAML
   ```

   （requirements.txt がある場合はそれを使ってください）

3. .env の初期作成（対話式ウィザード）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードで J-Quants トークンや kabuAPI のパスワード、DB パス、KABUSYS_ENV 等を設定して `.env` を生成します。

4. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告をエラー扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

5.（任意）logs ディレクトリの確認
   デフォルトでログは `logs/` に保存され、日次ローテーションされます。LOG_DIR 環境変数で変更可能です。

---

## 環境変数（主要なもの）

基本的に .env に設定します。主要なキー:

- 認証系
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - OPENAI_API_KEY（AI 機能を使う場合）

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: MockBroker を使用し、Paper 用 SQLite に記録（PAPER_TRADING_SQLITE_PATH）
    - live: 本番。注意して設定すること（LINE 等通知設定も要確認）

- DB / ログ
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - LOG_LEVEL（デフォルト: INFO）
  - LOG_DIR（デフォルト: logs/）

- 実行制御
  - PID_FILE_PATH（ExecutionEngine の pid ファイル、デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START=1 にすると Execution 起動時に kill.flag を自動クリア（本番では 0 推奨）
  - MONITOR_POLL_INTERVAL（監視ループのポーリング間隔秒、デフォルト 60）

- Paper Trading 挙動
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

注意: config.py はプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に `.env` を自動ロードします。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 使い方（起動方法）

プロジェクトをパッケージとして実行する例（プロジェクトルートで実行）:

- 監視プロセス起動（Monitoring）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（秒、デフォルト 60）。
  - 監視は常に本番用の sqlite_path を参照します（環境にかかわらず monitoring DB を共通で見る設計）。

- 実行エンジン起動（ExecutionEngine）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動時に data/stop_requested.flag が存在するとエンジンは起動せず終了します。
  - 実行中に stop フラグ（data/stop_requested.flag）を作成すると安全に停止処理が行われます。

- .env 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または環境変数で PAPER_TRADING_SQLITE_PATH を指定
  ```

運用時のファイルフラグ:
- 停止（run_* スクリプトの外部終了トリガ）: data/stop_requested.flag
- 実行エンジン pid ファイル: data/execution.pid（デフォルト）

Kill Switch:
- リスク条件（ドローダウンやポジション上限）を満たすと `KillSwitch` が `data/kill.flag` を書き込み、ExecutionEngine に停止を促します。

ログ:
- setup_logging により stdout と日次ローテートファイル（logs/<app_name>.log）に出力します。

プロセス優先度:
- 起動スクリプトは最初に set_process_priority("high") を呼び出します。psutil による権限がない場合は警告を出してスキップします。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）

- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト
- config.py — 環境変数 / Settings 管理
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI

サブパッケージ / モジュール
- ai/
  - news_nlp.py — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py — 市場レジーム判定（LLM + ETF MA）
- monitoring/
  - monitoring_db.py — SQLite 用永続化層（テーブル作成・CRUD）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 発注/約定の監視（存在）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — Kill Switch（ファイルフラグ）
  - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
  - alert_manager.py — アラート送信管理（存在）
- execution/
  - execution_engine.py — 実行エンジン（EngineConfig, run_session 等）
  - broker_factory.py — Broker クライアント生成（実ブローカー / Mock）
  - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 実行ロジック
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — ファクター計算（momentum, volatility, value）
  - feature_exploration.py — IC / forward returns / 統計
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

パッケージ初期化
- __init__.py — バージョン等

（注）この README はコードベースからの要約であり、実行環境や追加モジュールの有無によって動作が変わる場合があります。実際に起動する前に `python -m kabusys.validate_config` で設定を確認してください。

---

## 運用上の注意とトラブルシューティング

- .env は決してリポジトリにコミットしないでください（config_setup の README 行にも注記あり）。
- KABUSYS_ENV=live の場合は特に注意：実発注が行われます。LINE 通知や kill flag の設定を必ず確認してください。
- psutil によるプロセス優先度設定は権限が必要な場合があります。警告が出たら無視しても動作は続行します。
- DuckDB / SQLite のファイルパスの親ディレクトリが存在しない場合、validate_config は警告を出しますが、起動時に自動作成されることが多いです。
- OpenAI を利用する機能は API 利用料が発生します。API キーの管理に注意してください。
- monitoring の DB 初期化は起動スクリプト内で自動的に行われます（冪等）。

---

README は必要に応じてプロジェクト固有の運用手順（systemd ユニット、Dockerfile、CI/CD 設定、バックアップ方針等）を追加してください。必要であれば、サービスユニットやデプロイ手順のテンプレートも作成します。