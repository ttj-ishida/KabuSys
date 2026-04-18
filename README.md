# KabuSys

日本株向け自動売買システムの一部コンポーネント群（ライブラリ + 起動スクリプト群）。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤を想定した Python コードベースです。本リポジトリには以下の主要機能（ポートフォリオ構築、ポジションサイジング、ファクター計算、モニタリング、AI を使ったニュース評価、実行エンジン起動スクリプト等）が含まれます。

設計方針の要点:
- DuckDB / SQLite を用いたデータ分析・永続化
- 実行環境（本番 / ペーパートレード / 開発）を .env で切替
- OpenAI（gpt-4o-mini）を利用したニュース NLP とレジーム判定（任意）
- フェイルセーフ設計（API 失敗時のフォールバック、冪等性、停止フラグ）

---

## 主な機能一覧

- 起動スクリプト
  - run_execution: ExecutionEngine を起動（本番/ペーパートレードを分離）
  - run_monitoring: SystemMonitor のポーリングループ起動
- 設定管理
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: 起動前設定検証 CLI
  - Settings クラス: 環境変数から設定を取得・検証
- モニタリング
  - MonitoringDB: SQLite による監視ログ永続化
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch
  - run_monitoring が定期的に各モニタを呼び出し kill.flag を自動作成可能
- ポートフォリオ構成
  - 銘柄選定、等重・スコア重み、セクターキャップ、レジーム乗数、ポジションサイズ計算
- リサーチ
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI（任意）
  - news_nlp: OpenAI を使ってニュースを銘柄ごとにセンチメントスコア化（ai_scores へ保存）
  - regime_detector: ETF とニュースを併せて市場レジーム（bull/neutral/bear）を判定
- ツール
  - paper_verification_report: ペーパートレード DB を集計して PASS/FAIL レポートを表示

---

## 前提・依存ライブラリ

推奨 Python バージョン: 3.9 以上（型注釈やモジュール利用を想定）

