KabuSys
=======

日本株向けの自動売買システム（KabuSys）の一部実装です。  
このリポジトリは、発注エンジン、監視（モニタリング）、ポートフォリオ構築、リサーチ、AI を使ったニュース解析などのコンポーネントを含んでいます。ドキュメントは日本語でまとめています。

概要
----
KabuSys は以下を含むモジュール化された自動売買フレームワークです。

- ExecutionEngine: ブローカークライアントと連携して発注を実行するエンジン。paper_trading モードではモックブローカーを使い、本番 DB と分離して動作する。
- Monitoring: システム稼働状況、注文ログ、リスク（ドローダウン／ポジション上限）などをポーリングしてログ・アラート・Kill Switch を管理する。
- Portfolio: 候補選定、重み計算、ポジションサイズ決定、セクターキャップ等のポートフォリオ構築ロジック（純粋関数群）。
- Research: DuckDB 上の時系列データを使ったファクター計算・特徴量探索。
- AI: OpenAI を使ったニュースのセンチメントスコアリング、マクロセンチメントを用いた市場レジーム判定。
- Tools: Paper Trading の検証レポート生成などの CLI ツール。
- Config / Utils: 環境変数の読み込み / ウィザード、バリデーション、ログ設定、プロセス優先度設定などのユーティリティ。

