# KabuSys

日本株自動売買システムのモジュール群（ライブラリ・起動スクリプト・ユーティリティ群）。

このリポジトリはバックテスト／リサーチ用の DuckDB ベース処理、ExecutionEngine（発注ロジック／リスク管理）、
Monitoring（システム監視・Kill Switch）、AI を使ったニュース NLP / レジーム判定、ポートフォリオ構築ユーティリティなどを含みます。

---

## プロジェクト概要

- 自動売買のコア機能（発注管理・リスク管理・リコンシリエーション）を提供する Execution モジュール。
- 実行中のプロセスやデータ鮮度・約定ログを監視し、しきい値超過時にアラートや kill.flag を出す Monitoring モジュール。
- DuckDB を用いたファクター計算・リサーチ機能（momentum / value / volatility 等）。
- ニュース記事を LLM（OpenAI）でスコアリングする AI モジュール（news_nlp）と、それを利用するレジーム判定（regime_detector）。
- ペーパートレード用の分離された SQLite DB をサポート（KABUSYS_ENV=paper_trading）。
- .env のウィザード（interactive）や設定検証ツールを備え、起動前の安全性チェックを行える。

---

## 主な機能一覧

- Execution（起動スクリプト: run_execution.py）
  - BrokerClientFactory（本番/モックの切替）
  - OrderRepository / OrderManager / ExecutionEngine
  - RiskManager（ポジション上限・投下率等の制御）
  - Reconciler（発注整合）

- Monitoring（run_monitoring.py, monitoring/*）
  - SystemMonitor（CPU・メモリ・ディスク、プロセス監視、データ鮮度）
  - TradeMonitor（滞留注文・約定異常の検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件一致で data/kill.flag を書き込み Execution 停止）
  - MonitoringDB（SQLite ベースの永続ストア）

- Portfolio（portfolio/*）
  - 銘柄選定、重み算出、ポジションサイズ計算、セクターキャップ、レジーム乗数

- Research（research/*）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI（ai/*）
  - news_nlp: raw_news から銘柄別センチメントを取得して ai_scores に保存（OpenAI）
  - regime_detector: ETF（1321）の MA とマクロニュースで市場レジーム判定

- ユーティリティ
  - logging_setup: 一貫したログ出力設定（コンソール + 日次ファイルローテーション）
  - process_priority: プロセス優先度 / CPU affinity 設定
  - config_setup: .env を対話式で生成
  - validate_config: 起動前の設定検証 CLI
  - tools.paper_verification_report: ペーパートレードの検証レポート生成

---

## セットアップ手順

1. Python 3.9+（ソースが型ヒント等を使用）を用意してください。

2. 必要なパッケージをインストールします（代表例）。

   pip install duckdb psutil openai PyYAML

   - openai: AI モジュールを使用する場合
   - duckdb: リサーチ / AI 用の DB
   - psutil: プロセス・システム指標取得
   - PyYAML: validate_config が config/*.yaml を検証する場合

   （プロジェクトに requirements.txt があればそれを使ってください）

3. プロジェクトルートで .env を作成します（推奨: 対話式ウィザードを使用）:

   python -m kabusys.config_setup

   ウィザード完了後、設定内容を保存します。必須環境変数:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

4. 設定を検証:

   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict

5. DB データディレクトリを作成（ログや data ディレクトリの作成は自動で行われることが多いですが、権限に注意）:

   mkdir -p data logs

6. OpenAI を使う場合は環境変数を設定:

   export OPENAI_API_KEY="sk-..."

---

## 使い方（起動例）

- Execution（本番実行）:

  KABUSYS_ENV=live python -m kabusys.run_execution

- Execution（ペーパートレード。MockBroker を使用し data/paper_trading.db に記録）:

  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  ※ paper_trading 時は Settings.paper_sqlite_path（デフォルト data/paper_trading.db）が使用され、本番 DB と分離されます。

- Monitoring（ポーリング監視ループ）:

  python -m kabusys.run_monitoring

  - ポーリング間隔を変更するには環境変数 MONITOR_POLL_INTERVAL（秒）を設定します（デフォルト 60）。
    例: export MONITOR_POLL_INTERVAL=30

  - 停止フラグ: プロジェクトルート/data/stop_requested.flag が存在すると監視ループは終了します。

- 設定ウィザード:

  python -m kabusys.config_setup

- 設定検証:

  python -m kabusys.validate_config

- Paper Trading 検証レポート:

  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（プログラムから利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

  OpenAI キーは api_key 引数か環境変数 OPENAI_API_KEY を使用します。

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...。デフォルト INFO）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1。デフォルト 0）

---

## 運用上の注意

- Monitoring は設定に関わらず Settings.sqlite_path（本番 monitoring DB）を使用して監視テーブルを初期化します。
- Execution は KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用し paper_sqlite_path（デフォルト data/paper_trading.db）に記録します。本番 DB と分離されています。
- Kill Switch:
  - kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）を書き込むと ExecutionEngine に停止シグナルを送れます。
  - monitoring/kill_switch.py にトリガーロジックあり（ドローダウン・ポジション上限等）。
- 停止フラグ（stop_requested.flag）:
  - run_monitoring.py / run_execution.py は data/stop_requested.flag の存在を検出して終了もしくは停止します（デバッグ・管理用）。
- ログ:
  - kabusys.utils.logging_setup.setup_logging() によりコンソール出力と日次ローテートファイル（logs/<app_name>.log）を使用します。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                — .env 読み込み・Settings 管理
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring ポーリング起動スクリプト

src/kabusys/ai/
- news_nlp.py              — ニュースの LLM センチメント評価（ai_scores への書き込み）
- regime_detector.py       — 市場レジーム判定（MA + マクロセンチメント）
- __init__.py

src/kabusys/monitoring/
- monitoring_db.py         — SQLite テーブル初始化 / 永続化層
- system_monitor.py        — システム監視（CPU/メモリ/ディスク・データ鮮度）
- trade_monitor.py         — （約定 / 注文）監視ロジック
- risk_monitor.py          — ドローダウン・ポジション上限監視
- kill_switch.py           — kill.flag の作成 / 評価
- monitoring_engine.py     — 複数 Monitor を束ねるエンジン
- alert_manager.py         — （アラート送信の集約。実装を確認してください）

src/kabusys/execution/
- (ExecutionEngine, BrokerFactory, OrderManager, Reconciler, RiskManager 等の実装ファイル)

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py
- __init__.py

src/kabusys/research/
- factor_research.py
- feature_exploration.py
- __init__.py

src/kabusys/tools/
- paper_verification_report.py
- __init__.py

src/kabusys/utils/
- logging_setup.py
- process_priority.py
- __init__.py

（その他、data/, logs/ など運用用ディレクトリが想定されます）

---

## 開発・拡張のヒント

- テスト時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読込を無効化できます。
- OpenAI 呼び出し部分は内部で _call_openai_api をラップしており、ユニットテストではパッチで差し替え可能です（例: unittest.mock.patch）。
- DuckDB を使ったリサーチ関数は副作用を持たないため、別途スクリプトから呼び出して結果を検証できます。
- Logging 設定は setup_logging() で統一しているので、起動スクリプトから必ず呼んでください。

---

この README はコードベースの主要点を抜粋してまとめたものです。詳細な設計・仕様（PortfolioConstruction.md、StrategyModel.md 等）がリポジトリに含まれている場合はそちらも参照してください。質問や追記してほしい項目があれば教えてください。