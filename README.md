README
=====

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームのコードベースです。  
主な目的は以下のとおりです。

- 自動売買の実行（ExecutionEngine）
- システム稼働状況・注文状況・リスク監視（Monitoring）
- ポートフォリオ構築・ポジションサイズ算出（Portfolio）
- ファクター計算・特徴量探索などのリサーチ機能（Research）
- ニュース NLP を用いたセンチメント評価 / レジーム判定（AI）
- ペーパートレード検証・レポート生成などのツール群

機能一覧
--------
- Execution
  - 実際の発注（live）とペーパートレード（paper_trading）を環境で切り替え
  - Broker クライアントを抽象化して実装を差し替え可能
  - PID ファイル / stop フラグで外部から停止制御

- Monitoring
  - CPU/メモリ/ディスク・プロセス生存・データ鮮度のポーリング監視
  - 注文ログ / ポジション / リスクイベントの永続化（SQLite）
  - Kill Switch（ドローダウンやポジション過多で自動停止フラグ書き込み）
  - AlertManager 経由で通知（LINE 等の実装は別途）

- Portfolio
  - 候補選定、等配分・スコア加重配分、ポジションサイズ計算
  - セクター制約・レジーム乗数の適用

- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（情報係数）や統計サマリー

- AI
  - news_nlp: OpenAI を用いたニュースごとのセンチメントスコアリング（ai_scores へ保存）
  - regime_detector: ETF とマクロ記事の合成で市場レジーム判定

- Tools
  - paper_verification_report: ペーパートレード DB から検証レポートを生成

セットアップ手順
----------------
前提
- Python 3.10 以上を推奨（型注釈・Union 短縮構文を使用）
- システムに duckdb, psutil, openai などのライブラリをインストール

例: 仮想環境作成と依存関係インストール
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作る
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合は pip install -r requirements.txt）

4. 環境変数設定
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参照）
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI を使う場合）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い

6. ディレクトリ
   - data/ と logs/ は自動作成されますが、権限等で作成に失敗する場合は手動で作成してください。

使い方（主要コマンド）
--------------------
- 実行エンジンを起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、
      data/paper_trading.db（デフォルト）に記録して本番 DB と分離します。
    - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
    - 実行中に data/stop_requested.flag を作成するとエンジン停止要求が送られます。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（設計上の注意）

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式に生成・更新します

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗として exit(1)

- Paper Trading 検証レポートの生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数を上書き）

環境変数（主要）
----------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: 発注はモック、専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
  - live: 本番動作（注意して設定してください）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（ai.news_nlp / regime_detector を使うとき）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
- DUCKDB_PATH（分析用 DuckDB、デフォルト: data/kabusys.duckdb）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（デフォルト: logs/）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数）
- PAPER_FILL_MODE（instant | partial | never | reject、ペーパートレードの約定モード）
- KILL_FLAG_CLEAR_ON_START（1 にすると起動時に kill.flag を自動クリア）

停止制御 / フラグファイル
------------------------
- run_execution / run_monitoring はプロジェクトルート配下の data/stop_requested.flag を監視します。
  - ファイルが存在するとループを終了または起動をスキップします。
- Kill Switch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを出します。
  - kill.flag のパスは Settings.kill_flag_path（デフォルト data/kill.flag）。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされますが、本番では推奨されません。
- PID ファイル: data/execution.pid（ExecutionEngine が使用）

ログ
---
- ログ出力は kabusys.utils.logging_setup.setup_logging を通じて統一
- デフォルト: stdout（StreamHandler）と logs/<app_name>.log（日次ローテーション、30日保持）
- ログディレクトリは LOG_DIR 環境変数またはデフォルト logs/

開発者向け情報 / ライブラリ API（簡易）
-----------------------------------
- ポートフォリオ関連関数（純粋関数、外部依存なし）
  - kabusys.portfolio.select_candidates(...)
  - kabusys.portfolio.calc_equal_weights(...)
  - kabusys.portfolio.calc_score_weights(...)
  - kabusys.portfolio.calc_position_sizes(...)
  - kabusys.portfolio.apply_sector_cap(...)
  - kabusys.portfolio.calc_regime_multiplier(...)

- リサーチ（DuckDB 接続を渡して使用）
  - kabusys.research.calc_momentum(conn, date)
  - kabusys.research.calc_volatility(conn, date)
  - kabusys.research.calc_value(conn, date)
  - kabusys.research.calc_forward_returns(...)
  - kabusys.research.calc_ic(...)
  - kabusys.research.factor_summary(...)

- AI
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- Monitoring DB ヘルパー
  - kabusys.monitoring.monitoring_db.MonitoringDB — 永続化 API（log_system_status / log_trade_event / upsert_dashboard 等）

ディレクトリ構成（主なファイル）
------------------------------
以下は src/kabusys 配下の主要ファイル・モジュールと簡単な説明です。

- kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
  - config_setup.py — .env を対話式に作成するウィザード
  - validate_config.py — 起動前の設定検証 CLI

  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト

  - ai/
    - news_nlp.py — ニュース NLP（OpenAI 呼び出し、ai_scores 書き込み）
    - regime_detector.py — 市場レジーム判定

  - monitoring/
    - monitoring_db.py — SQLite テーブル作成・操作（MonitoringDB）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度のチェック
    - risk_monitor.py — ドローダウン・ポジション数監視
    - trade_monitor.py — （注文系監視、コードベースに実装あり）
    - kill_switch.py — kill.flag の読み書きロジック
    - monitoring_engine.py — 監視コンポーネントを束ねるエンジン
    - alert_manager.py — 通知管理（実装依存）

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算
    - risk_adjustment.py — セクター上限・レジーム乗数

  - research/
    - factor_research.py — Momentum/Volatility/Value 等の計算
    - feature_exploration.py — forward returns, IC, 統計サマリ

  - monitoring/, execution/, research/ など他サブパッケージが多数（主要ファイルは上記）

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

  - utils/
    - logging_setup.py — 共通ログ設定
    - process_priority.py — プロセス優先度 / CPU affinity 設定
    - その他ユーティリティ群

注意事項 / ベストプラクティス
----------------------------
- 本番稼働（KABUSYS_ENV=live）は慎重に設定してください。validate_config の警告を必ず精査してください。
- .env は絶対にバージョン管理にコミットしないでください（config_setup も README 内に警告あり）。
- OpenAI キーなどセンシティブな情報は安全に管理してください。
- run_monitoring は監視ログのために本番 sqlite_path を使用します（意図的）。
- ペーパートレードは本番 DB と分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。

ライセンス / 貢献
----------------
- （ここにプロジェクトのライセンス情報を追記してください）
- バグ報告や機能提案は issue を立ててください。

この README はコードベースの主要部分に基づいて作成しました。  
実行環境固有の設定や追加の依存関係はプロジェクト内のドキュメント / config/*.yaml / .env.example を参照してください。