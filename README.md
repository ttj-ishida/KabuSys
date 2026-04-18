# KabuSys

日本株向け自動売買システム（ライブラリ + 実行スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注実行・監視・研究ツールを含む自動売買プラットフォームの一部実装です。各モジュールは可能な限り副作用を避けて設計されており、環境変数や .env による設定で挙動を切り替えます。

バージョン: 0.1.0（src/kabusys/__init__.py）

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要スクリプト / コマンド）
- 環境変数（主要項目）
- ファイル / ディレクトリ構成

---

プロジェクト概要
- 各種モジュール群を提供：
  - strategy/research: ファクター計算・特徴量解析
  - portfolio: 候補選定・重み計算・ポジションサイズ算出・セクター上限適用
  - execution: 発注エンジン（モック/実ブローカー切替）、注文管理、リスク管理（実装ファイルは一部省略）
  - monitoring: システム稼働監視、注文監視、リスク監視、Kill Switch（停止フラグ）
  - ai: OpenAI を使ったニュース NLP / レジーム判定
  - tools: Paper Trading の検証レポート生成などユーティリティ
- SQLite / DuckDB を用いた永続化（監視 DB・分析 DB）
- 環境変数 / .env による設定管理（対話式ウィザード、検証ツールあり）
- ロギングは統一的に設定（コンソール + 日次ローテートファイル）

---

主な機能一覧
- run_execution: ExecutionEngine（発注エンジン）起動スクリプト
  - KABUSYS_ENV による paper_trading（モック）/ live 切替
  - paper_trading は専用 SQLite（data/paper_trading.db）へ記録して本番 DB と分離
- run_monitoring: SystemMonitor ポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能
  - 監視結果は monitoring DB（SQLite）へ永続化
- monitoring.*:
  - SystemMonitor: CPU/メモリ/ディスク/プロセス稼働・データ鮮度チェック
  - TradeMonitor / RiskMonitor: 注文滞留・成立異常・ドローダウン・ポジション上限監視
  - KillSwitch: 条件に応じて data/kill.flag を作成し ExecutionEngine を停止
  - MonitoringDB: 監視用の SQLite テーブル作成と読み書きユーティリティ
- portfolio.*:
  - 候補選定、等額・スコア加重配分、リスクベースのポジションサイズ計算、セクター制限、レジーム乗数
- research.*:
  - ファクター計算（モメンタム/ボラティリティ/バリュー）、将来リターン、IC 計算、統計サマリー
  - DuckDB を用いた SQL ベースの高速処理
- ai.*:
  - news_nlp: ニュースを LLM（OpenAI）でスコア化し ai_scores テーブルへ書き込み
  - regime_detector: ETF (1321) の MA200 とマクロニュースで市場レジーム判定
- tools.paper_verification_report:
  - Paper Trading の稼働率・注文成功率・レイテンシ等を集計し PASS/FAIL レポートを出力

---

