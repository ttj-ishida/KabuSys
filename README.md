# KabuSys

日本株自動売買システム KabuSys のコードベース README（日本語）

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（実行例）
- 主要な環境変数
- 停止・フラグ操作
- ディレクトリ構成（主要ファイル説明）
- 注意事項

---

## プロジェクト概要

KabuSys は日本株自動売買のためのモジュール群を提供するリポジトリです。  
主なコンポーネントは以下です。

- 発注・ExecutionEngine（ブローカー連携、リスク管理、再同期）
- 監視（System / Trade / Risk のポーリング、アラート）
- ポートフォリオ構築（銘柄選定、重み付け、ポジションサイズ計算）
- 研究モジュール（ファクター計算、特徴量探索）
- AI 支援（ニュースセンチメントの LLM スコアリング、レジーム判定）
- 各種ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計方針としては、DB（SQLite / DuckDB）を使ったオフライン分析、LLM 呼び出しは安全なリトライ/バリデーションを行う、ルックアヘッドバイアス回避などを重視しています。

---

## 機能一覧

- ExecutionEngine 起動 / 発注管理（OrderManager, OrderRepository, Reconciler）
- Paper Trading 対応（環境 `KABUSYS_ENV=paper_trading` で本番 DB と完全分離）
- 監視コンポーネント
  - SystemMonitor：CPU/メモリ/Disk/プロセスの監視、データ鮮度チェック
  - TradeMonitor：滞留注文・約定価格異常の検出
  - RiskMonitor：ドローダウン・ポジション数上限の監視
  - MonitoringEngine：各 Monitor を定期実行、KillSwitch 評価、AlertManager 連携
- アラート送信（LINE Push API 経由）
- Streamlit ダッシュボード（監視情報の可視化）
- Paper Trading 検証レポート出力ツール
- 研究用モジュール（モメンタム / ボラティリティ / バリュー等のファクター計算）
- AI モジュール
  - news_nlp: ニュース記事を OpenAI へ送りセンチメントを ai_scores に格納
  - regime_detector: MA200 比率 + マクロニュースセンチメントから市場レジーム判定

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を用意

2. 依存ライブラリをインストール  
   （requirements.txt はプロジェクトに含まれていない想定のため、主要依存を例示します）
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   - （必要に応じて）その他 DB/ブローカー関連ライブラリ

   例:
   pip install duckdb psutil requests openai streamlit

3. ディレクトリ（data 等）を作成
   - data/ ディレクトリを作成しておくとログ・DB 等の出力先として使われます。
   - デフォルト DB パス:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db

4. 環境変数を設定（詳細は下節を参照）
   - .env / .env.local に設定しておくと自動ロードされます（自動ロードはプロジェクトルートが見つかる場合のみ）。
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 初回起動時に Monitoring DB のスキーマは自動作成されます（init_monitoring_db が呼ばれるため手動初期化不要）。

---

## 使い方（実行例）

コードはパッケージとして実行可能になっているため、パッケージルート（src が PYTHONPATH に入っている状態）で以下のように起動します。開発環境に応じて Python のモジュール実行方法を調整してください（例: `python -m kabusys.run_monitoring`）。

- 監視ループを起動（ポーリング）
  - デフォルトのポーリング間隔は 60 秒（環境変数で上書き可能）
  - 実行:
    - python -m kabusys.run_monitoring
    - または python src/kabusys/run_monitoring.py
  - ポーリング間隔の変更:
    - export MONITOR_POLL_INTERVAL=30

- ExecutionEngine（発注エンジン）を起動
  - 環境 `KABUSYS_ENV=paper_trading` の場合は MockBroker を使い、data/paper_trading.db に書き込みを行います（本番 DB と分離）。
  - 実行:
    - python -m kabusys.run_execution
    - または python src/kabusys/run_execution.py

- Streamlit ダッシュボード
  - 実行例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成ツール
  - 実行例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション `--db` で SQLite DB の場所を指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）。

- AI 周りの関数（ライブラリとして利用）
  - ニューススコア付与（プログラム内で呼出し）:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="xxxxx")
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="xxxxx")

---

## 主要な環境変数

Settings クラスで参照・検証される主要なキー（抜粋）:

