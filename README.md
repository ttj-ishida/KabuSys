KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株の自動売買・研究・監視に使う内部ライブラリ群と起動スクリプト群を含みます。  
README ではプロジェクト概要、主な機能、セットアップ手順、使い方、及びディレクトリ構成を日本語でまとめます。

プロジェクト概要
----------------
KabuSys は以下の機能を持つ小規模な自動売買プラットフォームの一部です：

- 発注エンジン（ExecutionEngine）と監視（Monitoring）機能を分離して提供
- Paper Trading（ペーパートレード）モードをサポート（本番 DB とは分離）
- DuckDB を使った調査・ファクター計算モジュール（research）
- ニュース NLP（OpenAI）を使ったセンチメントスコア生成（ai）
- ポートフォリオ構築、リスク調整、ポジションサイズ計算（portfolio）
- 監視ログ（SQLite）と監視エンジン（monitoring）
- 環境設定ウィザード / 設定検証ツールを同梱

主な特徴（機能一覧）
-------------------
- 起動スクリプト
  - run_execution.py：ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を用い paper_trading DB に記録
  - run_monitoring.py：SystemMonitor をポーリングして監視ログを記録・Kill Switch 評価などを行う。MONITOR_POLL_INTERVAL で間隔変更可
- 設定管理
  - Settings クラスで環境変数を集約。.env 自動ロード機能あり（プロジェクトルートの .env / .env.local）
  - config_setup.py：対話式ウィザードで .env を作成・更新
  - validate_config.py：起動前チェック（必須環境変数や config/*.yaml の有無など）
- モニタリング
  - monitoring_db.py：SQLite にテーブル群を作成・操作する永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py、trade_monitor.py、risk_monitor.py、monitoring_engine.py、kill_switch.py 等で実運用監視と Kill Switch を実装
- 研究・分析
  - research パッケージ：ファクター計算（momentum/value/volatility）・特徴量探索・IC 計算など（DuckDB 利用）
- AI（OpenAI）連携
  - ai/news_nlp.py：ニュース記事を集約して OpenAI に送信し銘柄ごとにセンチメントを ai_scores テーブルへ記録
  - ai/regime_detector.py：ETF の MA とマクロニュースセンチメントを組み合わせて市場レジーム判定
- ポートフォリオ構築
  - portfolio パッケージ：候補選定・重み計算・セクター制限・ポジションサイズ計算（丸め、利用可能現金に応じたスケールダウン等）
- ユーティリティ
  - utils/logging_setup.py：統一的なログ設定（stdout + 日次ローテーション）
  - utils/process_priority.py：プラットフォーム差を吸収したプロセス優先度設定（可能な場合のみ）

必須・主要な環境変数（抜粋）
---------------------------
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
- OPENAI_API_KEY — OpenAI API を使う機能（ai）で必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（monitoring.db）のパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト 60）
- PAPER_FILL_MODE — paper_trading の MockBroker の fill モード（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START — 本番での kill.flag 自動クリア（デフォルト 0。1 にすると起動時にクリア）

注意: Settings モジュールはプロジェクトルートの .env / .env.local を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

セットアップ手順
----------------
1. Python 仮想環境を作成・有効化
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必須（主なもの）:
     - duckdb
     - psutil
     - openai (ai 機能を使う場合)
   - 任意（設定検証で YAML を検証する場合）:
     - PyYAML
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt があればそちらを利用してください。）

3. .env ファイルを作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに .env を作成（.env.example を参考にし、秘密情報は Git にコミットしない）

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります

5. ディレクトリ作成/パス
   - デフォルトでは data/（DB とフラグファイル）と logs/（ログ）を使います。必要な場合は環境変数でパスを指定してください。
   - ログディレクトリは自動作成を試みますが、権限エラーなどで失敗する場合はファイル出力が無効化され stdout のみになります。

使い方（主要コマンド）
---------------------
- ExecutionEngine の起動
  - 本番・ペーパー共有のランチャー:
    - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使い、本番 DB と分離される
    - 起動時に stop_requested.flag が存在すると起動しない
    - 実行中に data/stop_requested.flag が作成されるとエンジンは停止される（run_execution は stop フラグを監視）
    - 実行時に execution.pid に PID を書きます（Settings.pid_file_path）
    - プロセス優先度を「high」に設定しようとします（権限がない場合は警告）

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - Settings.sqlite_path（デフォルト data/monitoring.db）に接続して監視テーブルを初期化
    - DuckDB にも接続（Settings.duckdb_path）
    - デフォルト 60 秒間隔で SystemMonitor.check_once() を呼びます。環境変数 MONITOR_POLL_INTERVAL で秒数を変更できます
    - data/stop_requested.flag を検出するとループを抜けて終了します

- .env の生成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB 指定可（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI（ニューススコア／レジーム判定）
  - ai.news_nlp.score_news(conn, target_date, api_key=None) — DuckDB 接続を渡してスコアを ai_scores テーブルに書き込みます（OPENAI_API_KEY 必須）
  - ai.regime_detector.score_regime(conn, target_date, api_key=None) — 市場レジームを計算して market_regime テーブルへ保存します

ログと監視
-----------
- ログ出力:
  - kabusys.utils.logging_setup.setup_logging が共通のログ設定を行います
  - デフォルトで stdout と logs/<app_name>.log（日次ローテーション、30 日保管）に出力
- Kill Switch:
  - リスクモニタで閾値を超えた場合、KillSwitch が data/kill.flag を書き込んで ExecutionEngine に停止シグナルを送ります（ExecutionEngine は起動時にこのフラグの存在を確認）
  - Settings.kill_flag_clear_on_start が 1 の場合は起動時に kill.flag を自動的にクリアする挙動になります（本番では 0 推奨）

よくある注意点
--------------
- process priority（高優先度設定）は OS と権限に依存します。権限がない場合は警告が出て処理は続行されます。
- OpenAI を使う機能は API キーが必要です。キーのレート制限やエラーに対してはリトライロジックが組み込まれていますがコストと安定性に注意してください。
- Paper Trading は本番 DB とデータを分離するための仕組みが用意されています。テスト時に誤って本番 DB を使わないよう env を確認してください。
- DuckDB は大量データの分析に強いですが、schema（prices_daily / raw_financials 等）の準備が必要です。config/*.yaml は生成スクリプトやテンプレートを参照してください（リポジトリ内スクリプトで生成可能な場合あり）。

主なディレクトリ構成
-------------------
（プロジェクトルートの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前チェック CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成 CLI
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB（テーブル作成・永続化ヘルパ）
    - system_monitor.py
    - trade_monitor.py       —（ファイルは抜粋に含まれていませんが存在します）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       —（アラート送信ロジック）
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - ...（発注関連コンポーネント）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/                    — 実行時に使用される data/ ディレクトリ（デフォルトの DB 等）
  - logs/                    — ログ保存先（デフォルト）

（上記は実ソースに基づく抜粋です。実際のファイル一覧はリポジトリをご確認ください。）

開発者向けメモ
-------------
- 設定自動読み込み:
  - config.py はプロジェクトルートを .git または pyproject.toml で探し、.env / .env.local を読み込みます。テストや特別なケースでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って無効化できます。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存 DB の列チェックを行い、必要に応じてカラム追加（簡易マイグレーション）を行います。
- テストしやすさ:
  - AI 呼び出しや外部 API 呼び出し部分は簡単に差し替え（モック）できるように設計されています（例えば _call_openai_api を patch）。

ライセンス・その他
------------------
- 本 README に記載の仕様はコードコメント・実装に基づく解説です。実際のライセンスや配布形態はリポジトリの LICENSE 等を参照してください。

フィードバック／貢献
-------------------
不明点・改善提案やバグ修正の PR を歓迎します。まずは Issue を立ててください。

以上。必要があれば README を Markdown ファイルに整形して差し替えたり、各コマンドの実行例（環境変数の具体例や systemd/cron 用の起動例）を追加できます。どの形式・詳しさにするか指定してください。