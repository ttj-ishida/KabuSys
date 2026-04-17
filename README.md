# KabuSys

日本株自動売買システムのコードベース（抜粋）。この README はリポジトリ内の主要モジュールを基に作成しています。セットアップ、主要機能、実行方法、ディレクトリ構成などを日本語でまとめています。

## プロジェクト概要
KabuSys は日本株の自動売買・リサーチ・監視機能を備えたシステムです。主な機能は以下のとおりです：
- 発注エンジン（ExecutionEngine）／注文管理（OrderManager, OrderRepository）
- 監視（Monitoring）：システム状態、注文滞留、リスク（ドローダウン・ポジション上限）を監視し、Kill Switch を発動
- ポートフォリオ構築：候補選定、重み算出、ポジションサイズ計算、セクター制限、レジーム適用
- リサーチ：ファクター計算（Momentum/Value/Volatility 等）、特徴量探索（IC 等）
- AI モジュール：ニュースの NLP スコアリング、レジーム判定（OpenAI API を利用）
- ツール：Paper Trading 検証レポート生成、対話式 .env ウィザード、設定検証 CLI
- 永続化：DuckDB（分析用）および SQLite（監視/取引ログ用）

設計上のポイント：
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離（data/paper_trading.db が既定）
- 監視（monitoring）は環境に関わらず本番の sqlite_path を使用（意図的）
- LLM（OpenAI）呼び出しはフェイルセーフ実装で、API 失敗時は安全側のフォールバック

---

## 機能一覧（抜粋）
- run_execution.py: 発注エンジンを起動（KABUSYS_ENV に応じて MockBroker を使用）
- run_monitoring.py: SystemMonitor のポーリングループ起動
- config_setup.py: 対話式 .env 作成ウィザード
- validate_config.py: 環境変数 / config/*.yaml の事前検証 CLI
- tools/paper_verification_report.py: Paper Trading 検証レポート生成
- monitoring/*: system_monitor, trade_monitor, risk_monitor, monitoring_engine, alert_manager, kill_switch
- ai/*: news_nlp（ニュースセンチメント → ai_scores 書込）, regime_detector（市場レジーム判定）
- portfolio/*: 候補選定、重み計算、セクターキャップ、ポジションサイズ計算
- research/*: ファクター計算（momentum/value/volatility）、forward return、IC、統計サマリー
- utils/process_priority.py: プロセス優先度・CPU affinity のユーティリティ

---

## 必要な依存ライブラリ（例）
本リポジトリに requirements.txt は含まれていない想定です。少なくとも次をインストールしてください。
- Python 3.8+
- duckdb
- psutil
- openai
- requests
- PyYAML（config YAML 検証を行う場合に必要）

例：
pip install duckdb psutil openai requests pyyaml

---

## 環境変数（主なもの）
（Settings クラスにより取得されるもの。デフォルト値は Settings の docstring に準拠）

必須（少なくとも設定が必要）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意／デフォルト値
- KABUSYS_ENV: execution 環境（development / paper_trading / live） — デフォルト: development
- DUCKDB_PATH: 分析用 DuckDB のパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 sqlite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp, regime_detector 等）の API キー
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知の設定（任意）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant, partial, never, reject）

監視関連
- KILL_FLAG_PATH: data/kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアするか（"1" でクリア、デフォルト: "0"）
- PID_FILE_PATH: execution.pid のパス（デフォルト: data/execution.pid）

モニタリング間隔
- MONITOR_POLL_INTERVAL: run_monitoring が使うポーリング間隔（秒）。デフォルト 60 秒。1 未満・不正値は無視されデフォルトにフォールバック。

---

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローンして Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai requests pyyaml

3. .env を生成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   ウィザードは .env を生成します。生成後に設定検証を推奨します。

4. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合: python -m kabusys.validate_config --strict

5. DB ファイル初期化
   - monitoring 用の SQLite は run_execution/run_monitoring 実行時に init_monitoring_db により自動作成されます。
   - DuckDB ファイルは必要に応じて SQL スクリプトやデータインポートで準備してください。

---

## 実行方法（主要スクリプト）
パッケージをインストール済みであれば、モジュールとして Python から起動できます。

1. 実行エンジン（ExecutionEngine）
   - 本番・紙取引判定は KABUSYS_ENV に依存します。
   - 起動:
     - python -m kabusys.run_execution
   - 特記事項:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
     - data/stop_requested.flag が存在すると起動をスキップ・実行中に検知すると停止します。
     - 実行中は PID が data/execution.pid に書き込まれます。

2. 監視ループ（SystemMonitor）
   - 起動:
     - python -m kabusys.run_monitoring
   - モニタリング間隔:
     - 環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）
   - 注意:
     - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path（Settings.sqlite_path）を使用します（監視 DB は本番と共有される想定）。

3. Paper Trading 検証レポート（レポート生成）
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD
     - --to YYYY-MM-DD
     - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

4. 設定ウィザード / 検証
   - .env ウィザード: python -m kabusys.config_setup
   - 設定検証: python -m kabusys.validate_config [--strict]

5. AI 関連（ニュース NLP / レジーム判定）
   - OpenAI の API キー（OPENAI_API_KEY）を設定する必要があります。
   - news_nlp.score_news や regime_detector.score_regime は DuckDB 接続と target_date を渡して呼び出します（CLI ラッパーは無し、コード内から利用）。

---

## 停止・Kill Switch
- kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）を作成すると ExecutionEngine に停止シグナルを送ります（KillSwitch が評価して書き込み）。
- run_monitoring/run_execution はそれぞれ data/stop_requested.flag（プロジェクトルート下 data/stop_requested.flag）を監視します。これが存在すると監視ループは終了または起動をスキップします。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に kill.flag を自動クリアします（本番では危険なので推奨しません）。

---

## 使い方の例（実戦的な起動手順）
1. .env を作成・確認
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config

2. Paper trading（ローカルテスト）でエンジンを起動
   - export KABUSYS_ENV=paper_trading
   - python -m kabusys.run_execution

3. 監視プロセスを別ターミナルで起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL を変えたい場合:
     - export MONITOR_POLL_INTERVAL=30

4. Paper 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## ディレクトリ構成（抜粋）
以下はコードベース内にある主要ファイル / ディレクトリの抜粋です（実際のファイルはさらに存在する可能性があります）。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - utils/
      - __init__.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
    - execution/
      - (OrderManager / ExecutionEngine / BrokerFactory 等の実装ファイル群)
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
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - tools/
      - __init__.py
      - paper_verification_report.py

---

## 開発上の注意・補足
- ローカル開発では KABUSYS_ENV=development を推奨（実際の発注は行われないよう設計）。
- Paper trading は本番 DB と完全分離して動作するため、実機テストに便利です。
- LLM 呼び出し（OpenAI）はコストとレート制限があります。API キーとコスト管理に注意してください。
- monitoring の実行は本番の監視 DB を参照します。誤った設定で本番 DB を壊さないよう注意してください。
- Settings の自動 .env ロードは、プロジェクトルートの検出（.git または pyproject.toml）に依存します。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化できます。

---

もし README に追記したい内容（例: CI/CD 手順、詳細な API ドキュメント、実行例ログ、単体テスト方法など）があれば教えてください。必要に応じてセクションを追加して拡張します。