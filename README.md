# KabuSys

日本株向けの自動売買・研究プラットフォーム（ライブラリ兼実行スクリプト群）

このリポジトリは、取引エンジン、監視・アラート、ポートフォリオ構築、ファクター計算、AI を使ったニュース解析などを含むモジュール群で構成されています。ライブラリとしての機能提供に加え、起動用スクリプト（実行エンジン、監視ループ、設定ウィザード、検証ツール、レポート生成など）が同梱されています。

バージョン: 0.1.0

主な設計方針:
- 本番用設定とペーパートレード（検証）を分離可能
- DuckDB / SQLite をデータ層として使用（分析データと運用ログを分離）
- OpenAI を利用したニュースNLP / レジーム検知をサポート（APIキー必須）
- ログは統一的に設定（コンソール + 日次ローテーションファイル）

必要な Python バージョン: プロジェクトの pyproject.toml に準拠してください（パッケージ配布時に明示されます）。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（コマンド例 / ライブラリ API）
- 重要な環境変数
- 停止・Kill スイッチ
- ディレクトリ構成（主要ファイルの説明）

---

プロジェクト概要
- KabuSys は日本株自動売買システム向けのモジュール群です。  
  - ExecutionEngine: 注文発行・リスク管理・注文再送・約定処理等の実行ロジック（run_execution.py）
  - Monitoring: システム状態・注文ログ・リスク監視・Kill Switch の評価（run_monitoring.py、monitoring/*）
  - Portfolio: 候補選定、重み計算、株数算出、セクター制約・レジーム補正（portfolio/*）
  - Research: DuckDB を利用したファクター計算・特徴量解析（research/*）
  - AI: OpenAI を用いたニュースセンチメント / レジーム判定（ai/*）
  - Tools: 検証レポートなどユーティリティスクリプト（tools/*）
  - Utils: ロギング設定・プロセス優先度設定など共通ユーティリティ（utils/*）
- 設定は .env ファイルまたは環境変数で管理。config_setup.py による対話式ウィザードや validate_config.py による検証機能あり。

主な機能一覧
- 実行エンジン（ExecutionEngine）起動 / ペーパートレードモードの切替（MockBroker 使用）
- 監視ループ（System / Trade / Risk）とアラート・Kill Switch の評価
- ポートフォリオ構築・ポジションサイズ計算（等配分・スコア配分・リスクベース）
- ファクター計算（Momentum / Value / Volatility 等）および研究用ユーティリティ（IC, factor summary）
- OpenAI を利用したニュースセンチメントスコアリング（AI スコアを ai_scores テーブルへ書込）
- Paper Trading 検証レポート生成スクリプト
- ログ設定ユーティリティ（コンソール + 日次ローテートファイル）
- 設定ウィザード（.env 生成）と設定検証 CLI

セットアップ手順（簡易）
1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境作成（推奨）
   - python -m venv venv
   - source venv/bin/activate  (Windows: venv\Scripts\activate)

3. 必要パッケージをインストール
   - 依存はプロジェクトによって異なりますが、主に以下を含みます:
     - duckdb
     - psutil
     - openai
     - PyYAML (config 検証で利用)
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ 実際の requirements はリポジトリにある場合はそちらを使用してください。

4. .env の作成
   - 対話式ウィザードで生成:
     - python -m kabusys.config_setup
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - 重大な警告も FAIL 扱いにしたい場合:
       - python -m kabusys.validate_config --strict

5. データディレクトリ（デフォルト: data/）とログディレクトリ（logs/）を確認
   - ログはデフォルト logs/<app_name>.log に日次ローテーションで保存されます。
   - SQLite / DuckDB のデフォルトパス:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード時）

使い方（実行例）
- 実行エンジンを起動（通常 / ペーパートレードは KABUSYS_ENV による）
  - KABUSYS_ENV=live を .env に設定して実行すると実際に発注が行われます（KABU API 設定必須）
  - 起動:
    - python -m kabusys.run_execution
  - 実行時の挙動:
    - 起動時にプロセス優先度を “high” に設定
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト: 60）
  - 監視は本番 sqlite_path を常に使用（monitoring は環境にかかわらず本番の monitoring.db を参照）

- 設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード（警告でも exit 1）:
    - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- ライブラリ API の例（コード内利用）
  - DuckDB 接続を作成して調査関数を呼ぶ:
    - import duckdb
      conn = duckdb.connect("data/kabusys.duckdb")
      from kabusys.research import calc_momentum
      calc_momentum(conn, date(2026, 4, 1))
  - AI ニューススコアリング（OpenAI API キー required）:
    - from kabusys.ai import score_news
      score_news(conn, target_date, api_key="sk-...")

重要な環境変数（主要なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL（デフォルト: INFO）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の fill 動作: instant|partial|never|reject、デフォルト: instant）
- OPENAI_API_KEY（AI 機能を利用する場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知に利用）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、秒、デフォルト: 60）

停止・Kill スイッチ
- run_execution / run_monitoring はプロジェクト内 data/ に配置されるフラグファイルで停止・制御します:
  - data/stop_requested.flag: run_monitoring / run_execution のループを終了させる（手動で作成すると安全に停止）
  - data/kill.flag: Kill Switch（監視モジュールが条件を満たすと生成） — ExecutionEngine 停止のためのシグナル
  - PID ファイル: data/execution.pid（ExecutionEngine が起動時に書き込む）
- KillSwitch の条件:
  - ドローダウン超過（DRAWDOWN_ALERT）
  - ポジション数上限超過（POSITION_LIMIT）
  - 条件成立時に data/kill.flag を書き込み、ExecutionEngine 停止をトリガーします。

ログ
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一されます。
- 出力:
  - コンソール（stdout）
  - 日次ローテートファイル: logs/<app_name>.log（既定: logs/、30日分保持）
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で設定できます。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義、__version__
  - config.py — 環境変数 / .env の自動読み込み、Settings クラス
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数決定・aggregate cap
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py — ニュースセンチメント (OpenAI)
    - regime_detector.py — マクロ + MA200 を合成したレジーム判定
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化層（システム / トレード / リスクログ等）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度・プロセス監視
    - trade_monitor.py — 注文ログ監視（存在するファイル参照）
    - risk_monitor.py — ドローダウン・ポジション制限監視
    - kill_switch.py — Kill Switch 実装
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - execution/ (実行ロジック関連) — ExecutionEngine 本体、注文管理など（本コード省略）
  - utils/
    - logging_setup.py — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度・CPU affinity 設定
  - data/ — 実行時生成されるファイル（データベース / フラグ / pid 等）

補足・運用上の注意
- 本番（KABUSYS_ENV=live）では特に注意して設定してください（validate_config による警告あり）。
- .env は決して Git にコミットしないでください（README 内にも生成時に警告を出力する設計）。
- run_monitoring は監視用 DB（SQLITE_PATH）を常に本番用のパスで開きます。ペーパートレード時も監視は本番 DB を参照する設計です。
- run_execution は KABUSYS_ENV=paper_trading の場合に PAPER_TRADING_SQLITE_PATH を使用してペーパートレード DB を分離します。
- OpenAI を使う機能は API キーと通信コストが必要です。API 呼び出しは冗長性（リトライ）や安全側のフォールバック実装を多く含みますが、実運用前に十分にテストしてください。

問題報告・開発
- バグ報告・機能提案は Issue を立ててください。プルリク歓迎。

---

README は上記の要点を含めた簡易版です。より詳細な設計文書（PortfolioConstruction.md、StrategyModel.md 等）がプロジェクト内に存在する場合はそちらも参照してください。必要であれば README に起動フロー図やシーケンス図、config の例テンプレート（.env.example）などを追記できます。どの追加情報が必要か教えてください。