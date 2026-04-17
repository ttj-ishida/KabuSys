# KabuSys

日本株向け自動売買システムのコアライブラリ群（README）。  
ここではリポジトリ内の主要機能、セットアップ、起動方法、及びディレクトリ構成を日本語でまとめます。

注意: この README は src/kabusys 配下のコードベースに基づいて作成しています。実行時には環境変数や .env の設定が必要です。

---

## プロジェクト概要
KabuSys は日本株の自動売買／リサーチ／監視を行うためのモジュール群です。  
主な役割は以下です。

- 株価データや財務データを用いたファクター計算とリサーチ機能（research）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- ExecutionEngine（発注実行）の起動補助（run_execution.py）とブローカ抽象化
- 監視（Monitoring）機能：システム監視、注文監視、リスク監視、Kill Switch、アラート
- AI を用いたニュースセンチメント評価・市場レジーム判定モジュール（OpenAI 使用）
- 各種ユーティリティ（プロセス優先度設定など）
- CLI ツール群（.env ウィザード、設定検証、Paper Trading レポート等）

設計方針の一部:
- DuckDB / SQLite をデータ永続化に使用
- 本番 / ペーパートレードの DB を分離可能
- 外部 API 呼び出しは（AI やブローカーを除き）最小化
- ルックアヘッドバイアスを避ける設計（日時参照の扱い等）

---

## 機能一覧（抜粋）
- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBroker を用い、本番 DB と分離
- Monitoring 起動スクリプト: python -m kabusys.run_monitoring
  - モニタリングループ、MONITOR_POLL_INTERVAL でポーリング間隔調整可能
- Paper Trading 検証レポート出力: python -m kabusys.tools.paper_verification_report
- AI:
  - ニュース NLP（ニュースを LLM でスコアリングして ai_scores に書き込む）
  - 市場レジーム判定（ma200 + マクロセンチメント合成）
- Portfolio:
  - 候補選定、等重・スコア重み・リスクベース配分
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（lot 単位丸め、aggregate cap など）
- Monitoring:
  - SystemMonitor, TradeMonitor, RiskMonitor の統合
  - KillSwitch による flag ファイルで ExecutionEngine を停止する仕組み
- Utilities:
  - process priority / CPU affinity 設定（psutil ベース）
- DB スキーマ初期化 / マイグレーション（monitoring_db.init_monitoring_db）

---

## セットアップ手順（開発 / 実行環境）
前提:
- Python 3.10+（型記法に | を使っているため）
- git などでプロジェクトルートが存在すること（.env 自動ロードのために .git または pyproject.toml を参照）

1. リポジトリをチェックアウト:
   - git clone ... && cd repo

2. 仮想環境を作成して有効化（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要なパッケージをインストール:
   - 必須パッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で利用、任意）
   - インストール例:
     - pip install duckdb psutil openai pyyaml
   - プロジェクトに requirements.txt があれば:
     - pip install -r requirements.txt

4. 環境変数 / .env の準備:
   - プロジェクトルート（.git または pyproject.toml がある場所）に .env を配置すると自動で読み込まれます。
   - 自動読み込みを無効にする場合は:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - .env 作成は対話ウィザードを利用可能:
     - python -m kabusys.config_setup

主要な環境変数（必須・重要）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能を使う場合）
- KABUSYS_ENV: development | paper_trading | live（default: development）
- DUCKDB_PATH（default: data/kabusys.duckdb）
- SQLITE_PATH（monitoring 用、default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、default: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の約定動作: instant|partial|never|reject）
- LOG_LEVEL（DEBUG|INFO|...）
- KILL_FLAG_CLEAR_ON_START（0/1、本番では 0 推奨）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信用、任意）
- MONITOR_POLL_INTERVAL（Monitoring のポーリング間隔秒、デフォルト 60）

注意:
- Monitoring は KABUSYS_ENV にかかわらず「本番 sqlite_path」を使用する実装です（run_monitoring.py 内の設計）。
- Execution は KABUSYS_ENV=paper_trading のとき PAPER_TRADING_SQLITE_PATH を使い DB を分離します。

---

## 使い方（代表的なコマンド）
以下はプロジェクトルートで実行する想定です。

1. .env の初期作成（対話式）
   - python -m kabusys.config_setup
   - 生成後は python -m kabusys.validate_config で検証

2. 設定検証
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗とする）:
     - python -m kabusys.validate_config --strict

