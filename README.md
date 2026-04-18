README — KabuSys（日本株自動売買システム）
=======================================

概要
----
KabuSys は日本株向けの自動売買システム骨格です。取引実行（ExecutionEngine）、システム監視、ポートフォリオ構築、ファクター研究、ニュース NLP を用いた AI スコアリングなどのコンポーネントを備え、ローカル開発（development）、ペーパートレード（paper_trading）、本番（live）を想定した挙動切替をサポートします。

バージョン: 0.1.0

主な特徴（機能一覧）
-------------------
- 実行エンジン起動スクリプト（run_execution）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）に記録して本番 DB と分離
  - PID ファイル / stop フラグに基づく起動・停止制御
- 監視エンジン（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor のポーリング集約
  - SQLite（監視ログ）、DuckDB（分析用）への書き込み
  - Kill Switch（drawdown やポジション上限で停止フラグを書込む）
- ポートフォリオ構築（portfolio）
  - 候補選定、等配分／スコア配分、ポジションサイズ計算、セクター制約、レジーム乗数
- 研究用モジュール（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC 計算、統計サマリ
- ニュース NLP / レジーム検出（ai）
  - OpenAI を使ったニュースセンチメント評価（ai_scores への書き込み）
  - ETF とマクロニュースを組合せた市場レジーム推定
- ユーティリティ
  - .env 対話式生成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report）
- ロギング統一化（utils/logging_setup）、プロセス優先度制御（utils/process_priority）

前提（必要条件）
---------------
- Python 3.9+（typing の記述から推定）
- 必要 Python パッケージ（一部は任意）:
  - duckdb
  - psutil
  - openai（AI モジュールを使う場合）
  - pyyaml（validate_config が YAML 検証を行う場合に必要）
- SQLite（標準ライブラリに含まれます）
- ネットワークアクセス（kabu API / OpenAI を利用する場合）

推奨インストール例:
  pip install duckdb psutil openai pyyaml

セットアップ手順
---------------
1. リポジトリをクローン／展開する
   - プロジェクトルートに src/ 以下があることを確認

2. Python 環境を準備する（venv 推奨）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml

4. .env を作成
   - 対話式ウィザードを使う:
     python -m kabusys.config_setup
   - もしくは .env.example を参考にプロジェクトルートに .env を作成
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY（もしくは score_regime/score_news に api_key を渡す）

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告もエラーとして扱う場合: python -m kabusys.validate_config --strict

デフォルトのデータパス
- DuckDB: data/kabusys.duckdb
- SQLite（監視）: data/monitoring.db
- Paper Trading SQLite（paper_trading 環境）: data/paper_trading.db
- ログ: logs/<app_name>.log
- kill フラグ: data/kill.flag
- stop フラグ（スクリプト内で使用）: data/stop_requested.flag
- PID ファイル: data/execution.pid（設定で変更可能）

主要な環境変数（抜粋）
--------------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
- LOG_LEVEL（例: INFO）
- OPENAI_API_KEY（AI モジュール使用時）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、秒。デフォルト 60。0 以下や非整数は無視されデフォルトにフォールバック）
- PAPER_FILL_MODE（paper_trading の MockBroker の fill モード: instant|partial|never|reject）

使い方（起動・コマンド例）
------------------------
- 実行エンジン起動（常用）
  python -m kabusys.run_execution

  ペーパートレードで起動する例:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 監視プロセス起動（ポーリング）
  python -m kabusys.run_monitoring

  ポーリング間隔を変更する例（30 秒ごと）:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 設定ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  指定期間:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB を明示:
  python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db

- AI スコアリング／レジーム判定（ライブラリ API）
  Python REPL / スクリプト内から呼ぶ例:
    from kabusys.ai.news_nlp import score_news
    from kabusys.ai.regime_detector import score_regime
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    # news scoring
    score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
    # regime scoring
    score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")

停止・Kill Switch
----------------
- run_execution / run_monitoring はプロジェクト内の data/stop_requested.flag を検知すると安全に停止します（スクリプト内で定義）。
- Kill Switch（リスク基準を満たした場合）は data/kill.flag を書き込み、ExecutionEngine の停止トリガになります。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされますが、本番では 0 を推奨します。

ディレクトリ構成（主要ファイル）
------------------------------
以下は主要なソース配置の概要（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数／Settings
  - config_setup.py          — .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度設定
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル初期化・CRUD）
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — （trade 関連の監視ロジック）
    - risk_monitor.py        — ドローダウン等のリスク監視
    - kill_switch.py         — kill.flag 制御
    - alert_manager.py       — （通知管理）
  - execution/
    - execution_engine.py    — 実行エンジン本体
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）
    - regime_detector.py     — レジーム判定（OpenAI）
  - data/                    — データファイル（logs/, .env, sqlite/duckdb 等の配置先）
  - tools/
    - paper_verification_report.py

（実際のリポジトリは上記に加えてサブモジュールや追加ファイルが存在する可能性があります）

開発・運用上の注意
-----------------
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください（config_setup でも注意書きを出力します）。
- validate_config を使って必須の環境変数やパスを事前チェックしてください。特に KABUSYS_ENV=live での起動時は注意が必要です（LINE 通知設定や kill_flag の振る舞いなどの警告が出ます）。
- AI モジュールは OpenAI API を利用します。API の失敗に対してはリトライやフォールバックロジックが組まれていますが、API キーの扱いとコストに注意してください。
- ロギングは logs/<app>.log に日次ローテートで保存されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- MONITOR/EXECUTION の停止はフラグファイルによる制御と KeyboardInterrupt の双方に対応しています。

トラブルシューティング（簡易）
----------------------------
- .env が反映されない
  - プロジェクトルートが特定できない場合や自動ロードを無効化している場合があります。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数が設定されていないか確認してください。
  - 手動で環境変数をエクスポートするか、config_setup で .env を生成してください。

- DuckDB / SQLite のパスに関する警告
  - validate_config が「親ディレクトリが存在しない」と警告する場合がありますが、多くは起動時に自動作成されるため必ずしも致命的ではありません。必要なら事前にディレクトリを作成してください。

- OpenAI 関連のエラー
  - API key の設定確認（OPENAI_API_KEY）
  - レート制限や一時的なネットワーク障害はリトライ処理が行われます。繰り返し失敗する場合はログを確認してください。

ライセンス
----------
コード内に明示的なライセンスファイルがない場合は、リポジトリのルートにある LICENSE を確認してください。

お問い合わせ・貢献
-----------------
バグ報告や機能提案は Issue を立ててください。PR は歓迎します。コードのスタイル・テストを整備した上で提出してください。

以上で README の概要です。必要であれば「導入スクリプト例」「systemd ユニット例」「より詳細なディレクトリツリー」などを追記します。どの内容を重点的に詳述しますか？