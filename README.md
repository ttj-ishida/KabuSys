# KabuSys

日本株向け自動売買フレームワークの一部（ライブラリ/実行スクリプト群）。  
このリポジトリはトレード実行ロジック、モニタリング、ポートフォリオ構築、リサーチ、AI を用いたニュース解析などのコンポーネントで構成されています。

注意: .env ファイルには秘密情報（APIキー等）を含めるため、決して Git にコミットしないでください。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要コマンド）
- ディレクトリ構成（主要ファイルの説明）
- 運用上の留意点

---

プロジェクト概要
- KabuSys は日本株自動売買システムのコアライブラリ群と、実行/監視用スクリプトを提供します。
- コードはモジュール化されており、取引実行（ExecutionEngine）、監視（MonitoringEngine）、ポートフォリオ構築、ファクター計算、ニュースNLP（LLM を利用）などを含みます。
- 本番（live）・ペーパートレード（paper_trading）・開発（development）を環境変数（KABUSYS_ENV）で切り替え可能。ペーパートレードは発注をモック化し、専用の SQLite DB に記録されるため本番 DB と分離されています。

---

主な機能一覧
- Execution
  - 実行エンジンと Order 管理（ExecutionEngine、OrderManager、OrderRepository、RiskManager、Reconciler 等）
  - paper_trading 環境では MockBrokerClient を使用し data/paper_trading.db に記録
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、実行プロセスの存在、株価データ鮮度を監視
  - TradeMonitor: 注文滞留・約定異常価格を検出
  - RiskMonitor: ドローダウンやポジション上限監視、ダッシュボード更新
  - KillSwitch / AlertManager による自動停止・通知トリガ
  - monitoring DB 初期化と永続化（SQLite）
- Portfolio construction
  - 候補選択、等比重／スコア重み、ポジションサイズ計算、セクター上限・レジーム乗数
- Research
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン・IC 計算・統計サマリー
- AI（LLM）機能
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込み
  - regime_detector: ETF とマクロニュースのスコアを合成して市場レジーム判定を行い DB に書き込み
- CLI / ユーティリティ
  - .env 設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools/paper_verification_report）
  - プロセス優先度/CPU affinity 設定ユーティリティ（utils/process_priority）

---

セットアップ手順（ローカル開発・検証向け）
1. 前提
   - Python 3.10+（typing の | を使用しているため）を推奨
   - SQLite は標準ライブラリで利用可能
2. 必要なパッケージをインストール
   - 代表的な依存:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML 検査を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML
3. 環境変数（必須）
   - JQUANTS_REFRESH_TOKEN（J-Quants API）
   - KABU_API_PASSWORD（kabuステーション API）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - その他（任意/デフォルトあり）:
     - KABUSYS_ENV（development|paper_trading|live、デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）
4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 生成後、python -m kabusys.validate_config で検証
5. データディレクトリ
   - デフォルト DB 等は data ディレクトリ配下に置かれます（必要に応じて作成されます）。
6. （任意）システム設定
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
   - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動削除するか（0/1）

---

使い方（主要コマンド・スクリプト）
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit 1
- 実行エンジンを起動（通常はサービスや systemd 等で起動）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、paper_trading DB に記録
    - 停止は data/stop_requested.flag（プロジェクトルートの data 配下）を作成することで検知して安全に停止
    - 実行中は PID を data/execution.pid に書き込む（Settings.pid_file_path でカスタマイズ可能）
- 監視（Monitoring）を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（秒）
  - 監視は Settings によらず本番 sqlite_path を使用し、監視テーブルを初期化（冪等）
  - 停止は data/stop_requested.flag を検知して停止
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
- AI 関連（プログラムから呼び出す API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは OpenAI API キー（OPENAI_API_KEY）を要求します（api_key 引数でも可）。
- 監視エンジン単体（テスト用）
  - MonitoringEngine を作成して run_once / run を呼ぶことで動作確認できます（ユニットテスト向け）。

---

主要なファイル / ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数読み込み、自動 .env ロード、各種パス/フラグ設定を提供
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - .env と config/*.yaml の静的チェック CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（PID 管理、stop flag チェック）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, ...
    - 実取引ロジックとブローカ抽象化
  - monitoring/
    - monitoring_db.py: SQLite テーブル定義と永続化 API
    - system_monitor.py: CPU/メモリ/ディスク、プロセス/データ鮮度チェック
    - trade_monitor.py: 注文滞留・約定異常検出
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - kill_switch.py: data/kill.flag を書き込むロジック
    - monitoring_engine.py: 各 Monitor を束ねるループ実装
    - alert_manager.py: 通知（LINE 等）を管理（実装ファイルあり）
  - portfolio/
    - portfolio_builder.py: 候補選定・重み計算
    - position_sizing.py: 株数決定、単元丸め、集約上限スケーリング
    - risk_adjustment.py: セクター上限・レジーム乗数
  - research/
    - factor_research.py: Momentum / Value / Volatility 等の計算（DuckDB 利用）
    - feature_exploration.py: 将来リターン、IC、統計サマリー
  - ai/
    - news_nlp.py: ニュースを集約し OpenAI に投げて銘柄スコアを生成
    - regime_detector.py: マクロニュース + ETF MA を使ったレジーム判定
  - tools/
    - paper_verification_report.py: Paper Trading の検証レポート生成
  - utils/
    - process_priority.py: プロセス優先度 / CPU affinity のユーティリティ
  - data/ (実行時に使用されるデフォルトディレクトリ)
    - monitoring.db（デフォルト） / kabusys.duckdb / paper_trading.db など
    - kill.flag, stop_requested.flag, execution.pid などのフラグ・PID ファイル

---

運用上の留意点（短く）
- .env の自動ロードはプロジェクトルートが特定できる場合にのみ行われます。CI/テストで自動ロードを抑止するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番（KABUSYS_ENV=live）では通知設定や Kill Switch の設定を特に注意してください。validate_config は live 時に追加チェックを行います。
- run_execution/run_monitoring は stop フラグ（data/stop_requested.flag）を確認して安全に停止します。KillSwitch は data/kill.flag を作成して ExecutionEngine を外部から停止させます（clear を使って消去）。
- AI 機能は OpenAI API を使用するため、利用量・料金・レートリミットに注意してください。API エラーはフォールバックロジックを備えていますが、運用ルールを事前に定めてください。
- DB マイグレーション: monitoring_db.init_monitoring_db はテーブル作成といくつかの簡単な ALTER を実行します。大規模なスキーマ変更は別途マイグレーションが必要です。

---

追加情報 / 開発者向けメモ
- DuckDB をデータ分析/ファクター計算に使用します。prices_daily / raw_financials / raw_news 等のテーブルを前提に設計されています。
- 多くの内部関数は「ルックアヘッドバイアス」を避ける設計（target_date を明示的に受け取る、datetime.today を直接参照しない等）がされています。テスト時はこれを活かして deterministic な単体テストを作成してください。
- ロギングは標準 logging を使用。デバッグ時は LOG_LEVEL=DEBUG を設定してください。

---

問題・改善提案や README の追記希望があれば、どの項目を詳しく書くか教えてください（例: ExecutionEngine の API、OrderRepository スキーマ、AlertManager の設定方法など）。