# KabuSys

日本株自動売買システムのリファレンス実装（ライブラリ／実行スクリプト群）。  
このリポジトリはトレーディングロジック、実行エンジン、監視・アラート、リサーチ用ユーティリティ、AI を用いたニュース解析などのコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主な機能は以下のとおりです。

- 注文実行エンジン（ExecutionEngine）と注文管理
- リスク管理（ポジション上限、ドローダウン監視）
- 監視システム（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch（停止フラグ）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- リサーチ／ファクター計算（momentum / value / volatility 等）
- AI を使ったニュースセンチメント解析・市場レジーム判定
- ペーパートレード用分離 DB と検証レポート生成ツール
- .env 対話式ウィザードおよび設定検証 CLI

---

## 主な機能一覧

- run_execution: 実際の実行エンジン起動スクリプト
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、ペーパートレード用 DB に記録して本番 DB と分離
  - 起動時にプロセス優先度を High に設定
- run_monitoring: SystemMonitor ポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可（デフォルト 60s）
  - 監視ログは SQLite（monitoring DB）へ永続化
- monitoring.*:
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch / alert 管理
  - 監視ログの永続化層（monitoring_db）
- portfolio.*:
  - 銘柄選定、重み計算、ポジションサイジング、セクター制約など
- research.*:
  - DuckDB を用いたファクター計算、前方リターン計算、IC（情報係数）など
- ai.*:
  - news_nlp: OpenAI を用いたニュースセンチメント集約・ai_scores への書き込み
  - regime_detector: ma200 とマクロニュースを組み合わせた市場レジーム判定（market_regime へ書込）
- tools.paper_verification_report: ペーパートレード DB を元に PASS/FAIL レポート生成
- config_setup: .env を対話式に生成・更新するウィザード
- validate_config: .env と config/*.yaml の基本検証 CLI

---

## 必要条件 / 推奨環境

- Python 3.10 以上（型ヒントに「|」記法を使用しているため）
- 推奨パッケージ（最低限）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config YAML 検証を行う場合）
- 標準ライブラリ: sqlite3, logging 等

（requirements.txt はリポジトリに含まれていないため、プロジェクトに合わせて pip install してください。）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して依存関係をインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil openai PyYAML
   ```

3. .env を作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードは .env を生成します。必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）はここで設定してください。

4. 設定の検証
   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

5. （AI 機能を使う場合）OpenAI API キーを設定
   - 環境変数 `OPENAI_API_KEY` を .env に設定するか、score_regime / score_news 呼び出し時に引数を渡します。

6. データディレクトリ作成（必要に応じて）
   - デフォルトで `data/` と `logs/` を使用します。ログは `logs/<app_name>.log` に出力されます。起動時に自動作成されますが、権限やパスに注意してください。

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

推奨／設定:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、発注はモックとなりデータは `data/paper_trading.db`（PAPER_TRADING_SQLITE_PATH）へ保存される
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（上書き可）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI API を使う機能で必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — ペーパートレード時の約定挙動 ("instant" | "partial" | "never" | "reject")

サンプル .env（最小）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

---

## 使い方（コマンド例）

- 実行エンジン（ExecutionEngine）起動
  - 本番／ペーパートレードは KABUSYS_ENV に依存
  ```bash
  python -m kabusys.run_execution
  ```
  - 起動時に `data/execution.pid` を書き、`data/stop_requested.flag` や `data/kill.flag` があると停止します。
  - KABUSYS_ENV=paper_trading の場合、ペーパートレード専用 DB に記録されます。

- 監視ループ起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - デフォルトで 60 秒間隔で監視します。間隔を変更するには環境変数をセット:
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - Monitoring は環境に関わらず本番 sqlite_path（SQLITE_PATH）を使用します（監視ログは一元化）。

- .env ウィザード（設定作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report
  # 期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を直接指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI モジュール呼び出し（プログラム内から）
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
  - これらは DuckDB 接続と target_date を渡して呼び出します。OPENAI_API_KEY が必要です。

---

## 運用上のポイント

- Kill Switch:
  - KillSwitch は条件（ドローダウン超過、ポジション上限超過）で `data/kill.flag` を作成して ExecutionEngine に停止信号を送ります。
  - ExecutionEngine 起動時に `KILL_FLAG_CLEAR_ON_START=1` が設定されていると自動でクリアされますが、本番では 0 を推奨します。

- 監視と DB:
  - 監視ログとトレードログは SQLite（デフォルト `data/monitoring.db`）に保存されます。
  - 実行エンジンは paper_trading モード時のみ `data/paper_trading.db` を使用します。

- ログ:
  - 共通の logging 設定を利用しています。デフォルトは `logs/<app_name>.log`（日次ローテーション、30日保持）。
  - setup_logging() により stdout 出力とファイル出力が統一管理されます。

- プロセス優先度:
  - run_execution / run_monitoring は起動時にプロセス優先度を "high" に設定しようとします（プラットフォーム依存で失敗すると警告のみ）。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル・パッケージの構成例（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - paper_verification_report.py
  - execution/   # 実行エンジン関連（broker_factory, execution_engine, order_manager 等）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/ (runtime)
    - kill.flag
    - execution.pid
    - monitoring.db / paper_trading.db
  - logs/ (runtime)
    - execution.log
    - monitoring.log
    - ...

※ 上は実装ファイルの一部を抜粋したものです。実際のリポジトリにはさらに多くのモジュール・実装があります。

---

## 開発 / 拡張のヒント

- DuckDB を使ったファクター計算は SQL と Python の組合せで高速に実行できます。prices_daily / raw_financials テーブルを使っているため、データ投入部分が重要です。
- AI モジュール（news_nlp, regime_detector）は OpenAI のレスポンスに依存します。エラーや不正レスポンスに対するフェイルセーフ（デフォルト値やリトライ）を実装済みです。
- ポートフォリオ構築・ポジションサイズ計算は純粋関数群（テスト容易）なのでユニットテストが書きやすい設計です。

---

必要であれば README に「依存パッケージの正確なバージョン」「サンプル .env.example」「起動時のシステム要件（メモリ/ディスク）」などを追記できます。どの情報が欲しいか教えてください。