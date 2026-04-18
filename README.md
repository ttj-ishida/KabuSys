README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。  
主な役割はシグナル生成→ポートフォリオ構築→発注実行の一連処理に加え、システム監視・リスク管理・AI を使ったニュースセンチメント評価・研究用ファクター計算などを含みます。  
設計方針として「本番とペーパートレードの分離」「ルックアヘッドバイアス回避」「フェイルセーフ（API失敗などは耐える）」を重視しています。

主な機能
--------
- Execution Engine
  - 本番/ペーパートレード両対応（KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用）
  - リスク管理（position 上限、drawdown 等）
  - 注文管理・再整合（reconciler）を備えた実行ループ
- Monitoring
  - system / trade / risk の定期監視（SQLite へログ保存）
  - Kill Switch（条件に応じて data/kill.flag を書いて Execution を停止）
  - ログ・アラート発行フレームワーク（AlertManager 経由）
- Portfolio Construction（純粋関数群）
  - 候補選定、等配分/スコア加重、ポジションサイジング（単元丸め・集約上限）
  - セクターキャップ・レジーム乗数調整
- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）等の統計ユーティリティ
- AI モジュール
  - news_nlp: OpenAI（gpt-4o-mini）でニュースをスコアリングして ai_scores に保存
  - regime_detector: ETF の MA とマクロニューススコアを合成して market_regime を判定
- ユーティリティ
  - logging_setup（コンソール + 日次ローテートファイル）
  - process_priority / cpu affinity 設定
  - config ウィザード (.env 作成) / 設定検証 CLI
- ツール
  - paper_verification_report: ペーパートレード DB を集計して検証レポートを出力

セットアップ
-----------
※ 以下は一般的な開発環境向けの手順です。実運用時は適宜 OS 権限やサービス化を行ってください。

1. Python 仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（代表的なパッケージ）
   - pip install duckdb psutil openai
   - （任意）PyYAML（config/*.yaml を検証したい場合）: pip install pyyaml

   ※ requirements.txt が無い場合は上記を参考に必要パッケージを追加してください。

3. 環境変数設定（.env をプロジェクトルートに置くことを推奨）
   - 推奨の設定は .env.example を参照してください（リポジトリにある想定ファイル）。
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（主要一覧）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY: OpenAI を使う場合必須
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: 監視 DB のデフォルト data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード時の DB（デフォルト data/paper_trading.db）
     - LOG_LEVEL: DEBUG/INFO/…
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等

4. .env を対話的に作る（推奨）
   - python -m kabusys.config_setup
   - その後設定検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱い

使い方
------
各種モジュールはモジュールとして直接起動できます（プロジェクトルートで実行する前提）。

- 実行エンジン（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録します（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします（停止フラグ）。
  - 実行中に stop フラグファイルが置かれるとエンジンが停止します。

- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒指定（デフォルト 60）
  - 監視は常に本番 sqlite_path を使ってログを残します（環境に依らず）

- 設定ウィザード / 検証
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 簡易的に PAPER_TRADING_SQLITE_PATH 環境変数でも DB を指定可能

- AI 関連（ライブラリ呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OpenAI API キー（引数 or 環境変数 OPENAI_API_KEY）が必要

ログ
----
- logging_setup により stdout と logs/<app_name>.log（日次ローテーション）に出力されます。
- デフォルトログディレクトリ: logs/
- ログレベルは環境変数 LOG_LEVEL で制御可能（または setup_logging の引数で上書き）。

重要な挙動 / 環境設定メモ
------------------------
- KABUSYS_ENV:
  - development: ローカル開発（発注なし想定）
  - paper_trading: 発注は仮想（MockBroker）で paper DB を使用
  - live: 本番
- Paper trading は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番データと完全分離
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）
- Kill Switch:
  - risk_monitor / kill_switch によって条件成立時に data/kill.flag を作成し Execution を停止させる仕組み
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリア（本番では 0 推奨）
- プロセス優先度:
  - 実行スクリプトは起動直後に set_process_priority("high") を試みます（psutil を利用）
  - 権限不足や未サポート OS の場合は警告を出して継続します
- .env の自動読み込み:
  - デフォルトでプロジェクトルートの .env / .env.local を自動ロードします
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

ディレクトリ構成（主要ファイル）
-----------------------------
以下は src/kabusys 以下の主なファイル・ディレクトリ構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / Settings 管理
  - config_setup.py             — .env 対話生成ウィザード
  - validate_config.py          — 起動前設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - ai/
    - news_nlp.py               — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py        — 市場レジーム判定
  - research/
    - factor_research.py        — ファクター計算
    - feature_exploration.py    — 将来リターン / IC / 統計
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py          — SQLite 永続化層
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py          — （trade 監視ロジックが存在）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py          — （アラート送信ロジックが存在）
  - execution/                  — Execution 側の実装（broker_factory, execution_engine, order_manager 等）
  - data/                       — データパイプライン / DuckDB クエリ関連
  - utils/
    - logging_setup.py
    - process_priority.py
    - その他ユーティリティ群

（上記はコードベースの代表的なファイル群を抜粋したものです。すべてのファイルはソースツリーを参照してください。）

開発・運用上の注意
-----------------
- 機密情報（API トークン等）は .env に保存する際、決して Git にコミットしないでください。
- 本番環境 (KABUSYS_ENV=live) では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを強く推奨します。
- OpenAI 呼び出しはコストやレート制限に注意してください。news_nlp / regime_detector は再試行ロジックを持ちますが、上限に達すると当該処理はスキップされます（フェイルセーフ）。
- process_priority / cpu_affinity は OS 権限に依存します。設定に失敗してもログ警告を出して継続します。

貢献・拡張のヒント
------------------
- DuckDB のスキーマ（prices_daily / raw_financials 等）に合わせて research モジュールを拡張できます。
- position_sizing の lot_size を銘柄別に拡張するためには stocks マスタの追加とインターフェース変更が必要です（TODO コメントあり）。
- AI モジュールのテストは _call_openai_api をモックして行えるよう設計されています。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンス情報や更に詳細な設計文書（PortfolioConstruction.md, StrategyModel.md 等）がプロジェクト内にあれば併せて参照してください。

問題報告 / サポート
-------------------
バグ報告や提案は issue を作成してください。README にある注意点を満たした上で、再現手順・ログ・環境変数（機密部分は除く）を添えてください。

以上。