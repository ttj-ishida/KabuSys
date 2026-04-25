README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のプロトタイプです。  
本リポジトリには、以下の主要コンポーネントが含まれます:

- ExecutionEngine: 発注・注文管理・リスク管理を行う実行エンジン
- Monitoring: システム稼働状況・注文状態・リスク指標を定期監視してアラート/Kill Switch を発動
- Research: DuckDB を使ったファクター計算・特徴量解析
- AI モジュール: ニュースセンチメント評価 / レジーム判定（OpenAI を利用）
- Portfolio: 銘柄選定・ウェイト計算・ポジションサイズ計算の純粋関数群
- ツール群: 環境設定ウィザード、設定検証、Paper Trading 検証レポート生成 等

特徴一覧
--------
- 環境変数/.env を使った柔軟な設定管理（.env と .env.local 自動ロード）
- Execution と Monitoring を別プロセスで分離（PID / フラグファイルによる制御）
- Paper Trading モード（KABUSYS_ENV=paper_trading）では Mock ブローカーと専用 DB を使用し、本番 DB と完全分離
- DuckDB を用いた高速なリサーチ（prices_daily / raw_financials などを想定）
- OpenAI を用いたニュース NLP（バッチ処理、リトライ/バリデーション実装済）
- 監視 DB（SQLite）用の永続化層とマイグレーション処理
- 監視レポート生成ツール（Paper Trading 検証レポート）

前提 / 要件
-----------
最低限の実行環境（例）
- Python 3.10+
- pip
- SQLite（標準ライブラリ）
- 主要 Python パッケージ（インストール手順参照）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config.yaml の検証を行う場合、なくても動作するが検証はスキップされる）
- ネットワーク: OpenAI API を使う場合は API キーが必要

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

4. 環境変数 / .env の準備
   - 対話式ウィザードで .env を作る:
     - python -m kabusys.config_setup
   - またはテンプレート（.env.example）がある場合はコピーして編集

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も厳密に扱う場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリ作成（必要に応じて）
   - デフォルトの SQLite / DuckDB パスは data/ 配下なので、必要に応じてディレクトリを作成します（logging は logs/）。

使い方
------
主要な実行 / ツールの例

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- ExecutionEngine 起動
  - python -m kabusys.run_execution
    - KABUSYS_ENV が paper_trading に設定されている場合、MockBrokerClient が使われ、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録されます
    - 起動時に data/stop_requested.flag が立っていると起動せず終了
    - 実行中に stop フラグを書けば安全に停止できます（Monitoring の KillSwitch 等と連携）

- Monitoring 起動
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（SQLITE_PATH）を使用します（監視は本番 DB を参照するため）
    - 停止フラグ（data/stop_requested.flag）を監視しており、存在するとループを終了します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - データベースパスを明示する場合:
    - --db path/to/paper_trading.db

- AI 関連（ニューススコア / レジーム判定）
  - OpenAI API キーを環境変数 OPENAI_API_KEY に設定するか、該当関数に api_key を渡して実行
  - 例: kabusys.ai.score_news(conn, target_date, api_key=...)
  - 注意: AI モジュールは API 呼び出し時にリトライ・結果バリデーションを実装しているが、API キー未設定時は ValueError

環境変数（主なもの）
-------------------
※ .env で管理します。自動ロードはプロジェクトルートの検出に基づき行われます（.env / .env.local）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

必須
- JQUANTS_REFRESH_TOKEN : J-Quants API 用トークン（必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）

