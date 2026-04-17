# KabuSys — 日本株自動売買システム

このリポジトリは、日本株自動売買システム「KabuSys」のコアライブラリとユーティリティ群です。戦略 / ポートフォリオ構築、発注エンジン、監視、AI を使ったニュース解析、リサーチ用ファクター計算などの主要コンポーネントを含みます。

## プロジェクト概要
- 目的: 自動売買に必要な「シグナル生成 → ポートフォリオ構築 → 発注 → モニタリング」までの一連機能をモジュール化して提供する。
- 設計方針:
  - 本番 DB とペーパートレード DB を分離可能（KABUSYS_ENV による切替）。
  - DuckDB を使ったデータ分析 / ファクター計算。
  - SQLite を使った監視・トレードログ永続化（monitoring.db / paper_trading.db 等）。
  - OpenAI（gpt-4o-mini 等）を用いたニュース NLP・マクロ判定（オプション）。
  - 外部 API への直接発注は broker_factory 経由で抽象化（ペーパー時は MockBrokerClient）。

## 主な機能一覧
- Execution（発注エンジン）
  - ExecutionEngine、OrderManager、RiskManager、Reconciler による発注フロー
  - ペーパートレードモード（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し DB を分離
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセスの生存確認、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定価格逸脱の検出
  - RiskMonitor: ドローダウン監視・ポジション上限監視
  - KillSwitch: リスク条件に応じて data/kill.flag を書き込み Execution を停止
  - MonitoringEngine: 上記を束ねたポーリングループ
- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額/スコア重み、位置サイズ計算、セクター制限、レジーム乗数
- Research（リサーチ）
  - ファクター計算（モメンタム/バリュー/ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
- AI（OpenAI 統合、オプション）
  - news_nlp: ニュース記事を集約して LLM で銘柄ごとにセンチメントスコアを算出し DB に保存
  - regime_detector: ETF の MA とマクロニュースセンチメントを組み合わせて市場レジーム判定
- ユーティリティ
  - config_setup: .env 対話式ウィザード
  - validate_config: .env と config/*.yaml の初期検証 CLI
  - tools.paper_verification_report: ペーパートレード検証レポート出力

## セットアップ手順（ローカル）
前提: Python 3.9+（環境に合わせて調整）

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 最低限の依存例（実際の requirements.txt を参照してください）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（validate_config で YAML 検証を行う場合）
   ```
   pip install duckdb psutil openai pyyaml
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` を作成するか、対話式ウィザードを利用します。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - OPENAI_API_KEY: OpenAI を使う場合
     - LOG_LEVEL: INFO 等
   - 自動 .env ロードはデフォルトで有効。無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. .env の作成（ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```

6. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告も厳密に扱う場合:
   python -m kabusys.validate_config --strict
   ```

## 使い方（主なコマンド例）
- ExecutionEngine を起動（デーモン的に実行する想定）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録されます。
  - 実行中は data/execution.pid に PID が書かれ、停止は data/stop_requested.flag（内部）や data/kill.flag を利用します。

- Monitoring を起動（ポーリングループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを保存します。

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定例:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI モジュールの呼び出し（ライブラリ関数）
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

  （これらは直接 Python スクリプトやスケジューラから呼び出して利用します。OpenAI API キーは環境変数 OPENAI_API_KEY で指定可能。）

- .env の自動読み込み・上書き
  - .env（プロジェクトルート）を自動で読み込みます。
  - .env.local があれば .env を上書き（.env.local は .env より優先して読み込まれます）。
  - OS 環境変数は保護され、.env がそれらを上書きしないよう配慮されています。

## 重要なファイル・パス
- data/execution.pid — ExecutionEngine の PID（既定）
- data/kill.flag — KillSwitch による停止フラグ
- data/monitoring.db — 監視ログ（SQLite、デフォルト）
- data/paper_trading.db — ペーパートレード用 DB（KABUSYS_ENV=paper_trading 時）
- data/kabusys.duckdb — DuckDB（分析用、デフォルト: data/kabusys.duckdb）
- data/stop_requested.flag — run_execution / run_monitoring の内部停止フラグとして使用

## ディレクトリ構成（主要ファイル）
以下は主要モジュールの概要と代表的なファイルです（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py                — 環境変数／設定読み込み
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - utils/
    - process_priority.py    — プロセス優先度・CPU affinity ユーティリティ
  - execution/
    - execution_engine.py    — (発注エンジン本体)
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
    - order_record.py
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義／永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
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
  - tools/
    - paper_verification_report.py

（上記は含まれる主要なモジュールの抜粋です。各ディレクトリにさらに補助モジュールが存在します。）

## 運用上の注意
- 本番運用（KABUSYS_ENV=live）の際は、LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や KILL_FLAG に関する挙動を十分確認してください。
- validate_config は本番設定ミスの初期検出に役立ちます。運用前に必ず実行してください。
- OpenAI を使う機能は API 利用料が発生します。利用時は API キー管理とコストに注意してください。
- PID ファイルやフラグファイルを手動で操作すると期待しない停止や起動阻害を招くため注意してください。
- paper_trading モードは本番 API と完全に分離されたデータ記録となるよう設計されていますが、設定ミスにより本番接続されないか必ず確認してください。

---

さらに詳しい内部ドキュメント（PortfolioConstruction.md、StrategyModel.md など）がプロジェクトに付属している場合は、それらを参照して各アルゴリズムの詳細を確認してください。疑問点や追加で README に載せてほしい情報があれば教えてください。