# KabuSys

日本株自動売買システムのリポジトリ（ライブラリ / 実行スクリプト群）。

この README はコードベースの主要コンポーネント、セットアップ、実行方法、およびディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システムのコアモジュール群です。  
主な機能は次の通りです。

- データパイプライン（DuckDB を用いた時系列データ参照）
- ファクター計算・研究モジュール（モメンタム、ボラティリティ、バリュー等）
- ポートフォリオ構築（候補選定、重み付け、リスク調整、ポジションサイズ計算）
- 実行エンジン（ExecutionEngine）とブローカークライアントの抽象化（本番/ペーパー分離）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- AI モジュール（OpenAI を用いたニュースセンチメント／レジーム判定）
- 運用ツール（設定ウィザード、設定検証、Paper Trading レポート生成）

設計方針として、ルックアヘッドバイアスを避けるために現在日付の直接参照を最小限にし、ペーパートレード時に本番データと完全に分離するようになっています。

---

## 機能一覧（抜粋）

- 環境設定
  - .env の対話式ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
- 実行系
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV によって paper_trading を切替）
  - run_monitoring: SystemMonitor のポーリングループを起動（監視ログを SQLite に保存）
- モニタリング
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - KillSwitch: ドローダウンやポジション上限で停止フラグを書き込み
  - monitoring_db: 監視用 SQLite スキーマと永続化 API
- ポートフォリオ
  - 候補選定、等分配/スコア配分、リスク調整（セクター上限、レジーム乗数）、ポジションサイズ計算
- リサーチ
  - ファクター計算（momentum/volatility/value）、特徴量探索、IC 計算
- AI
  - news_nlp: ニュース記事を OpenAI（gpt-4o-mini）で評価し ai_scores に格納
  - regime_detector: ma200 とマクロニュースで市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレード用 DB を集計して検証レポートを出力

---

## 必要要件（概略）

主な Python ライブラリ（バージョンはプロジェクトに合わせて調整してください）:

- Python 3.9+
- duckdb
- psutil
- openai
- sqlite3（標準ライブラリ）
- PyYAML（config 検証で任意）
- その他（logging 等は標準ライブラリで賄われます）

インストール例:
```bash
pip install duckdb psutil openai pyyaml
```
（要件ファイルがある場合は `pip install -r requirements.txt` を推奨）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 環境を用意（仮想環境推奨）
3. 必要パッケージをインストール（上記参照）
4. .env の作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動で `.env` を作成（.env.example を参考に）
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 時の DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - PAPER_FILL_MODE（paper_trading 時の約定挙動: instant | partial | never | reject）
5. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も失敗扱いになります。

6. データディレクトリ（logs, data 等）を作成するか、スクリプトが自動作成します。

---

## 使い方（起動例）

- 実行エンジン（注文実行）
  - 本番/ペーパーは KABUSYS_ENV で制御。paper_trading の場合、MockBrokerClient が利用され、データは PAPER_TRADING_SQLITE_PATH に記録されます。
  ```
  python -m kabusys.run_execution
  ```
  - 実行中に停止したい場合はプロジェクトルートの data/stop_requested.flag を作成すると起動中のエンジンは検知して停止します。
  - PID ファイルは data/execution.pid（デフォルト）に書き出されます。

