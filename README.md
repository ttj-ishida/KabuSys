# KabuSys

日本株自動売買システムの軽量モジュール群（ライブラリ＋起動スクリプト群）。  
このリポジトリは取引実行エンジン、監視（Monitoring）やリサーチ／ポートフォリオ構築、AI ニュース NLP 等の領域ごとに分かれて実装されています。

以下はこのコードベースの概要・セットアップ・使い方・主要構成のまとめです。

重要: これはドキュメント生成用 README です。実際に運用する前に .env.example を参考に環境変数を適切に設定し、十分なテストを行ってください。

---

## プロジェクト概要

- 目的: 日本株の自動売買に必要なコンポーネント群（ExecutionEngine、監視／アラート、Portfolio Construction、Research、AI ベースのニュースセンチメント、等）を提供する。
- 設計方針:
  - モジュールはできるだけ純粋関数／副作用を限定して設計（DBアクセスの有無を明示）。
  - Paper Trading（検証）環境は本番 DB と完全に分離可能。
  - 外部 API 呼び出し（OpenAI など）はキーを注入可能にしてテストをしやすくしている。
  - 監視は SQLite に永続化し、Streamlit ダッシュボードで可視化できる。

---

## 主な機能一覧

- Execution 周り
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - Reconciler：再起動時の注文・ポジション突合
  - OrderManager / OrderRepository：注文ライフサイクル管理

- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク/プロセス状態・データ鮮度監視
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン／ポジション上限監視とリスクイベント記録
  - KillSwitch：リスク基準超過時に kill.flag を生成して Execution を止める
  - AlertManager：LINE Push による通知（クールダウン管理）
  - MonitoringEngine：上記を束ねるポーリングエンジン
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）

- Portfolio / Position Sizing
  - 候補選定、等配分・スコア加重配分、リスク調整（セクターキャップ、レジーム乗数）、発注株数計算（単元丸め・aggregate cap）

- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン算出、IC 計算、ファクター統計サマリ

- AI
  - ニュース NLP（OpenAI を使った銘柄別センチメント scoring）
  - 市場レジーム判定モジュール（ETF MA200 とマクロセンチメントの合成）

- ユーティリティ
  - 環境変数／.env 読み込みと Settings（src/kabusys/config.py）
  - プロセス優先度 / CPU affinity 設定ユーティリティ（psutil ベース）

- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）

---

## セットアップ手順（ローカル開発 / 実行）

前提
- 推奨 Python バージョン: 3.10+（型ヒントや一部構文を想定）
- 必須ライブラリ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
これらを pip でインストールしてください。requirements.txt は付属していないため、以下は例です。

例:
- pip install duckdb psutil requests openai streamlit

環境変数
- .env / .env.local に環境変数を置けます。自動ロードは Settings モジュールが行います（プロジェクトルートに .git または pyproject.toml が存在する場合）。
- 自動ロードを抑制するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

代表的な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API 用（必須）
- OPENAI_API_KEY — OpenAI 呼び出し用（AI 機能を使う場合に必須）
- KABUSYS_ENV — 実行環境。development / paper_trading / live（デフォルト: development）
  - paper_trading を指定すると、Execution は MockBrokerClient を使い paper_trading 用 DB に記録する（本番 DB と分離）
- PAPER_FILL_MODE — paper_trading の約定モード（instant / partial / never / reject、デフォルト: instant）
- SQLITE_PATH — 監視用 SQLite DB のパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring で上書き可能、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など（Settings を参照）

初期データディレクトリ
- data/ 以下に DB や pid / flag ファイルが置かれる想定です。実行ユーザーに書き込み権限を与えてください。

DB 初期化
- run_monitoring や run_execution は起動時に監視テーブル (monitoring_db.init_monitoring_db) を冪等で作成します。DuckDB や SQLite の初期化は自動で行われます。

---

## 使い方（主要スクリプト）

プロジェクトルートから、もしくはパッケージとして実行できます。

1. 監視ループ（SystemMonitor の単体起動）
- 目的: システム状態をポーリングして monitoring DB に記録する
- 実行:
  - python -m kabusys.run_monitoring
- オプション:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト: 60）
- 停止:
  - 実行スレッドは data/stop_requested.flag を検出すると終了します（ファイルを作成して停止を要求）。
  - Ctrl+C（KeyboardInterrupt）でも終了します。

