# KabuSys

日本株向け自動売買システムの一部（ライブラリ／起動スクリプト・監視・解析ツール群）。

以下はこのコードベースの README（日本語）。起動方法や主要コンポーネント、ディレクトリ構成、セットアップ手順をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関する内部ライブラリ群と起動スクリプト、監視・解析ツールを提供します。主な機能は次のとおりです。

- ExecutionEngine：注文の作成・管理・執行（paper_trading モード時は MockBrokerClient を使用し、発注は専用のペーパートレード DB に記録）
- Monitoring：システム状態・取引状態・リスク監視、Kill Switch による安全停止
- Research / AI：ファクター計算、リターン計算、ニュースを用いた LLM ベースのセンチメント評価、レジーム判定
- Portfolio：銘柄選定・重み付け・ポジションサイズ計算（純粋関数群）
- ユーティリティ：ロギングセットアップ、プロセス優先度設定、設定ファイル読み込みウィザード、設定検証 CLI
- ツール：ペーパートレード検証レポート生成スクリプト 等

設計上の特徴：
- .env ファイルまたは環境変数から設定を読み込む（自動ロードを行う。ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
- 実行環境は KABUSYS_ENV（development / paper_trading / live）で切替
- DuckDB を分析用データベース、SQLite を監視・注文履歴用 DB として利用
- OpenAI API を使ったニュース NLP 機能を含む（API キー必須）

---

## 機能一覧（概要）

- 起動スクリプト
  - run_execution.py：ExecutionEngine の起動（KABUSYS_ENV による挙動差分あり）
  - run_monitoring.py：SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）

- 設定関連
  - config_setup.py：.env の対話式作成／更新ウィザード
  - validate_config.py：起動前の設定検証 CLI（必須環境変数・パス・YAML ファイル存在チェック等）

- 監視（monitoring）
  - monitoring_db.py：監視用 SQLite のスキーマ初期化・読み書き API
  - system_monitor.py：CPU/メモリ/ディスク・データ鮮度・実行プロセス存在チェック
  - trade_monitor.py / risk_monitor.py / kill_switch.py / monitoring_engine.py：取引状態・リスク監視、Kill Switch 評価、アラート連携

- 実行（execution）
  - execution_engine, order_manager, order_repository, reconciler, risk_manager 等（注文処理の中核。実装は別ファイル群）

- ポートフォリオ関連（純粋関数）
  - portfolio_builder.py / position_sizing.py / risk_adjustment.py：候補選定、重み計算、ポジションサイズ算出、セクター制限、レジーム乗数

- 解析・研究（research）
  - factor_research.py：モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB ベース）
  - feature_exploration.py：将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（OpenAI）
  - news_nlp.py：ニュースをまとめて LLM に投げ、銘柄別センチメントスコアを ai_scores テーブルへ書き込む
  - regime_detector.py：ETF の MA 乖離とマクロニュースセンチメントを合成して日次レジーム判定

- ツール
  - tools/paper_verification_report.py：ペーパートレード結果の検証レポート生成

- ユーティリティ
  - utils/logging_setup.py：統一ログ設定（コンソール + 日次ローテートファイル）
  - utils/process_priority.py：プロセス優先度 / CPU affinity 設定

---

## 必要条件（概略）

- Python 3.9+（型注釈や一部の機能を想定）
- 必須ライブラリ（代表例）:
  - duckdb
  - psutil
  - openai (AI 機能を使用する場合)
  - PyYAML（config の YAML 検証を行いたい場合）
- SQLite（Python 組み込みモジュール）
- ネットワークアクセス（kabuステーション API / J-Quants / OpenAI を使う場合）

（実際の requirements.txt はこのリポジトリに含めることを推奨します。ここでは主要依存のみ列挙しています。）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <project-root>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

   （プロジェクトで requirements.txt を用意している場合は `pip install -r requirements.txt` を使用してください）

4. .env の作成
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに `.env` を作成（例に沿って以下を設定）
     - 必須:
       - JQUANTS_REFRESH_TOKEN
       - KABU_API_PASSWORD
     - 推奨 / オプション:
       - KABUSYS_ENV (development | paper_trading | live)
       - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
       - SQLITE_PATH (デフォルト: data/monitoring.db)
       - PAPER_TRADING_SQLITE_PATH (ペーパートレード専用 DB)
       - LOG_LEVEL, LOG_DIR, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
       - OPENAI_API_KEY（AI 機能を利用する場合）

   - 自動ロードの注意:
     - デフォルトで .env / .env.local は自動で読み込まれます（config.py）。
     - 自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 設定検証（起動前に必須）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります:
     - python -m kabusys.validate_config --strict

