# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システムのコアライブラリ群です。戦略・ポートフォリオ構築、発注実行（本番／ペーパートレード）、監視、リサーチ（DuckDBベース）、およびニュースNLP／レジーム判定などの補助機能を含みます。

---

## プロジェクト概要

- モジュール化された自動売買基盤。
- ExecutionEngine（発注・注文管理・リスク管理）と monitoring（システム監視・Kill Switch）を分離して運用可能。
- DuckDB を用いたリサーチ（ファクター計算、特徴量解析）。
- OpenAI を利用したニュースセンチメント（news_nlp）およびレジーム判定（regime_detector）機能。
- 開発/ペーパートレード/本番の環境分離（`KABUSYS_ENV`）。
- 設定ウィザード・検証ツールを備え、`.env` による環境設定をサポート。

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（`kabusys.run_execution`）
  - Broker クライアント切替（本番 / Mock for paper_trading）
  - OrderManager、RiskManager、Reconciler、OrderRepository
  - ペーパートレード用 DB 分離（`data/paper_trading.db`）
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor の統合（`kabusys.run_monitoring`）
  - kill.flag による強制停止（KillSwitch）
  - 監視結果の永続化（SQLite）
- Portfolio construction（純粋関数群）
  - 候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数
- Research
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI / NLP
  - ニュースのセンチメントスコア化（OpenAI GPT 系）
  - マクロニュース + ETF MA による市場レジーム判定
- ツール
  - 環境設定ウィザード（`.env` 生成）: `kabusys.config_setup`
  - 設定検証 CLI: `kabusys.validate_config`
  - ペーパートレード検証レポート: `kabusys.tools.paper_verification_report`

---

## 前提・依存関係

- Python 3.10 以上（| 型注釈を使用しているため）
- 必須パッケージ（代表例）
  - duckdb
  - psutil
  - openai
- オプション
  - PyYAML（`kabusys.validate_config` の YAML 検証に使用）
- 標準モジュール: sqlite3, logging, threading, datetime 等

（プロジェクトに requirements.txt がある場合はそれを利用してください。なければ上記パッケージを pip でインストールしてください。）

例:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境（推奨）を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb psutil openai PyYAML
   ```

4. 初期設定（.env ファイル作成）
   ```
   python -m kabusys.config_setup
   ```
   - 対話式ウィザードで `.env` を生成・更新します。
   - 重要: `.env` は絶対に Git にコミットしないでください。

5. 設定検証
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告も FAIL とする
   ```

6. データディレクトリ（必要に応じて）
   - デフォルトでは `data/`、ログは `logs/` に出力されます。自動作成されますが、権限などを確認してください。

---

## 環境変数（主要）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパー用 SQLite（paper_trading 時に使用。デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定振る舞い（instant/partial/never/reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, MONITOR_POLL_INTERVAL など

注: `.env.example` を参照して `.env` を整備してください。

---

## 実行方法（代表例）

- ExecutionEngine（発注エンジン）起動
  ```
  # 通常はプロセス管理ツール（systemd / supervisord / tmux など）で実行
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient が利用され、発注は `data/paper_trading.db` に記録されます。
  - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します。
  - エンジンは内部で PID ファイル（デフォルト: data/execution.pid）を扱います。

- Monitoring（監視ループ）起動
  ```
  python -m kabusys.run_monitoring
  ```
  - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔（秒）を変更できます（デフォルト 60 秒）。
  - Monitoring は常に本番の sqlite_path（`SQLITE_PATH`）を参照して監視情報を記録します。
  - `data/stop_requested.flag` を置くと監視ループを終了します。

- 設定検証（再掲）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ペーパートレード検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # --db で別DB指定可能（環境変数 PAPER_TRADING_SQLITE_PATH が優先）
  ```

---

## 使い方（API / ライブラリ呼び出し例）

- ポートフォリオ計算（Python API）
  ```py
  from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

  candidates = select_candidates(buy_signals, max_positions=10)
  weights = calc_score_weights(candidates)
  shares = calc_position_sizes(weights, candidates, portfolio_value, available_cash, current_positions, open_prices)
  ```

- Research（DuckDB 接続を渡して利用）
  ```py
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date)
  ```

- ニューススコアリング（OpenAI キー必須）
  ```py
  from kabusys.ai.news_nlp import score_news
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, target_date, api_key="sk-...")
  ```

- レジーム判定
  ```py
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date, api_key="sk-...")
  ```

---

## 停止・Kill Switch

- KillSwitch は監視コンポーネントで一定条件（ドローダウン超過、ポジション上限超過など）を満たすと `data/kill.flag` を書き込み、ExecutionEngine の停止トリガーになります。
- 手動で停止を要求するには `data/stop_requested.flag` を作成してください。Execution/Monitoring は次のループで検出して終了します。
- 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると `.env` により起動時に kill.flag を自動クリアできます（本番では 0 推奨）。

---

## ディレクトリ構成

（重要ファイル・主要パッケージを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
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
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/
    - pipeline.py
    - stats.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
- data/                      — デフォルト DB / フラグ置き場（自動作成される）
- logs/                      — ログ出力先（デフォルト）

---

## 運用上の注意

- KABUSYS_ENV が `live` の場合は、設定（APIキー、LINE通知など）を慎重に確認してください。`validate_config` は本番向けのガードチェックを行います。
- PID ファイル / stop flag / kill flag の扱いに注意してください。複数プロセスの同時起動を避ける運用（systemd / supervisor 等）を推奨します。
- OpenAI を利用する機能は API コストが発生します。API 呼び出しの頻度・バッチサイズに注意してください。
- DuckDB / SQLite ファイルはバックアップ・権限管理を行ってください。

---

## 貢献・開発

- テストやローカル開発では `.env` を用いず `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自前の環境を用いることも可能です。
- 新しい依存関係を追加する場合は requirements 管理を行ってください。

---

README は以上です。必要であれば起動例の systemd ユニットや docker-compose、requirements.txt や CI 用のテスト手順（ユニットテストの書き方）などの追加ドキュメントを作成します。どの情報を優先して追加しますか？