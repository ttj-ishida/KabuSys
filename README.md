# KabuSys

日本株の自動売買・研究プラットフォーム用ライブラリ群および起動スクリプト一式。

このリポジトリは取引エンジン（ExecutionEngine）、監視処理（Monitoring）、研究用ファクター計算、AI（ニュースセンチメント・レジーム判定）などで構成される。DuckDB を分析用に、SQLite を監視ログ / ペーパートレード用に使用する設計になっています。

バージョン: 0.1.0

---

概要
- 自動売買の実行エンジン（実口座/ペーパートレード切替対応）
- システム稼働監視、注文監視、リスク監視、Kill Switch（停止フラグ）機能
- ファクター計算・特徴量探索（DuckDB を利用）
- ニュースの自然言語処理による銘柄センチメント集計（OpenAI API 経由）
- ペーパートレード結果の検証レポート生成ツール
- .env 対話式ウィザード、設定検証 CLI を提供

主な機能一覧
- Execution
  - ExecutionEngine：ブローカークライアントを切り替えて発注処理を実行
  - RiskManager / OrderManager / Reconciler 等の実行周りコンポーネント
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、プロセス有無、データ鮮度の監視
  - TradeMonitor：注文の滞留／約定異常など検知（実装ファイルあり）
  - RiskMonitor：ドローダウン・ポジション上限のチェックとアラートログ
  - KillSwitch：条件に応じた停止フラグ（data/kill.flag）を書き込み
  - MonitoringEngine：上記を束ねたポーリングループ
- Research
  - factor_research：モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - feature_exploration：将来リターン計算、IC（Spearman）等
- AI
  - news_nlp：ニュースを集約して OpenAI に送信し銘柄別スコアを ai_scores テーブルへ書込
  - regime_detector：ETF の MA やマクロ記事を元に市場レジーム（bull/neutral/bear）判定
- Tools
  - paper_verification_report：ペーパートレード DB を集計して PASS/FAIL レポートを出力
- Utilities
  - .env ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ログ設定ユーティリティ、プロセス優先度調整ユーティリティ

前提 / 必要環境
- Python 3.10+（typing の `X | Y` 構文を使用）
- 必須パッケージ（例）
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML（config/*.yaml の内容検証に使用）
- SQLite（標準ライブラリに含まれます）

インストール（開発環境例）
1. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
2. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （設定検証で YAML チェックを行う場合）pip install pyyaml

セットアップ手順（基本）
1. プロジェクトルートに移動（README と同階層）
2. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参考に）
3. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば修正し再度実行
4. データディレクトリ / ログディレクトリを確認
   - デフォルト DB / ログパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite (ペーパー時): data/paper_trading.db
     - logs/: ログファイル（アプリごとに日次ローテート）

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時必須）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1。デフォルト 0。本番は 0 推奨）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒。run_monitoring で使用。デフォルト 60）

使い方（起動 / コマンド）
- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使い、data/paper_trading.db に記録します。
  - ExecutionEngine は data/execution.pid を使って PID 管理します。
  - 停止は data/stop_requested.flag を作成することで行えます（run_execution はこのファイルを監視して停止）。
- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）。
  - 監視は常に本番 sqlite_path を使用（環境に依らず同一 DB へ書き込み）。
- .env ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱いで終了コード1
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）
- AI 関連（ニューススコア / レジーム判定）
  - KabuSys の AI 機能は OpenAI API に依存します。API キーは OPENAI_API_KEY を設定してください。
  - 関数レベルで利用する場合は kabusys.ai.score_news 等をインポートして呼び出します。

停止 / Kill Switch
- 実行中のエンジンを外部から停止させる仕組み:
  - data/stop_requested.flag: run_execution / run_monitoring が存在を検知して終了または停止処理を行う
  - data/kill.flag: KillSwitch によって書き込まれる。ExecutionEngine は起動時に kill.flag を検出すると起動を中止する設定がある
  - KILL_FLAG_CLEAR_ON_START=1 に設定すると起動時に自動で kill.flag をクリアする（本番では推奨されない）

ログ
- ログは標準出力と logs/<app_name>.log（日次ローテート、30日保持）に出力されます。
- setup_logging(app_name="execution" など) を各起動スクリプトが呼び出します。

ディレクトリ構成（主要ファイル抽出）
- src/kabusys/
  - __init__.py
  - config.py                — 環境設定読み込み・Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (存在を前提とした設計箇所あり)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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

補足（設計上の注意点）
- DuckDB は分析・研究用の大容量データ処理に使う想定です。prices_daily / raw_financials / raw_news 等のテーブルに依存します。
- 実行スクリプトはプロセス優先度の設定を試みます（psutil に依存）。権限がない場合は警告を出して継続します。
- OpenAI 呼び出しはリトライや JSON バリデーションを組み込んでおり、失敗時はフェイルセーフ（一定のデフォルト）で継続する設計です。
- .env は決してリポジトリへコミットしないでください（config_setup でも同旨の注記あり）。

開発 / 貢献
- まずは .env を作成し、python -m kabusys.validate_config で問題がないか確認してください。
- DuckDB のテーブルやサンプルデータはプロジェクトの別スクリプト（data pipeline 等）で準備してください（この README にはデータロードの手順は含まれていません）。
- ユニットテストや CI は別途セットアップすることを推奨します。

以上が本コードベースの概要と利用方法です。追加でREADMEに記載したい具体的な起動例や運用上の手順（systemd ユニット例、ログローテーション設定、バックアップ方針等）があれば教えてください。必要に応じて追記します。