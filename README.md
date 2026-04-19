# KabuSys

日本株向け自動売買システムのコアライブラリ群（モジュール群のみ）。  
このリポジトリには実行エントリ、監視・リスク管理、ポートフォリオ構築、調査用ユーティリティ、AI連携などの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたモジュール群です。主な機能は以下のとおりです。

- ExecutionEngine（発注エンジン）起動スクリプト（run_execution）
  - 本番 / ペーパートレードの切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（Mock を使ったペーパートレード対応）
- Monitoring（監視）コンポーネント（run_monitoring / monitoring_engine）
  - システム稼働状況、データ鮮度、注文の滞留や約定異常、ドローダウン監視
  - Kill Switch（閾値を超えたら停止フラグを書き込む）
- ポートフォリオ構築（portfolio モジュール）
  - 候補選定、重み計算、リスク調整、ポジションサイジング
- 研究 / 調査ユーティリティ（research）
  - ファクター計算、IC計算、将来リターン計算
- AI連携（ai）
  - ニュースの NLP スコアリング（OpenAI）、市場レジーム判定
- ユーティリティ
  - ログ設定、プロセス優先度制御、設定ウィザード、設定検証、検証レポート作成ツール

設計上のポイント:
- 本番 DB（SQLite / DuckDB）・ペーパートレード DB の分離
- .env による設定管理 + 対話式ウィザード / 検証ツール
- フェイルセーフ（API失敗やデータ欠損時は安全なデフォルトで継続）
- LLM 呼び出しはリトライ / バックオフやレスポンス検証を備える

---

## 機能一覧（主なモジュール）

- エントリポイント
  - src/kabusys/run_execution.py — ExecutionEngine 起動（スレッドで実行、停止フラグ監視）
  - src/kabusys/run_monitoring.py — SystemMonitor ポーリングループ起動
- 設定
  - src/kabusys/config.py — 環境変数 / .env 自動ロード / Settings クラス
  - src/kabusys/config_setup.py — .env を対話的に作成するウィザード
  - src/kabusys/validate_config.py — 起動前の設定検証 CLI
- 監視
  - src/kabusys/monitoring/monitoring_db.py — SQLite ベースの永続化層（テーブル作成・読み書き）
  - src/kabusys/monitoring/system_monitor.py — CPU/メモリ/ディスク・データ鮮度・プロセス監視
  - src/kabusys/monitoring/risk_monitor.py — ドローダウン / ポジション数監視
  - src/kabusys/monitoring/trade_monitor.py — （注文ログ監視 — リポジトリに含まれる）
  - src/kabusys/monitoring/monitoring_engine.py — 各モニタの合成（アラート / Kill Switch）
  - src/kabusys/monitoring/kill_switch.py — data/kill.flag 書き込みによる停止シグナル
- ポートフォリオ
  - src/kabusys/portfolio/portfolio_builder.py
  - src/kabusys/portfolio/position_sizing.py
  - src/kabusys/portfolio/risk_adjustment.py
- 研究 / 調査
  - src/kabusys/research/factor_research.py
  - src/kabusys/research/feature_exploration.py
- AI
  - src/kabusys/ai/news_nlp.py — ニュース記事を LLM でスコアリングして ai_scores に保存
  - src/kabusys/ai/regime_detector.py — ma200 とマクロセンチメントを合成してレジーム判定
- ユーティリティ
  - src/kabusys/utils/logging_setup.py — 統一的なログ設定（stdout + 日次ローテートファイル）
  - src/kabusys/utils/process_priority.py — プロセス優先度 / CPU affinity 設定
  - src/kabusys/tools/paper_verification_report.py — ペーパートレード検証レポート生成

---

## 必要条件（依存パッケージの一例）

少なくとも以下をインストールしてください（実行する機能により追加が必要です）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- (任意) PyYAML（validate_config で YAML 検証を行う場合）

インストール例:
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成・有効化し、必要なパッケージをインストール
3. .env を作成
   - 対話式ウィザードで作成:
     python -m kabusys.config_setup
   - あるいは手動でプロジェクトルートに `.env` を配置（.env.example を参照）
