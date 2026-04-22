KabuSys — 日本株自動売買システム
==============================

このリポジトリは日本株向けの自動売買システム（プロトタイプ）です。  
戦略・ポートフォリオ構築、発注エンジン、監視・アラート、研究用ファクター計算、AI を使ったニュース評価等のコンポーネントを含みます。

主なポイント
- 実行用エンジン（ExecutionEngine）と監視ループ（Monitoring）を分離
- Paper Trading（モックブローカー）をサポートし、本番 DB と分離
- DuckDB を分析用 DB、SQLite を監視・トレードログ用 DB に使用
- .env ウィザード / 検証ツールを提供して起動前チェックを簡単化
- OpenAI を利用したニュース NLP や市場レジーム判定（API キー必須）

機能一覧
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、data/paper_trading.db に記録
  - プロセス優先度設定、PID ファイル管理、停止フラグ検出
- 監視ループ起動スクリプト（run_monitoring.py）
  - SystemMonitor をポーリングし system_status / risk_logs / trade_logs 等を SQLite に保存
  - MONITOR_POLL_INTERVAL によるポーリング間隔調整（デフォルト 60 秒）
- 設定ウィザード（config_setup.py）
  - 対話式で .env を生成 / 更新
- 設定検証 CLI（validate_config.py）
  - 必須環境変数や config/*.yaml、パスの存在等をチェック（--strict あり）
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - paper_trading DB を集計して指標（稼働率・成立率・P95 レイテンシ等）を出力
- ポートフォリオ構築モジュール（portfolio/*）
  - 候補選定、重み計算、ポジションサイズ計算、セクターキャップ、レジーム乗数等の純粋関数
- 研究用モジュール（research/*）
  - DuckDB を使ったファクター計算（momentum/value/volatility 等）、IC 計算、統計サマリ
- AI モジュール（ai/*）
  - ニュースを OpenAI でスコアリング（news_nlp）
  - 市場レジーム判定（regime_detector）
  - OpenAI API 呼び出しは環境変数 OPENAI_API_KEY または引数で指定
- ユーティリティ
  - ログ設定ユーティリティ（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity 設定ユーティリティ（utils/process_priority.py）
  - 監視 DB 永続化層（monitoring/monitoring_db.py）

前提 / 必要な依存
- Python 3.9+
- 推奨ライブラリ（例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml の検証を行う場合）
- これらは requirements.txt がある場合はそれを利用してください。なければ pip install duckdb psutil openai PyYAML

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存インストール
   - pip install duckdb psutil openai PyYAML
4. 環境変数設定（.env 作成）
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいは .env を手動で作成（.env.example を参照）
   - 自動ロード: kabusys.config はプロジェクトルートで .env / .env.local を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 重要: 本番環境では python -m kabusys.validate_config --strict を推奨

主要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG / INFO / ...、デフォルト: INFO）
- OPENAI_API_KEY（AI 機能使用時に必須）
- MONITOR_POLL_INTERVAL（監視ループの秒数、デフォルト 60）
- PAPER_FILL_MODE（paper_trading の約定挙動: instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START（本番での Kill Flag 自動クリア、0/1）

使い方（起動 / 利用方法）
- 実行エンジン（ExecutionEngine）の起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は paper_trading DB にログが残り、本番 DB と分離されます
  - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します
  - 停止は data/stop_requested.flag を作成すると監視・エンジンが終了します（または Kill Switch により data/kill.flag が書かれると停止トリガー）
- 監視ループの起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を秒数で設定してポーリング間隔を上書き可能
  - 監視は設定にかかわらず本番 sqlite_path を使って監視ログを書きます
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - DB パスは --db > 環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト の優先度で解決
- AI 系機能
  - news scoring / regime scoring はそれぞれ kabusys.ai.news_nlp.score_news, kabusys.ai.regime_detector.score_regime としてプログラム的に呼び出せます
  - OpenAI API キーが必要（OPENAI_API_KEY）

停止 / Kill
- 即時の手動停止（実験的 / 運用用）
  - data/stop_requested.flag を作成すると run_monitoring や run_execution が検知して終了します
  - 監視側の KillSwitch は条件により data/kill.flag を書き、ExecutionEngine に停止シグナルを送ります
  - KillSwitch のクリアは KillSwitch.clear() で行うか、ファイルを手動削除してください

ログ
- ログはデフォルトで標準出力に出力され、さらに logs/<app_name>.log に日次ローテーションで保存されます（logs ディレクトリが作成されます）
- ログレベルは環境変数 LOG_LEVEL または setup_logging の引数で設定可能

DB / マイグレーション
- monitoring_db.init_monitoring_db は起動時に必要テーブルを冪等に作成します
- 既存 DB に対する簡易マイグレーション（カラム追加等）も実装されています（例: dashboard.peak_value, trade_logs.latency_ms）

注意事項 / 運用メモ
- KABUSYS_ENV=live のときは設定値を慎重に確認してください（validate_config で追加警告あり）
- .env を絶対に Git にコミットしないこと
- Paper Trading はあくまで検証用。本番挙動は cabuステーション API の実際の挙動に依存します
- OpenAI 呼び出し部分は API エラーに対してリトライやフォールバック（0.0）を行い、サービス停止に繋がらないよう設計されていますが、API 利用制限やコストに注意してください

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / .env 自動ロード・Settings 定義
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py                 — ニュース NLP スコアリング
    - regime_detector.py          — 市場レジーム判定
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (実装参照)
  - execution/                     — 発注エンジン関連（BrokerFactory, Engine, OrderManager, etc.）
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                           — 既定の data ディレクトリ（SQLite / PID / flag ファイル 等）

（注）実際のファイル・サブモジュールは上記に含まれるものを中心に実装されています。詳細は各モジュールの docstring を参照してください。

よく使うコマンド例
- .env 作成（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動
  - python -m kabusys.run_execution
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

ライセンス / 責任
- このリポジトリはサンプル・プロトタイプです。実運用の前に十分なテストとコード監査を行ってください。金融取引には固有のリスクと法規制があります。

問題報告・貢献
- バグ報告や改善提案は Issue を立ててください。プルリクエスト歓迎です。

以上がこのコードベースの概要と基本的な使い方です。具体的な実装や細かい API の使い方は各モジュールの docstring とソースコードを参照してください。必要であれば README に含めるサンプル .env のテンプレートや起動スクリプトの systemd ユニット例なども追記します。どの追加情報が欲しいか教えてください。