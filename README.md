# KabuSys

日本株自動売買システムの軽量モノリポジトリ（ライブラリ + 実行スクリプト群）。

この README はリポジトリ内の主要モジュールを参照して作成しています。開発者向けに起動方法、設定、監視・検証ツールの使い方をまとめています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。主な役割は以下の通りです。

- 注文発行・状態管理（ExecutionEngine / OrderManager）
- 監視 (MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor)
- ポートフォリオ構築（候補選定、ウェイト計算、ポジションサイズ決定）
- 研究用ファクター計算・特徴量探索（DuckDB を使ったファクター計算）
- AI ベースのニュースセンチメント / レジーム判定（OpenAI を利用）
- Paper Trading（本番 DB と分離した専用 DB に記録）
- 監視ダッシュボード（Streamlit）
- 検証レポート生成ツール（Paper Trading 向け）

設計上、DuckDB は時系列・ファクターデータの集計に、SQLite は監視ログ・注文履歴などの永続化に使用します。

---

## 主な機能一覧

- Execution
  - ExecutionEngine（起動・セッション実行）
  - Broker クライアントの抽象化（本番 / Paper Trading を切替）
  - Reconciler による再起動後の注文・ポジション同期
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、プロセス PID、データ鮮度を監視
  - TradeMonitor：滞留注文・約定異常価格を監視
  - RiskMonitor：ドローダウン・ポジション上限を監視しイベントをログ
  - KillSwitch：重大リスク検出時に停止フラグ（kill.flag）を書き込み
  - AlertManager：LINE によるプッシュ通知（オプション）
  - Streamlit ダッシュボード（監視表示）
- Portfolio
  - 候補選定、等ウェイト／スコア重み、リスク調整（セクターキャップ／レジーム乗数）、ポジションサイズ計算
- Research
  - momentum/volatility/value 等のファクター計算（DuckDB）
  - 将来リターン、IC、統計サマリなど
- AI
  - news_nlp: OpenAI を用いたニュースごとのセンチメント集計と ai_scores への書込
  - regime_detector: MA200 とマクロニュースから市場レジームを判定して market_regime に書込
- Tools
  - paper_verification_report：Paper Trading DB から検証レポートを生成（稼働率・注文成功率・レイテンシ等）

---

## 必要要件

- Python 3.10+
- インストールが必要な主要パッケージ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード使用時)
- これらは環境に合わせて pip でインストールしてください。requirements.txt がない場合は個別にインストールします。

例:
pip install duckdb psutil requests openai streamlit

---

## セットアップ手順

1. リポジトリをクローン / 作業ディレクトリへ移動
2. Python 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール
   - pip install duckdb psutil requests openai streamlit
4. data ディレクトリを作成（デフォルト DB 等の格納先）
   - mkdir -p data
5. 環境変数設定（.env を用意するのが便利）
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（Settings モジュールが自動ロード）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

推奨設定（.env 例）:
- KABUSYS_ENV=development | paper_trading | live
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...
- PAPER_FILL_MODE=instant
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- SQLITE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...

Settings モジュール:
- .env を自動読み込み（優先度: OS 環境変数 > .env.local > .env）
- 読み込みの微妙な仕様（クォート / コメント処理）に対応
- 必須キーは Settings クラスが参照時にチェックして ValueError を投げます

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 起動環境。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須で参照時にエラー）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須で参照時にエラー）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを利用する場合必須）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring の上書き、デフォルト: 60）
- PAPER_FILL_MODE: paper_trading の MockBroker の約定動作（instant|partial|never|reject）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 監視・停止制御関連

---

## 実行方法（使い方）

パッケージをルート（src がパッケージルート）で実行できる想定です。あるいは PYTHONPATH を適切に設定して下さい。

1. Execution Engine を起動（本番 or paper_trading）
   - デフォルトは Settings.env に従って動作。paper_trading の場合は MockBroker を使用し、専用 DB に記録します。
   - 起動:
     - python -m kabusys.run_execution
   - 停止:
     - run_execution はプロジェクトルート/data/stop_requested.flag を監視します。停止したい場合はそのファイルを作成してください（手動で作成すればループは停止します）。
   - 実行時のプロセス優先度を high に設定する機能があります（成功しない場合は警告ログ）。

