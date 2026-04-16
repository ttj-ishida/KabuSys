# KabuSys

日本株自動売買システムの一部を実装したリポジトリの README（日本語）です。本ドキュメントはソースコード（src/kabusys 以下）を参照して作成しています。

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 環境変数（主要項目）
- 実行方法（使い方）
- ディレクトリ構成
- 運用上の注意 / 補足

---

## プロジェクト概要

KabuSys は日本株の自動売買に関するコンポーネント群を提供するプロジェクトです。本リポジトリには以下のような機能実装が含まれます。

- 実行エンジン（ExecutionEngine）起動スクリプトと周辺モジュール（注文管理、リスク管理、リコンシリエーション）
- 監視（Monitoring）モジュール：システム状態、注文状態、リスク検知、アラート送信、kill スイッチ
- ポートフォリオ構築ロジック（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- リサーチ / ファクター計算（モメンタム、ボラティリティ、バリュー）
- AI 関連モジュール（ニュース NLP によるセンチメントスコア、レジーム判定）
- 各種ユーティリティ（プロセス優先度設定、DB スキーマ初期化、Streamlit ダッシュボード、紙トレード検証レポート生成ツール）

用途としては、本番口座／紙トレード両対応の運用、監視・アラート、研究用のファクター計算などを想定しています。

---

## 主な機能（抜粋）

- Execution
  - 起動時のリコンシリエーション（Reconciler）
  - OrderManager / OrderRepository による注文・状態管理
  - RiskManager による位置づけ（閾値・利用率等）
  - BrokerClientFactory 経由で実際のブローカー or MockBroker を選択可能（KABUSYS_ENV に依存）
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 / 実行プロセスの監視
  - TradeMonitor：滞留注文や約定価格異常の検出
  - RiskMonitor：ドローダウン・ポジション上限の検出とリスクログ記録
  - KillSwitch：致命的トリガー時に flag ファイルを書き ExecutionEngine を停止
  - AlertManager：LINE Push による通知（クールダウン実装）
  - Streamlit ダッシュボード（読み取り専用で監視情報表示）
- Portfolio
  - 候補選定、等配分 / スコア配分、リスクベース発注量計算、セクターキャップ適用など
- Research / AI
  - DuckDB を前提としたファクター計算（momentum / volatility / value）
  - OpenAI を使ったニュースセンチメント（ai_scores）と市場レジーム判定（market_regime）
  - Paper Trading 向けの検証レポート生成ツール

---

## セットアップ手順

前提
- Python >= 3.10（型表記に PEP 604 の union 型（|）などが使われているため）
- 仮想環境の利用を推奨

1. リポジトリをクローン / 作業ディレクトリへ移動
2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate（Unix 系） / .venv\Scripts\activate（Windows）
3. 依存パッケージをインストール（必要に応じて pyproject.toml / requirements.txt を参照）
   - 代表的な依存：
     - duckdb
     - psutil
     - requests
     - openai（AI 機能利用時）
     - streamlit（ダッシュボード利用時）
   - 例:
     - pip install duckdb psutil requests openai streamlit
4. データディレクトリの準備
   - デフォルトでは data/ に DB 等のファイルを作成します。
   - 例: mkdir -p data
5. 環境変数設定
   - .env または .env.local をプロジェクトルートに配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。
   - 必須キーや主要な設定は下の「環境変数」節を参照してください。

---

## 主要な環境変数

config モジュール（kabusys.config）で読み込まれます。自動ロード順序: OS 環境 > .env.local > .env

必須（未設定時はエラー）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（Research 等で必要）
- KABU_API_PASSWORD — kabuステーション API 用

任意 / デフォルトあり
- KABUSYS_ENV — 起動環境: development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、Execution は MockBrokerClient を使い data/paper_trading.db を使用（本番 DB と分離）
- OPENAI_API_KEY — OpenAI API（AI 機能利用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager（LINE Push）に必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定挙動（instant / partial / never / reject、デフォルト: instant）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — 実行監視・停止フラグ関係
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

プロンプト周り
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）。1 未満や不正な値はデフォルトにフォールバック。

---

## 実行方法（使い方）

以下は代表的な起動例です。src が PYTHONPATH にあるか、python -m を使ってモジュールとして実行してください。

