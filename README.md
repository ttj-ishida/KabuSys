# KabuSys — 日本株自動売買システム

このリポジトリは日本株自動売買システム「KabuSys」のコア部分を含みます。  
主に注文実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、ニュースNLP（OpenAI連携）などの機能を提供します。

バージョン: 0.1.0

---

## 概要

- ExecutionEngine: ブローカークライアント経由での発注、注文管理、リスク管理、リコンシリエーション。
- Monitoring: システム稼働状況、データ鮮度、注文ログ、リスク指標の定期チェックとアラート、必要に応じて Kill Switch による停止。
- Portfolio: 候補選定、重み付け、ポジションサイズ決定、セクター制限、レジーム乗数。
- Research: DuckDB を用いたファクター計算（Momentum、Volatility、Value）や特徴量解析。
- AI モジュール: ニュース記事のセンチメントを OpenAI で評価（news_nlp）、マクロとETFを使った市場レジーム判定（regime_detector）。
- CLI / ツール: .env 対話ウィザード、設定検証、Paper Trading 検証レポート生成等。

設計上の特徴:
- 設定は環境変数（.env）で管理。自動ロード機能あり。
- Paper Trading（テスト）は本番 DB と分離（data/paper_trading.db を使用）。
- 監視 DB（SQLite）や分析 DB（DuckDB）へ接続して内部テーブルを管理。
- OpenAI 等の外部 API 呼び出しはフェイルセーフにして、失敗時はスキップまたはフォールバックする設計。

---

## 主な機能一覧

- 実行（run_execution.py）
  - 環境に応じて MockBrokerClient（paper_trading）または実ブローカーを使用
  - OrderRepository / OrderManager / RiskManager / Reconciler 組み立て
  - ExecutionEngine をスレッドで起動、stop flag による安全停止

