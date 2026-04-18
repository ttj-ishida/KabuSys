KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。主な目的は
- 日次の銘柄選定・ポジションサイズ計算（ポートフォリオ構築）
- 発注・注文管理（ExecutionEngine）
- システム運用監視（Monitoring）
- 研究用ファクター計算・特徴量解析（DuckDB を使用）
- ニュースを用いた AI（LLM）ベースのセンチメント評価および市場レジーム判定
を統合的に提供することです。

主な特徴
--------
- ExecutionEngine：実際のブローカー／モックを選択して発注を管理（KABUSYS_ENV=paper_trading でペーパートレード）
- Monitoring：CPU/メモリ/ディスク、データ鮮度、注文状態、ドローダウン等を定期的に記録・評価
- Kill Switch：監視結果に応じた停止フラグの書き込み（ExecutionEngine 停止トリガ）
- Portfolio construction：候補選定、重み付け、ポジションサイズ計算、セクター上限、レジーム乗数などの純粋関数群
- Research：DuckDB 上でモメンタム、ボラティリティ、バリュー等のファクター算出、将来リターン・IC 計算
- AI モジュール：OpenAI（gpt-4o-mini 等）を使ったニュースのセンチメント計算、マクロニュースによるレジーム判定
- ツール：Paper Trading の検証レポート生成スクリプト等
- 設定支援：対話式 .env 生成（config_setup）と起動前検証 CLI（validate_config）

依存（主要）
--------------
（実行環境に応じてインストールしてください）
- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml の内容チェックを行う場合に必要）
- （その他、ブローカー実装や追加ユーティリティに依存する場合があります）

セットアップ手順
----------------
1. リポジトリを取得
   - git clone ... / またはアーカイブを展開

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （将来的に requirements.txt がある場合は pip install -r requirements.txt）

4. 必要ディレクトリを作成
   - data/ と logs/ がデフォルトで使用されます。自動的に作成されますが、手動で作る場合:
     - mkdir -p data logs

5. 環境変数（.env）の準備
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
     - ウィザードは .env を作成/更新します（.env は決して Git にコミットしないこと）
   - もしくは .env を手動で作成し、下記の主要環境変数を設定してください（例）:
     - JQUANTS_REFRESH_TOKEN=your_token_here
     - KABU_API_PASSWORD=your_password_here
     - KABUSYS_ENV=development | paper_trading | live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db  (paper_trading 用)
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=sk-...

6. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）

使い方（起動・主なコマンド）
---------------------------
- ExecutionEngine（売買エンジン）起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在すると起動しません（停止フラグ）。
    - ExecutionEngine の PID は data/execution.pid に書き出されます。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（デフォルト 60 秒）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - Monitoring は KABUSYS_ENV に関係なく本来の sqlite_path（SQLITE_PATH）を使用して監視 DB を初期化/書き込みします。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db で指定するか環境変数 PAPER_TRADING_SQLITE_PATH を参照

- 設定ウィザード / 検証
  - .env 作成: python -m kabusys.config_setup
  - 検証: python -m kabusys.validate_config [--strict]

運用メモ / フラグ・停止方法
-------------------------
- ExecutionEngine の停止
  - 監視モジュールや外部から Kill Switch（data/kill.flag）を書き込むと ExecutionEngine 停止のトリガになります。
  - 手動で停止したい場合は data/kill.flag を作成してください（中身は理由テキストでも可）。
  - run_execution/run_monitoring は data/stop_requested.flag を監視しており、存在すると起動ループを終了します（stop flag と kill.flag は別物で用途が異なる点に注意）。

- ログ
  - デフォルトで logs/<app_name>.log に日次ローテートでログが保存されます（app_name は "execution" / "monitoring" 等）。
  - ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一されています。
  - ログレベルは環境変数 LOG_LEVEL で調整可能（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

主要な環境変数一覧（抜粋）
--------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live) デフォルト development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- LOG_LEVEL (デフォルト: INFO)
- OPENAI_API_KEY（AI モジュール利用時に必要）
- MONITOR_POLL_INTERVAL（監視ポーリング秒、デフォルト 60）
- PAPER_FILL_MODE（paper_trading の MockBrokerClient の約定挙動: instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START（本番での自動クリアは推奨されない）
- PID_FILE_PATH / KILL_FLAG_PATH（パスは Settings 経由でカスタム可能）

ディレクトリ構成（抜粋）
----------------------
リポジトリの主要構成（src/kabusys 以下を中心に）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度・CPU affinity
  - execution/               — 発注・注文管理関連（BrokerFactory, Engine, OrderManager, Reconciler, RiskManager 等）
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ・永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py     — 市場レジーム判定
  - data/ （実行時に作成される想定）
  - logs/ （ログ保存ディレクトリ）

設計上の注意点
--------------
- Monitoring は KABUSYS_ENV に関係なく監視用の本番 sqlite_path を使用します（監視は実行環境に依存せず本番DBを監視する意図のため）。
- ExecutionEngine は paper_trading 環境であれば paper_trading 用の専用 SQLite DB を使用して本番 DB と分離します。
- AI モジュール（news_nlp / regime_detector）は OpenAI API を用います。API キーが未設定のときは明示的にエラーを出すかフェイルセーフでスキップする設計です（関数による）。
- DuckDB はリサーチ系（prices_daily, raw_financials, raw_news など）で SQL を用いた高速集計に利用します。
- .env の自動ロード機能があり、プロジェクトルートに .env / .env.local を置くことで環境変数を補完します。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑止できます。

開発・拡張のヒント
-------------------
- モジュール設計は「ビジネスロジックを持たない永続層」「純粋関数群」「IO を含むエンジン/監視」の分離を意識しています。単体テストは純粋関数（portfolio/*, research/*）から整備すると効果的です。
- OpenAI 呼び出し部分はテストで差し替えやすいよう _call_openai_api をラップしています。unittest.mock で差し替えてテスト可能です。
- DuckDB のスキーマや CSV インポートを整備すると研究用ワークフロー（ファクター算出・特徴量探索）がスムーズになります。

サポート／問い合わせ
--------------------
この README はコードベースの概要と基本的な運用手順をまとめたものです。実行時の詳細ログや validate_config の出力を参照して設定不備を解消してください。質問や改善提案があれば Issue を立ててください。

（以上）