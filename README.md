# KabuSys

KabuSys は日本株向けの自動売買・リサーチ・監視ツール群のミニマル実装です。本リポジトリは取引実行エンジン、監視/アラート基盤、ポートフォリオ構築ユーティリティ、リサーチ（ファクター計算・特徴量解析）、および一部 AI（ニュースセンチメント / レジーム判定）連携機能を含みます。

以下はコードベースから抽出した概要・機能・セットアップ／使い方・ディレクトリ構成です。

注意: 実際の証券会社 API の呼び出しや本番運用に係るリスクは本 README の想定外です。実行は自己責任で行ってください。

---

## プロジェクト概要

- 設計思想
  - モジュール単位で責務を分離（実行・監視・ポートフォリオ構築・リサーチ・AI）
  - DuckDB / SQLite をデータ層に利用（時系列データや監視ログを格納）
  - Paper Trading（模擬売買）と Live（本番）を環境変数で切替可能
  - OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント / マクロ判定機能を提供（任意）

- 主な技術スタック（想定）
  - Python 3.10+
  - duckdb
  - sqlite3（標準ライブラリ）
  - psutil
  - requests
  - openai（AI機能を使用する場合）
  - streamlit（ダッシュボード表示用）

---

## 主な機能一覧

- Execution（発注）
  - 起動エントリ: python -m kabusys.run_execution
  - Broker クライアントの抽象化（paper_trading モードでは MockBroker を使用）
  - OrderManager / OrderRepository / Reconciler 等による注文管理・起動時の同期処理
  - RiskManager（複数のリスク制約を実装、設定で制御可能）

- Monitoring（監視）
  - 起動エントリ: python -m kabusys.run_monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス PID ファイルの監視、株価データ鮮度チェック
  - TradeMonitor: 注文の滞留（stale order）・約定価格異常の検出
  - RiskMonitor: ドローダウン / ポジション上限の監視、ダッシュボード集計の永続化
  - AlertManager: LINE Messaging API によるプッシュ通知（チャンネル設定が必要）
  - KillSwitch: フラグファイル書き込みで ExecutionEngine 停止を指示

- ポートフォリオ構築（純粋関数群）
  - 候補選定（スコア順）、等金額・スコア重み配分
  - セクター集中制限の適用
  - ポジションサイズ計算（単元株丸め、risk_based 等）

- リサーチ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC（Information Coefficient）計算
  - 統計サマリー（factor_summary）

- AI（任意）
  - news_nlp.score_news: raw_news を集約して OpenAI でセンチメント評価 → ai_scores に書き込み
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュースセンチメントを合成して市場レジーム判定
  - OpenAI API キー（OPENAI_API_KEY）が必要。API 呼び出しはリトライやフェイルセーフを備えます。

- ツール
  - Paper Trading 検証レポート生成ツール
    - 実行例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を参照

- ダッシュボード
  - streamlit ベースの簡易監視ダッシュボード
    - 起動例:
      streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## セットアップ手順（ローカル）

1. Python 環境（推奨: 3.10 以上）を用意
2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール（目安）
   - pip install duckdb psutil requests openai streamlit
   - 実行環境や追加パッケージがある場合は requirements.txt を作成して管理してください
4. データディレクトリを作成
   - mkdir -p data
5. 環境変数の設定
   - .env または .env.local をプロジェクトルートに置くと自動で読み込まれます（ただし OS 環境変数が優先）
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 主要な環境変数（抜粋、デフォルト値含む）

- KABUSYS_ENV: 実行モード
  - 有効値: development / paper_trading / live
  - デフォルト: development

- データベース
  - SQLITE_PATH: 監視用 SQLite（monitoring） — デフォルト data/monitoring.db
  - DUCKDB_PATH: DuckDB ファイル — デフォルト data/kabusys.duckdb
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite — デフォルト data/paper_trading.db

- Paper Trading 固有
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- 監視・PID
  - PID_FILE_PATH: 実行プロセスの PID ファイルパス — デフォルト data/execution.pid
  - KILL_FLAG_PATH: Kill Switch 用のフラグファイル — デフォルト data/kill.flag
  - KILL_FLAG_CLEAR_ON_START: 実行開始時に kill.flag をクリアする場合 1 に設定

- ログレベル
  - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）

- モニタのポーリング間隔
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。デフォルト 60。1 未満や不正な値は無視されデフォルトが使われます。

- OpenAI
  - OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）で使用

- その他
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（kabu API を使う場合）など、必須の環境変数は Settings クラスでチェックされます。未設定時はエラーになります。

---

## 使い方（例）

- ExecutionEngine を起動（本番 or paper_trading を KABUSYS_ENV で指定）
  - production（本番）想定:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - Paper Trading（分離された DB に書き込む）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - run_execution は起動時に:
    - process priority を high に設定しようとする（psutil 権限に依存）
    - sqlite/duckdb に接続し、コンポーネントを組み立ててセッションを実行します

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（デフォルト 60）
  - monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用することに注意

- Streamlit ダッシュボード（読み取り専用）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- AI 機能（ニューススコアリング / レジーム判定）
  - OPENAI_API_KEY を設定して、該当モジュールの関数を呼び出す（自動化スクリプトや cron などで実行）
  - 例: kabusys.ai.score_news(conn, target_date, api_key=...) / kabusys.ai.regime_detector.score_regime(...)

---

## 注意点 / 運用上のヒント

- PID ファイル管理
  - SystemMonitor は PID ファイル（Settings.pid_file_path）を参照して実行中プロセスの有無を確認します。stale PID を検出した場合は削除しリスクログに記録します。
- DB マイグレーション
  - init_monitoring_db はテーブル作成と簡易マイグレーション（カラム追加）を行います（冪等）。
- プロセス優先度設定
  - set_process_priority は psutil を利用します。権限不足やプラットフォーム非対応時はログに警告を出してスキップされます。
- OpenAI API 呼び出し
  - レート制限やネットワーク障害にはリトライ（指数バックオフ）を入れていますが、APIキーや課金設定は事前に確認してください。
- Paper Trading
  - paper_trading モードは本番 DB と完全分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み、Settings クラス（デフォルト値・バリデーション）
  - run_execution.py
    - ExecutionEngine 起動エントリ
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
      - Paper Trading の検証レポート生成 CLI
  - monitoring/
    - __init__.py
    - monitoring_db.py
      - SQLite による監視ログ永続化用関数 / MonitoringDB クラス
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - （Broker 関連・order_repository 等は同ディレクトリに存在）
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

（上記は本リポジトリの主要ファイルを抜粋したものです。実際のプロジェクトでは data/, docs/, tests/ 等が別に存在する想定です。）

---

## トラブルシューティング

- SQLite / DuckDB が開けない
  - ファイルパスを確認し、権限やファイル存在をチェックしてください。
  - Streamlit で read-only モードで開けない場合は MonitoringEngine を先に起動して DB を作成してください。

- OpenAI 連携が失敗する
  - OPENAI_API_KEY が設定されているか確認
  - ネットワーク接続、API 利用制限、モデル名（gpt-4o-mini）を確認

- process priority の設定失敗
  - psutil の権限不足（Linux で負の nice 値をセットするには root 権限が必要）や未対応 OS の可能性があります。ログに警告が出ますが処理は継続します。

---

## 参考: よく使うコマンドまとめ

- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate

- パッケージインストール
  - pip install duckdb psutil requests openai streamlit

- Execution 起動
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、README に含める具体的な .env.example のサンプル、requirements.txt の推奨内容、運用手順（systemd ユニット例や cron 用スクリプト）なども作成します。どの範囲を追加したいか教えてください。