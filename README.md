# KabuSys

日本株向けの自動売買システム（ライブラリ / ツール群）。  
ポートフォリオ構築、ポジションサイズ計算、監視 / Kill Switch、ペーパートレード検証、ニュース NLP に基づく AI スコアリング、レジーム判定などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール化された Python コードベースです。

- 市場データ（DuckDB の prices_daily 等）に基づくファクター計算・特徴量探索
- ポートフォリオ候補選定、重み付け、株数計算（単元丸め・リスク制約対応）
- ExecutionEngine / Broker 抽象経路（本番 / ペーパートレード切替）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch（安全停止）
- ニュースの LLM（OpenAI）によるセンチメント評価と市場レジーム判定
- ペーパートレード検証レポート生成ツール
- .env 対話式セットアップ & 設定検証 CLI

設計上、データベース（DuckDB / SQLite）や外部 API（kabuステーション、J-Quants、OpenAI）との連携を想定していますが、各モジュールは可能な限り副作用を抑え、テストしやすい純関数・小さなクラスに分割されています。

---

## 主な機能一覧

- portfolio
  - select_candidates（スコア降順選定）
  - calc_equal_weights / calc_score_weights（配分重み）
  - calc_position_sizes（リスクベース / 等配分 による発注株数算出）
  - apply_sector_cap / calc_regime_multiplier（セクター上限・レジーム乗数）
- research
  - calc_momentum / calc_value / calc_volatility（ファクター計算）
  - calc_forward_returns / calc_ic / factor_summary（特徴量解析）
- ai
  - news_nlp.score_news（ニュースを LLM に送って ai_scores を生成）
  - regime_detector.score_regime（マクロニュース + ETF MA によるレジーム判定）
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor（定期チェック）
  - MonitoringEngine（各 Monitor の統括ループ）
  - KillSwitch（Flag ファイルで ExecutionEngine を停止）
  - monitoring_db（SQLite テーブル初期化・永続化層）
- 実行スクリプト
  - run_execution.py（ExecutionEngine 起動スクリプト）
  - run_monitoring.py（SystemMonitor ポーリング起動スクリプト）
- ツール
  - config_setup.py（.env の対話式作成）
  - validate_config.py（設定検証 CLI）
  - tools/paper_verification_report.py（Paper Trading 検証レポート生成）
- ユーティリティ
  - logging_setup（統一的なログ設定）
  - process_priority（プロセス優先度 / CPU affinity 設定）

---

## セットアップ手順

前提: Python 3.10+ を想定（型ヒントの構文を使用しています）。プロジェクトルートは `.git` または `pyproject.toml` を基準として自動検出されます。

1. リポジトリをクローン / 配置

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Linux/macOS）
   - .venv\Scripts\activate（Windows）

3. 必要パッケージをインストール
   - 推奨パッケージ（最低限）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証や YAML パースに必要、任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements ファイルがある場合は pip install -r requirements.txt を使用）

4. ディレクトリ作成（初回）
   - data/ と logs/ を作成しておくと便利:
     - mkdir -p data logs

5. 環境変数の設定（.env 推奨）
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 簡易的な .env の例（.env.example を参考にしてください）:
     - KABUSYS_ENV=development
     - JQUANTS_REFRESH_TOKEN=your_token_here
     - KABU_API_PASSWORD=your_password_here
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=sk-...

6. 設定の検証
   - python -m kabusys.validate_config
   - 本番想定で警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

---

## 使い方（主要スクリプト）

- 設定ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 成功すると 0 を返し、問題があればエラー / 警告を出力

- ExecutionEngine（注文実行プロセス）起動
  - python src/kabusys/run_execution.py
  - またはパッケージ実行:
    - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、data/paper_trading.db に記録します（本番 SQLite と分離）。
    - 起動時に data/stop_requested.flag が存在すると起動を中止します。
    - 実行中に停止させたい場合は data/stop_requested.flag を作成（もしくは KillSwitch により data/kill.flag が書かれる）。

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを記録します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定する例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または `--db` オプションで指定可能（デフォルト: data/paper_trading.db）

- AI 関連（ニュースセンチメント / レジーム判定）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY を使用
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - 同じく OPENAI_API_KEY が必要
  - 注意: OpenAI を利用する処理は API 呼び出し失敗時にフェイルセーフ動作（スコアを 0 にする等）を行う設計ですが、実行には API キーが必須です。

- Kill Switch
  - KillSwitch は監視コンポーネントが条件を満たした場合に `data/kill.flag` を書き込みます。ExecutionEngine 起動時にこのフラグがあると起動を避けるか、実行中にフラグを検出して停止します。
  - フラグを手動でクリアするには:
    - rm data/kill.flag
  - Settings で `KILL_FLAG_CLEAR_ON_START=1` を指定すると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

---

## 主要な環境変数（抜粋）

（全て Settings クラスで管理されています。主要なものを記載します。）

- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY — OpenAI を使う機能で必要
- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

---

## ロギング

- 共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` を使って root ロガーを統一的に設定します。
- デフォルトで logs/ ディレクトリに日次ローテーション（TimedRotatingFileHandler）でログを保存し、標準出力にも出力します。
- ログディレクトリは環境変数 `LOG_DIR` または setup_logging の引数で変更可能。

---

## ディレクトリ構成（概要）

以下は主要なファイル / サブパッケージの構成です（src/kabusys を基点）:

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (参照あり)
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (参照あり)
  - tools/
    - __init__.py
    - paper_verification_report.py
  - execution/ (注文実行関連のパッケージ: Engine, BrokerFactory 等。参照あり)
  - data/ (実行時に生成される sqlite/duckdb/log/pid/flag ファイルを格納する想定)

※ 上記構成はリポジトリ内のファイル群に基づく抜粋です。詳細なサブモジュールは各ファイルをご参照ください。

---

## 運用上の注意 / ベストプラクティス

- 本番環境では KABUSYS_ENV=live を設定します。validate_config の警告に注意してください（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START=1 などは危険です）。
- Monitoring は KABUSYS_ENV に無関係に本番の sqlite_path を使用するため、本番 DB の扱いに注意してください。
- ExecutionEngine の停止は基本的に Kill Switch（data/kill.flag）で行います。手動でフラグを操作する場合は意図を十分確認してください。
- OpenAI を用いる機能は API 呼び出しに依存するため、レート制限やコストに注意してください。news_nlp / regime_detector にはリトライロジックが組み込まれていますが、運用上の監視が必要です。
- DuckDB / SQLite のバックアップやデータ整合性を運用ポリシーとして確立してください。

---

## 参考コマンドまとめ

- .env 作成（ウィザード）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

README の内容で不明点や、より詳細な運用手順（systemd ユニットファイル、Docker 化、CI/CD、バックアップ方針 など）をご希望であれば、目的に合わせた追加ドキュメントを作成します。どの項目を優先したいか教えてください。