4. 設定検証（起動前）
   python -m kabusys.validate_config
   --strict を付けると警告もエラー扱いになります
5. 必要なディレクトリ作成（data, logs などは自動作成されますが事前に作ると権限問題を回避できます）
   mkdir -p data logs

注意点:
- KABUSYS_ENV により挙動が変わります。`paper_trading` の場合は MockBroker を用い、DB は分離されます（PAPER_TRADING_SQLITE_PATH）。
- .env は機密情報を含むため決して Git にコミットしないでください。

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

運用 / 動作制御:
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）

DB 関連:
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）

AI:
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）

その他:
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動で消す (0/1)

例 (.env の一部):
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
OPENAI_API_KEY=sk-...

---

## 実行方法

基本的にはモジュールをモード付きで実行します（各モジュールは __main__ を持ち CLI として動作します）。

- ExecutionEngine を起動（本番 / ペーパーは KABUSYS_ENV に依存）:
  python -m kabusys.run_execution

  ペーパートレード用 DB を使用（KABUSYS_ENV=paper_trading）:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring を起動:
  python -m kabusys.run_monitoring

  ポーリング間隔を上書き:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- .env を対話的に作成:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB 指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

ログ:
- デフォルトでは logs/<app_name>.log（日次ローテート）と標準出力に出力されます。
- app_name は run_execution なら "execution"、run_monitoring なら "monitoring" でログファイルが作られます。

停止方法:
- run_monitoring / run_execution はプロジェクトの data/stop_requested.flag を監視しています。停止させたい場合はこのファイルを作成するとループは終了します（ファイルパスはスクリプト内定義）。
- Kill Switch（自動停止）は data/kill.flag による ExecutionEngine 停止シグナルです。KillSwitch クラスは状況に応じてこのファイルを書き込みます。手動でクリアする場合は file を削除してください（設定により起動時に自動クリアも可能）。

PID ファイル:
- run_execution は data/execution.pid を使用してプロセス管理に利用します。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- run_execution.py
- run_monitoring.py
- config.py
- config_setup.py
- validate_config.py

src/kabusys/ai/
- __init__.py
- news_nlp.py
- regime_detector.py

src/kabusys/monitoring/
- monitoring_db.py
- system_monitor.py
- trade_monitor.py
- risk_monitor.py
- monitoring_engine.py
- kill_switch.py
- alert_manager.py (参照あり)

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py
- __init__.py

src/kabusys/research/
- factor_research.py
- feature_exploration.py
- __init__.py

src/kabusys/tools/
- __init__.py
- paper_verification_report.py

src/kabusys/utils/
- logging_setup.py
- process_priority.py
- __init__.py

その他:
- data/ — (runtime) monitoring DB / paper_trading DB / kill.flag / stop_requested.flag / pid ファイル 等
- logs/ — ログ出力先（デフォルト）

（注: 一部ファイルはここに列挙されていない補助モジュールや未表示の実装ファイルが存在します）

---

## 運用上の注意・ベストプラクティス

- .env に API キーなど秘密情報を保存する場合は安全に管理（.gitignore に .env を追加）。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 に設定し、LINE 通知設定を必ず確認すること。
- openai を利用する機能は API 呼び出しによりコストが発生します。テストではモックを使うか API キーの取り扱いに注意してください。
- DuckDB / SQLite のパスは環境変数で設定可能。バックアップや永続化戦略を検討してください。
- ロギングは logs/ に日次でローテートされます。ストレージ容量に注意してください。

---

## 開発・テスト補助

- MonitoringEngine.run_once を使うことで、実際のループを回さず 1 回のみモニタ群を実行してテストできます（ユニットテスト向け）。
- news_nlp._call_openai_api や regime_detector._call_openai_api はテスト時にモック化することを想定して設計されています。

---

README はこのプロジェクトの主要な使用方法と構成を簡潔にまとめたものです。より詳細な設計文書（PortfolioConstruction.md / StrategyModel.md 等）や設定テンプレートはリポジトリ内の別資料を参照してください。必要があれば、特定のモジュールの使用例や設定例を追加で作成します。