# KabuSys

日本株自動売買システムの Python コードベースの README（日本語）

概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。開発者向けの参照ドキュメントとして利用してください。

---

## プロジェクト概要

KabuSys は日本株の自動売買・バックテスト・リサーチ用のモジュール群を備えたシステムです。本リポジトリには以下の主要機能を実装するコンポーネントが含まれます。

- ExecutionEngine（発注・注文管理・リスク管理）
- Monitoring（システム稼働監視・リスク監視・アラート・Kill Switch）
- Portfolio construction（候補選定・重み計算・ポジションサイズ算出・セクター制限）
- Research（ファクター計算・特徴量探索）
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、環境設定ウィザード、設定検証）
- ツール（Paper Trading の検証レポート生成など）

設計上の注意点：
- Paper Trading（シミュレーション）と Live（本番）は DB を分離して扱えるようになっています。
- OpenAI API を使う機能（ニュース NLP / レジーム判定）は API キーを必要とし、フェイルセーフ（API 失敗時のフォールバック）を備えています。
- .env により環境変数を管理し、`config/*.yaml` による構成ファイルも想定されています。

---

## 主な機能一覧

- 実行（Execution）
  - BrokerClientFactory によるブローカークライアント生成（本番 / mock の切替）
  - OrderRepository / OrderManager / RiskManager / ExecutionEngine による注文フロー
  - Paper Trading 用に専用 SQLite DB を利用可能

- 監視（Monitoring）
  - SystemMonitor：CPU / メモリ / ディスク、Execution プロセスの生存確認、データ鮮度チェック
  - TradeMonitor：注文の滞留・約定異常等の検出（実装ファイルあり）
  - RiskMonitor：ドローダウン・ポジション上限の監視とリスクログ記録
  - KillSwitch：条件に応じて `data/kill.flag` を書き込み、ExecutionEngine 停止をトリガー
  - MonitoringEngine：各 Monitor を束ねたポーリングループ

- ポートフォリオ構築（Portfolio）
  - 候補選定（スコア順ソート）
  - 重み算出（等金額・スコア加重）
  - セクターキャップ適用
  - ポジションサイズ算出（リスクベース／等分配等、単元株丸め、aggregate cap）

- リサーチ（Research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリ

- AI（OpenAI 連携）
  - news_nlp.score_news：ニュース記事を集約して LLM に投げ、銘柄ごとのセンチメントを ai_scores テーブルへ書き込む
  - regime_detector.score_regime：ETF MA 乖離とマクロニュースセンチメントを合成して市場レジームを判定・永続化