- 監視ループ
  - SystemMonitor のポーリングループを起動します。MONITOR_POLL_INTERVAL 環境変数で秒数を指定可能（デフォルト 60 秒）。
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 監視ループはデフォルトで Settings.sqlite_path を使用して監視ログを永続化します。
  - 停止はプロジェクトルートの data/stop_requested.flag を作成。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` で DB パスを明示可能。環境変数 PAPER_TRADING_SQLITE_PATH より優先されます。

- 設定ウィザード、検証
  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

---

## 主要設定・環境変数（よく使うもの）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- OPENAI_API_KEY: OpenAI を使う場合に必須
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: paper_trading の約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 起動時 Kill Flag を自動クリアするか（0/1）

各設定のデフォルトや検証は `kabusys.config.Settings` と `kabusys.validate_config` を参照してください。

---

## ログ・ファイル

- ログ出力:
  - デフォルトは logs/<app_name>.log（日次ローテーション、30日保持）
  - console は stdout に出力
- PID / フラグ:
  - data/execution.pid（ExecutionEngine の PID）
  - data/stop_requested.flag（手動停止フラグ）
  - data/kill.flag（KillSwitch が書き込む停止フラグ）
- DB:
  - DuckDB: data/kabusys.duckdb（分析用）
  - 監視 SQLite: data/monitoring.db
  - ペーパートレード SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時は分離）

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込みと Settings クラス定義（.env 自動ロード機能あり）
  - config_setup.py
    - .env を対話式に作成するウィザード
  - validate_config.py
    - .env と config/*.yaml の静的検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（プロセス優先度設定・DB 接続・スレッドで実行）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 指定可）
  - utils/
    - logging_setup.py: 統一的なログ設定（Stream + 日次ローテーション）
    - process_priority.py: プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py: 監視用 SQLite のスキーマ生成と永続化 API
    - system_monitor.py: システム状態・データ鮮度監視
    - trade_monitor.py: （trade の監視用モジュール群）
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - kill_switch.py: 停止フラグの生成/操作
    - monitoring_engine.py: 各モニタのまとめ（Polling）
    - alert_manager.py: （通知機能）
  - execution/
    - execution_engine.py: 実行エンジン本体（注文管理・セッション管理）
    - broker_factory.py: ブローカークライアント生成（本番/Mock 切替）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py
  - portfolio/
    - portfolio_builder.py: 候補選定・スコアソート
    - position_sizing.py: 株数決定、資金配分ロジック
    - risk_adjustment.py: セクター上限、レジーム乗数
  - research/
    - factor_research.py: ファクター計算（momentum/volatility/value）
    - feature_exploration.py: 将来リターン計算、IC、統計サマリー
  - ai/
    - news_nlp.py: ニュースから銘柄毎センチメントを算出して ai_scores に書き込む
    - regime_detector.py: ma200 + マクロニュースで市場レジーム判定
  - tools/
    - paper_verification_report.py: ペーパートレード DB 集計・検証レポート
  - data/ （実行時に作られることが多い）
    - monitoring.db, paper_trading.db, kill.flag, stop_requested.flag, execution.pid
  - logs/ （ログファイル出力先）

（各サブモジュールは README 内の「機能一覧」やコードコメントを参照してください）

---

## 運用上の注意

- KABUSYS_ENV=live の場合は本番の注文が実際にブローカーに送信されます。設定（LINE 通知や Kill Switch 等）を十分に確認してください。
- ペーパートレード時は PAPER_TRADING_SQLITE_PATH に完全にデータを分離する設計になっています。誤った DB パスの設定に注意してください。
- OpenAI を使うモジュール（news_nlp, regime_detector）は API キーとコストの管理が必要です。API の失敗はフェイルセーフとして無効化（スコア 0 等）されますが、運用ポリシーを定めてください。
- ログディレクトリ作成に失敗した場合はコンソール出力のみになります（setup_logging がその旨を警告します）。

---

## 開発者向けメモ

- テスト容易性のため、OpenAI 呼び出しや time.sleep などは patch しやすい設計（内部関数を差し替え可能）になっています。
- DB マイグレーションは簡易的にスクリプト内でカラム追加を行います（init_monitoring_db）。
- Monitor / Engine は run_once（テスト用）と run（本番ループ）を分けて設計しています。
- ログは stdout に出力することで cron / systemd などからのリダイレクトを容易にしています。

---

必要であれば、README にさらに詳細なコマンド例、.env のサンプル、API レート制御やデプロイ手順（systemd / Docker）を追記できます。追加で欲しい情報があれば教えてください。