6. DB 初期化
   - 実行スクリプト（run_monitoring / run_execution）は起動時に必要なテーブルを作成します（init_monitoring_db を呼ぶ）。

---

## 使い方（主要コマンド）

- ExecutionEngine 起動（実際に注文を出す/ペーパートレードを行う）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
    - 実行中は data/execution.pid に PID が書かれます
    - data/stop_requested.flag が作成されると起動スクリプトはエンジンを停止します

- Monitoring 起動（SystemMonitor のポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト: 60）
  - 重要:
    - Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path（SQLITE_PATH）を使用します（監視データは本番 DB を参照／書込）
  - 停止:
    - data/stop_requested.flag を置くとループを抜けます

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定:
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数の代わりに指定可能）

- AI 機能（ライブラリ利用）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY）
  - ニュースのスコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)
    - 引数 conn は DuckDB 接続（kabusys の DuckDB path を使って接続）

  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)

- Research / Factor 計算（ライブラリ利用）
  - DuckDB 接続を渡して関数呼び出し：
    - from kabusys.research import calc_momentum, calc_volatility, calc_value
    - calc_momentum(conn, date_obj) など

---

## 運用上の注意点

- KABUSYS_ENV の値は "development", "paper_trading", "live" のいずれか。live は本番のため慎重に設定すること。
- validate_config.py を本番起動前に必ず実行し、エラーや警告を確認すること。
- Kill Switch:
  - KillSwitch は risk_monitor 等の判定により data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - Settings.kill_flag_clear_on_start が 1 の場合、起動時に自動クリアされるため本番では 0 を推奨。
- ログ:
  - logs/<app_name>.log に日次ローテーションでログが出力されます（utils.logging_setup で設定）。
- DB の分離:
  - paper_trading モード時は paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番データと分離します。
  - ただし Monitoring は常に sqlite_path（監視 DB）を使用する点に注意。

---

## ディレクトリ構成

（プロジェクトルート直下に src/kabusys がある想定。重要なファイル・モジュールを示します）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト

  - execution/                — Execution 関連（Engine、OrderManager、BrokerFactory 等）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
    (※実装ファイル群は本リポジトリ内の該当ディレクトリを参照)

  - monitoring/
    - monitoring_db.py        — 監視用 SQLite テーブル定義・永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py

  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py

  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py       — レジーム判定（MA + マクロ NLP）
    - __init__.py

  - monitoring/                — （上記と重複）監視機能群

  - utils/
    - logging_setup.py         — 共通ログ設定
    - process_priority.py      — プロセス優先度 / CPU affinity 設定
    - __init__.py

  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート

- data/                        — デフォルト DB / flag / pid 等（実行時に作成される）
  - kabusys.duckdb (デフォルト DUCKDB_PATH)
  - monitoring.db (デフォルト SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - execution.pid
  - kill.flag
  - stop_requested.flag

- logs/                        — ログ出力先（デフォルト）

---

## 参考例（よくある作業フロー）

1. 開発環境でセットアップ:
   - 仮想環境作成 → パッケージインストール → python -m kabusys.config_setup
   - python -m kabusys.validate_config

2. ペーパートレード実行（安全に動作確認）:
   - export KABUSYS_ENV=paper_trading
   - python -m kabusys.run_execution
   - 別ターミナルで python -m kabusys.run_monitoring

3. ペーパートレードの検証:
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

4. AI を使ったレジーム判定（スクリプトまたは REPL）:
   - from kabusys.ai.regime_detector import score_regime
   - import duckdb, datetime
   - conn = duckdb.connect("data/kabusys.duckdb")
   - score_regime(conn, datetime.date(2026, 4, 12))

---

## 最後に（運用上の注意まとめ）

- 本番（KABUSYS_ENV=live）で稼働させる場合は、必須環境変数・LINE 通知設定・ログ周り・Kill Switch 設定を十分に確認してください。
- validate_config.py を起動前チェックに組み込み、--strict モードは本番デプロイ前の必須手順として扱うことを推奨します。
- AI（OpenAI）機能は API 呼び出し・レート制限に依存するため、リトライやフェイルセーフ（失敗時ゼロフォールバック）が実装されていますが、運用環境では API キー管理とコストに注意してください。

---

必要があればこの README をプロジェクトの実際のファイル構成・要件に合わせて調整します（例: requirements.txt の内容、実際の実装ファイル名の追加など）。