セットアップ手順（開発環境向け）
1. Python (3.10+) を用意
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - optional: PyYAML（config/*.yaml の検証を有効にする場合）
     - pip install pyyaml
4. プロジェクトルートに移動（pyproject.toml または .git がある場所）
5. 初期 .env を作成
   - 対話式ウィザードを使う: python -m kabusys.config_setup
   - あるいは .env.example を参考に手動で .env を作成
6. 設定の検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）
7. データディレクトリの作成（必要なら）
   - デフォルトでは data/ に DB / pid / フラグ等を置く

注意: OpenAI を使用する機能（ai モジュール）を利用する場合は環境変数 OPENAI_API_KEY を設定してください。

---

使い方（主要コマンド例）

1. 環境設定ウィザード（.env を作成 / 更新）
   - python -m kabusys.config_setup
   - 対話式に値を入力して .env を保存します

2. 設定検証
   - python -m kabusys.validate_config
   - 出力にエラー/警告/INFO が表示されます

3. ExecutionEngine を起動（発注エンジン）
   - 本番（KABUSYS_ENV=live）:
     - 環境変数を設定後: python -m kabusys.run_execution
   - ペーパートレード（KABUSYS_ENV=paper_trading）:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     - この場合 MockBrokerClient を用い、データは data/paper_trading.db（デフォルト）へ記録されます
   - 停止方法:
     - data/stop_requested.flag を作成すると順次終了します（スクリプトは起動時に stop flag を確認）

4. Monitoring を起動（ポーリングループ）
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数で間隔を秒単位で上書き可能（デフォルト 60）
   - Monitoring は常に本番 sqlite_path（SQLITE_PATH）を使用

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db を使って別 DB を指定可能。デフォルトは data/paper_trading.db

6. AI 系処理（ニューススコアリング / レジーム判定）
   - 必要: OPENAI_API_KEY を設定
   - 直接モジュール経由で呼ぶ例（スクリプトは含まれていないため、アプリケーション側から呼び出す）:
     - from kabusys.ai.news_nlp import score_news
     - score_news(duckdb_conn, target_date, api_key="...")

ログ出力
- デフォルトログディレクトリ: logs/
- 各アプリケーション名ごとに日次ローテーションされたファイルが作られます（例: logs/execution.log, logs/monitoring.log）
- ログレベルは .env の LOG_LEVEL で指定（デフォルト INFO）

停止 / Kill Switch について
- KillSwitch は監視モジュールが DRAWDOWN 等の条件を満たすと data/kill.flag を作成します
  - ExecutionEngine 起動時は Settings.kill_flag_clear_on_start に応じクリアする挙動あり（本番は 0 推奨）
- 手動停止用の stop flag:
  - data/stop_requested.flag を作成すると run_monitoring/run_execution のループが検出して順次停止します

---

主要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
- 環境/動作
  - KABUSYS_ENV: execution モード（development / paper_trading / live） — デフォルト development
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- データパス
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- Paper Trading
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト "instant"）
- OpenAI
  - OPENAI_API_KEY: OpenAI API キー（ai/news_nlp, ai/regime_detector で使用）
- ログ / PID / Kill
  - LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）
  - PID_FILE_PATH: ExecutionEngine が使用する pid ファイル（デフォルト data/execution.pid）
  - KILL_FLAG_PATH: Kill Switch が書き込むパス（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill flag を自動クリアするか（"1" で有効、本番は "0" を推奨）

設定の自動読み込み
- プロジェクトルート（.git または pyproject.toml がある場所）を起点として .env と .env.local を自動読み込みします
- OS 環境変数が優先され、.env.local は .env の値を上書きできます
- 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

ディレクトリ構成（主要ファイル抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py       — ログセットアップ
    - process_priority.py    — プロセス優先度 / affinity
  - monitoring/
    - monitoring_db.py       — SQLite 用永続化レイヤ
    - system_monitor.py
    - trade_monitor.py       — （本 README のコード抜粋では一部省略）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信ロジック、コード抜粋では省略）
  - execution/               — Execution 関連（broker_factory, engine 等）
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
  - tools/
    - paper_verification_report.py

サンプルツリー（省略表現）
- .env
- data/
  - monitoring.db
  - paper_trading.db
  - execution.pid
  - kill.flag
  - stop_requested.flag
- logs/
  - execution.log
  - monitoring.log
- src/
  - kabusys/...

---

設計上の注意点 / 運用上のヒント
- 設定検証ツール（validate_config）は起動前チェックに便利です。--strict を使うと警告も失敗として扱えます。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0（無効）にしておくことを推奨します。自動クリアを有効にすると Kill Switch の保護が弱まります。
- paper_trading モードは本番 DB と隔離されるため、発注ロジックやデータの影響を完全に分離して検証できます。
- OpenAI を利用する箇所は API 利用料金・レート制限に注意してください。news_nlp, regime_detector はリトライ・フォールバック設計がなされていますが、API キーの管理は厳重に行ってください。
- ログディレクトリの作成に失敗するとファイル出力はスキップされますが、コンソール出力は残ります。CI/監視環境では logs/ の書き込み権限を確認してください。

---

貢献 / 開発
- クローン後、仮想環境を作成して依存をインストールし、config_setup → validate_config → run_monitoring/run_execution の順で動作確認してください。
- DB スキーマ変更時は monitoring_db.init_monitoring_db にマイグレーションロジックを追記してください（既存コードは幾つかの互換性チェックを含みます）。

---

問い合わせ / 参考
- コード内の docstring・コメントに設計意図や利用法が記載されています。各モジュールの関数 docstring を参照してください。

以上

--- 

（README は実装の抜粋から作成しています。実行前に config_setup や validate_config を使って環境変数・ファイルパスを確認してください。）