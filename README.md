# KabuSys — 日本株自動売買システム

簡単な概要、セットアップ手順、使い方、主要機能、ディレクトリ構成をまとめた README です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム（研究・ポートフォリオ構築・発注・監視・AI 支援）を目的としたコードベースです。  
主なコンポーネントは以下です。

- ExecutionEngine: 発注処理・注文管理・リスク管理を担う実行エンジン
- Monitoring: システム稼働・注文状態・リスクを監視してアラート・Kill Switch を管理
- Portfolio: 銘柄選定、重み付け、ポジションサイズ計算
- Research: ファクター計算・特徴量探索
- AI: ニュースセンチメント（OpenAI を利用）や市場レジーム判定
- Tools: ペーパートレード検証レポート生成などのユーティリティ
- Utilities: 設定ロード、ロギング設定、プロセス優先度制御など

ライブラリ的に純粋関数群（ポートフォリオ計算等）と、実行時に DB / API にアクセスするモジュールが混在しています。

---

## 主な機能一覧

- 設定管理
  - `.env` の自動ロード（プロジェクトルートの `.env` / `.env.local`）
  - 対話式の環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

- 実行 / 発注
  - ExecutionEngine（本番 / ペーパートレード切替）
  - BrokerClientFactory によるブローカークライアント抽象化
  - RiskManager / OrderManager / Reconciler 等による堅牢な注文制御

- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク/データ鮮度/プロセス生存をチェックし SQLite に記録
  - TradeMonitor: 注文の滞留や約定異常を検出（trade_logs 等を参照）
  - RiskMonitor: ドローダウン監視・ポジション上限監視
  - KillSwitch: 指定条件で `data/kill.flag` を作成して ExecutionEngine を停止
  - MonitoringEngine: 上記をまとめて定期実行、AlertManager へ通知

- 研究・ファクター
  - momentum / volatility / value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ

- AI（OpenAI を利用）
  - news_nlp: ニュースから銘柄別センチメントを取得して ai_scores に書き込む
  - regime_detector: 市場レジーム判定（ETF MA とマクロ記事センチメントの合成）

- ツール
  - paper_verification_report: ペーパートレード DB を参照して検証レポートを生成

- ロギング / プロセス管理
  - 統一的な logging 設定（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順（ローカル開発向け）

前提: Python 3.10 以上を推奨（Union 型表記や型ヒントを使用）。

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 代表的な依存パッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

   ※ requirements.txt が提供されている場合はそれを使ってください。

4. .env の準備
   - 対話ウィザードで作成:
     - python -m kabusys.config_setup
   - または手動で `.env` を作成（プロジェクトルート）:
     - 主要な環境変数（例）:
       - JQUANTS_REFRESH_TOKEN=your_token_here
       - KABU_API_PASSWORD=your_kabu_password
       - KABU_API_BASE_URL=http://localhost:18080/kabusapi
       - DUCKDB_PATH=data/kabusys.duckdb
       - SQLITE_PATH=data/monitoring.db
       - KABUSYS_ENV=development|paper_trading|live
       - OPENAI_API_KEY=sk-...
       - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
       - PAPER_FILL_MODE=instant|partial|never|reject
       - LOG_LEVEL=INFO

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い:
     - python -m kabusys.validate_config --strict

6. データディレクトリ作成（必要に応じて）
   - デフォルトでは `data/` と `logs/` を想定。自動作成されますが権限に注意。

---

## 使い方

- 実行エンジン（ExecutionEngine）起動:
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 用 DB（`data/paper_trading.db`）へ記録します。本番 DB と完全分離されます。
    - 起動時に `data/stop_requested.flag` が存在すると起動を行わず終了します。
    - 実行中は `data/execution.pid` に PID を書きます。停止は KillSwitch やフラグファイルで行います。

- 監視プロセス（Monitoring）起動:
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト: 60）。
  - 監視は設定にかかわらず本番 sqlite_path を使って永続化されます（monitoring 用の DB スキーマを初期化します）。
  - 停止は `data/stop_requested.flag` を設置するか、Ctrl+C で中断。

