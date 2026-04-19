# KabuSys

日本株自動売買システムのモジュール群（ライブラリ・起動スクリプト・運用ツール群）です。  
このリポジトリは取引エンジン・監視・ポートフォリオ構築・リサーチ・AI 補助（ニュースセンチメントなど）を含むコンポーネントを提供します。

## 概要
- System / Execution / Monitoring / Research / AI / Portfolio などの機能を分離したモジュール構成。
- ローカル開発（development）、ペーパートレード（paper_trading）、本番（live）を環境変数で切り替え可能。
- SQLite（監視・ペーパートレード DB）と DuckDB（時系列 / 分析）を使用するデータレイヤ。
- OpenAI を利用したニュースセンチメント評価、レジーム判定等の AI モジュールを提供（API キーが必要）。
- 運用向けにログ設定・プロセス優先度設定・Kill Switch 等の安全機構を備えています。

## 主な機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番/ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアントの抽象化（MockBrokerClient をペーパートレードで使用）
  - PID ファイル管理、停止フラグ検知
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリング
  - KillSwitch 評価 → 必要時に data/kill.flag を書き込み
  - 監視ログを SQLite に永続化（monitoring_db）
- Portfolio 構築ユーティリティ
  - 候補選定、重み計算、ポジションサイズ計算、セクターキャップ、レジーム乗数
- Research（research パッケージ）
  - ファクター計算（momentum/value/volatility）
  - 将来リターン・IC 計算・特徴量統計
- AI（ai パッケージ）
  - news_nlp: ニュースから銘柄ごとのセンチメントを生成して ai_scores に格納（OpenAI 使用）
  - regime_detector: ETF とマクロニュースを使った市場レジーム判定
- Tools
  - paper_verification_report: ペーパートレード DB を集計して検証レポートを出力
- ユーティリティ
  - 環境設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ロギング設定、プロセス優先度設定ユーティリティ

## 必要条件（主な Python パッケージ）
（プロジェクトに requirements.txt が無い場合は下記を参考にインストールしてください）
- Python 3.10+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config の静的検証を行う場合に推奨）
- そのほか標準ライブラリ

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

## セットアップ手順（ローカル）
1. リポジトリをクローン
2. 仮想環境の作成と依存パッケージのインストール（上記参照）
3. データ / ログ ディレクトリの作成（任意ですが自動で作られます）
   - デフォルト DB / ログパス:
     - data/monitoring.db (SQLITE_PATH デフォルト)
     - data/paper_trading.db (PAPER_TRADING_SQLITE_PATH デフォルト)
     - data/kabusys.duckdb (DUCKDB_PATH デフォルト)
     - logs/ (LOG_DIR デフォルト)
4. 環境変数を設定 (.env を作成)
   - 対話式で .env を作る: python -m kabusys.config_setup
   - 手動で設定する場合は .env にキーを記載（.env.example を参考にすること）
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合: python -m kabusys.validate_config --strict

## 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: 分析用 DuckDB パス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必要）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60 秒）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

※ Settings クラスで環境変数の検証を行います。必須が欠けていると起動時に例外を送出します。

## 実行方法（代表的なコマンド）
- 環境設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視ループ起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（秒）
  - run_monitoring はプロセス優先度を high に設定し、監視ログを監視用 SQLite に書き込みます。
  - 停止はプロジェクトの data/stop_requested.flag を作成することで検知され終了します。

- ExecutionEngine 起動
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中に data/stop_requested.flag を作るとエンジンを停止します。

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db で DB パスを指定可能。未指定時は PAPER_TRADING_SQLITE_PATH 環境変数またはデフォルトを使用。
  - 稼働率・約定率・レイテンシ等を評価し PASS/FAIL を表示します。

- AI モジュール（プログラムから呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数または OPENAI_API_KEY 環境変数で指定します。

## 運用上の注意・フラグ周り
- 停止リクエスト:
  - run_monitoring / run_execution はプロジェクトルートの data/stop_requested.flag を監視しており、作成されるとループを抜けます。
  - KillSwitch（監視コンポーネント）は data/kill.flag を書き込み、ExecutionEngine 側の安全停止トリガーとして機能します（本番運用で重大なリスク条件が検知された場合に用いる）。
- KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動で削除します（本番では危険なので 0 推奨）。
- Logging:
  - setup_logging を全起動スクリプトが呼び出します。デフォルトでコンソール出力と logs/<app_name>.log に日次ローテーションで保存します。

## ディレクトリ構成（要約）
（src/kabusys 以下の主要ファイル・パッケージ）
- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数 / .env 自動読み込み / Settings クラス
- src/kabusys/config_setup.py
  - .env 対話式ウィザード
- src/kabusys/validate_config.py
  - 起動前の設定検証 CLI
- src/kabusys/run_monitoring.py
  - Monitoring ポーリングループ起動スクリプト
- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト
- src/kabusys/utils/
  - logging_setup.py — ログ初期化
  - process_priority.py — 優先度 / CPU affinity
- src/kabusys/monitoring/
  - monitoring_db.py — SQLite 永続化層
  - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py 等
- src/kabusys/execution/
  - execution_engine, broker_factory, order_manager, order_repository, reconciler, risk_manager 等（発注ロジック）
- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- src/kabusys/research/
  - factor_research.py, feature_exploration.py
- src/kabusys/ai/
  - news_nlp.py, regime_detector.py
- src/kabusys/tools/
  - paper_verification_report.py

（実際のリポジトリは上記以外にも細かいファイルが存在します。上の一覧は主要ファイルの概要です。）

## 開発時のヒント
- DuckDB は分析用途の読み取り中心 DB として想定されています。DuckDB 接続を渡すことでファクター計算等が行われます。
- SQLite は軽量な永続化（監視ログ / ペーパートレードログ）に使用します。ペーパートレードは本番 DB と分離するため PAPER_TRADING_SQLITE_PATH を用意しています。
- AI 機能（news_nlp/regime_detector）は OpenAI API を利用します。ローカルでのテスト時は API 呼び出し部分をモックすることを推奨します（モジュール内で呼び出し関数を分離しているため patch が容易です）。
- config.py はプロジェクトルート（.git または pyproject.toml）を基準に .env を自動ロードします。テストで自動ロードを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## ライセンス / バージョン
- パッケージのバージョンは src/kabusys/__init__.py の __version__ を参照してください（現在 0.1.0）。

---

さらに詳細な使い方や各モジュールの内部仕様はソースコードのドキュメンテーション文字列（docstring）を参照してください。質問や README の拡張希望があれば、どの箇所を詳述したいか教えてください。