2. 実行エンジン（ExecutionEngine 起動）
- 目的: 実際の発注処理（本番または paper_trading）
- 実行:
  - python -m kabusys.run_execution
- 動作:
  - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path に記録して本番 DB から分離
  - 起動前に data/stop_requested.flag が存在すると起動しない
  - 実行中に data/stop_requested.flag が生成されたらエンジンを停止する
  - 実行時にプロセス優先度を "high" に設定しようとする（権限に依存）

3. Paper Trading 検証レポート
- 目的: paper_trading DB を集計して主要指標（稼働率・注文成功率・レイテンシ等）の PASS/FAIL を出力
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
- 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能

4. Streamlit ダッシュボード（監視の可視化）
- 実行:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- DB を読み取り専用で開き、Positions / Orders / System / Overview を表示

5. AI 関連
- kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime 等は OpenAI API キー (OPENAI_API_KEY) が必要です。テスト時は API 呼び出しをモックできます（モジュール内で呼び出し関数を patch する設計あり）。

---

## 運用上のファイル / フラグ

- data/stop_requested.flag — run_*.py スクリプトが常時監視する「停止要求」フラグ。存在すると起動を中止/実行中のプロセスを停止する。
- data/kill.flag — KillSwitch が書き込むファイル。ExecutionEngine 側でこのフラグを検出すると停止処理を行う想定（Settings.kill_flag_path で上書き可能）。
- data/execution.pid（デフォルト）— ExecutionEngine の PID ファイル。SystemMonitor はこの PID を確認して実行有無を判定し、stale（死んだ PID）なら削除・アラートを上げる。
- DB ファイル:
  - data/monitoring.db（SQLite、監視ログ）
  - data/paper_trading.db（Paper Trading 用の SQLite）
  - data/kabusys.duckdb（DuckDB、prices_daily 等の時系列データ）

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョンなど）
  - config.py — Settings クラス（.env 自動読み込み、環境変数定義）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py — psutil を使った process priority / cpu_affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite ベースの監視ログ永続化（テーブル作成、CRUD ヘルパー）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - alert_manager.py — LINE Push 通知
    - monitoring_engine.py — 各 Monitor を束ねるポーリング実行
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, ... — 注文処理／同期に関する実装（OrderRecord/OrderRepository/OrderManager 等）
    - broker_factory.py, broker_api.py — ブローカークライアント抽象化
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数算出
    - risk_adjustment.py — セクターキャップ／レジーム乗数
  - research/
    - factor_research.py — momentum/value/volatility 等のファクター計算（DuckDB 経由）
    - feature_exploration.py — 将来リターン計算・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュースを集約して OpenAI でスコア付け、ai_scores に書き込み
    - regime_detector.py — マクロニュース + ETF MA200 でレジーム判定し market_regime テーブルへ保存
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成ツール

その他:
- data/ — DB や pid/flag を格納する想定ディレクトリ（実行時に作成されることがある）
- .env, .env.local — 機微な設定はここへ（レポジトリに格納しないこと）

---

## 設定 / 実運用に関する注意点

- 環境変数の自動読み込みは Settings モジュールで行うため、CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 にして明示的に設定することを推奨します。
- process priority / cpu affinity の設定は OS 権限に依存します。実行ユーザーに適切な権限がないと警告が出ますが処理は継続します。
- OpenAI やブローカー API の呼び出しは料金やレート制限の対象となるため、本番前にテスト環境で挙動確認を行ってください。
- Paper Trading を利用する場合は KABUSYS_ENV=paper_trading を設定し、PAPER_TRADING_SQLITE_PATH を適宜指定します（本番 DB とは別ファイルを使うこと）。
- KillSwitch の動作は監視モジュールに依存します。kill.flag の自動作成は慎重に扱ってください（クリアのための CLI などを整備することを推奨します）。
- DB スキーマは init_monitoring_db により必要な列があるかチェックし、マイグレーション的なカラム追加（例: latency_ms, peak_value）を行いますが、本番運用前にバックアップを取ること。

---

## よく使うコマンドまとめ

- 依存インストール（例）
  - pip install duckdb psutil requests openai streamlit

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

README は以上です。必要であれば以下を続けて用意できます:
- サンプル .env.example（主要環境変数のテンプレート）
- systemd / supervisord 用の簡易ユニット定義（run_monitoring / run_execution のデーモン化）
- 運用チェックリスト（デプロイ前の確認項目）
ご希望があれば作成します。