- ペーパートレード検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH、最終フォールバックは data/paper_trading.db）

- Kill Switch の利用:
  - KillSwitch は監視コンポーネントが判断して `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送ります。
  - ExecutionEngine は定期的にフラグファイルを参照して停止します。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動でクリアします（本番では `0` 推奨）。

- AI 機能（news_nlp / regime_detector）
  - OpenAI を使うために `OPENAI_API_KEY` を設定してください。
  - news_nlp は raw_news / news_symbols テーブルの内容を集約して LLM に投げ、ai_scores に書き込みます。
  - LLM 呼び出しは再試行・バックオフ・レスポンス検証を行い、失敗時は安全にフォールバックします。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE: instant | partial | never | reject (デフォルト: instant)
- OPENAI_API_KEY (AI 機能で必須)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO)
- MONITOR_POLL_INTERVAL (監視ループのポーリング間隔 秒、デフォルト 60)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアする場合 1)

詳細は `kabusys.config.Settings` に実装されています。

---

## 停止・制御フラグ

- data/stop_requested.flag
  - run_execution.py / run_monitoring.py はこのファイルの存在を確認してループを終了します（手動停止やデプロイ用スイッチとして利用）。
- data/kill.flag
  - KillSwitch が作成するフラグ。ExecutionEngine に対する安全停止指示。

---

## ログ

- ログは共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` で設定されます。
- コンソール（stdout）とファイル（logs/<app_name>.log）に出力し、ファイルは日次ローテーション（30日保持）です。
- ログレベルは `LOG_LEVEL` 環境変数または引数で指定可能。

---

## よく使うコマンドまとめ

- 対話的に .env を作る:
  - python -m kabusys.config_setup
- 設定を検証する:
  - python -m kabusys.validate_config
- 実行エンジンを起動:
  - python -m kabusys.run_execution
- 監視プロセスを起動:
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## ディレクトリ構成（抜粋）

（プロジェクトルートから `src/kabusys` 以下を中心に）

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定読み込み
  - config_setup.py                   — 対話式 .env 作成ウィザード
  - validate_config.py                — 起動前設定検証 CLI
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - run_monitoring.py                 — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py    — ペーパートレード検証レポート
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                              — デフォルトの DB / フラグファイル等が置かれる（実行時に作成される）

（実際のファイルは上記の他にも多数あります。ここでは主要なものを抜粋しています。）

---

## 開発上の注意 / トラブルシューティング

- Python バージョン
  - 型注釈で 3.10 以上の構文（PEP 604 など）を使用しているため 3.10 以上を推奨します。

- DB
  - DuckDB は分析用データベース（prices_daily / raw_financials / raw_news 等）を想定しています。
  - 監視ログは SQLite (`SQLITE_PATH`, デフォルト data/monitoring.db) に永続化されます。
  - ペーパートレード時は `KABUSYS_ENV=paper_trading` にすると `PAPER_TRADING_SQLITE_PATH` を使用します（本番 DB と完全分離）。

- OpenAI
  - AI 機能を使う場合は `OPENAI_API_KEY` を設定してください。API 呼び出しは再試行や検証を行いますが、API 利用料が発生します。

- 権限 / ディレクトリ
  - `logs/`, `data/` ディレクトリは実行権限があり書き込み可能であることを確認してください。`setup_logging` はログディレクトリ作成に失敗するとファイル出力を無効にしてコンソールのみで継続します。

- 停止制御
  - `data/stop_requested.flag` や `data/kill.flag` を用いた外部制御（CI / デプロイ / 手動停止）が実装されています。運用時はこれらのファイルに注意してください。

---

以上が KabuSys の README.md 相当の概要です。必要であれば、実際の運用手順（systemd でのサービス化、Dockerfile、CI ワークフロー）や詳細な設定テンプレート（.env.example）を追加で作成します。どの情報を優先して追加しますか？