# KabuSys

日本株向けの自動売買・研究基盤（KabuSys）のコードベース説明書です。  
このリポジトリは取引エンジン、監視、ポートフォリオ構築、ファクター計算、AIを使ったニュース評価などのコンポーネントで構成されています。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（実行コマンド例）
- よく使う環境変数（主要なもの）
- ディレクトリ構成（主要ファイルの説明）
- 補足（ログ・停止フラグ・Paper Tradingの扱い など）

---

プロジェクト概要
- KabuSys は日本株自動売買システムのコアライブラリ群と実行用スクリプトを含むプロジェクトです。
- 監視（Monitoring）、発注実行（Execution）、ポートフォリオ構築、ファクター計算・リサーチ、AI を用いたニューススコアリングなどを提供します。
- SQLite（監視ログ）、DuckDB（時系列・分析データ）を用いたデータ永続化・分析を想定しています。
- OpenAI を用いた NLP を一部で利用するため、APIキーの設定により外部LLMと連携できます（任意）。

主な機能一覧
- 環境設定管理
  - .env 自動ロード / .env ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
- 実行エンジン（Execution）
  - Broker クライアント抽象化（実口座 / モックの切替）
  - OrderManager / RiskManager / Reconciler / ExecutionEngine の統合
  - Paper Trading モード（完全に別DBに記録）
- 監視（Monitoring）
  - SystemMonitor：プロセス健全性・データ鮮度・リソース監視
  - TradeMonitor / RiskMonitor：注文の滞留・ドローダウン・ポジション上限監視
  - KillSwitch：条件に応じた停止フラグ（data/kill.flag）発行
  - MonitoringEngine：各モニタを束ねて定期実行
- ポートフォリオ構築
  - 候補選定、重み計算、ポジションサイジング、セクターキャップ、レジーム乗数
- リサーチ（DuckDBベース）
  - モメンタム・バリュー・ボラティリティなどのファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計要約
- AI / ニュースNLP
  - raw_news から銘柄別センチメントスコアを生成し ai_scores へ格納（OpenAI利用）
  - マクロニュースを使った市場レジーム判定（regime_detector）
- ツール
  - Paper Trading の検証レポート生成スクリプト（paper_verification_report）

セットアップ手順（開発環境）
1. リポジトリをクローンして Python 仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
2. 依存パッケージをインストール
   - pip install -r requirements.txt
     （本リポジトリに requirements.txt がない場合、少なくとも以下が必要）
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（config 検証で YAML のパースを行いたい場合）
3. .env の作成
   - 対話式ウィザードを実行して .env を作る:
     - python -m kabusys.config_setup
   - 手動で環境変数を設定しても可（.env を編集）
4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict
5. データディレクトリの確認
   - デフォルトでは data/ に各種 DB（data/monitoring.db, data/kabusys.duckdb, data/paper_trading.db）やフラグファイルが置かれます。
   - 必要に応じて DB ファイルパスは環境変数で変更可能（下記参照）。

基本的な使い方（実行例）
- 監視ループ起動
  - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書きできます（デフォルト 60 秒）。
  - python -m kabusys.run_monitoring
  - 注意: run_monitoring は監視用 SQLite（settings.sqlite_path）を本番パスとして使用します（KABUSYS_ENV に関係なく）。
- Execution 起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB と分離）。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db もしくは環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。
- AI 関連
  - ニューススコアリング: kabusys.ai.score_news（API キー OPENAI_API_KEY 必須）
  - レジーム判定: kabusys.ai.regime_detector.score_regime（OPENAI_API_KEY 必須）

主要な環境変数（抜粋とデフォルト）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (default: development) — 有効値: development, paper_trading, live
  - paper_trading: MockBroker を使い paper DB に記録
  - live: 本番（発注が実際に行われます）
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db) — 監視用 DB（monitoring は環境にかかわらず本番 sqlite_path を使用）
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db) — paper_trading 専用 DB
- PAPER_FILL_MODE (paper_trading 時の約定モード、default: "instant") — 有効値: instant | partial | never | reject
- LOG_LEVEL (default: INFO)
- LOG_DIR (default: logs/)
- OPENAI_API_KEY（AI機能を使う場合必須）
- MONITOR_POLL_INTERVAL（run_monitoring 用、秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（Execution 起動時に kill.flag を自動クリアするか。デフォルト 0 = クリアしない。本番では 0 推奨）

