# KabuSys

日本株向け自動売買システムのコアライブラリ群および付帯ツール群です。  
このリポジトリは、実行エンジン・監視・リサーチ・ポートフォリオ構築・AI 補助（ニュース NLU / レジーム判定）など、実運用を意識したコンポーネントで構成されています。

---

## 概要

KabuSys は以下を主眼に設計されています：

- 実行（ExecutionEngine）と監視（MonitoringEngine）を分離した堅牢な運用フロー
- ペーパートレード（本番 DB と分離）をサポートし、安全に戦略検証が可能
- DuckDB を使ったファクター計算・リサーチ処理（prices_daily / raw_financials 前提）
- OpenAI を利用したニュースセンチメント（news_nlp）とマクロレジーム判定（regime_detector）
- 環境設定ウィザードと検証 CLI による導入支援
- ログローテーション、プロセス優先度設定、Kill Switch 等の運用機能

---

## 主な機能一覧

- 実行関連
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により Paper / Live を切替）
  - ブローカークライアント抽象化（BrokerClientFactory）で Mock / 実ブローカーを選択
  - リスク管理（RiskManager）、注文管理（OrderManager）、照合（Reconciler）

- 監視関連
  - run_monitoring.py: SystemMonitor を定期ポーリングで実行
  - MonitoringEngine による複数モニタ（System / Trade / Risk）統合
  - Kill Switch（data/kill.flag）による ExecutionEngine 停止機構
  - 監視ログの永続化（SQLite）

- ポートフォリオ構築
  - 候補選定（select_candidates）、重み付け（equal / score）、ポジションサイズ計算（risk_based 等）
  - セクター上限適用、レジーム乗数

- リサーチ / ファクター計算
  - momentum / volatility / value 等のファクターを DuckDB 上で計算
  - 将来リターン、IC（Information Coefficient）、統計サマリ機能

- AI（OpenAI）連携
  - ニュースセンチメント（news_nlp.score_news）
  - マクロレジーム判定（ai.regime_detector.score_regime）
  - API 呼び出しはリトライやバリデーションを備え、フェイルセーフ設計

- 開発／運用ツール
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 環境変数・設定ファイルの起動前検証
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成

- ユーティリティ
  - ロギング設定（ログの stdout と 日次ローテーション）
  - プロセス優先度／CPU affinity 設定ユーティリティ

---

## セットアップ手順

1. Python 環境を準備
   - Python 3.9+ を想定（実際の依存バージョンは requirements.txt を参照してください）。
   - 仮想環境を作るのがおすすめ:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 例:
     - pip install duckdb psutil openai
   - オプション:
     - PyYAML があれば validate_config の YAML 検証が有効になります（pip install pyyaml）。

3. 環境変数の設定
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - または手動で .env を作成（リポジトリルートに置く）。主な必須変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - 主要な環境変数（省略可/デフォルトあり）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: DEBUG|INFO|...
     - PAPER_FILL_MODE: instant|partial|never|reject (Paper Trading の約定振る舞い)
     - LOG_DIR: ログ保存先（デフォルト logs/）

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります。

5. データディレクトリ等（任意）
   - デフォルトでは data/ 、logs/ を使用します。必要に応じて作成してくださいが、多くの起動スクリプトは起動時に自動作成を試みます。

---

## 使い方（主要コマンド）

- 実行エンジンを起動（本番 or paper_trading は KABUSYS_ENV に依存）
  - python -m kabusys.run_execution

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定例:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- ライブラリ API（コードから呼び出し）
  - AI スコアリング:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key=...)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=...)

注意点:
- run_execution/run_monitoring はそれぞれ data/ 内のフラグファイルを参照して停止制御を行います:
  - data/stop_requested.flag: これが存在するとループを停止します（両スクリプトで参照）
  - Kill Switch: monitoring が条件を満たすと data/kill.flag を書き込み、ExecutionEngine の停止を促します
- Paper Trading は本番 DB を汚さないよう専用の SQLite を使用します（PAPER_TRADING_SQLITE_PATH）

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用／挙動制御:
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL
- DUCKDB_PATH
- SQLITE_PATH
- PAPER_TRADING_SQLITE_PATH
- PID_FILE_PATH (デフォルト data/execution.pid)
- KILL_FLAG_PATH (デフォルト data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (1 にすると起動時に kill.flag を自動で削除)

AI 関連:
- OPENAI_API_KEY
- PAPER_FILL_MODE（paper_trading 時の約定モード）

その他:
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒）

---

## ディレクトリ構成

（src/kabusys をルートにした主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - execution/               — 実行エンジン関連（BrokerFactory, ExecutionEngine 等）
    - (複数の実装ファイル)

  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文ログ・滞留注文検知 等（実装あり）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - monitoring_engine.py   — 各 Monitor を束ねて定期実行
    - kill_switch.py         — kill.flag 書込みロジック
    - alert_manager.py       — 通知（LINE など）管理（実装あり）

  - portfolio/
    - portfolio_builder.py   — 候補選定・スコアソート
    - position_sizing.py     — 発注株数算出（risk / equal / score）
    - risk_adjustment.py     — セクター上限・レジーム乗数

  - research/
    - factor_research.py     — momentum/volatility/value 等
    - feature_exploration.py — 将来リターン・IC・統計サマリ

  - ai/
    - news_nlp.py            — ニュースを LLM でスコアリングし ai_scores に書込
    - regime_detector.py     — マクロ＋ETF MA でレジーム判定

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

  - data/                    — デフォルト DB / flag 等が置かれる場所（実行時に作成されることが多い）
  - logs/                    — ログファイル（logs/<app_name>.log）

---

## 運用上の注意

- KABUSYS_ENV=live の場合は設定ミスが重大な実資金損失に繋がります。validate_config の実行と LINE 通知の確認を必ず行ってください。
- kill.flag（KILL_FLAG_PATH）は本番環境で自動クリア（KILL_FLAG_CLEAR_ON_START=1）させると危険です。デフォルトは 0（クリアしない）を推奨します。
- run_execution は paper_trading 時に MockBrokerClient を使用し data/paper_trading.db に記録します。本番 SQLite（monitoring.db）とは分離されます。
- OpenAI API を利用する機能は API キーと使用料が必要です。モデルや呼び出し頻度に注意してください。
- DuckDB は大規模な分析に適しますが、prices_daily/raw_financials 等のテーブルは事前にロードしておく必要があります。

---

## 参考コマンドまとめ

- 仮想環境作成:
  - python -m venv .venv && source .venv/bin/activate
- 依存インストール（例）:
  - pip install duckdb psutil openai pyyaml
- .env 作成（ウィザード）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 監視起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースの現状に基づく概要・運用メモです。細部の実装や追加の設定は各モジュール（特に execution/*.py や monitoring/alert_manager.py 等）を参照してください。必要であれば、README に含める追加情報（依存パッケージの固定バージョン、docker-compose 例、systemd サービス定義など）を作成します。どの情報を追加しますか？