主な依存ライブラリ:
- duckdb
- psutil
- openai (AI 機能を使用する場合)
- PyYAML（config/*.yaml の検証をする validate_config で任意）

インストール例（仮の requirements）:
pip install duckdb psutil openai PyYAML

（実際の requirements.txt はリポジトリに合わせて準備してください）

---

## セットアップ手順

1. リポジトリをチェックアウト
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. データディレクトリの準備（デフォルト）
   - data/ （SQLite, DuckDB, PID/フラグファイルなどを格納）
   - logs/ （ログ出力先）
   これらは起動時に自動作成されることが多いですが、権限等の都合で事前作成しておくと安全です。
5. .env ファイルを作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - 手動: .env.example を参考に .env を作成（.env は絶対に Git に含めないでください）
6. 設定検証（起動前確認）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い

---

## 環境変数（主要）

（代表的なもののみ抜粋）

- KABUSYS_ENV
  - development / paper_trading / live
  - 動作モードを指定。paper_trading の場合は発注にモックブローカーを利用し DB を分離します。
- JQUANTS_REFRESH_TOKEN
  - J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD
  - kabuステーション API パスワード（必須）
- KABU_API_BASE_URL
  - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LOG_LEVEL
  - ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（ペーパートレードの約定モード: instant / partial / never / reject）
- OPENAI_API_KEY（AI 機能利用時に必要）
- LOG_DIR（ログ出力先ディレクトリ。デフォルト logs/）
- KILL_FLAG_CLEAR_ON_START（起動時に既存 kill.flag を自動クリアするか。0/1）

実行時上書き例:
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。デフォルト 60。1 以上の正の整数。

---

## 使い方（起動 / CLI）

- 対話式 .env 作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 概要:
    - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）
    - 停止は data/stop_requested.flag を作成すると検知して停止する
    - PID ファイル: data/execution.pid（Settings.pid_file_path）

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 概要:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定（秒、デフォルト 60）
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用（監視は常に本番 DB を見に行く）
    - 停止は data/stop_requested.flag を検知して終了

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能（優先度: --db > 環境変数 > デフォルト）

- AI 機能（ライブラリ呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続、対象日、OpenAI API key（未指定なら環境変数 OPENAI_API_KEY）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - DuckDB 接続に対してレジームを判定して DB へ書き込み

注意: AI 機能は OpenAI API キーが必須。API 呼び出しは外部料金が発生します。

---

## 停止 / Kill Switch の取り扱い

- run_execution / run_monitoring はプロセス管理のため下記ファイルを参照します:
  - data/stop_requested.flag: 存在すると run_execution/run_monitoring は終了します（手動停止用）。
  - data/kill.flag: Monitoring の KillSwitch が検知した場合に書き込まれ、ExecutionEngine に停止シグナルとして利用されます。
  - data/execution.pid: ExecutionEngine の PID を保存するファイル（Settings.pid_file_path）。

- KillSwitch は RiskMonitor 等の結果をもとに kill.flag を作成します（冪等）。起動時に自動クリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を設定できますが、本番では 0 を推奨します。

---

## ロギング

- ログはデフォルトで stdout に出力され、ファイルは logs/<app_name>.log に日次ローテーションで保存されます（30日分保持）。
- setup_logging を全スクリプトから呼び出して統一的に扱います。
- ログ出力先・レベルは環境変数 LOG_DIR / LOG_LEVEL で調整可能。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py                                — パッケージ定義（__version__ 等）
  - config.py                                  — Settings クラス: 環境変数読み込み・検証、自動 .env ロード機能
  - config_setup.py                             — .env 対話型ウィザード
  - validate_config.py                          — 起動前設定検証 CLI
  - run_execution.py                             — ExecutionEngine 起動スクリプト
  - run_monitoring.py                            — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py               — ペーパートレード検証レポート
  - utils/
    - logging_setup.py                           — ログ初期化ユーティリティ
    - process_priority.py                        — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py                           — MonitoringDB（SQLite テーブル定義・永続化 API）
    - monitoring_engine.py                       — 各 Monitor を束ねる Engine
    - system_monitor.py                          — システム状態・データ鮮度監視
    - risk_monitor.py                            — ドローダウン・ポジション上限監視
    - trade_monitor.py                            — (存在想定) 発注ログ監視（抜粋コードでは参照あり）
    - kill_switch.py                              — kill.flag 管理
    - alert_manager.py                            — (存在想定) アラート送信管理
  - execution/
    - execution_engine.py                         — (存在想定) 実行エンジン本体（run_execution から使用）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py 等
  - portfolio/
    - portfolio_builder.py                        — 候補選定・等重／スコア重み計算
    - position_sizing.py                          — 発注株数決定・集約キャップ処理
    - risk_adjustment.py                          — セクター制限・レジーム乗数
  - research/
    - factor_research.py                          — モメンタム・バリュー・ボラティリティ等
    - feature_exploration.py                      — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py                                 — ニュースセンチメント評価（OpenAI 使用）
    - regime_detector.py                          — 市場レジーム判定（ETF + マクロ記事 + LLM）
  - data/ (実行時生成)
    - monitoring.db (デフォルト: data/monitoring.db)
    - paper_trading.db (paper_trading 時)
    - kabusys.duckdb (デフォルト: data/kabusys.duckdb)
    - execution.pid, stop_requested.flag, kill.flag, ...

注: 上記は主要ファイルの一覧です。実行エンジンやブローカークライアント等、ここに含まれないモジュールは別途実装が必要です。

---

## 実用上の注意 / ベストプラクティス

- 本番での起動前に必ず python -m kabusys.validate_config を実行して設定ミスを検出してください。
- .env は機密情報を含むためバージョン管理に含めないでください。
- paper_trading モードは本番 DB と明確に分離されるよう PAPER_TRADING_SQLITE_PATH を利用してください（デフォルト: data/paper_trading.db）。
- OpenAI を使う機能は費用が発生します。API キー管理と利用頻度に注意してください（レート制限・コスト）。
- run_execution / run_monitoring は stop_requested.flag を検知して終了します。デプロイ時にプロセスマネージャ（systemd / supervisor / docker 等）で適切に管理してください。
- ログディレクトリ作成に失敗するとファイルロギングが無効化され、コンソール出力のみとなります。ログディレクトリ権限を確認してください。

---

## 参考コマンドまとめ

- .env 作成（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 実行エンジン起動
  - python -m kabusys.run_execution
- 監視ループ起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- AI モジュール呼び出し（ライブラリ利用例）
  - from kabusys.ai import score_news
    score_news(conn, date(2026,4,1), api_key="sk-...")

---

もし README に追記してほしい内容（例: 実行エンジン内部仕様、OrderRepository API、CI 設定、実運用時の systemd サービス定義など）があれば教えてください。