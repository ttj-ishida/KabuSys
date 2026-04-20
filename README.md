KabuSys — 日本株自動売買システム（簡易 README）
======================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の一部をまとめたコードベースです。本リポジトリには、実行エンジン（ExecutionEngine）や監視（Monitoring）、ポートフォリオ構築、研究（ファクター計算・特徴量解析）、AI（ニュースセンチメント評価・レジーム判定）などのモジュール群が含まれます。設計方針として「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアスを避ける」「外部 API 失敗時はフェイルセーフで継続」などが盛り込まれています。

主な機能
--------
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading 時は MockBroker を使い data/paper_trading.db に記録
  - 起動時にプロセス優先度を設定し、データベース／依存コンポーネントを組み立ててセッションを実行
  - 停止フラグ（data/stop_requested.flag）を検知して安全に停止
- 監視プロセス起動スクリプト（run_monitoring.py）
  - System / Trade / Risk モニタを定期ポーリングしログを SQLite に保存
  - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）
  - KillSwitch による停止フラグ（data/kill.flag）発行・評価
- 監視 DB 層（monitoring_db.py）
  - system_status / trade_logs / positions / risk_logs / dashboard テーブルを作成・マイグレーション
  - 監視ログの読み書きユーティリティを提供
- リスク監視（risk_monitor.py）
  - ドローダウンやポジション数超過を検知しリスクイベントを記録、必要時に kill.flag を作成
- ポートフォリオ構築（portfolio/*.py）
  - 候補選定、等ウェイト／スコア加重、リスクベースの株数計算、セクター上限適用など
- リサーチ（research/*）
  - DuckDB を使ったファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン・IC 計算、ファクター統計サマリー等
- AI（ai/*）
  - ニュースセンチメント（OpenAI を利用）、マクロニュースを組み合わせたレジーム判定
  - API 呼び出しはリトライ・検証・クリッピングを含む安全な実装
- ユーティリティ
  - 環境設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ロギング設定ユーティリティ（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity ユーティリティ（utils/process_priority.py）
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

セットアップ手順（ローカル開発向け）
---------------------------------
1. Python 環境
   - Python 3.10+ を推奨（コードは型ヒントに Python 3.10+ の構文を使用）。
2. 依存ライブラリをインストール
   - 代表的な必須ライブラリ:
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - PyYAML（validate_config の YAML 検証は任意）
   - 例:
     - pip install duckdb psutil openai pyyaml
   - （パッケージ配布・requirements.txt がある場合はそちらを使用してください）
3. プロジェクトルートに移動
   - この README があるディレクトリ（pyproject.toml/.git を含むはずのルート）
4. .env の作成（対話式推奨）
   - python -m kabusys.config_setup を実行すると対話式ウィザードで .env を生成できます。
   - 必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告を厳格扱いする場合: python -m kabusys.validate_config --strict
6. データディレクトリ / ログディレクトリ
   - デフォルトでは data/ および logs/ を使用します。必要に応じて .env でパスを変更してください。

主要な環境変数（抜粋）
--------------------
（Settings クラスで読み取られる主な変数とデフォルト）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live) （デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: Paper 用 DB（デフォルト data/paper_trading.db）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知（任意）
- LOG_LEVEL: デフォルト INFO
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY: OpenAI を使う機能で参照

使い方（実行例）
----------------
- .env を作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 監視プロセス起動（コンソールで）
  - MONITOR_POLL_INTERVAL を上書きする場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - あるいは単に:
    - python -m kabusys.run_monitoring
  - 監視は設定された SQLite DB（Settings.sqlite_path）に記録します。監視は本番 sqlite_path を使う設計です（KABUSYS_ENV に依存しません）。
- 実行エンジン（ExecutionEngine）起動
  - 簡易:
    - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使い data/paper_trading.db に記録します（本番 DB とは分離）。
- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/db.sqlite
- AI 機能（ニューススコアリング / レジーム判定）
  - Python API 経由で呼び出す（例: kabusys.ai.score_news）
  - OPENAI_API_KEY を設定してから実行してください（詳細は関数 docstring を参照）
- ログ
  - logs/<app_name>.log に日次ローテートで出力（app_name は "monitoring", "execution" 等）
  - stdout へも出力されます

運用に関する注意点
-------------------
- Kill Switch / Stop フラグ:
  - KillSwitch（監視側）が条件を満たすと data/kill.flag を書き込み、実行エンジンを停止させる仕組みです。
  - run_execution/run_monitoring は data/stop_requested.flag の存在を利用してプロセス停止や起動抑制を行います。
  - 本番では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨します（誤って自動クリアすると危険）。
- Paper と Live の DB 分離:
  - paper_trading モードでは paper_sqlite_path（デフォルト data/paper_trading.db）に記録され、本番 monitoring.db とは分離されます。
- OpenAI / 外部 API:
  - API 呼び出しはリトライやフォールバック（失敗時に無視して続行）を組み込んでいますが、API キーやレート制限には注意してください。
- ロギングディレクトリ作成に失敗した場合、ファイル出力は無効になり stdout のみになります（警告が出ます）。

ディレクトリ構成（主要ファイル）
--------------------------------
（src/kabusys 配下の主要ファイル／パッケージ）
- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings クラス、自動 .env ロード
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 起動前の設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py                — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py         — マーケットレジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py           — SQLite テーブル定義・簡易 ORM
    - system_monitor.py
    - trade_monitor.py           — （トレード監視ロジック：ファイルで一部実装あり）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py           — （未列挙だがアラート集約用）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

付録：よく使うコマンドまとめ
----------------------------
- .env の対話式作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 監視起動:
  - python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- Paper レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

問い合わせ・拡張
----------------
各モジュールは docstring と関数コメントで設計意図や安全策（例: ロック、トランザクション、フェイルセーフ）を説明しています。実運用での導入・監査・テスト作業の際はそれらの注記を必ず確認してください。

以上。必要であれば「導入手順の自動化（requirements.txt / docker-compose）」「実行エンジンの詳細なデバッグ手順」「各コンポーネントのユニットテスト方針」など、追加ドキュメントを作成します。どれを優先しますか？