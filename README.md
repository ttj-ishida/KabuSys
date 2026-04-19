KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買／検証フレームワークです。  
このリポジトリには、取引実行エンジン、監視（Monitoring）コンポーネント、ポートフォリオ構築・リスク制御ロジック、研究用ファクター計算、そして OpenAI を使ったニュース NLP / レジーム判定などのユーティリティが含まれます。

バージョン: 0.1.0

主な特徴
--------
- ExecutionEngine（発注実行）と Monitoring の独立起動スクリプト
  - run_execution: 実取引 / ペーパートレード（KABUSYS_ENV=paper_trading）に対応
  - run_monitoring: システム監視のポーリングループ
- 設定管理・ウィザード・検証
  - .env 対応の対話ウィザード（config_setup）
  - 起動前設定検証 CLI（validate_config）
- 監視（Monitoring）
  - システム状態 / 注文ログ / リスクログ / ダッシュボードの永続化（SQLite）
  - Kill Switch（条件を満たすと data/kill.flag を書き込み ExecutionEngine に停止シグナルを送る）
- ポートフォリオ構築（純粋関数）
  - 銘柄選定、重み計算、ポジションサイズ計算、セクター制約、レジーム乗数
- 研究・分析
  - DuckDB を使ったファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - ファクターと将来リターンの解析（IC 計算等）
- AI 機能（OpenAI）
  - ニュースのセンチメントスコアリング（news_nlp）
  - 市場レジーム判定（regime_detector）
  - いずれも OPENAI_API_KEY を必要とし、失敗時はフェイルセーフ挙動

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須（実行環境による）: duckdb, psutil, openai
   - 開発/解析で便利: PyYAML（validate_config が YAML を検証する場合）
   例:
     pip install duckdb psutil openai PyYAML

4. .env を用意
   - 対話ウィザードを使う:
     python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参照して作成してください。
   - 自動読み込み: プロジェクトルートに .env / .env.local があれば自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

5. ディレクトリ作成（必要なら）
   - data/ と logs/ は起動時に自動作成されますが、権限等で失敗する環境では事前に作成してください:
     mkdir -p data logs

重要な環境変数（主なもの）
-------------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
- DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb (デフォルト)
  - SQLITE_PATH: data/monitoring.db (Monitoring 用、本番 DB として使用)
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 用の分離 DB)
- ログ:
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL (デフォルト: INFO)
  - LOG_DIR: ログ出力先（デフォルト: logs）
- OpenAI:
  - OPENAI_API_KEY: AI 機能利用時に必要
- その他:
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。デフォルト 60）
  - PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）

セットアップ補足
- .env 自動ロード順: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- .env は絶対に Git にコミットしないでください

使い方（起動・CLI）
-------------------

1) 設定検証
- 設定が整っているかを事前にチェック:
  python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いして exit(1) になります。

2) 環境設定ウィザード（.env 作成）
  python -m kabusys.config_setup

3) 実行エンジン（ExecutionEngine）起動
- 実行:
  python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録します（本番 DB と完全分離）。
  - 起動時にプロセス優先度を "high" に設定し、PID ファイル（data/execution.pid）を管理します。
  - data/stop_requested.flag が存在すると起動を中止・停止します。
  - Kill Switch（data/kill.flag）が書き込まれると ExecutionEngine に停止を指示できます。

4) 監視（Monitoring）起動
- 実行:
  python -m kabusys.run_monitoring
- 挙動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを記録します。
  - run_monitoring もプロセス優先度を "high" に設定します。
  - data/stop_requested.flag があると監視ループを終了します。

5) Paper Trading 検証レポート
- ペーパートレード DB から検証レポートを生成:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

6) AI 機能（プログラム呼び出し）
- ニューススコアやレジーム判定はライブラリ関数を呼び出して使用します（OpenAI API キー必須）。
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- api_key が None の場合は環境変数 OPENAI_API_KEY を参照します。未設定の場合は ValueError。

停止・Kill 手順
---------------
- 優雅に停止（run_* スクリプト用）
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検知して終了します。
- Execution を強制停止させる（Kill Switch）
  - KillSwitch はリスク条件（ドローダウン超過、ポジション数上限超過等）で data/kill.flag を書き込み、ExecutionEngine 側がそれを検知して停止します。
  - 手動で kill.flag をクリアする場合:
    rm data/kill.flag
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に自動クリアされます（本番では 0 推奨）。

ログ
----
- 共通ロギングユーティリティ: kabusys.utils.logging_setup.setup_logging
  - コンソール (stdout) と日次ローテーションのファイル出力（logs/<app_name>.log）を設定します。
  - デフォルトで 30 日分のログを保持します。

ディレクトリ構成（主要ファイル）
--------------------------------
- src/kabusys/
  - __init__.py                       — パッケージ定義（version）
  - config.py                         — 環境変数・設定読み込み・Settings
  - config_setup.py                   — .env 対話ウィザード
  - validate_config.py                — 設定検証 CLI
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - run_monitoring.py                 — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py    — ペーパートレード検証レポート CLI
  - ai/
    - news_nlp.py                     — ニュース NLP スコアリング（OpenAI 呼び出し）
    - regime_detector.py              — 市場レジーム判定（OpenAI 呼び出し）
  - monitoring/
    - monitoring_db.py                — Monitoring 用 SQLite レイヤ
    - system_monitor.py               — システム監視
    - trade_monitor.py (参照あり)     — 注文監視（実装ファイルが別にある想定）
    - risk_monitor.py                 — ドローダウン・ポジション監視
    - monitoring_engine.py            — 各 Monitor を束ねるエンジン
    - kill_switch.py                  — Kill Switch 実装
    - alert_manager.py (参照あり)    — 通知管理（実装ファイルが別にある想定）
  - portfolio/
    - portfolio_builder.py            — 銘柄選定・重み計算
    - position_sizing.py               — 株数決定・丸め・スケールダウン
    - risk_adjustment.py               — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py              — ファクター計算（momentum/volatility/value）
    - feature_exploration.py           — 将来リターン・IC・統計解析
  - utils/
    - logging_setup.py                — ログユーティリティ
    - process_priority.py             — プロセス優先度・CPU affinity
  - monitoring/monitoring_db.py       — DB スキーマ定義・永続化ロジック

開発・貢献
----------
- 設定ファイルやシークレット (.env) は絶対にコミットしないでください。
- ツールやモジュールはユニットテストを想定した副作用少なめの設計です（OpenAI 呼び出しなどはモック可能）。
- 新しい依存を追加する場合は requirements.txt / pyproject.toml に追記してください。

補足（設計上の注意）
-------------------
- Monitoring は本番 sqlite（SQLITE_PATH）を参照するため、環境に応じた DB 分離が必要な場合は設定で PAPER_TRADING_SQLITE_PATH を適切に設定してください。
- Run スクリプトは起動直後にプロセス優先度を "high" に設定します（プラットフォーム依存で失敗してもログ警告で続行します）。
- AI 機能は外部 API を使います。API の有効性や料金に注意してご利用ください。
- .env 自動読み込みはプロジェクトルートの検出（.git または pyproject.toml）に依存します。特殊な配置の場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動で環境変数を管理してください。

ライセンス
---------
- この README ではライセンス情報が含まれていません。実際のライセンスはリポジトリの LICENSE ファイルを参照してください。

以上がこのコードベースの概要と利用方法です。必要なら実行例や .env のサンプル（セキュリティに配慮しつつ）を追記します。どの部分を詳しく説明しましょうか？