停止 / Kill フラグ / PID
- data/kill.flag: KillSwitch が作成するフラグ。ExecutionEngine はこのフラグを検知すると停止します。
- data/stop_requested.flag: run_monitoring/run_execution が存在をチェックして終了するために使用。
- data/execution.pid: Execution 起動時に PID を書き込む（設定で変更可）。
- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag が自動クリアされますが、本番では危険なので注意してください。

ログ
- ログは標準出力（stdout）と日次ローテートされたファイル（logs/<app_name>.log）に出力されます。
- ログレベルは環境変数 LOG_LEVEL または setup_logging の引数で制御できます。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数の読み取り、.env 自動ロード機能
  - config_setup.py
    - 対話式 .env 生成ウィザード
  - validate_config.py
    - 起動前チェック CLI
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading では MockBroker）
  - utils/
    - logging_setup.py: 統一ログ設定（stdout + 日次ファイルローテーション）
    - process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py: SQLite に対する永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py: CPU/メモリ/ディスク/プロセス状態・データ鮮度のチェック
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - trade_monitor.py: （注文ログ監視、滞留・異常価格検出）※実装ファイルあり
    - kill_switch.py: kill.flag を書くロジック
    - monitoring_engine.py: 各 Monitor を束ねる実行エンジン
    - alert_manager.py: （LINE 等への通知管理）※実装ファイルあり
  - execution/
    - execution_engine.py: 実際のセッション実行ループ
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py / broker_factory.py
      - ブローカー抽象化、注文管理、リスクチェックなど
  - portfolio/
    - portfolio_builder.py: 候補選定、重み計算
    - position_sizing.py: 発注株数計算（単元丸め、aggregate cap）
    - risk_adjustment.py: セクター上限・レジーム乗数
  - research/
    - factor_research.py: モメンタム・ボラティリティ・バリュー等の計算（DuckDB）
    - feature_exploration.py: 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py: ニュース記事の LLM スコアリング（OpenAI）
    - regime_detector.py: マクロ + ETF MA200 乖離から市場レジーム判定
  - tools/
    - paper_verification_report.py: Paper Trading 検証レポート生成スクリプト
  - data/ (実行時に使用/作成される)
    - monitoring.db (監視用 SQLite)
    - paper_trading.db (paper_trading 用 SQLite)
    - kabusys.duckdb (DuckDB)
    - kill.flag / stop_requested.flag / execution.pid など

補足・注意事項
- モジュール設計上、DuckDB は分析・リサーチ用途、SQLite は監視・注文ログ用途に使い分けられています。
- run_monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（監視 DB）を使用します。一方、run_execution は paper_trading 時に paper_sqlite_path を使用して DB を分離します。
- OpenAI を用いる機能は API 呼び出しの失敗に対しフェイルセーフ（デフォルト値で継続）を設ける設計です。ただし API キーが未設定の場合は明示的にエラーを投げる箇所もあります（事前に OPENAI_API_KEY を設定してください）。
- ログディレクトリの作成に失敗した場合、ファイルへのログ出力はスキップされコンソールログのみで継続します。
- 実運用（KABUSYS_ENV=live）の場合は .env の内容・Kill Switch の設定・LINE 通知設定を慎重に確認してください。validate_config の警告は特に注意を促します。

問題の切り分け / 開発時のヒント
- 簡単な動作確認:
  - .env を作成→ validate_config 実行 → python -m kabusys.run_monitoring を1回だけテストしたければ MonitoringEngine を直接インポートして run_once を呼ぶ（ユニットテスト的に）。
- Paper Trading の検証:
  - 実運用データを汚さないよう、KABUSYS_ENV=paper_trading を指定して起動。paper_trading は専用 DB に記録されます。
- ローカルで AI 機能をテストする場合は OPENAI_API_KEY を設定してください。テストでは _call_openai_api をモックできます。

---

READMEは以上です。実際の運用・デプロイ時は .env の管理（秘匿情報の保護）と validate_config による事前チェックを必ず行ってください。必要であれば各モジュール（ExecutionEngine、RiskManager、TradeMonitor 等）の API ドキュメントや設定の詳細を別途まとめます。