主な機能一覧
--------------
- 起動前の環境チェック・検証（kabusys.validate_config）
- .env の対話式生成・更新（kabusys.config_setup）
- ExecutionEngine の起動（本番 / ペーパートレード切替）
- Monitoring のポーリングループ（システム状態、注文ログ、リスク監視、Kill Switch）
- Paper Trading 用検証レポート出力（kabusys.tools.paper_verification_report）
- DuckDB を用いたファクター計算（モメンタム / ボラティリティ / バリュー等）
- OpenAI（gpt-4o-mini 等）を用いたニュース NLP スコアリングとレジーム判定
- ログの日次ローテーション（logs/*.log）

セットアップ手順
----------------
以下は一般的なセットアップ手順です。実際のプロジェクトでは requirements.txt や pyproject.toml を参照してください。

1. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb openai psutil
   - （任意）PyYAML をインストールすると config/*.yaml の構文検査が有効になります:
     - pip install PyYAML

   ※ 実際の依存関係はプロジェクトで管理される requirements.txt / pyproject.toml を参照してください。

3. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動で .env を作成する。

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. データディレクトリ
   - デフォルトでは data/ に SQLite / DuckDB / PID/flag ファイルが作成されます。必要に応じて .env の DUCKDB_PATH / SQLITE_PATH 等を設定してください。

環境変数（主要）
----------------
config.Settings で参照する主要な環境変数（抜粋）:

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須） — kabuステーション API 用パスワード
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY — AI モジュールで必要
- KABUSYS_ENV — one of: development | paper_trading | live （デフォルト: development）
- PAPER_FILL_MODE — paper_trading 時の fill モード（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリアする（0/1）
- PID_FILE_PATH / KILL_FLAG_PATH — パスをカスタマイズ可能
- MONITOR_POLL_INTERVAL — monitoring のポーリング間隔（秒、デフォルト 60）

使い方（主要コマンド）
---------------------

- .env のセットアップ（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB に記録します（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在すると起動を中止します。
    - 実行中は data/execution.pid が作成されます（PIDファイルの場所は Settings で変更可）。

- Monitoring 起動
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path を使用して監視ログを残します（env に関係なく）。
    - 停止は data/stop_requested.flag を作成すると次のポーリングで検知して終了します。

- Kill Switch（Execution を停止させる仕組み）
  - KillSwitch はリスク条件を満たすと data/kill.flag を作成します。
  - ExecutionEngine は kill.flag を検出すると安全に停止する設計です。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアします（本番では推奨されません）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または --db オプションで指定可能。

注意点 / 運用メモ
-----------------
- ロギング
  - logs/<app_name>.log に日次ローテーションで出力されます（デフォルト logs/）。ログディレクトリは LOG_DIR 環境変数や setup_logging の引数で変更可能。
- DB
  - paper_trading モードは paper_trading 用 SQLite に完全分離して記録されます。
  - monitoring は設定に関わらず監視用 SQLite（SQLITE_PATH）を使用します。
- AI
  - news_nlp / regime_detector は OpenAI API を使用します。OPENAI_API_KEY を設定してください。
  - API 呼び出しはリトライ・バックオフの実装がありますが、レート制限やコストに注意してください。
- プロセス制御
  - 実行スクリプトは起動直後にプロセス優先度を "high" に設定しようとします。権限不足時は警告が出ます。
- データ鮮度
  - SystemMonitor は DuckDB 上の prices_daily 等のデータ鮮度も検査し、古いデータがある場合にアラートします。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数／Settings
- config_setup.py              — .env 対話式ウィザード
- validate_config.py           — 設定検証 CLI
- run_execution.py             — ExecutionEngine 起動スクリプト
- run_monitoring.py            — Monitoring 起動スクリプト

src/kabusys/utils/
- logging_setup.py             — ログ設定ユーティリティ
- process_priority.py          — プロセス優先度 / CPU affinity
- (他ユーティリティ)

src/kabusys/monitoring/
- monitoring_db.py             — SQLite 永続化層
- system_monitor.py            — システム状態監視
- trade_monitor.py             — 注文の監視（テーブル参照）
- risk_monitor.py              — ドローダウン / ポジション上限監視
- kill_switch.py               — Kill Switch フラグ管理
- monitoring_engine.py         — 各監視の統合ループ
- alert_manager.py             — （アラート送信管理：LINE 等。該当ファイルを参照）

src/kabusys/execution/
- execution_engine.py          — 発注エンジン本体（EngineConfig 等）
- broker_factory.py            — ブローカークライアント生成
- order_manager.py, order_repository.py, reconciler.py, risk_manager.py 等

src/kabusys/portfolio/
- portfolio_builder.py         — 候補選定・重み付け
- position_sizing.py           — 株数決定・資金割当
- risk_adjustment.py           — セクターキャップ・レジーム乗数
- __init__.py

src/kabusys/research/
- factor_research.py           — ファクター計算（momentum/value/volatility）
- feature_exploration.py       — 将来リターン・IC・統計サマリ

src/kabusys/ai/
- news_nlp.py                  — ニュース NLP（OpenAI 経由）
- regime_detector.py           — マクロ + ETF MA によるレジーム判定
- __init__.py

src/kabusys/tools/
- paper_verification_report.py — Paper Trading 検証レポート

監視・停止ファイル（data/ 以下）
- data/stop_requested.flag     — run_* スクリプトでポーリングループを止めるために参照
- data/kill.flag               — Kill Switch が書き込む停止フラグ（ExecutionEngine 側が検出）
- data/execution.pid           — ExecutionEngine の PID ファイル（デフォルト）

開発向け / トラブルシューティング
-----------------------------------
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CI/テストで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PyYAML がない場合、validate_config の YAML 検査はスキップされます（警告）。
- DuckDB / SQLite のパスの親ディレクトリが存在しない場合は警告が出ます（起動時に自動作成されることが多いです）。
- 監視ループや ExecutionEngine の強制停止は data/stop_requested.flag を作成することで安全に行えます。kill.flag は自動発生する可能性があるため、起動前にクリアしたい場合は設定や KillSwitch.clear() を利用してください。

ライセンス / 貢献
-----------------
本 README はコードベースに基づく概要ドキュメントです。実際にデプロイする際はライセンスやセキュリティ、外部 API の利用規約、資金管理ポリシーを十分に確認してください。

---

必要であれば、README に付け加える例: systemd 用ユニットファイル例、Docker 化手順、requirements.txt の推奨内容、より詳細な運用手順（log rotation、バックアップ、監視アラートの実運用設計）も作成できます。どの情報を追記しますか？