2. Monitoring を起動（SystemMonitor の単体起動スクリプト）
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（例: export MONITOR_POLL_INTERVAL=30）。
   - 起動:
     - python -m kabusys.run_monitoring
   - こちらも停止は data/stop_requested.flag を作成します（run_monitoring は同ファイルを見て終了します）。
   - 注意: Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path（Settings.sqlite_path）を参照します。

3. Streamlit ダッシュボード（監視 UI）
   - 起動例:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - read-only URI を使って DB を開きます（監視プロセスが書き込み中でも閲覧できるよう配慮）。

4. Paper Trading 検証レポート生成ツール
   - 起動例:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB を明示する場合: --db /path/to/data/paper_trading.db
   - 指標: 稼働率、注文成功率、送信率、P95 レイテンシなどを算出して PASS/FAIL 判定を行います。

5. AI モジュール（ライブラリ API）
   - news_nlp.score_news(conn, target_date, api_key=None)
     - raw_news / news_symbols / ai_scores テーブルを参照・更新します。api_key が None の場合は OPENAI_API_KEY 環境変数を参照します。
   - regime_detector.score_regime(conn, target_date, api_key=None)
     - prices_daily / raw_news / market_regime を参照・更新します。
   - これらはライブラリ関数として呼び出す想定です（CLI エントリは用意されていません）。

---

## 停止・キルフラグ

- stop_requested.flag
  - run_execution.py / run_monitoring.py の両方で監視される停止フラグです。該当ファイルが存在するとループを抜けて安全に終了します。
  - 位置: プロジェクトルート/data/stop_requested.flag（スクリプト内の相対参照を参照）
- kill.flag
  - KillSwitch（監視側）を通じて生成される「ExecutionEngine を止める理由」を格納するフラグです。ExecutionEngine 側はこの flag を起点に停止処理を行います。
  - 作成は KillSwitch.evaluate() による冪等書き込み。Clearing は KillSwitch.clear() を呼ぶか手動削除。

---

## DB ファイルとマイグレーション

- デフォルト:
  - monitoring SQLite: data/monitoring.db
  - paper trading SQLite: data/paper_trading.db
  - DuckDB: data/kabusys.duckdb
- monitoring_db.init_monitoring_db(conn) は冪等でテーブルを作成し、古いスキーマに対する簡易マイグレーション（カラム追加）を含みます。
- Streamlit ダッシュボードは read-only URI で接続するため、監視中の DB を安全に閲覧できます。

---

## ロギング・優先度・CPU affinity

- 起動スクリプトは起動直後に set_process_priority("high") を呼び、可能ならプロセス優先度を変更します（Windows / POSIX を考慮）。
- set_cpu_affinity() により CPU コア固定も可能（必要に応じて呼び出す設計）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数／設定管理（.env 自動ロード等）
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート CLI
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py (実装ファイルあり)
    - broker_factory.py, broker_api.py, ...
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
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
  - utils/
    - process_priority.py

（上記は主要ファイルの抜粋です。詳細はソースを参照してください。）

---

## 開発上の注意・ベストプラクティス

- 環境変数は .env / .env.local に記載して自動読込させることができます。OS 環境変数が優先されます。
- テスト・ローカル開発時は KABUSYS_ENV=paper_trading を使用すると本番 DB へ影響を与えず検証できます。
- AI モジュールを使う場合は OPENAI_API_KEY を必ず設定してください。失敗時はフェイルセーフ（スコア0やスキップ）する設計の個所もありますが、基本はキー必須です。
- 監視ループの間隔は MONITOR_POLL_INTERVAL で調節可能。0 以下・不正値はデフォルト（60秒）にフォールバックします。
- データ鮮度チェックは DuckDB の prices_daily テーブルを参照します。research / ai の集計は DuckDB にデータを入れてから実行してください。

---

## よく使うコマンド例

- Execution 起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、README に含めるサンプル .env.example、具体的な requirements.txt、または各モジュールの API 使用例（関数呼び出し例）も追記できます。どの情報を追加したいか教えてください。