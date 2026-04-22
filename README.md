# KabuSys

日本株向けの自動売買 / 研究基盤ライブラリ群および起動スクリプト群です。  
このリポジトリは自動売買のコアロジック（発注エンジン・リスク管理・監視）、ファクター計算・研究ツール、AI を利用したニュースセンチメント評価などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のサブシステムで構成されています。

- ExecutionEngine（発注エンジン）: ブローカークライアントを通じて注文を発行し、Order 管理・リスク管理・照合を行う。
- Monitoring（監視）: システム稼働・注文ログ・リスク指標を定期ポーリングして SQLite に永続化、アラートや Kill Switch を提供する。
- Portfolio（ポートフォリオ構築）: 候補選定・配分重み計算・ポジション決定を行う純粋関数群。
- Research（研究）: DuckDB 上でファクター計算・将来リターン計算・IC 等の解析ツール。
- AI（ニュース NLP / レジーム検出）: OpenAI を使ったニュースセンチメント評価やマクロセンチメントを基に市場レジーム判定。
- Tools（ユーティリティ）: 設定ウィザード、設定検証、Paper Trading レポート生成など。

設計方針の一部:
- DB（DuckDB / SQLite）をデータ層として利用。分析は DuckDB、監視・発注ログは SQLite。
- 本番・ペーパートレードの DB は分離（paper_trading 時は専用 DB を使用）。
- 環境変数・.env による設定管理（自動ロードはプロジェクトルートの .env/.env.local）。
- フェイルセーフ（API 失敗時のフォールバック、部分成功時の DB 書き込み保護など）。

---

## 主な機能一覧

- 起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine を起動
  - python -m kabusys.run_monitoring : SystemMonitor のポーリングループを起動
- 設定関連
  - python -m kabusys.config_setup : .env の対話式ウィザードで作成/更新
  - python -m kabusys.validate_config : .env と config/*.yaml の事前検証
- 研究・分析
  - ファクター計算（momentum, value, volatility）
  - 将来リターン、IC、統計サマリー
- AI 系
  - kabusys.ai.score_news: OpenAI を使ったニュースセンチメントスコアリング
  - kabusys.ai.regime_detector: マクロ + ETF MA による日次レジーム判定
- 監視
  - system_status / trade_logs / risk_logs / dashboard の永続化（SQLite）
  - Kill Switch（閾値超過時に data/kill.flag を書き込んで ExecutionEngine を停止）
  - monitoring_engine による複数モニターの定期実行
- ツール
  - Paper Trading 検証レポート生成（sqlite を読み取り統計・閾値判定）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして作業ディレクトリへ移動
   - (例) git clone ... && cd your-repo

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なライブラリをインストール  
   主要な依存例（環境により追加が必要）:
   - duckdb
   - psutil
   - openai
   - PyYAML（config の YAML 検証が必要な場合）

   例:
   - pip install duckdb psutil openai pyyaml

   （requirements.txt がある場合はそれを利用してください）

4. 初期設定（.env）を作成
   - 推奨: 対話ウィザードを使う
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成して必要な環境変数を設定

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いで exit(1) になります

6. データディレクトリやログディレクトリの準備
   - デフォルトの SQLite / DuckDB / logs ディレクトリはコードが自動作成しますが、権限等に注意してください。

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants API（データ取得等）
- KABU_API_PASSWORD : kabuステーション API のパスワード

主要な任意項目:
- KABUSYS_ENV : 実行環境 (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : paper_trading 時の専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL : ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY : OpenAI を利用する機能で必要
- PAPER_FILL_MODE : paper_trading の約定挙動（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL : run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START : 起動時に data/kill.flag を自動削除するか（0/1）

自動 .env ロード:
- プロジェクトルートにある .env / .env.local は自動的に読み込まれます。
- 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（起動・主要コマンド）

- .env の初期化（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）の起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db を用います（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - エンジンは別スレッドで run_session を実行し、data/stop_requested.flag や data/kill.flag によって停止できます。
    - 実行中は data/execution.pid が生成されます（設定で別パスに変更可能）。

- Monitoring（監視）の起動
  - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（SQLITE_PATH）を使用して監視データを永続化します（意図的動作）。
    - data/stop_requested.flag を検知するとループを終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションでデータベースパス指定可（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI / レジーム検出（ライブラリ関数として利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OpenAI API キーが必要（api_key 引数または OPENAI_API_KEY 環境変数）

- ログ
  - デフォルトで stdout に出力しつつ logs/<app_name>.log に日次ローテーションで保存されます（logs ディレクトリは自動作成を試みます）。
  - setup_logging を全スクリプトで使用しているためログ出力は統一されています。

- Kill Switch / 停止フラグ
  - KillSwitch は条件（ドローダウン超過等）で data/kill.flag を書き込みます。ExecutionEngine はこのファイルを検知して安全に停止します。
  - 手動でクリアする場合:
    - rm data/kill.flag などで削除してください。
  - 設定で起動時に自動クリアする場合: KILL_FLAG_CLEAR_ON_START=1（本番では推奨されません）

---

## ディレクトリ構成（主要ファイル）

（パッケージルートに src/kabusys 以下が配置されています。主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings の取得ロジック（.env 自動ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py       — ロギング初期化（Stream + 日次ファイルローテーション）
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ
  - execution/                — ExecutionEngine 関連（OrderManager / RiskManager 等）
    - (実装ファイル群)
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化・監視 DB ラッパー
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文ログ監視（滞留注文・異常約定など）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - monitoring_engine.py   — 複数 monitor を束ねるエンジン
    - kill_switch.py         — フラグファイルを使った停止判定
    - alert_manager.py       — （実装があればアラート出力）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数計算・キャップ処理
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — momentum / value / volatility 計算
    - feature_exploration.py — forward return / IC / 統計関数
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — レジーム判定（MA + マクロセンチメント）
  - data/                    — (実行時に使用するデータファイル場所のデフォルト)
    - monitoring.db (デフォルト)
    - paper_trading.db (デフォルト)
    - kill.flag / stop_requested.flag / execution.pid など制御ファイル

---

## 実運用上の注意事項

- 本番環境（KABUSYS_ENV=live）では設定ミスが致命的になるため、validate_config で入念にチェックしてください。
- .env は機密情報を含むため、絶対にバージョン管理にコミットしないでください。
- OpenAI や外部 API の呼び出しはコストやレート制限に留意してください（score_news / regime_detector はリトライ・バックオフ実装あり）。
- Monitoring は監視用 DB（SQLITE_PATH）を環境に関係なく参照します。paper_trading と分離したい場合は注意してください。
- process priority 設定やログディレクトリの作成に失敗した場合は警告ログが出ますが、プロセスは継続するように設計されています。

---

## 開発者向けヒント

- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効化できます。
- AI の API 呼び出し部分は _call_openai_api をユニットテストで patch することで簡単にモックできます（コード内にその旨のコメントあり）。
- DuckDB 接続を受け取る関数は副作用を最小限にする純関数設計が意図されています。分析機能は本番の発注処理に影響を与えないよう DB 読み取り専用です。

---

必要であれば、この README を元にさらに詳しいセットアップ手順（docker-compose、systemd ユニット例、CI 設定例など）や各モジュールの API ドキュメントを追加します。どの情報がさらに必要か教えてください。