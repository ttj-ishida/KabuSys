KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。本リポジトリは以下の主要コンポーネントを備えます。

- ExecutionEngine: 注文発行・リスク管理・約定調整を行う実行エンジン
- Monitoring: システム稼働状況・注文ログ・リスク指標の監視とアラート / Kill Switch
- Research / Portfolio: ファクター計算、銘柄選定、配分・ポジションサイジング
- AI 補助: ニュースの NLP スコアリング・市場レジーム判定（OpenAI 利用）
- CLI ユーティリティ: .env ウィザード、設定検証、ペーパートレード検証レポート生成等

特徴
----
- 起動スクリプトでプロセス優先度を設定し、監視/実行処理をデーモン的に運用可能
- Paper trading（KABUSYS_ENV=paper_trading）時は本番 DB と分離して動作
- DuckDB を用いた研究用分析レイヤ（prices_daily / raw_financials など参照）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価・レジーム判定（任意）
- SQLite（監視・トレードログ）を用いた永続化とマイグレーション対応
- kill.flag による安全な外部停止（Kill Switch）運用

必要条件
----
- Python 3.10+
- 必須ライブラリ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- 任意 / 推奨:
  - PyYAML（config/*.yaml の内容検証で使用）
- データベース: DuckDB（ファイル指定）および SQLite（ファイル指定）を利用（ファイルは自動作成されます）

例: 仮想環境作成とパッケージのインストール
- macOS / Linux
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil openai pyyaml

セットアップ手順
----
1. リポジトリをクローンする
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境を用意して依存ライブラリをインストールする（上記参照）

3. .env の用意
   - 対話式ウィザード: python -m kabusys.config_setup
     - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須
     - KABUSYS_ENV: development | paper_trading | live
   - あるいは手動で .env を作成（.env.example を参照して設定）

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いで exit(1)

5. データディレクトリ
   - デフォルトでは data/ 以下に DB（data/monitoring.db / data/kabusys.duckdb 等）や
     フラグファイルを置きます。必要に応じて .env でパスを変更してください。

主要環境変数（主なもの）
----
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — 動作モード
- DUCKDB_PATH (例: data/kabusys.duckdb)
- SQLITE_PATH (例: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB)
- PAPER_FILL_MODE (paper_trading の約定挙動: instant | partial | never | reject)
- OPENAI_API_KEY (AI 機能利用時)
- LOG_LEVEL, LOG_DIR
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか: 0 / 1)

使い方（起動・ユーティリティ）
----
- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話形式で生成 / 更新します

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60）
  - 監視は常に本番 sqlite_path を用いる設計です（環境にかかわらず）

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、data/paper_trading.db に記録
  - 起動前に data/stop_requested.flag が存在すると起動せず終了します
  - 実行中に stop flag を検知すると安全停止処理を行います

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db <path> （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をプログラムから呼び出して利用

停止 / Kill Switch / フラグ
----
- run_monitoring / run_execution はプロジェクト直下の data/stop_requested.flag を監視しており、
  ファイル存在でループを抜けます（安全停止）。
- Kill Switch: KillSwitch は data/kill.flag を作成して ExecutionEngine を停止させる仕組みです。
  - KillSwitch が発動すると .flag ファイルに理由を記載して生成します
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動的に kill.flag をクリアします（開発用、注意）
- PID ファイル: 実行エンジンは data/execution.pid を使用します

ログ
----
- ログはコンソール出力（stdout）と日次ローテートファイル出力（logs/<app_name>.log）に出力されます
- ログ設定は kabusys.utils.logging_setup.setup_logging で一元管理
- LOG_DIR 環境変数や引数でログディレクトリを指定可能

ディレクトリ構成（主要ファイル）
----
以下はコードベースの主要ファイル／モジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / 設定読み込みロジック
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 設定検証 CLI
  - run_monitoring.py      — Monitoring ポーリングループ起動スクリプト
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py     — ロギング設定ユーティリティ
    - process_priority.py  — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py     — SQLite 永続化レイヤ（テーブル作成・CRUD）
    - system_monitor.py     — システム状態／データ鮮度監視
    - trade_monitor.py      — （注文ログ監視, ソース参照）
    - risk_monitor.py       — ドローダウン・ポジション数監視
    - monitoring_engine.py  — 各 Monitor をまとめるポーリングエンジン
    - kill_switch.py        — kill.flag 管理
    - alert_manager.py      — （アラート送信管理: LINE 等、実装ファイル参照）
  - execution/              — Execution 関連（Engine / OrderManager / BrokerFactory 等）
  - portfolio/
    - portfolio_builder.py  — 候補選定・重み計算
    - position_sizing.py    — 株数決定・キャップ適用
    - risk_adjustment.py    — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py    — Momentum / Value / Volatility 計算（DuckDB）
    - feature_exploration.py— 将来リターン・IC・統計集計
  - ai/
    - news_nlp.py           — ニュースの NLP スコアリング（OpenAI）
    - regime_detector.py    — 市場レジーム判定（MA + マクロ NLP）
  - data/                   — 実行時に使用する DB / フラグ類（data/monitoring.db など）

注意事項 / トラブルシューティング
----
- Python バージョン: 型注釈（|）を多用しているため Python 3.10 以上を推奨します。
- psutil によるプロセス優先度設定は OS と権限に依存します（Windows と POSIX で実装差異あり）。
  権限不足で設定できない場合は警告を出して続行します。
- OpenAI API を利用する機能はネットワーク・API 利用制限に左右されます。キーやレート制限に注意してください。
- validate_config は PyYAML がない場合、YAML 検証をスキップします（警告表示）。
- DuckDB / SQLite のファイルパスはデフォルトで data/ 以下を使用します。必要なら .env で上書きしてください。
- 監視（monitoring）は監査・安全用に常に本番の monitoring.db を使用する設計です（実行コンテキストに依存しない）。

貢献 / 拡張ポイント
----
- BrokerClient の実装を追加して実際の発注連携を行う（kabuステーション等）
- alert_manager を実装して LINE / Slack などへの通知を行う
- strategy / execution のアルゴリズム拡張（新しいファクター、リスク制御）
- 単体テスト・CI を整備して各モジュールの堅牢化

最後に
----
まずは python -m kabusys.config_setup で .env を作成し、python -m kabusys.validate_config で設定検証を行ってください。paper_trading モードで動作を確認したのち、実運用（KABUSYS_ENV=live）への移行を検討してください。

必要であれば README を英語版や詳細な運用手順（デプロイ、systemd / Supervisor / コンテナ化、バックアップ方針など）に拡張できます。ご希望があれば続けて作成します。