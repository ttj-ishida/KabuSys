KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買フレームワーク（研究・ポートフォリオ構築・実行・監視・AI 補助）です。本リポジトリは以下の主要機能を持つモジュール群で構成されています。

- 実行エンジン（ExecutionEngine） — 発注・リスク管理・オーダー管理
- 監視（Monitoring） — システム状態、注文・リスク監視、Kill Switch
- ポートフォリオ構築（Portfolio） — 候補選定・重み付け・ポジションサイズ計算・セクター制限
- リサーチ（Research） — ファクター計算・将来リターン・IC 計算など
- AI モジュール — ニュースの NLP によるセンチメント評価、レジーム判定（OpenAI）
- ユーティリティ — ロギング設定、プロセス優先度設定、環境設定ウィザード等
- ツール — ペーパートレード検証レポート生成スクリプト 等

主な特徴
--------
- 環境変数 / .env による設定管理（config_setup.py による対話ウィザード）
- Production / Paper Trading の明確な分離（paper_trading 用 DB を利用）
- DuckDB を用いた時系列データ処理（リサーチ / AI のデータ取得）
- OpenAI（gpt-4o-mini 等）を用いたニュース NLP / マクロセンチメント（オプション）
- 監視コンポーネントによりプロセス停止・高負荷・ドローダウン等を検出し Kill Switch による安全停止
- 日次ローテートのログ（logs/<app>.log）を標準化して出力

前提条件 / 必要パッケージ
------------------------
推奨 Python バージョン: 3.10+

主要な外部依存（例）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（validate_config の YAML 検証を行いたい場合、必須ではない）

インストール例:
    python -m pip install duckdb psutil openai PyYAML

セットアップ手順
--------------
1. リポジトリをクローンする
    git clone <repo-url>
    cd <repo-root>

2. 仮想環境を用意（任意）
    python -m venv .venv
    source .venv/bin/activate

3. 依存パッケージをインストール
    pip install duckdb psutil openai PyYAML

4. 環境変数ファイル (.env) を作成
   - 対話式ウィザードで簡単に作成できます:
       python -m kabusys.config_setup
   - .env の主なキー:
       - JQUANTS_REFRESH_TOKEN (必須)
       - KABU_API_PASSWORD (必須)
       - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
       - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
       - SQLITE_PATH (デフォルト: data/monitoring.db)
       - KABUSYS_ENV (development | paper_trading | live)
       - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR)
       - KILL_FLAG_CLEAR_ON_START (0 | 1)

5. 設定検証（起動前チェック）
    python -m kabusys.validate_config
   --strict を付けると警告も FAIL 扱いになります。

6. データディレクトリ作成（必要なら）
    mkdir -p data logs

使い方
------

起動スクリプト
- 実行エンジン（Execution）
    - コマンド:
        python -m kabusys.run_execution
    - 概要:
        - KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用し paper_trading 用 DB（data/paper_trading.db など）に記録します。本番（live）では実際のブローカークライアントを利用します。
        - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
        - エンジンは別スレッドで実行され、stop フラグ検出時にエンジン.stop() を呼び停止します。
        - 実行時に PID ファイルを data/execution.pid 等に出力します（Settings で変更可能）。

- 監視ループ（Monitoring）
    - コマンド:
        python -m kabusys.run_monitoring
    - 概要:
        - SystemMonitor をポーリングし、MonitoringDB（SQLite）へ記録・各種 Monitor を動かします。
        - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可（デフォルト 60 秒）。
        - 監視は常に本番用 sqlite_path を参照（KABUSYS_ENV にかかわらず）。
        - data/stop_requested.flag の存在を検知するとループを終了します。

停止 / Kill Switch
- KillSwitch（kabusys.monitoring.kill_switch）はリスク条件（例: ドローダウン超過、ポジション上限超過）を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
- 手動で停止させる方法:
    - data/stop_requested.flag を作成すると run_execution / run_monitoring のループが検知して終了します。
    - kill.flag を手動で書くと KillSwitch を使う仕組みが反応します（Execution 側が kill.flag の存在を確認する設計）。

ログ
- ログはデフォルトで logs/<app_name>.log に日次ローテートで保存されます（logs ディレクトリを作成してください）。
- ログ設定は kabusys.utils.logging_setup.setup_logging から全アプリで共通化されています。
- 環境変数 LOG_DIR でログディレクトリを指定可能。

ツール
- Paper Trading 検証レポート:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで SQLite パスを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH でも可）。
  出力は稼働率・注文成功率・レイテンシ等の集計と PASS/FAIL 判定です。

AI 機能
- kabusys.ai.news_nlp.score_news: raw_news を集約して OpenAI に投げ、銘柄ごとの ai_score を ai_scores テーブルへ保存します。OPENAI_API_KEY が必要です。
- kabusys.ai.regime_detector.score_regime: ETF（1321）MA とマクロニュースセンチメントを合成して market_regime テーブルを更新します。こちらも OPENAI_API_KEY が必要。

環境変数の注意点
- 自動ロード:
  - プロジェクトルートに .env / .env.local があれば自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- 重要な変数:
  - KABUSYS_ENV: development / paper_trading / live（必須値チェックあり）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 必須
  - OPENAI_API_KEY: AI 機能を使う際に必要
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
  - PAPER_FILL_MODE: paper_trading の MockBroker 動作（instant|partial|never|reject）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（default: data/paper_trading.db）
  - DUCKDB_PATH / SQLITE_PATH: DB パスの上書き

ディレクトリ構成（主要ファイル）
-----------------------------
プロジェクトルート（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照)
  - execution/               — Execution 関連（Engine, OrderManager, BrokerFactory, 等）
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

その他ルートディレクトリ（運用上の慣例）
- .env (プロジェクト固有の環境変数。絶対に Git にコミットしないこと)
- config/ (config YAML ファイル群: system_config.yaml 等)
- data/ (SQLite / PID / flag ファイル を配置: data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag, data/execution.pid)
- logs/ (ログファイルを保存)

運用上の注意
------------
- .env は機密情報を含むため必ず .gitignore に入れてください（config_setup でも注意文を出しています）。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 1 にしないでください（安全上の理由）。
- OpenAI を使う機能は外部 API 呼び出しに依存するため、ネットワーク障害や API 制限に備えてフェイルセーフ（フォールバック値）を実装していますが、使用時は API キー管理・コストに注意してください。
- DuckDB / SQLite のパスは .env で指定できます。バックアップと定期メンテナンスを推奨します。

開発者向けメモ
---------------
- ログ設定は kabusys.utils.logging_setup.setup_logging を各エントリから呼び出して統一してください。
- モジュールはできるだけ副作用を避け、テストしやすい純粋関数（portfolio / research 等）と I/O を担う層（DB、Broker）を分離しています。
- validate_config は YAML のパース検証に PyYAML を利用します（未インストール時は検証スキップ）。

お問い合わせ / 貢献
------------------
不具合報告・改善提案は Issue を作成してください。プルリクエストは歓迎します。README の補足や運用手順の改善なども大歓迎です。

---  
この README はコードベースの現状に基づいて作成しています。実行スクリプトや設定の詳細は各モジュールの docstring を参照してください。