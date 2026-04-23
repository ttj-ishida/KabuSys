# KabuSys

日本株向け自動売買フレームワークのリファレンス実装（モジュール群、監視・実行エンジン、リサーチ・AI補助など）。  
この README はリポジトリ内の主要スクリプト／モジュールの使い方、セットアップ手順、ディレクトリ構成をまとめたものです。

## 概要
KabuSys は次の機能を持つコンポーネント群で構成されています。

- ExecutionEngine：発注・注文管理・リスク管理を行うエンジン（本番 / ペーパートレード対応）
- MonitoringEngine：システム稼働状況、注文ログ、リスク状態をポーリングして監視・アラート・Kill Switch を発動
- Portfolio モジュール：銘柄選定、重み付け、ポジションサイズ計算、セクター制約などの純粋関数群
- Research モジュール：ファクター計算・特徴量解析（DuckDB を想定）
- AI モジュール：OpenAI を利用したニュースセンチメント評価・市場レジーム判定
- ツール群：Paper Trading の検証レポート生成などの CLI スクリプト
- 設定ユーティリティ：.env を対話的に生成するウィザード、起動前検証ツール

重要な設計方針（抜粋）：
- 本番/ペーパートレード DB は分離（KABUSYS_ENV=paper_trading の場合は paper_trading.db を使用）
- 監視（monitoring）は環境にかかわらず本番用 sqlite_path を使用してログを一元化
- AI 系処理は API キー必須（OPENAI_API_KEY）
- ルックアヘッドバイアス防止のため日付参照は外部引数（target_date）ベース

## 機能一覧（主な機能）
- 実行系
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - ブローカークライアントの抽象化（MockBroker 対応）
  - 注文管理、リスク管理、オーダーリコンシリエーション
- 監視系
  - SystemMonitor（CPU/メモリ/ディスク、Execution プロセス存在チェック、データ鮮度チェック）
  - TradeMonitor（滞留注文・約定異常検出）
  - RiskMonitor（ドローダウン・ポジション数閾値監視）
  - KillSwitch（閾値超過時に data/kill.flag を書き込み Execution 停止）
  - MonitoringEngine（各 Monitor を束ねるポーリングループ）
- ポートフォリオ構築
  - 候補選定、等重/スコア重み付け、セクターキャップ、レジーム乗数、ポジションサイズ計算（単元丸め含む）
- リサーチ
  - モメンタム／ボラティリティ／バリューなどのファクター計算（DuckDB 参照）
  - 将来リターン・IC 計算、統計サマリー
- AI
  - ニュース記事のセンチメント評価（OpenAI を利用、ai_scores テーブルへ書き込み）
  - 市場レジーム判定（ma200 とマクロセンチメントの合成）
- ツール
  - Paper Trading 検証レポート生成（src/kabusys/tools/paper_verification_report.py）
- 設定補助
  - .env 対話型生成ウィザード（src/kabusys/config_setup.py）
  - 設定検証 CLI（src/kabusys/validate_config.py）

## 必要条件 / 依存パッケージ
最低限必要な Python パッケージ（環境により追加が必要）:
- Python 3.9+（推奨）
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（設定ファイルの検証で任意）
- （標準ライブラリ: sqlite3 等）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```
※requirements.txt がある場合はそれを利用してください（本リポジトリの例では明示的に含まれていません）。

## セットアップ手順
1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・依存パッケージをインストール（上記参照）

3. .env を作成（対話ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは J-Quants トークンや kabuステーション API パスワード、DB パスや実行環境 (KABUSYS_ENV) などを対話的に設定し .env を出力します。
   生成後、必要に応じて .env を編集してください。

4. 設定検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告も失敗扱いになります:
   ```
   python -m kabusys.validate_config --strict
   ```

5. ログディレクトリ
   デフォルトでは logs/ に日次ローテーションでログが書かれます。必要に応じて LOG_DIR 環境変数で変更できます。

## 主要な環境変数（主なもの）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
  - paper_trading: 発注は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録
  - live: 実口座で発注されます（注意）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必須）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant / partial / never / reject）

## 使い方（起動 / 実行）
- ExecutionEngine を起動（実際に発注する可能性があるため KABUSYS_ENV に注意）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）へ記録します。
  - 実行中は data/execution.pid に PID を書き込みます（設定に応じて変更可）。
  - 停止指示は data/stop_requested.flag を作成（Monitoring の stop フラグと共通）。
  - Kill Switch（監視が閾値検出時に data/kill.flag を書き込み）によって ExecutionEngine を停止できます。

- MonitoringEngine（または単体 SystemMonitor を用いるスクリプト）を起動
  - 直接のエントリポイント: run_monitoring.py（ポーリングループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 注意: monitoring は環境変数にかかわらず本番用 sqlite_path（SQLITE_PATH）を利用してログを残します。

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  または環境変数で DB を指定:
  ```
  PAPER_TRADING_SQLITE_PATH=data/paper_trading.db python -m kabusys.tools.paper_verification_report
  ```

- AI スコアリング（プログラム的に呼び出す）
  - ニュースセンチメント:
    - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
    - OPENAI_API_KEY を環境変数に設定するか、api_key を渡してください。
  - レジーム判定:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

## 停止・Kill フラグの扱い
- data/stop_requested.flag: run_execution/run_monitoring が存在を検知してループを終了（手動停止用）
- data/kill.flag: Monitoring の KillSwitch が書き込むと ExecutionEngine の起動を拒否し、既に稼働中なら停止指示を出す運用想定
- KILL_FLAG_CLEAR_ON_START 環境変数が 1 のときは起動時に kill.flag を自動クリア（本番では 0 推奨）

## ロギング
- 共通ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution"など)
- 出力:
  - コンソール（stdout）
  - 日次ローテーションファイル: logs/<app_name>.log （デフォルト）
- ログレベルは LOG_LEVEL または setup_logging の引数で制御

## ディレクトリ構成（主なファイル）
以下はリポジトリ内の主要な Python モジュールの概観（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/.env ロード・Settings クラス
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - execution/                 — 実行系（BrokerFactory, ExecutionEngine, OrderManager など）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化レイヤ
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/ (ランタイムで生成されることが多い)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)
    - kill.flag, stop_requested.flag, execution.pid など

## 追加の注意点 / 運用メモ
- KABUSYS_ENV=live をセットすると本番発注が行われます。資格情報や通知設定（LINE 等）を事前に十分に確認してください。
- モニターは本番 sqlite DB を書き込むため、紙上でのテストや検証は paper_trading モードを使い DB 分離を行ってください。
- AI 機能を利用する場合は OPENAI_API_KEY を設定してください。API 利用にはコストとレート制限があります。
- process_priority（utils/process_priority.py）でプロセス優先度を上げようとしますが、環境や権限により失敗する場合があります（警告ログのみ）。
- DuckDB を用いた分析・ファクター計算は prices_daily / raw_financials / raw_news 等のテーブルが前提です。データ投入パイプラインを別途用意してください。

---

以上が本リポジトリの README 相当の説明です。README をさらにプロジェクト固有の導入手順やチュートリアル（最小実行例、CI 設定、デプロイ手順など）で拡充したい場合は、どの項目を追加したいか教えてください。