1. 監視ループ起動（Monitoring）
   - python -m kabusys.run_monitoring
   - 機能:
     - SystemMonitor のポーリングループを実行し、監視データを SQLite に書き込む。
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒）。
     - 実行時はプロセス優先度を "high" に設定しようとします（psutil の権限に依存）。
     - 停止は data/stop_requested.flag の作成で検知して終了します。

2. 実行エンジン起動（Execution）
   - python -m kabusys.run_execution
   - 機能:
     - Broker クライアントを作成（KABUSYS_ENV=paper_trading なら MockBrokerClient を使用）。
     - OrderManager / RiskManager / Reconciler 等を組み立てて ExecutionEngine を起動。
     - 停止は data/stop_requested.flag を置くことで検知して安全に停止します。
   - Paper trading:
     - KABUSYS_ENV=paper_trading を指定すると paper_sqlite_path（デフォルト data/paper_trading.db）へ記録し、本番 DB と完全に分離します。

3. Streamlit ダッシュボード（監視 UI、読み取り専用）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ローカルの monitoring SQLite を読み取り専用で開いてダッシュボード表示します。

4. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - 例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB: data/paper_trading.db。--db で上書き可能。

5. AI 機能（ニュース NLP / レジーム判定）
   - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime 関数を利用して、DuckDB のテーブルに対してスコアを作成し書き込みます。
   - 実行には OPENAI_API_KEY が必要です（関数引数でも渡せます）。
   - API の呼び出しはリトライ等の安全策が組み込まれていますが、料金・レート制限に注意してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数 / .env の自動読み込みロジック、Settings クラス
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ
- execution/
  - order_manager.py
  - reconciler.py
  - order_repository.py (参照あり)
  - execution_engine.py (参照あり)
  - broker_factory / broker_api / broker クラス群（実際のブローカー実装を分離）
- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化 / 永続化ロジック（MonitoringDB）
  - system_monitor.py — システム状態・データ鮮度チェック
  - trade_monitor.py — 注文滞留 / 約定異常チェック
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag 書き込み / 判定
  - alert_manager.py — LINE 通知
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード
- portfolio/
  - portfolio_builder.py — 候補選定・スコアソート
  - position_sizing.py — 発注株数計算（risk_based / equal / score）
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — momentum/volatility/value の計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- ai/
  - news_nlp.py — raw_news を OpenAI でスコア（ai_scores へ書き込み）
  - regime_detector.py — ETF MA とマクロニュースを組み合わせたレジーム判定
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

data/（実行時に生成・使用される想定）
- monitoring.db（デフォルト SQLITE_PATH）
- paper_trading.db（paper_trading の場合）
- kabusys.duckdb（デフォルト DUCKDB_PATH）
- execution.pid, stop_requested.flag, kill.flag などの制御ファイル

---

## 運用上の注意 / 補足

- .env 自動読み込み
  - プロジェクトルートは config._find_project_root が .git または pyproject.toml を探して決定します。CWD に依存しません。
  - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等にテーブル作成と一部カラム追加の簡易マイグレーションを行います。
- PID / Stop / Kill フラグ
  - run_execution と run_monitoring はプロセス管理のため data 内のファイル（例: execution.pid, stop_requested.flag, kill.flag）を使用します。適切に扱ってください。
- 権限
  - set_process_priority や CPU affinity 設定は OS と権限に依存します。psutil の挙動により設定できない場合は警告が出ますが処理は継続します。
- Paper Trading と本番 DB の分離
  - KABUSYS_ENV=paper_trading を使用すると paper_sqlite_path（デフォルト data/paper_trading.db）に記録され、本番用の monitoring DB とは分離されます。運用時はこの分離を利用して安全に検証してください。
- AI / OpenAI
  - OpenAI 利用時は API キー（OPENAI_API_KEY）とコストに注意。API 呼び出しはモデル名やレスポンス形式に依存します（コード内で gpt-4o-mini を使用する想定）。
- テスト・モック
  - AI 呼び出し等はテスト時に差し替え可能な実装（関数を patch）になっています。ユニットテストでのモッキングを想定した作りです。

---

必要であれば、README に含めるサンプル .env.example、起動スクリプトの systemd ユニット例、あるいは各モジュールの詳細な API ドキュメント（OrderRepository のスキーマ、DuckDB テーブル定義など）も追加できます。どの内容を優先して追加するか指示してください。