必須（未設定時は起動時にエラー）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / デフォルトあり:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、別 DB（PAPER_TRADING_SQLITE_PATH）へ記録し MockBroker を使用
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- OPENAI_API_KEY: OpenAI 呼び出しに必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE Push）で使用
- LOG_LEVEL: DEBUG/INFO/...
- PID_FILE_PATH: 実行 engine が書き込む pid ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が出力する flag（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動で消すなら "1"
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 をセットすると .env 自動読み込みを無効化

注意: .env の自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を検出できた場合のみ行われます。

---

## 停止・フラグ操作

- 停止フラグ（run_monitoring / run_execution がチェック）
  - data/stop_requested.flag: これを作成するとポーリングループ / エンジンは次のチェックで停止します。
- KillSwitch（自動停止）
  - KillSwitch は risk_monitor の結果から data/kill.flag を書き込む可能性があります。ExecutionEngine 起動時にこの flag が存在すると起動を中止します。
  - KillSwitch.clear() により kill.flag を削除可能（Execution 起動時のクリーンアップ用途）。
- PID ファイル
  - 実行中の ExecutionEngine は PID を `data/execution.pid` に書きます。SystemMonitor はその PID の存在を確認してプロセス生存チェックを行います。PID が stale（存在しないプロセスを指す）ならファイル削除してアラート記録します。

---

## ディレクトリ構成（主要部分の説明）

以下はソース内の主要モジュールと役割の簡易一覧です（src/kabusys 以下）。

- kabusys/
  - __init__.py: パッケージ定義
  - config.py: 環境変数/設定の取得ロジック（.env 自動ロード機能含む）
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプト（paper_trading モード対応）
  - tools/
    - paper_verification_report.py: Paper Trading 検証レポート生成 CLI
  - utils/
    - process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py: SQLite ベースの監視ログ永続化層（テーブル作成・読み書き）
    - system_monitor.py: CPU/メモリ/Disk/データ鮮度/プロセス監視
    - trade_monitor.py: 滞留注文・約定異常検出
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - monitoring_engine.py: 各 Monitor の束ね（run / run_once）
    - alert_manager.py: LINE へ一方向プッシュ通知
    - kill_switch.py: kill.flag 書き込みロジック
    - streamlit_dashboard.py: Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py: 発注の高レベル API（重複検知等）
    - reconciler.py: 起動時の自動復旧（ブローカーとの照合）
    - （その他：broker_factory, execution_engine, order_repository 等が存在）
  - ai/
    - news_nlp.py: ニュースを LLM でセンチメント評価して ai_scores に書込む
    - regime_detector.py: MA200 とマクロニュースで市場レジームを判定
  - portfolio/
    - portfolio_builder.py: 候補選定・重み付け関数
    - position_sizing.py: 株数計算・集約上限調整
    - risk_adjustment.py: セクターキャップ・レジーム乗数
  - research/
    - factor_research.py: Momentum/Volatility/Value ファクター計算（DuckDB）
    - feature_exploration.py: 将来リターン・IC・統計サマリー等
  - data/ (実行時に使用される想定のディレクトリ)
    - monitoring.db（SQLite）
    - paper_trading.db（Paper Trading 用 SQLite）
    - kabusys.duckdb（DuckDB）
    - execution.pid, stop_requested.flag, kill.flag など

---

## 注意事項 / 実装上のポイント

- DB 初期化: monitoring_db.init_monitoring_db は冪等でテーブル作成と簡単なマイグレーション（カラム追加）を行います。
- Paper Trading: `KABUSYS_ENV=paper_trading` の場合、発注は MockBroker を使い Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と完全分離されます。
- LLM 呼び出し: OpenAI を利用する箇所はリトライや応答バリデーションを行い、失敗時はフォールバック（0.0）やスキップするようフェイルセーフに設計されています。必ず OPENAI_API_KEY を設定してください。
- プロセス優先度: 起動直後に set_process_priority("high") を呼んでいます。psutil による権限不足などはログでスキップされます。
- .env の自動読み込み: プロジェクトルート検出に .git または pyproject.toml を使います。CI やパッケージ配布後に別動作が必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使ってください。

---

README は開発開始向けの概要を示したものです。実運用やデプロイ時にはログローテーション、機密情報管理、監視の拡張（通知チャネル増加）、セキュリティ対策（APIキー管理）などの追加作業を行ってください。

必要であれば、この README をベースにインストール手順（requirements.txt、Dockerfile、systemd ユニット例、簡易デプロイ手順）を追加で作成します。どの形式がよいか教えてください。