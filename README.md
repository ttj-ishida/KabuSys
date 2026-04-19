# KabuSys

日本株自動売買システムのモジュール群（ライブラリ + 起動スクリプト群）です。  
このリポジトリは取引エンジン（ExecutionEngine）、監視（Monitoring）、
リサーチ/ファクター計算、AI を用いたニュース解析などのコンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株向けの自動売買フレームワークで、以下の役割を持つモジュール群で構成されています。

- Execution: ブローカークライアントを用いた発注ロジック（本番 / ペーパートレード切替）
- Monitoring: システム状態・注文状態・リスク監視、Kill Switch による停止制御
- Portfolio: 候補選定、重み計算、ポジションサイジング、セクター制限など
- Research: DuckDB を使ったファクター計算、特徴量解析
- AI: OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価・レジーム判定
- Tools: ペーパートレード検証レポート生成等のユーティリティ
- Utils / Config: ロギング設定、プロセス優先度、環境変数読み込み、設定ウィザード等

設計上の特徴：
- 設定は .env（自動読み込み） / 環境変数で行う
- Paper Trading は本番 DB と分離（別 SQLite）
- DuckDB を分析 DB として利用
- OpenAI 呼び出しは堅牢なリトライ・バリデーションを実装

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV による本番/ペーパートレード切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更）
- 設定 / 検証
  - config_setup.py: .env を対話式に生成・更新するウィザード
  - validate_config.py: 起動前の設定検証 CLI（--strict オプションあり）
- 監視
  - system_monitor / trade_monitor / risk_monitor / monitoring_engine / kill_switch
  - 監視ログは SQLite（デフォルト: data/monitoring.db）に永続化
- ポートフォリオ構築
  - 候補選定、等重/スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数
- リサーチ
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）
  - IC 計算・将来リターン計算・統計サマリー
- AI
  - ニュースを LLM でスコア化して ai_scores テーブルへ書き込み
  - レジーム判定（ETF + マクロニュース）
- ツール
  - paper_verification_report: ペーパートレードの検証レポート生成

---

## セットアップ手順（開発用）

前提:
- Python 3.10 以上（型ヒントの union 演算子 `|` を使用）
- SQLite（標準ライブラリ）
- DuckDB, psutil, openai 等のパッケージが必要

1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   例:
   pip install duckdb psutil openai

   任意（YAML 検証）:
   pip install PyYAML

   （プロジェクトに requirements.txt がない場合、上記パッケージを手動でインストールしてください）

3. .env 作成（推奨: 対話式ウィザード）
   - python -m kabusys.config_setup
   これで .env が生成されます。既存の .env があれば読み込んで編集できます。

4. 設定検証
   - python -m kabusys.validate_config
   - 警告も厳密に扱いたい場合は --strict を付ける

5. データディレクトリ等の作成
   - デフォルトでは logs/、data/ 下に DB /フラグが作られます。必要に応じてディレクトリを作成。

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
  - paper_trading: MockBroker を使用し DB を分離
  - live: 本番発注
- DUCKDB_PATH: 分析用 DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで必須）
- LOG_LEVEL: ログレベル（例: INFO）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番アラート（任意）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（"1" で有効、デフォルト 0）

.env は .env.local で上書き可能。自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

---

## 使い方（最小コマンド例）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番/ペーパーは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - ペーパートレード時は KABUSYS_ENV=paper_trading を設定するか .env で指定する

  停止方法:
  - data/stop_requested.flag を作成するとループが検知して安全停止します
  - Kill Switch による停止は data/kill.flag を生成（KillSwitch クラス）することで ExecutionEngine を停止させられます

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI / リサーチ関数（プログラム的に利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - kabusys.research.calc_momentum(conn, date), calc_volatility, calc_value 等
  - DuckDB 接続（kabusys.config.Settings.duckdb_path）を渡して利用

---

## ログ / ファイル

- ログ: logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション、デフォルト 30 日保持）
- PID / フラグ:
  - data/execution.pid（ExecutionEngine が書き込む PID）
  - data/stop_requested.flag（ループを安全に終了するための外部フラグ）
  - data/kill.flag（KillSwitch が書き込む停止シグナル）
- DB:
  - DuckDB: data/kabusys.duckdb（分析用）
  - Monitoring SQLite: data/monitoring.db
  - Paper Trading DB: data/paper_trading.db（paper_trading 環境向け）

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py      — 監視 DB（SQLite）永続化層
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (参照)
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照)
  - execution/              — 発注関連（BrokerFactory, ExecutionEngine, OrderManager 等）
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

（上記は主要ファイルの抜粋です。細かいモジュールはソースを参照してください。）

---

## 運用上の注意

- KABUSYS_ENV=live の場合、設定ミスは実際の発注に繋がります。validate_config で十分に検証してください。
- ペーパートレードは本番 DB と完全分離されますが、.env の設定ミスに注意（PAPER_TRADING_SQLITE_PATH を確認）。
- OpenAI API を利用するモジュールは API キーとコストに注意して運用してください。API 呼び出しはリトライ・失敗フォールバックを実装していますが、過剰呼び出しは避けるべきです。
- ログディレクトリ / data ディレクトリに対する書き込み権限を確保してください。
- プロセス優先度設定（set_process_priority）や CPU affinity は権限不足で失敗する場合があります（警告ログが出ます）。

---

## 開発／拡張のヒント

- DuckDB を使ったリサーチモジュールは SQL を直接書いて効率的に集計を行います。テーブル定義に合わせてクエリを拡張してください。
- AI 呼び出し周り（news_nlp / regime_detector）は API レスポンスのバリデーションを重視しています。テスト時は内部の API 呼び出しをモックしてください（モジュール内で差し替え可能）。
- ポートフォリオ構築ロジック（position_sizing 等）は純粋関数として設計されているため、ユニットテストが書きやすくなっています。

---

何か追加で README に入れたい情報（例: サンプル .env、requirements.txt、デプロイ手順など）があれば教えてください。README をその内容に合わせて更新します。