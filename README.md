# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買システムのコードベースです。戦略・ポートフォリオ構築、注文実行、監視、研究ツール、ニュース NLP / レジーム判定（LLM 利用）などを含むモジュール群で構成されています。

---

## プロジェクト概要

本リポジトリは以下の責務を持つ主要コンポーネントを提供します。

- 実行エンジン（ExecutionEngine）: ブローカークライアント経由での発注管理・リスク管理・再整合（reconciler）。
- 監視（Monitoring）: システム状態、注文の滞留・約定異常、ドローダウン・ポジション数監視、Kill Switch。
- ポートフォリオ構築（Portfolio）: 候補選定、重み計算、ポジション決定（ロット丸め・集約上限）。
- 研究（Research）: ファクター計算、特徴量探索、IC 計算など（DuckDB を利用）。
- AI モジュール: ニュースのセンチメント付与（OpenAI）、市場レジーム判定（OpenAI と価格指標の合成）。
- ユーティリティ: 環境設定ウィザード、設定検証ツール、停動管理ユーティリティ、プロセス優先度設定など。
- ツール: Paper Trading の検証レポート生成スクリプト等。

設計方針として、DB は分析用に DuckDB、監視/注文履歴には SQLite を使用し、本番とペーパートレードは分離できるようになっています。

---

## 主な機能一覧

- 環境設定ウィザード（.env 生成）: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config [--strict]
- ExecutionEngine 起動スクリプト:
  - 本番/開発/ペーパートレード切替（KABUSYS_ENV）
  - ペーパートレード時は MockBrokerClient を利用し paper_trading DB に記録
  - 停止フラグ（data/stop_requested.flag）で安全停止
- Monitoring（監視）:
  - SystemMonitor（CPU/メモリ/ディスク/データ鮮度/プロセス生存）
  - TradeMonitor（滞留注文・約定価格異常）
  - RiskMonitor（ドローダウン・ポジション上限）
  - KillSwitch（条件により data/kill.flag を書き込み Execution を停止）
  - MonitoringEngine によるポーリングループ（interval 可変）
- Portfolio モジュール:
  - 候補選定（スコア降順）
  - 等配分 / スコア加重配分
  - セクター制限適用、レジーム乗数
  - ポジションサイズ計算（ロット丸め、コストバッファ、集約キャップ）
- Research モジュール:
  - Momentum / Volatility / Value ファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Spearman）や統計サマリー
- AI モジュール:
  - ニュース NLP（OpenAI）で ai_scores 更新
  - レジーム判定（ETF MA + マクロ記事センチメント）
  - リトライ・エラーハンドリング・JSON バリデーション実装済み
- ツール:
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## 前提条件

- Python 3.10 以上（typing の | 演算子等を使用）
- 必要な Python パッケージ（主要例）:
  - duckdb
  - psutil
  - openai
  - (オプション) PyYAML — 設定検証で config/*.yaml をパースする場合
- システム上での DB ファイル書き込み権限（data/ ディレクトリ等）

（requirements.txt は付属していないため、利用する機能に応じて上記パッケージをインストールしてください。）

例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順（ローカル開発向け簡易）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境の作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # POSIX
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install duckdb psutil openai PyYAML

4. .env の作成（対話式）
   python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - オプション:
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用）
     - LOG_LEVEL（デフォルト: INFO）
     - KILL_FLAG_CLEAR_ON_START（デフォルト: 0）

5. 設定検証（任意）
   python -m kabusys.validate_config
   strict モード: python -m kabusys.validate_config --strict

6. data ディレクトリの作成（必要に応じて）
   mkdir -p data

※ OpenAI を使う機能（news_nlp, regime_detector）を利用する場合は OPENAI_API_KEY を環境変数に設定してください。

---

## 使い方（代表的なコマンド）

- 監視ループ起動（Monitoring）
  python -m kabusys.run_monitoring

  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60。
  - 注意:
    - Monitoring は KABUSYS_ENV に依らず sqlite_path（通常 production path）を使用して監視テーブルを初期化します。

- 実行エンジン起動（ExecutionEngine）
  python -m kabusys.run_execution

  - ペーパートレードで起動する例:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - ペーパートレード時は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を利用し、本番 DB と完全分離されます。
  - 起動時に data/stop_requested.flag が存在すると起動しません。
  - エンジンは data/execution.pid に PID を書きます。stale PID の検出と削除ロジックあり。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション:
    --db PATH : PAPER_TRADING_SQLITE_PATH 環境変数を上書き

- 環境設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Kill / Stop の制御
  - ExecutionEngine 停止（外部から）:
    - kill_switch による自動書き込み: data/kill.flag が作成されると ExecutionEngine 停止処理がトリガーされます（条件は RiskMonitor 等で評価される）。
    - 手動停止: data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検知して停止します（スクリプトはこれを参照します）。

---

## 環境変数（Settings） — 主な項目とデフォルト

設定は .env または環境変数で行います。主要項目:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN (任意)
- LINE_USER_ID (任意)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_FILL_MODE (デフォルト: "instant") 有効値: instant | partial | never | reject
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (デフォルト: 0) — 1 にすると起動時に kill.flag を自動クリア（注意: 本番では危険）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — デフォルト INFO

（より詳しい説明は src/kabusys/config.py のプロパティコメントを参照してください）

---

## 重要なファイル / フラグ

- data/stop_requested.flag — run_execution / run_monitoring が存在を見てループを停止します
- data/kill.flag — KillSwitch が書き込む停止フラグ（Execution 停止要求）
- data/execution.pid — ExecutionEngine が書き込む PID（SystemMonitor が stale PID を検出可能）
- デフォルト DB:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - SQLite (paper trading): data/paper_trading.db

---

## ディレクトリ構成（概要）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / 設定管理（自動 .env ロード・検証）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - execution/ (発注関連コンポーネント)
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py など
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・プロセス監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch（flag 書き込み）
    - monitoring_engine.py — 各 Monitor の統合ポーリング
    - alert_manager.py — （通知管理、LINE 等に繋ぐ想定）
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数計算・ロット丸め・集約上限処理
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value の計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計要約
  - ai/
    - news_nlp.py — raw_news を LLM でスコアリングして ai_scores へ書き込み
    - regime_detector.py — ETF MA + マクロニュース LLM を合成して market_regime を更新
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成ツール
  - data/（実行時に使用するファイル/フラグ/DB のルート。リポジトリに含めないこと）

---

## 運用上の注意点

- 本番 (KABUSYS_ENV=live) では各種トークン・パスワードや LINE 通知設定を必ず見直してください。
- KILL_FLAG_CLEAR_ON_START を本番で 1 にするのは危険です（誤って Kill Switch をクリアしてしまう可能性）。
- Monitoring は環境に依らず監視用 SQLite（設定された sqlite_path）を使用して監視テーブルを初期化します。
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）が必要です。API 利用はコストとレイテンシを伴います。
- run_execution / run_monitoring は stop フラグファイルに依存した簡易的な停止機構を使用しています。外部監視やサービス管理 (systemd 等) と併用してください。
- DuckDB / SQLite のバックアップ・ファイルローテーション等は運用で検討してください（ファイルサイズ増加への対策）。

---

README はコードベース全体の入門的な説明です。各モジュールの詳細、公開 API、設定の細かな意味・テスト手順などはソースコード内コメント（docstring）や該当ファイルを参照してください。必要ならばコマンドごとの具体的な例や systemd サービス定義、CI / テスト手順の追記も対応できます。