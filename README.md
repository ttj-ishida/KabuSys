README
=====

概要
----
KabuSys は日本株の自動売買・研究用ライブラリ兼実行フレームワークです。  
このリポジトリには、実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュース NLU（OpenAI を用いたセンチメント評価）、ペーパートレード検証ツール等のコンポーネントが含まれます。  
設計方針としては「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアスの排除」「外部 API 呼び出しのフェイルセーフ化」などに配慮されています。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db に記録して本番 DB と分離
  - 停止フラグ（data/stop_requested.flag）による安全停止
  - PID ファイル出力（data/execution.pid）
- Monitoring（run_monitoring.py / monitoring package）
  - システム状態（CPU/メモリ/ディスク）、データ鮮度やプロセス生存監視
  - トレード・リスク監視（滞留注文、約定異常、ドローダウン、ポジション上限）
  - Kill Switch（条件が満たされたら data/kill.flag を書き込み ExecutionEngine を停止）
  - 監視データを SQLite に永続化（monitoring_db）
- Portfolio construction（portfolio package）
  - 候補選定、等ウェイト / スコア重み、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap のスケールダウン）
- Research（research package）
  - ファクター計算（モメンタム・バリュー・ボラティリティ）
  - 将来リターン・IC（Information Coefficient）計算、特徴量サマリ
  - DuckDB を用いた高速データ処理
- AI（ai package）
  - news_nlp: OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価と ai_scores への書き込み
  - regime_detector: ETF とマクロニュースを合成して市場レジーム判定（bull/neutral/bear）
  - API 呼び出しはリトライやフェイルセーフを実装
- ユーティリティ
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
  - ログ設定、プロセス優先度制御ユーティリティ等

セットアップ手順
---------------
1. Python と仮想環境
   - 推奨: Python 3.10+
   - 仮想環境の作成例:
     python -m venv .venv
     source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - 主な依存例:
     pip install duckdb psutil openai
   - オプション（YAML 検証など）:
     pip install PyYAML
   - 実プロジェクトでは requirements.txt を用意している場合はそれを使用してください。

3. .env の作成
   - 対話式で作る:
     python -m kabusys.config_setup
   - もしくはプロジェクトルートに .env を手動作成する。必須項目:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - （必要に応じて）OPENAI_API_KEY を環境変数または引数で指定
   - .env のサンプル（最小）:
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here
     KABUSYS_ENV=development
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb
     LOG_LEVEL=INFO

4. 設定検証
   - 自動読み込み後、検証を実行:
     python -m kabusys.validate_config
   - 警告も厳密に扱う場合:
     python -m kabusys.validate_config --strict

5. データディレクトリ
   - 実行時に data/ や logs/ を自動作成しますが、権限や配置に注意してください。
   - 監視・実行は data ディレクトリに stop_requested.flag / kill.flag / execution.pid 等のファイルを作成します。

使い方（主要コマンド）
--------------------
- 実行エンジン起動（Production / Paper）
  - 実行（モジュールとして起動）:
    python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading のときは paper 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用
    - 停止フラグ data/stop_requested.flag がある場合は起動しない
    - 実行中に stop_requested.flag が作成されると安全に停止します

- 監視ループ起動
  - 実行:
    python -m kabusys.run_monitoring
  - ポーリング間隔:
    - デフォルト: 60 秒
    - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能（例: export MONITOR_POLL_INTERVAL=30）
    - 0 以下や不正値はデフォルト（60秒）にフォールバックします
  - 監視は常に settings.sqlite_path（monitoring DB）を使用します（環境によらず）

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 関連（プログラム呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と target_date を渡してニュースセンチメントを ai_scores に書き込みます
    - api_key を省略すると環境変数 OPENAI_API_KEY を参照
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジームを計算して market_regime テーブルへ書き込み

ログと PID / フラグファイル
---------------------------
- ログ:
  - kabusys.utils.logging_setup.setup_logging を各エントリポイントで呼び出し、stdout と logs/<app_name>.log（日次ローテーション）に出力します
  - LOG_DIR 環境変数でログ保存先を上書き可能
- PID / Stop / Kill:
  - Execution 起動時に data/execution.pid（デフォルト）に PID を書きます（Settings.pid_file_path で変更可能）
  - 停止要求は data/stop_requested.flag（run_scripts が監視）を使う
  - Kill Switch は data/kill.flag を作成して ExecutionEngine に停止シグナルを送ります（KillSwitch）

重要な環境変数（主なもの）
-------------------------
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（ai/news_nlp, ai/regime_detector で使用）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング秒数（デフォルト: 60）

ディレクトリ構成（概要）
----------------------
src/kabusys/
- __init__.py
- config.py                  — 環境変数・設定管理（Settings クラス）
- config_setup.py            — .env 対話式ウィザード
- validate_config.py         — 起動前設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — Monitoring ポーリングループ起動スクリプト

パッケージ（機能ごと）
- ai/
  - news_nlp.py              — ニュースの LLM センチメント評価（ai_scores 更新）
  - regime_detector.py       — 市場レジーム判定
- monitoring/
  - monitoring_db.py         — SQLite テーブル作成・永続化 API
  - system_monitor.py        — システム / データ鮮度監視
  - trade_monitor.py         — （トレード監視、コード参照）
  - risk_monitor.py          — ドローダウン・ポジション上限監視
  - kill_switch.py           — Kill Switch 制御（kill.flag 書き込み）
  - monitoring_engine.py     — 各 Monitor を束ねる実行ループ
  - alert_manager.py         — （通知管理、コード参照）
- execution/
  - execution_engine.py      — ExecutionEngine（起動・セッション管理）
  - broker_factory.py        — ブローカークライアント生成（Mock/実装）
  - order_manager.py / order_repository.py / reconciler.py / risk_manager.py
- portfolio/
  - portfolio_builder.py     — 候補選定・重み計算
  - position_sizing.py       — 株数決定・投下資金スケーリング
  - risk_adjustment.py       — セクター上限・レジーム乗数
- research/
  - factor_research.py       — ファクター計算（momentum/value/volatility）
  - feature_exploration.py   — 将来リターン・IC・統計サマリ
- monitoring/ (上記に含む)
- utils/
  - logging_setup.py         — 共通ログ設定
  - process_priority.py      — プロセス優先度 / CPU affinity
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

注意事項 / 運用メモ
------------------
- 本番実行前に必ず python -m kabusys.validate_config で設定を検証してください。KABUSYS_ENV=live の場合は特に LINE 通知や KILL_FLAG_CLEAR_ON_START 等を確認してください。
- OpenAI 呼び出しや外部 API はリトライ・フェイルセーフを備えていますが、API キーやレート制限には注意してください。
- デフォルトで logs/ と data/ にファイルを書きます。運用時は適切な場所・パーミッションを設定してください。
- Paper Trading は本番 DB と分離されていますが、運用時に設定を誤ると本番 DB を上書きする可能性があるため dotenv / validate_config の確認を推奨します。

ライセンス / バージョン
-----------------------
パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状: 0.1.0）。

問い合わせ / 貢献
------------------
バグ報告や機能追加提案は Issue を立ててください。開発に参加する場合はコードスタイルやテスト方針に従って PR を送ってください。

以上。README に不足している点や、実行時の具体的なエラー対応や設定例が必要なら教えてください。必要に応じてサンプル .env や運用フロー（起動・監視・停止手順）を追記します。