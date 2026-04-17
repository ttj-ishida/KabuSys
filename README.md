README.md

KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買（Execution）・監視（Monitoring）・リサーチ（Research）機能を備えた軽量フレームワークです。  
設計方針として以下を重視しています。

- 本番とペーパートレードの分離（環境変数 KABUSYS_ENV）
- DuckDB を用いた因子計算・リサーチ（オフライン分析向け）
- SQLite を用いた監視ログ（monitoring.db）、ペーパートレードは別 DB（paper_trading.db）
- OpenAI（gpt-4o-mini）を用いたニュース NLP / レジーム判定（API キー必須）
- 設定管理を .env ベースで簡易ウィザード提供

主な機能
--------
- ExecutionEngine（run_execution.py）
  - ブローカークライアント抽象化（実口座 / Mock）
  - 注文管理、リスク管理、和解（reconciler）コンポーネントの統合
  - KABUSYS_ENV=paper_trading 時は MockBroker を使用し DB を分離
- Monitoring（run_monitoring.py / monitoring/*）
  - システム状態監視（CPU / メモリ / ディスク / プロセス生存）
  - 注文滞留・約定異常の監視
  - ドローダウン / ポジション上限の監視と Kill Switch（kill.flag）の発動
  - 監視結果は SQLite（monitoring.db）へ永続化
- Portfolio construction（portfolio/*）
  - 候補選定、等重・スコア重み、リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ算出（単元丸め、aggregate cap）
- Research（research/*）
  - モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB SQL ベース）
  - 将来リターン、IC（Spearman）計算、統計サマリー
- AI（ai/*）
  - ニュース記事のセンチメント化（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
  - OpenAI API の呼び出し・バックオフ・レスポンス検証を扱う
- ツール
  - 環境設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ペーパートレード検証レポート生成（tools/paper_verification_report.py）

依存関係（主なもの）
-------------------
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config の YAML 検証は任意）

セットアップ手順
----------------
1. リポジトリを取得しインストール
   - git clone ... && cd <project_root>
   - 仮想環境を作成して依存をインストールしてください（例: pip install -r requirements.txt）。

2. .env を作成（ウィザード推奨）
   - 対話式で .env を生成:
     python -m kabusys.config_setup
   - 重要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY（news_nlp / regime_detector に必要）

3. 設定を検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

4. データディレクトリ
   - デフォルトでは data/ 以下を使用（duckdb: data/kabusys.duckdb、sqlite: data/monitoring.db、paper_trading.db 等）。
   - 必要に応じて .env 内の DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH を変更。

使い方
------
- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV により動作モードが変わります:
    - development : 発注なし（開発用）
    - paper_trading: MockBroker を使い data/paper_trading.db に記録
    - live        : 本番ブローカーを使用（注意して運用）
  - 起動時に data/execution.pid に PID が書き込まれます。停止シグナルは data/stop_requested.flag（run_execution/run_monitoring が参照）や kill.flag（Kill Switch）で制御される場合があります。

- 監視ループを起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path を使用します（監視は環境に依存しない本番 DB を想定）。

- 環境設定のウィザード:
  - python -m kabusys.config_setup
  - .env を生成・更新します。生成後は必ず git にコミットしないでください（シークレットを含むため）。

- 設定検証:
  - python -m kabusys.validate_config
  - 設定漏れ・パスの存在チェック・YAML 構文チェック（PyYAML がインストール済みの場合）等を行います。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 簡易的な Pass/Fail 判定（稼働率・注文成功率・送信率・P95 レイテンシなど）を出力します。

- AI 機能を使う:
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。

注意事項（運用上のポイント）
----------------------------
- 本番環境（KABUSYS_ENV=live）では LINE 通知などの設定を必ず確認してください（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）。
- .env は絶対にリポジトリにコミットしないでください。
- Kill Switch（kill.flag）や stop_requested.flag を用いたプロセス停止は冪等性や誤動作に注意して運用してください。
- paper_trading モードは本番 DB と分離されていますが、パス設定に注意してください（PAPER_TRADING_SQLITE_PATH）。

ディレクトリ構成
----------------
（src/kabusys 配下の主なファイル/モジュール）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・.env 自動読み込みロジック・Settings クラス
  - config_setup.py
    - 対話式 .env 生成ウィザード
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
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
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py  (アラート送信ロジック)
  - execution/
    - (注文関連のエンジン・リポジトリ・リスク管理などを含む)
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py
  - data/  (runtime)
    - monitoring.db (デフォルト)
    - kabusys.duckdb (デフォルト)
    - paper_trading.db (paper_trading モード)
    - execution.pid / kill.flag / stop_requested.flag

監視 DB の主なテーブル（monitoring/monitoring_db.py）
- system_status: CPU/Memory/Disk/プロセス状態 / recorded_at
- trade_logs: 注文イベントログ（event_type: Created/Sent/Filled 等）、latency_ms 等
- positions: 保有ポジション
- risk_logs: リスク関連ログ（DRAWDOWN_ALERT / STALE_ORDER / PRICE_ANOMALY 等）
- dashboard: 集計（portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value）

開発・貢献
----------
- 新しい構成項目を追加したら config_setup と validate_config を更新してください。
- DuckDB の SQL を更新する場合、research モジュールのテストデータで動作検証を行ってください。
- AI 系機能を変更する際はエラー時のフェイルセーフ（スコア 0.0 など）を維持してください。

ライセンス
----------
プロジェクトに同梱された LICENSE を参照してください。

お問い合わせ
------------
問題報告や改善提案は Issue を立ててください。README の改善や使い方の補足が必要であれば教えてください。