# KabuSys

日本株向け自動売買システムのコアライブラリ群。ポートフォリオ構築、ポジションサイジング、監視・アラート、ペーパートレード検証、LLM を使ったニュースセンチメント評価などの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なロジックとユーティリティを集約した Python パッケージです。主な目的は次のとおりです。

- ファクター計算・リサーチ（DuckDB を利用）
- ポートフォリオ構築とポジションサイズ計算（純関数実装）
- ExecutionEngine（発注）とそれを監視する Monitoring（停止フラグ・Kill Switch 等）
- Paper Trading 用の分離された DB と検証レポート生成
- OpenAI を使ったニュースセンチメント評価 / 市場レジーム判定
- 環境設定ウィザード・設定検証ツール

設計上、データベースアクセスは DuckDB（時系列・分析）と SQLite（監視・履歴）を使い分けています。Paper Trading モードでは発注系は MockBroker によって本番 DB と分離されます。

---

## 機能一覧

- 環境設定ウィザード（`.env` の対話式作成）: `kabusys.config_setup`
- 設定検証 CLI（.env と config/*.yaml のチェック）: `kabusys.validate_config`
- ExecutionEngine 起動スクリプト: `kabusys.run_execution`
  - `KABUSYS_ENV=paper_trading` 時は MockBroker を使用し DB を分離
  - 停止フラグ（data/stop_requested.flag / data/kill.flag）による制御
- Monitoring 起動スクリプト（ポーリング）: `kabusys.run_monitoring`
  - 環境にかかわらず監視用に本番 sqlite_path を使用
  - ポーリング間隔は `MONITOR_POLL_INTERVAL` で上書き可
- MonitoringEngine：SystemMonitor / TradeMonitor / RiskMonitor の統括とアラート発行
- MonitoringDB：SQLite ベースの監視ログ永続化
- RiskMonitor：ドローダウンやポジション上限の監視とリスクログ化
- KillSwitch：条件検知時に `data/kill.flag` を書いて ExecutionEngine を停止
- Paper Trading 検証レポート生成スクリプト: `kabusys.tools.paper_verification_report`
- Research モジュール：ファクター計算（momentum/volatility/value）・IC 計算・統計サマリー
- AI モジュール：
  - `kabusys.ai.news_nlp`: ニュースを OpenAI で評価し ai_scores に書き込み
  - `kabusys.ai.regime_detector`: ETF の MA 乖離＋マクロニュースで市場レジーム判定
- ユーティリティ：ログ設定、プロセス優先度設定、など
- Portfolio モジュール：候補選定／重み計算／ポジションサイズ算出／セクター制約適用

---

## 要件（推奨）

- Python 3.10+
- 必須外部ライブラリ（最低限）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で YAML をパースする場合）
- 標準ライブラリ: sqlite3, logging, threading, datetime など

インストール例（仮）:
```bash
python -m pip install duckdb psutil openai pyyaml
```

実際のプロジェクトでは requirements.txt / pyproject.toml を使って依存管理してください。

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作成・有効化します。

2. 必要ライブラリをインストールします（上記参照）。

3. 環境変数（`.env`）を作成します。対話式ウィザードが用意されています:
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードは `.env` を生成・更新します。J-Quants トークンや kabu API パスワードなどの機密値はマスクされます。

4. 作成した `.env` を検証します:
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ（デフォルト: `data/`）とログディレクトリ（デフォルト: `logs/`）が存在するか確認します。多くのコードは起動時に自動作成しますが、権限等で失敗する可能性があるため事前に準備しておくと確実です。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: `development` | `paper_trading` | `live`（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（デフォルト: INFO）
- LOG_DIR: ログファイル出力ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- PAPER_FILL_MODE: paper_trading の約定モード（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）

注意:
- `KABUSYS_ENV=paper_trading` の場合、ExecutionEngine は MockBrokerClient を使い `data/paper_trading.db` を使用して本番 DB と分離します。
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を参照します（監視は本番データに対して行う想定）。

---

## 使い方

- 環境設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動
  ```bash
  python -m kabusys.run_execution
  ```
  - 起動前に `data/stop_requested.flag` が存在すると起動せずに終了します。
  - 実行はスレッドで行われ、停止フラグや kill.flag によって安全に停止できます。
  - 起動時に PID ファイル（デフォルト `data/execution.pid`）を作成します。

- Monitoring を起動（ポーリング監視）
  ```bash
  # ポーリング間隔を環境変数で上書きする例（30秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 監視ループは `data/stop_requested.flag` を検知すると終了します。
  - 監視は system_status / trade_logs / risk_logs / dashboard テーブルを利用してログ・アラート・Kill Switch 評価を行います。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を直接指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 機能（ニューススコア・レジーム判定）
  - OpenAI API キーを `OPENAI_API_KEY` に設定して使用します。
  - `kabusys.ai.news_nlp.score_news()` や `kabusys.ai.regime_detector.score_regime()` をプログラムから呼び出して利用します。

- ログ
  - デフォルトで `logs/<app_name>.log`（日次ローテーション、30 日分保持）と標準出力に出力します。
  - `kabusys.utils.logging_setup.setup_logging(app_name="execution")` 等で共通設定が行われます。

- 強制停止 / Kill Switch
  - リスク条件を満たした場合、Monitoring 側から `data/kill.flag` が書き込まれ、ExecutionEngine はこれを検知して安全に停止します。
  - 管理者が手動で停止させたい場合は `data/kill.flag` を作成する、または `data/stop_requested.flag` を作成してループ停止を促します。

---

## よく使うコマンドまとめ

- .env 作成:
  - `python -m kabusys.config_setup`
- 設定検証:
  - `python -m kabusys.validate_config`
- 実行エンジン起動:
  - `python -m kabusys.run_execution`
- 監視起動:
  - `MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring`
- ペーパートレード検証レポート:
  - `python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11`

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内部の主要モジュール構成（抜粋）です。実際のリポジトリではこの他に README、設定ファイル、スクリプト等が存在する場合があります。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py (参照あり)
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py (参照あり)
    - execution/
      - execution_engine.py (参照あり)
      - broker_factory.py (参照あり)
      - order_manager.py (参照あり)
      - order_repository.py (参照あり)
      - reconciler.py (参照あり)
      - risk_manager.py (参照あり)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - data/  (実行時に利用されるディレクトリ、例: data/monitoring.db, data/paper_trading.db, data/kill.flag)

---

## 注意事項 / 運用上のヒント

- 本番環境（KABUSYS_ENV=live）では特に killflag や通知設定（LINE）を確実にしてから運用してください。`validate_config` は本番向けの注意を行います。
- `.env` は絶対にソース管理（Git）にコミットしないでください。`config_setup.py` はファイル冒頭にその注意を記載します。
- OpenAI API を利用する機能は API レート制限やコストの影響を受けます。API キー・使用頻度・リトライ設定を運用方針に合わせて調整してください。
- Monitoring は監視ルールに従って `data/kill.flag` を書き込むため、ExecutionEngine 起動前に `KILL_FLAG_CLEAR_ON_START` 設定を確認してください（本番では `0` 推奨）。
- DuckDB のスキーマ（prices_daily / raw_financials / raw_news 等）に依存するモジュールが多いため、データ準備が適切に行われていることを確認してください。

---

この README はコードベースの主要点をまとめたものです。詳細な API 仕様やアルゴリズム設計（PortfolioConstruction.md、StrategyModel.md 等）はプロジェクト内の設計ドキュメントを参照してください。必要であれば README を拡張し、セットアップの自動化（Docker / systemd / supervisor）や CI 設定の例を追加できます。