主要（デフォルト値あり）
- KABUSYS_ENV : 実行環境 (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH : data/kabusys.duckdb
- SQLITE_PATH : data/monitoring.db
- PAPER_TRADING_SQLITE_PATH : data/paper_trading.db
- LOG_LEVEL : INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY : OpenAI を使用する場合に必要
- PAPER_FILL_MODE : paper_trading の fill 動作 (instant | partial | never | reject) — デフォルト instant
- MONITOR_POLL_INTERVAL : run_monitoring で上書き可能（秒）

ファイル / フラグ
- PID ファイル: data/execution.pid（デフォルト、Settings.pid_file_path で変更可）
- Kill Flag: data/kill.flag（Settings.kill_flag_path、KillSwitch が書き込む）
- Stop フラグ: data/stop_requested.flag（run_* スクリプトはこれを監視して安全終了）

ログ
---
- デフォルトでコンソール（stdout）とファイル（logs/<app_name>.log）に出力されます
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一
- LOG_DIR / LOG_LEVEL で挙動を制御可能

ディレクトリ構成（抜粋）
----------------------
以下は主要なファイル／モジュールのツリー（src/kabusys 配下のみ抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数/.env 自動ロードと Settings
  - config_setup.py              — .env 対話ウィザード
  - validate_config.py           — 起動前設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py                — ニュースセンチメント取得（OpenAI）
    - regime_detector.py         — 市場レジーム判定（OpenAI + ETF MA）
  - monitoring/
    - monitoring_db.py           — SQLite テーブル定義・永続化 API
    - monitoring_engine.py       — モニタ群の統合実行ループ
    - system_monitor.py          — CPU/メモリ/データ鮮度監視
    - trade_monitor.py           — （存在）発注・約定監視（コードベースに実装あり）
    - risk_monitor.py            — ドローダウン・ポジション数監視
    - kill_switch.py             — Kill Switch の管理（flag ファイルの書き込み）
    - alert_manager.py           — （存在）通知管理（LINE 等）
  - portfolio/
    - portfolio_builder.py       — 候補選定・ウェイト計算
    - position_sizing.py         — 株数計算・向きの丸め・aggregate cap
    - risk_adjustment.py         — セクター制限・レジーム乗数
  - research/
    - factor_research.py         — Momentum/Volatility/Value の計算
    - feature_exploration.py     — 将来リターン・IC・統計サマリ
  - utils/
    - logging_setup.py           — ログ初期化ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity 設定
  - execution/                   — 発注実行周り（Engine / BrokerFactory / OrderManager 等）
  - data/                        — データパイプライン・スキーマ定義（prices_daily 等） ※別ファイル群

（上記はリポジトリによって多少異なる場合があります。実際のファイルは src/kabusys 以下をご確認ください）

運用上の注意
------------
- KABUSYS_ENV=live では本番取引が行われます。設定（特に API キー、LINE 通知、Kill Switch の設定）は十分に確認してください。
- Monitoring は SQLITE_PATH（監視 DB）を参照してシステム健全性を判断します。Monitoring は常に本番監視 DB を使う設計です（環境に依存せず）。
- ExecutionEngine と Monitoring は別 DB（paper_trading モードでの paper DB 等）と分離して運用できます。paper_trading の場合、実行は data/paper_trading.db に限定されるため本番 DB を汚染しません。
- Kill Switch（data/kill.flag）を使用すると、ExecutionEngine に安全停止を指示できます。起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動でフラグを消しますが、本番では推奨されません（誤って自動クリアしてしまうリスク）。

開発者向けメモ
---------------
- DuckDB 接続を渡して純粋関数をテストできる設計です（research / ai モジュール等）。
- テスト時に .env の自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API 呼び出しはモジュール内部でラッパー関数化されており、ユニットテストではパッチして外部呼び出しを置き換えることを想定しています。

サポート / 参考
----------------
- 設定ファイルの雛形: .env.example（存在する場合）を参照してください
- 設定検証（python -m kabusys.validate_config）を常に実行してから本番起動することを推奨します

ライセンス等
-----------
プロジェクトのライセンス情報・貢献ルールはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

おわりに
-------
この README はリポジトリ内のコードベースから抽出した意図・使用法をまとめたものです。実環境で運用する際は config/*.yaml や各モジュールの実装（execution ブローカー実装、alert_manager の通知先設定 等）を合わせて十分な検証を行ってください。