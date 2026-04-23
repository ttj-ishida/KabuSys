# KabuSys

日本株向けの自動売買システム用ライブラリ / 実行スクリプト群。  
戦略・ポートフォリオ構築、発注実行、監視、研究（ファクター計算）、AI を用いたニュースセンチメント評価などのコンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

このリポジトリは、以下の主要機能を持つモジュール群で構成されています。

- ExecutionEngine：発注・注文管理・リスク管理の実行エンジン
- Monitoring：システム健全性・注文状況・リスク（ドローダウン、ポジション上限）を定期チェックし、Kill Switch を発動可能
- Portfolio：候補選定・重み計算・ポジションサイズ算出・セクター制約適用
- Research：DuckDB 上の価格・財務データを用いたファクター計算・特徴量解析
- AI：OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価・レジーム判定
- ユーティリティ：ログ設定、プロセス優先度設定、設定の読み込み/ウィザード/検証ツール 等
- CLI スクリプト群：設定ウィザード、設定検証、監視・実行プロセス起動、ペーパートレード検証レポート生成 等

設計方針の一部：
- 環境変数（.env / .env.local）を優先して設定を読み込む
- Paper Trading は本番 DB と分離（専用 SQLite）
- AI 呼び出しは安全なリトライ・バリデーション処理を実装
- DuckDB を分析用データベースとして利用

---

## 機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
- Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）
- MonitoringEngine：System / Trade / Risk 各 Monitor を束ね、Kill Switch 評価・アラート送信
- RiskMonitor：ドローダウン監視、ポジション上限監視、ダッシュボード更新
- MonitoringDB：SQLite による監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）
- Portfolio モジュール：候補選定、等重/スコア重み、ポジションサイズ計算、セクター上限・レジーム乗数
- Research モジュール：モメンタム・ボラティリティ・バリュー等のファクター計算、将来リターン・IC 計算
- AI モジュール：
  - news_nlp.score_news: raw_news を集約して OpenAI に投げ、ai_scores に書き込む
  - regime_detector.score_regime: ETF の MA 乖離＋マクロニュースセンチメントで市況レジームを判定
- ツール: Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順

1. リポジトリをチェックアウト
   - ソースはパッケージルートが src/ にある想定です（例: src/kabusys/...）。

2. Python 環境の準備（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt があれば: pip install -r requirements.txt  
   - 最低限必要なパッケージ（本コードベースから）:
     - duckdb
     - psutil
     - openai (AI 機能を利用する場合)
     - PyYAML（config 検証で YAML を検査する場合に任意で必要）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - 重要: .env は Git にコミットしないでください。

5. データディレクトリの準備（必要に応じて）
   - デフォルトのファイルパス（環境変数で上書き可能）:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - PID_FILE_PATH: data/execution.pid
     - KILL_FLAG_PATH: data/kill.flag
   - ログディレクトリ:
     - デフォルト logs/（環境変数 LOG_DIR で変更可能）

6. OpenAI を使う機能を利用する場合
   - OPENAI_API_KEY を環境変数または関数引数で設定してください。
   - AI 機能は API キー必須（news_nlp, regime_detector など）。

---

## 使い方

- 設定ウィザード（.env を作成 / 更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いで exit(1)

- 監視ループを起動（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止方法:
    - data/stop_requested.flag を作成するとループが検知して終了します（スクリプト内で参照）
    - Ctrl+C (KeyboardInterrupt) で停止

- 実行エンジンを起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV による挙動:
    - development: 開発用（発注しない）
    - paper_trading: MockBrokerClient を使用、データは PAPER_TRADING_SQLITE_PATH（既定 data/paper_trading.db）に保存
    - live: 本番ブローカーを使用（kabuステーション等）
  - 停止フラグ:
    - data/stop_requested.flag があると起動を停止／実行中に検知して停止
  - PID ファイル:
    - 実行時に data/execution.pid（デフォルト）が使われます

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合: --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI モジュール（ニューススコア / レジーム評価）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - api_key が None の場合は環境変数 OPENAI_API_KEY を参照
  - regime_detector.score_regime(conn, target_date, api_key=None)

注意事項:
- Kill Switch（data/kill.flag）
  - RiskMonitor 等の判定により KillSwitch がトリガーされると kill.flag が書かれ、ExecutionEngine に停止シグナルを送る設計です。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされます（本番では 0 推奨）。
- Paper Trading は本番 DB と完全に分離されます。

---

## 主要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- DB / ファイルパス
  - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db)
  - PID_FILE_PATH (デフォルト data/execution.pid)
  - KILL_FLAG_PATH (デフォルト data/kill.flag)
- ロギング
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
  - LOG_DIR (デフォルト logs/)
- Monitoring
  - MONITOR_POLL_INTERVAL (秒、デフォルト 60)
- Paper Trading
  - PAPER_FILL_MODE (instant|partial|never|reject; デフォルト instant)
- AI
  - OPENAI_API_KEY

---

## ディレクトリ構成（抜粋）

（src 配下がパッケージルートです）

- src/
  - kabusys/
    - __init__.py
    - config.py                 -- 環境変数 / .env ロード・Settings
    - config_setup.py           -- .env 対話式ウィザード
    - validate_config.py        -- 設定検証 CLI
    - run_execution.py          -- ExecutionEngine 起動スクリプト
    - run_monitoring.py         -- SystemMonitor ポーリングループ起動スクリプト
    - utils/
      - logging_setup.py        -- ログ設定ユーティリティ
      - process_priority.py     -- 優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py        -- SQLite 永続化層（テーブル作成・読み書き）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - broker_factory.py
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
    - data/                      -- 実行時生成・配置想定（DB / flag / pid / logs 等）
  - pyproject.toml / setup.cfg 等（プロジェクトルート）

---

## 開発時のヒント / 注意点

- .env の自動読み込みは Settings モジュールで行われます（プロジェクトルートの .env / .env.local）。テスト等で自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- Monitoring と Execution はそれぞれ stop_requested.flag（data/stop_requested.flag）を監視して優雅に停止する設計です。手動停止や自動化のためにこのフラグを利用できます。
- ログ設定は kabusys.utils.logging_setup.setup_logging を全起動スクリプトで利用しており、logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリに書き込み権限が必要です。
- DuckDB を分析用に使うため、prices_daily / raw_financials / raw_news 等のテーブルスキーマに従ったデータ投入が必要です（本リポジトリには ETL スクリプトの抜粋はありません）。
- AI 機能を使う際は API コストに注意してください。エラーハンドリングはありつつもリクエスト頻度の管理が重要です。

---

必要であれば、README に含めるコマンド例、systemd ユニット例、docker-compose 構成例、より詳細な環境変数一覧やマイグレーション手順を追記します。どの情報を優先して追加しますか？