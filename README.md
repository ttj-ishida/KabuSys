# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム（KabuSys）の一部実装です。ポートフォリオ構築・ポジションサイズ計算・監視・発注エンジンの起動スクリプトや、研究 / AI 補助モジュールを含みます。

本 README ではプロジェクト概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

- 目的: 日本株の自動売買を行うためのバックエンドロジック群（シグナル→ポートフォリオ構築→発注）と、稼働監視・リスク管理、検証ツールを提供。
- 設計方針:
  - DuckDB を使った時系列データ分析（prices_daily / raw_financials 等）
  - SQLite に監視ログ・トレードログを保存（運用時は本番 DB、ペーパートレードは別ファイル）
  - モジュールは可能な限り副作用を避け、純粋関数や明確な入出力で実装
  - 本番／ペーパートレードの分離（環境変数 KABUSYS_ENV）
  - OpenAI（gpt-4o-mini など）を用いたニュース NLP・レジーム判定機能（APIキー必須）

---

## 主な機能一覧

- 実行系 / 監視
  - run_execution: ExecutionEngine の起動スクリプト（KABUSYS_ENV=paper_trading では MockBroker を使用し、paper_trading DB に記録）
  - run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可能）
  - Kill Switch: 条件（ドローダウンやポジション上限等）を満たすと data/kill.flag を書き込み ExecutionEngine を停止
  - AlertManager: LINE Messaging API による通知（トークン未設定時はログ出力のみ）

- 監視・リスク
  - SystemMonitor: CPU/メモリ/Disk、データ鮮度、Execution プロセス監視
  - TradeMonitor: 滞留注文・約定異常価格チェック
  - RiskMonitor: ドローダウン・ポジション上限の監視とダッシュボード更新
  - MonitoringDB: SQLite 用の永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）

- ポートフォリオ / 発注（ライブラリ）
  - portfolio: 候補選定、等重/スコア重み、ポジションサイズ計算（単元株丸め、リスクベース等）
  - position_sizing: 投下資金制御、lot 単位での丸め、aggregate cap のスケーリング

- 研究 / 分析
  - research.factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - research.feature_exploration: 将来リターン計算、IC（スピアマンランク相関）、統計サマリー

- AI 関連
  - ai.news_nlp: raw_news を OpenAI に投げて銘柄単位のセンチメントスコアを ai_scores テーブルへ書き込み
  - ai.regime_detector: ETF（1321）の MA200 乖離 + マクロニュースの LLM センチメントを合成し市場レジーム判定を実行

- ツール
  - tools.paper_verification_report: ペーパートレード結果のサマリ／Pass/Fail 判定（稼働率・約定率・レイテンシ等）
  - config_setup: .env の対話式生成ウィザード
  - validate_config: .env と config/*.yaml の起動前検証 CLI

---

## セットアップ手順（開発 / 簡易）

1. Python 環境（推奨: 3.10+）を用意
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール（プロジェクトに requirements.txt が無い場合、少なくとも以下）
   - pip install duckdb psutil requests openai
   - 追加で YAML 検証を使う場合: pip install pyyaml
4. プロジェクトルートに移動（README などがあるルート）
5. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは .env.example を参考に .env を手動作成
6. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告を厳格に扱う: python -m kabusys.validate_config --strict
7. データディレクトリ作成（必要に応じて）
   - デフォルト DB パス: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db
   - 監視フラグ等: data/kill.flag, data/stop_requested.flag, data/execution.pid

注意:
- OpenAI を使う処理（news_nlp, regime_detector）は OpenAI API キー (OPENAI_API_KEY) が必要です。
- 本番モード（KABUSYS_ENV=live）での実行は実際の発注を行います。設定は慎重に。

---

## 主要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker を使い data/paper_trading.db に記録
  - live: 実発注
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の約定モード: instant | partial | never | reject）
- OPENAI_API_KEY（AI 機能で必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager 用）
- LOG_LEVEL（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、"1" でクリア）

---

## 使い方（実行例）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（発注系）起動
  - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading の場合、MockBroker が使われ paper_trading DB（PAPER_TRADING_SQLITE_PATH）に分離して記録される
    - 停止は data/stop_requested.flag を作成するか、ExecutionEngine による kill.flag 検出によって行われる
    - 実行中は data/execution.pid に PID が書き込まれる

- Monitoring 起動（SystemMonitor のループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔(秒)を上書き可能（例: MONITOR_POLL_INTERVAL=30）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 系（例: ニューススコアリング・レジーム判定）
  - ai.score_news, ai.regime_detector.score_regime を呼ぶ（コードから直接使用）
  - どちらも OPENAI_API_KEY が必要。関数は DuckDB 接続と target_date を受け取り DB に書き込みます。

- Kill Switch / 強制停止
  - KillSwitch は監視結果から条件を満たした場合に data/kill.flag を書き込みます（ExecutionEngine はこの存在を検出して停止を試みます）
  - 手動で停止する場合: data/stop_requested.flag を作成して run_monitoring/run_execution のループを終了させることができる（両スクリプトで利用）

---

## 重要な挙動・注意点

- 監視用 SQLite（monitoring）は run_monitoring が本番 DB パスを使って初期化します（KABUSYS_ENV に依らず同じ sqlite_path を使う実装箇所あり）。一方、ExecutionEngine は paper_trading 時に専用 DB を使う。
- .env 自動読み込み: プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に .env / .env.local を自動で読み込みます。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定して無効化できます。
- モジュールは外部 API（kabu API, J-Quants, OpenAI）に依存します。テスト時は該当呼び出しをモックすることを推奨します（コード内でもテストフレンドリーな設計になっています）。
- DB スキーマのマイグレーションは起動時に簡易処理があります（例: dashboard に peak_value が無い場合は追加）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数の取得・検証、自動 .env 読み込み機能
  - config_setup.py
    - .env を対話式に生成
  - validate_config.py
    - 起動前チェック CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py  — SQLite スキーマ初期化／読み書き
    - system_monitor.py  — システム・データ鮮度監視
    - trade_monitor.py   — 注文滞留・約定異常チェック
    - risk_monitor.py    — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 監視コンポーネント束ね
    - alert_manager.py   — LINE 通知
    - kill_switch.py     — kill.flag の管理
  - execution/  （発注関連コンポーネント: BrokerFactory, ExecutionEngine, OrderManager, OrderRepository など）
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
  - utils/
    - process_priority.py  — 高優先度設定 / CPU affinity ユーティリティ
  - data/ （実行時のデータディレクトリ、DB ファイル・フラグ類を配置）

- config/
  - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
  - （validate_config が存在確認／パースを行います。pyyaml がない場合はパースはスキップされます）

---

## 開発のヒント / テスト上の取り扱い

- OpenAI 呼び出し、外部 API、psutil などはユニットテストでモック可能です。コード中にもテスト用に差し替え可能なポイント（例: _call_openai_api の patch）が用意されています。
- データベースは DuckDB / SQLite を用いるためテスト用に小さなファイルを作成して検証できます（paper_trading 用 DB を別ファイルで分けることで本番データを汚しません）。
- config_setup による .env 作成後は必ず validate_config でチェックしてください（特に KABUSYS_ENV=live の場合は注意喚起が出ます）。

---

この README はコードベースの主要機能と使用手順をまとめたものです。詳細な API 仕様や設計文書（PortfolioConstruction.md、StrategyModel.md など）が別途ある想定で、実装のコメントや docstring にも利用法や制約が書かれています。必要であれば各モジュール（例: ai/news_nlp.py、portfolio/position_sizing.py、monitoring/*）に対する詳細ドキュメントを追加します。