- 監視（run_monitoring.py / monitoring/*）
  - CPU/メモリ/ディスク、Execution プロセスの存在確認、データ鮮度チェック
  - trade_logs / risk_logs / dashboard の永続化（SQLite）
  - KillSwitch による停止フラグ生成と AlertManager 連携

- ポートフォリオ（portfolio/*）
  - 候補選定（スコア降順）、等配分/スコア加重配分
  - セクター上限チェック、レジーム乗数適用
  - ポジションサイズ計算（lot 単位丸め、aggregate cap のスケール調整）

- リサーチ（research/*）
  - DuckDB を用いたファクター計算（momentum, volatility, value）
  - 将来リターン・IC（スピアマン）・統計サマリ等

- AI（ai/*）
  - news_nlp: raw_news を集約し OpenAI で銘柄ごとのセンチメントスコアを生成して ai_scores に保存
  - regime_detector: ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して日次で regime 判定と保存

- ツール（tools/*）
  - paper_verification_report: Paper Trading DB を解析して Pass/Fail 判定のレポートを生成

- 設定管理
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の検証 CLI

---

## 要件 (推奨)

- Python 3.10+
  - typing の Union 短縮表記 (A | B) を使用しています。
- 主な依存パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証で YAML を検証する場合）
- 実行環境に応じたブローカークライアント（kabuステーション等）設定

インストール例:
- 仮想環境作成:
  - python -m venv .venv
  - source .venv/bin/activate
- 必須パッケージのインストール（requirements.txt がない場合の例）:
  - pip install duckdb psutil openai pyyaml

---

## セットアップ手順

1. リポジトリをクローンする
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 代表的な環境変数（.env に設定）:
     - JQUANTS_REFRESH_TOKEN=your_token_here
     - KABU_API_PASSWORD=your_password_here
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - OPENAI_API_KEY=sk-...
     - LOG_LEVEL=INFO
     - KILL_FLAG_CLEAR_ON_START=0

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 必要に応じて --strict を付けて警告もエラー扱いにする:
     - python -m kabusys.validate_config --strict

6. データディレクトリ等の作成（通常は自動作成されますが明示的に）
   - mkdir -p data logs

---

## 使い方（起動例）

- ExecutionEngine を起動（デフォルトDB を使用。paper_trading の場合は .env で KABUSYS_ENV を設定）
  - python -m kabusys.run_execution

  注意:
  - 起動時に data/kill.flag が存在する場合は起動を中止します（kill flag があるとエンジンを起動しない安全設計）。
  - 実行中の停止は data/stop_requested.flag を作成すると検知して安全に停止します。
  - 実行時に PID ファイル (data/execution.pid) が使用されます。

- Monitoring を起動（ポーリングで SystemMonitor.check_once を周期実行）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト: 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  備考:
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを書きます。
  - 監視は system_status / trade_logs / risk_logs / dashboard を更新します。
  - data/stop_requested.flag を作ると監視ループは終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パス指定可能（優先度: --db > PAPER_TRADING_SQLITE_PATH 環境変数 > data/paper_trading.db）

- AI ツールの呼び出し（プログラム内 API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、target_date のニュースウィンドウを処理して ai_scores テーブルへ書き込む
    - api_key を省略すると OPENAI_API_KEY を参照

  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の ma200 とニュースセンチメントを使って market_regime に書き込む

---

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- DUCKDB_PATH: data/kabusys.duckdb (デフォルト)
- SQLITE_PATH: data/monitoring.db (監視 DB)
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 用 DB)
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか (0|1)

---

## 安全性・運用メモ

- Kill Switch:
  - RiskMonitor 等で条件を満たすと data/kill.flag を生成し、ExecutionEngine はこのフラグにより停止シグナルを受け取ります。
  - 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します（自動クリアは危険）。
- 停止フラグ:
  - data/stop_requested.flag を作成すると run_monitoring と run_execution のループが検知して終了します。
- ログ:
  - ログは stdout（StreamHandler）と日次ローテートファイル（logs/<app_name>.log）に出力されます。ログディレクトリへの書き込み権限に注意してください。
- DB マイグレーション:
  - init_monitoring_db() はテーブル作成や簡単なマイグレーション（カラム追加）を行います。運用環境での直接テーブル操作は注意してください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env ロードと Settings クラス
  - config_setup.py          — .env 対話ウィザード CLI
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP / OpenAI 連携
    - regime_detector.py      — 市場レジーム判定
  - monitoring/
    - monitoring_db.py        — SQLite 永続化レイヤー
    - system_monitor.py       — システム / データ鮮度監視
    - trade_monitor.py        — （注文ログ監視: ファイルにないが概念あり）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 制御
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — （アラート送信機能）
  - execution/
    - execution_engine.py     — ExecutionEngine 実装（エンジン本体）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py        — 共通ログ設定
    - process_priority.py     — プロセス優先度 / CPU affinity のユーティリティ

（実際のファイルは src/kabusys 以下を参照してください。ここに一部のみ抜粋しています）

---

## 開発・テスト時のヒント

- 自動環境変数ロードはデフォルトで有効。テストで無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI を利用するモジュールは API 呼び出し部分を容易にモック可能な設計です。テスト時は該当する内部呼び出し関数をパッチしてください（例: kabusys.ai.news_nlp._call_openai_api）。
- DuckDB / SQLite のパスは設定により変更可能。テスト用に別ファイルを使って本番 DB を汚さないでください（paper_trading 用 DB は別に用意されています）。

---

## よくあるコマンドまとめ

- .env を生成:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 実行:
  - python -m kabusys.run_execution

- Monitoring 実行:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または: python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

---

README に含めるべき追加情報（要望があれば追記します）
- requirements.txt の推奨内容
- デプロイ / systemd / Supervisor 用のサービス定義サンプル
- AlertManager の具体的な LINE 通知設定方法
- ExecutionEngine の API ドキュメント（関数シグネチャや挙動詳細）

必要であれば上記のうちどれを追加するか指示してください。