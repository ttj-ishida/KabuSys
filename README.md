# KabuSys

日本株自動売買システムの一部をまとめた Python パッケージ（README）。  
このドキュメントはリポジトリ内のスクリプト・モジュール群に基づいて作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買（発注・監視・ポートフォリオ構築・リサーチ・AIによるニュース解析など）を支援するモジュール群です。  
主な機能は以下の通り：

- 実行エンジン（ExecutionEngine）による発注処理（本番 / ペーパートレード切替）
- 監視コンポーネント（System / Trade / Risk）による運用状態監視と Kill Switch
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算・セクター制限）
- リサーチモジュール（ファクター計算・特徴量探索）
- AI モジュール（ニュースのセンチメント評価、レジーム判定：OpenAI API を使用）
- ユーティリティ（ログ設定、プロセス優先度設定、DB 初期化など）
- 各種 CLI（.env の対話式ウィザード、設定検証、Paper Trading レポート生成）

パッケージバージョン:
- kabusys.__version__ == 0.1.0

---

## 機能一覧（抜粋）

- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV により paper_trading モード（MockBrokerClient）と実盤モードを切替。
  - Paper trading は専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。

- run_monitoring.py
  - SystemMonitor を定期実行して CPU / メモリ / ディスク / データ鮮度 / 実行プロセスの監視を行う。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
  - 監視ログは SQLite（デフォルト: data/monitoring.db）に永続化される。

- monitoring モジュール
  - MonitoringDB: 監視用 SQLite テーブルの初期化と CRUD。
  - SystemMonitor: システム稼働率、データ鮮度、PID ファイル確認等。
  - RiskMonitor: ハイウォーターマーク・ドローダウン監視、ポジション上限監視と risk_logs 書き込み。
  - KillSwitch: flag ファイル（data/kill.flag）により ExecutionEngine 停止要求を発行。
  - MonitoringEngine: 各モニタを束ねて定期実行、AlertManager 経由で通知。

- portfolio モジュール
  - 銘柄選定（select_candidates）、重み計算（等金額・スコア重み）、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ算出（lot 単位・資金配分・aggregate cap）

- research モジュール
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）などの統計解析ユーティリティ

- ai モジュール
  - news_nlp: raw_news を OpenAI に投げて銘柄別センチメント（ai_scores）を保存。バッチ・リトライ・バリデーション実装あり。
  - regime_detector: ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して market_regime を決定し永続化。

- utils
  - logging_setup: 統一ログ設定（stdout + 日次ローテーションファイル）
  - process_priority: 優先度 / CPU affinity 設定（psutil 利用）

- tools
  - paper_verification_report: ペーパートレード DB を集計して PASS/FAIL レポートを生成（稼働率・約定率・レイテンシ等）

---

## セットアップ手順（ローカル）

1. Python 仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - 必須（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で利用）
   - 例:
     - pip install duckdb psutil openai pyyaml

   ※ 開発用に package 管理がある場合は requirements.txt / pyproject.toml からインストールしてください。

3. パッケージをインストール（編集可能に）
   - pip install -e .

4. ディレクトリの準備（通常はスクリプトが自動作成しますが、手動で作る場合）
   - mkdir -p data logs

5. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは .env.example を参照して手動で .env を作成してください。

6. 設定検証
   - python -m kabusys.validate_config
   - 必要なら --strict を付けて警告もエラー扱いにする。

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）, デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（ai/news_nlp, ai/regime_detector が使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant/partial/never/reject）

その他は config_setup ウィザードや config/*.yaml（存在すれば）で補足。

---

## 使い方（主なコマンド）

- 環境ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録されます。
  - 停止:
    - data/stop_requested.flag を作成するとエンジンは安全に停止します。
    - システム内 KillSwitch がトリガーした場合は data/kill.flag に理由が書き込まれ実行が止まります。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番 sqlite_path を参照する仕様です（環境に依らず監視 DB は本番パスを使用）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）

- AI スコア生成 / レジーム判定（モジュール関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OpenAI API キーを参照（引数優先 -> 環境変数 OPENAI_API_KEY）

---

## 停止・キルフラグ

- data/stop_requested.flag
  - run_execution / run_monitoring の外部停止用フラグ。存在を検知するとループを終了します。

- data/kill.flag
  - KillSwitch により書き込まれる止めのフラグ（ExecutionEngine 停止指示）。
  - kill.flag が存在すると ExecutionEngine は起動を拒否したり、起動中は停止します。
  - Settings.kill_flag_clear_on_start を 1 にすると起動時に自動クリアされます（本番では 0 推奨）。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主なパッケージ構成（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（自動 .env ロード機能含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        — SQLite テーブル定義・監視 DB 操作
    - system_monitor.py       — システム監視ロジック
    - trade_monitor.py        — （存在する想定）発注ログ監視（ファイル内では参照あり）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag の作成 / 制御
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — （存在する想定）通知ロジック
  - execution/                — Execution 系コンポーネント（Engine, BrokerFactory, OrderManager 等）
  - portfolio/
    - portfolio_builder.py    — 候補選定 / 重み計算
    - position_sizing.py      — 株数計算・資金制約・lot丸め
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI）処理
    - regime_detector.py      — レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

（この README は提示されたソース群の抜粋に基づいて作成されています。該当リポジトリ全体のファイル構成は実際のリポジトリのルートを参照してください。）

---

## 注意事項 / 運用上のヒント

- 本番環境（KABUSYS_ENV=live）での運用は慎重に。validate_config の警告は必ず確認してください。
- .env は機密情報を含むため Git にはコミットしないでください（config_setup は注意書きを出力します）。
- OpenAI の呼び出しは API キーが必要で、レート制限・課金に注意してください。news_nlp と regime_detector はリトライ・フェイルセーフを備えていますが、呼び出しコストは実行回数に比例します。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます。LOG_DIR を環境変数で変更可能です。
- ペーパートレード（paper_trading）は本番用 DB と分離されるため、テスト時は KABUSYS_ENV=paper_trading を活用してください。

---

README にある使い方で不明点があれば、目的のモジュールや起動スクリプト名を教えてください。具体的な実行例や .env のサンプルを提供します。