- ツール
  - config_setup.py：.env を対話的に作成・更新するウィザード
  - validate_config.py：.env および config/*.yaml の事前検証 CLI
  - tools.paper_verification_report：Paper Trading の検証レポート生成（コンソール出力）

- ユーティリティ
  - logging_setup: 統一ログ設定（コンソール + 日次ローテーションファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定
  - config.Settings: 環境変数管理と検証ユーティリティ

---

## 必要な依存パッケージ（代表例）

（プロジェクトに合わせて requirements.txt を用意してください。ここは代表的なパッケージ）

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config ファイル検証を行う場合）
- sqlite3（標準ライブラリ）
- logging（標準ライブラリ）

インストール例（pip）:
pip install duckdb psutil openai pyyaml

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) / .venv\Scripts\activate (Windows)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は上記の代表パッケージを個別にインストール）
4. .env を作成
   - 対話的に作る: python -m kabusys.config_setup
   - 主要な必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=your_token
     - KABU_API_PASSWORD=your_password
     - OPENAI_API_KEY=sk-...
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db (paper_trading 用)
     - LOG_LEVEL=INFO
     - KILL_FLAG_CLEAR_ON_START=0
     - PAPER_FILL_MODE=instant|partial|never|reject
   - 注意: .env は絶対に VCS にコミットしないでください

5. DB / ディレクトリ確認
   - default では data/ に SQLite・PID/flag ファイルが作成されます。必要に応じてディレクトリを作成してください（logging_setup が自動で logs/ を作成しますがパーミッションに注意）。

6. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict をつけると警告もエラー扱いになります

---

## 使い方（主要なコマンド）

CLI 形式でスクリプトを起動できます。いずれも仮想環境を有効にした状態で実行してください。

- 実行エンジン（発注・Order Engine）起動
  - python -m kabusys.run_execution
  - 説明: ExecutionEngine を起動し、BrokerClient（本番 or Mock）を使って注文フローを実行します。
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に結果を保存します（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在すると起動せずに終了します。
    - 実行中は data/execution.pid に PID が書かれます。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 説明: SystemMonitor をポーリングして監視ログを SQLite に記録します。
  - 環境変数:
    - MONITOR_POLL_INTERVAL（秒）: ポーリング間隔（デフォルト 60）
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（SQLITE_PATH）を使用して監視テーブルを永続化します。
  - 停止: data/stop_requested.flag を作成するとループが停止します

- 設定ウィザード
  - python -m kabusys.config_setup
  - 説明: .env を対話的に作成・更新します

- 設定検証
  - python -m kabusys.validate_config [--strict]
  - 説明: 必須環境変数や config/*.yaml の存在・基本整合性をチェックします

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 説明: paper_trading DB（デフォルト data/paper_trading.db）から統計を集計し PASS/FAIL 判定を出力します

- AI モジュールの利用（コードから呼び出す）
  - ニュース NLP（センチメント集計）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)  # api_key 未指定の場合は環境変数 OPENAI_API_KEY を使用
    - 引数 conn は duckdb.connect(...) で作成した DuckDB 接続オブジェクト
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)

注意: OpenAI の呼び出しは API 料金・レート制限があります。API キーは安全に管理してください。API 失敗時はフェイルセーフ動作（0.0 フォールバック等）がありますが、想定通りの動作保証はありません。

---

## 重要なファイル / フラグ / 動作影響

- data/kill.flag
  - KillSwitch が書き込む停止シグナルファイル。ExecutionEngine はこれを検知して停止します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされます（本番では 0 を推奨）。

- data/stop_requested.flag
  - run_monitoring / run_execution の外部停止トリガー（起動スクリプトが監視しているフラグ）

- data/execution.pid
  - run_execution によって書かれる PID ファイル

- logs/
  - 各アプリケーション（execution, monitoring など）のログファイルがここに日次ローテーションで保存されます。ログの設定は kabusys.utils.logging_setup.setup_logging を通して統一的に行われます。

---

## ディレクトリ構成

以下は src/kabusys 配下の主なファイル・モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理、自動 .env 読み込み
  - config_setup.py               — .env 対話的ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py                  — ニュース NLP / OpenAI 連携
    - regime_detector.py           — 市場レジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py             — SQLite 永続化層（monitoring 用）
    - system_monitor.py
    - trade_monitor.py             — （注文監視ロジック）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py             — （アラート発行ロジック、LINE等と連携する想定）
  - execution/
    - execution_engine.py          — ExecutionEngine 実装
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - monitoring/ (上記と重複)
  - data/ (実行時に生成される想定ディレクトリ: DB, pid, flag など)

（上記は主要ファイルの抜粋です。詳細はソースを参照してください。）

---

## 設定項目（主な環境変数一覧）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合に必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔秒。run_monitoring で使用)
- PAPER_FILL_MODE (paper_trading の MockBroker の約定挙動: instant|partial|never|reject)
- KILL_FLAG_CLEAR_ON_START (0 or 1)

---

## 開発上のヒント / 注意事項

- .env 自動ロード: config.py はプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動的に読み込みます。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- SQLite / DuckDB のパスは環境変数で上書き可能です（開発環境と本番で分離してください）。
- OpenAI 呼び出しは外部 API かつコストが発生します。レート制限や失敗時の挙動をコード内で確認してから運用してください。
- 本番環境（KABUSYS_ENV=live）の場合は特に kill.flag / KILL_FLAG_CLEAR_ON_START の設定、LINE 通知等の監視体制を整えてください。validate_config.py は live 用の追加ガードをチェックします。
- logging_setup でログディレクトリ作成に失敗した場合、ファイル出力は無効化されコンソール出力のみになります。ログの永続化先のパーミッションに注意してください。

---

README はここまでです。必要であれば以下の情報も追加できます（要望に応じて）：
- 各モジュールの詳細な API ドキュメント（関数引数・戻り値の仕様）
- テストの実行方法（pytest 等）
- デプロイ / systemd / コンテナ化に関する手順
- sample .env.example の生成

何を追加しましょうか？