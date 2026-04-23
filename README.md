# KabuSys

日本株向けの自動売買・研究基盤ライブラリです。ポートフォリオ構築、ポジションサイジング、監視、Execution エンジン、Paper Trading 検証、LLM を使ったニュース NLP やレジーム判定などを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 前提・依存関係
- セットアップ手順
- 使い方（主要スクリプト・CLI）
- 環境変数 / 設定
- ディレクトリ構成（主要ファイル一覧）
- 補足

---

プロジェクト概要
- KabuSys は日本株向けのアルゴリズム取引・研究支援のためのモジュール群です。
- データ格納に DuckDB / SQLite を使い、ExecutionEngine（発注ロジック）と Monitoring（監視）を分離して運用できる設計です。
- LLM（OpenAI）を用いたニュースセンチメント評価・市場レジーム判定機能を備えています（任意）。

---

主な機能一覧
- Execution 起動スクリプト（run_execution.py）
  - 実取引 / ペーパートレードを切り替え可能（KABUSYS_ENV）
  - ブローカークライアントの抽象化、OrderManager / RiskManager / Reconciler などを組み合わせて ExecutionEngine を起動
  - ペーパートレード時は専用 DB（data/paper_trading.db）を使用して本番 DB と分離
- Monitoring（run_monitoring.py / monitoring_engine）
  - SystemMonitor, TradeMonitor, RiskMonitor を組み合わせたポーリング監視
  - Kill Switch（data/kill.flag）で ExecutionEngine 停止指示可能
  - 監視結果は SQLite（デフォルト: data/monitoring.db）に永続化
- Config ユーティリティ
  - 対話式 .env ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- Portfolio 建設モジュール（pure function）
  - 銘柄選定、等金額/スコア重み計算、ポジションサイズ計算（単元丸め、リスク制限反映）
  - セクター上限適用、レジーム乗数計算
- Research（DuckDB ベース）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI（LLM）関連
  - news_nlp: ニュース記事から銘柄ごとにセンチメントを評価して ai_scores に格納
  - regime_detector: マクロニュース + ETF MA を使って市場レジーム判定（market_regime テーブルへ書込み）
  - OpenAI API（gpt-4o-mini）を利用（APIキー必要）
- ツール
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
- ログ / プロセス管理ユーティリティ
  - 統一ログ設定（kabusys.utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）

---

前提・依存関係
- Python 3.10+（型ヒントに | 形式を使用）
- 必須ライブラリ（用途に応じてインストール）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（validate_config の YAML 検証を有効にする場合）
- 推奨: 仮想環境を作成して運用してください。

例（最小インストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil
# AI 機能を使う場合:
pip install openai
# validate_config の YAML 検証を有効にする場合:
pip install pyyaml
```

---

セットアップ手順（推奨フロー）
1. リポジトリをクローンし、仮想環境を作成・有効化する。
2. 必要なパッケージをインストール（上記参照）。
3. 対話式ウィザードで .env を作成：
   ```bash
   python -m kabusys.config_setup
   ```
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - KABUSYS_ENV（development / paper_trading / live）を選択
4. 設定を検証：
   ```bash
   python -m kabusys.validate_config
   # 警告をエラー扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```
5. 必要に応じて DuckDB / SQLite の初期データを用意する（prices_daily, raw_financials, raw_news など）。これは環境依存です。

---

使い方（主要コマンド例）

- ExecutionEngine を起動（本番 / ペーパートレードは KABUSYS_ENV で切替）
  ```bash
  python -m kabusys.run_execution
  ```
  - 実行中は data/execution.pid が作成されます。
  - 停止させたい場合は data/stop_requested.flag を作成すると安全に停止します。
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録します。

- Monitoring を起動（デフォルトポーリング間隔 60 秒）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます。
  - Monitoring は本番 sqlite_path を常に使用して監視ログを残します。
  - 停止フラグ: data/stop_requested.flag を作成するとループを終了します。

- .env を対話式に生成 / 更新
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート（ローカルの paper_trading DB に対して実行）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI スコアリング / レジーム判定（プログラム呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは api_key 引数か環境変数 OPENAI_API_KEY を利用

--- 

主要な環境変数 / デフォルト値
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject （デフォルト: instant）
- LOG_LEVEL: INFO（デフォルト）
- LOG_DIR: logs/
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: 0/1（デフォルト0、本番では 0 推奨）
- MONITOR_POLL_INTERVAL: 監視間隔（秒、run_monitoring で参照）
- OPENAI_API_KEY: OpenAI を使う際に必要

自動 .env ロード
- プロジェクトルート（.git または pyproject.toml が存在する場所）から .env と .env.local を自動で読み込みます。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ログ
- kabusys.utils.logging_setup.setup_logging が統一ログ設定を行います。
- デフォルトでは stdout にログを出力し、logs/<app_name>.log に日次ローテートでファイル出力します（30 日保持）。
- ログディレクトリは LOG_DIR 環境変数で変更可。

Kill Switch / Stop フラグ
- Execution の強制停止や Monitoring からの停止指示に使用するファイル:
  - data/kill.flag — Kill Switch（手動 or 自動で書込まれると Execution を止める）
  - data/stop_requested.flag — run_* スクリプトのループ停止シグナル
  - data/execution.pid — ExecutionEngine の PID（run_execution により作成）

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — Settings / .env 自動読込
  - config_setup.py          — .env 対話式ウィザード（CLI）
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - portfolio/
    - portfolio_builder.py   — 銘柄選定・重み計算
    - position_sizing.py     — 株数決定・資金割当
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — Momentum / Volatility / Value ファクター
    - feature_exploration.py — forward returns / IC / summary utilities
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）
    - regime_detector.py     — レジーム判定（OpenAI + MA）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化 / 永続化層
    - system_monitor.py      — システム状態 / データ鮮度監視
    - trade_monitor.py       — (存在) 注文滞留・約定異常監視（本リポジトリに一部実装）
    - risk_monitor.py        — ドローダウン / ポジション数監視
    - kill_switch.py         — kill.flag の書き込み
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（起動スクリプトから利用）
    - broker_factory.py      — ブローカークライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート出力

（実運用では上記以外に data/ logs/ config/ などの配置が必要です）

---

補足 / 運用上の注意
- 本番環境（KABUSYS_ENV=live）では kill_flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。デフォルト 0 を推奨します。
- AI 機能は OpenAI API を利用するため API 使用料が発生します。API キーは厳重に管理してください。
- ペーパートレード用 DB は本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH）。テスト時はペーパートレードモードを推奨します。
- .env は機密情報を含むため Git 管理に入れないでください（config_setup が警告文を出力します）。
- validate_config は起動前チェックに有用です。--strict オプションで警告も exit(1) 扱いにできます。

---

質問や追加で README に入れたい内容があれば教えてください。必要であればサンプル .env のテンプレートや運用フロー（systemd / supervisor 用のユニット例）も作成します。