3. ExecutionEngine を起動（本番 / paper_trading: KABUSYS_ENV に依存）
   - python -m kabusys.run_execution
   - 実行中に data/stop_requested.flag を作ると停止シグナル（run_execution は data/execution.pid に PID 書き込み）
   - run_execution は起動時に kill.flag の存在を確認しているため、必要に応じて .env の KILL_FLAG_CLEAR_ON_START 設定に注意

4. Monitoring を起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可（例: export MONITOR_POLL_INTERVAL=30）
   - 停止は data/stop_requested.flag を作成

5. Paper Trading 検証レポート（SQLite DB を読みレポートを標準出力へ）
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

6. AI 関連（プログラムから関数を呼ぶ）
   - ニュースセンチメント（例）:
     from kabusys.ai.news_nlp import score_news
     # score_news(conn, target_date, api_key="...")
   - レジーム判定:
     from kabusys.ai.regime_detector import score_regime
     # score_regime(conn, target_date, api_key="...")

7. ライブラリ関数の呼び出し（例）
   - ポートフォリオ候補選定:
     from kabusys.portfolio import select_candidates, calc_equal_weights
   - リサーチ関数:
     from kabusys.research import calc_momentum, calc_volatility, calc_value

停止フラグ / Kill Switch
- 実行停止: data/stop_requested.flag（run_monitoring/run_execution が監視している）
- Kill Switch（強制停止用）: data/kill.flag（KillSwitch が作成／存在チェック）
- 実行開始時に kill_flag の自動クリアをするかは KILL_FLAG_CLEAR_ON_START に依存

ログレベルは LOG_LEVEL 環境変数で調整します。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 配下の主なファイル・モジュールと役割です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数/.env 読み込み・Settings クラス
  - config_setup.py
    - .env の対話式ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading では MockBroker を使用）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - utils/
    - process_priority.py
      - psutil を使った優先度・CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py
      - SQLite スキーマ初期化 + MonitoringDB クラス（永続化層）
    - system_monitor.py
      - CPU/メモリ/Disk/プロセス/データ鮮度監視
    - trade_monitor.py
      - 注文滞留・約定異常監視
    - risk_monitor.py
      - ドローダウン／ポジション上限監視
    - kill_switch.py
      - Kill Switch（flag ファイル書き込みロジック）
    - monitoring_engine.py
      - 各モニタを束ねるエンジン（run / run_once）
    - alert_manager.py
      - （ファイル途中まで：アラート送信管理）
  - execution/
    - （ExecutionEngine、OrderRepository など — 起動スクリプトから利用）
  - portfolio/
    - portfolio_builder.py
      - 候補選定、等重／スコア重み
    - risk_adjustment.py
      - セクターキャップ、レジーム乗数
    - position_sizing.py
      - 発注株数の計算（lot 単位、aggregate cap）
  - research/
    - factor_research.py
      - モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB を使用）
    - feature_exploration.py
      - 将来リターン計算、IC（スピアマン）等
  - ai/
    - news_nlp.py
      - ニュース記事を OpenAI でスコアリングし ai_scores テーブルへ書き込み
    - regime_detector.py
      - ma200 とマクロセンチメントを合成して market_regime を算出・永続化
  - tools/
    - paper_verification_report.py
      - Paper Trading の検証レポート出力（SQLite DB の集計）

---

## 注意点 / 運用上のヒント
- 本番運用時は KABUSYS_ENV=live を設定し、LINE の通知設定や Kill Switch 設定を慎重に行ってください（validate_config がライブ時の追加チェックを行います）。
- OpenAI の呼び出しは API キー（OPENAI_API_KEY）が必須。API の失敗はフェイルセーフでロジック内で扱われますが、コスト・レイテンシを考慮してください。
- Paper Trading 用 DB は paper_trading モードで分離されます。実際の注文ロジックとデータを分けて検証できます。
- monitoring_db.init_monitoring_db は既存 DB に対しても冪等にスキーマを作成・マイグレーションしますが、重要な DB 操作を行う前にはバックアップを推奨します。
- .env は機密情報を含むため Git にコミットしないでください（config_setup はヘッダで注意喚起しています）。

---

## 参考コマンドまとめ
- .env ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

この README は現行コードベースの主要部分をカバーしています。追加の設定例や実運用時のデプロイ手順（systemd／Docker など）は、運用方針に合わせて別途まとめることを推奨します。必要があれば起動例（systemd ユニットや Dockerfile のテンプレート）も作成します。