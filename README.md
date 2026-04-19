# KabuSys

日本株自動売買システムのサンプル実装（KabuSys）。  
この README はコードベースの主要機能・セットアップ・使い方・ディレクトリ構成を日本語でまとめたものです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要機能を備えた自動売買プラットフォームの構成要素群です。

- 注文実行エンジン（ExecutionEngine） — ブローカー連携、オーダー管理、リスク管理、照合
- 監視サブシステム（Monitoring） — システム稼働性・注文流通・リスク監視、Kill Switch
- ポートフォリオ構成（Portfolio） — 候補選定、重み算出、ポジションサイズ計算、セクター制限・レジーム補正
- リサーチ（Research） — ファクター計算（Momentum/Volatility/Value）、特徴量探索、IC計算等（DuckDB ベース）
- AI 関連（AI） — ニュース NLP（OpenAI）によるセンチメント、レジーム判定
- ユーティリティ — 設定ウィザード、設定検証、ログ/プロセス優先度設定、各種ツール（例: ペーパートレード検証レポート）

設計方針の一部：
- DuckDB と SQLite を分けて使用（分析は DuckDB、運用ログは SQLite）
- 環境変数 / .env による設定管理（自動ロード機能あり）
- Paper Trading と Live を明確に分離（Paper は専用 SQLite を使用）
- 外部 API 呼び出し（OpenAI 等）は明示的に API キーを要求

---

## 主な機能一覧

- run_execution.py: ExecutionEngine の起動スクリプト
  - KABUSYS_ENV=paper_trading 時は MockBroker を使用し paper_trading.db に記録
  - 起動時に PID ファイル（data/execution.pid）を扱う、stop フラグによる停止対応
- run_monitoring.py: SystemMonitor をポーリングする監視プロセス起動スクリプト
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き（デフォルト 60 秒）
  - 監視は本番用 sqlite_path を常に使用（KABUSYS_ENV に依存しない）
- config_setup.py: 対話式 .env 生成ウィザード
- validate_config.py: 起動前の設定検証 CLI（--strict で警告も失敗扱い）
- tools/paper_verification_report.py: ペーパートレード検証レポート生成
- portfolio/*: 候補選定、重み付け、リスク調整、ポジションサイズ計算
- research/*: DuckDB を使ったファクター計算（momentum/volatility/value）、IC・統計
- ai/news_nlp.py: OpenAI によるニュースセンチメント集計（ai_scores テーブルへ永続化）
- ai/regime_detector.py: 市場レジーム判定（ma200 + マクロセンチメント統合）
- monitoring/*: DB 永続化（monitoring_db）、System/Trade/Risk Monitor、KillSwitch、MonitoringEngine
- utils/*: ログ設定（TimedRotatingFileHandler 等）、プロセス優先度・CPU affinity 設定

---

## 前提・依存関係

推奨 Python バージョン: 3.9+

主な外部ライブラリ（必須または任意）:
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML (validate_config で YAML 検証を行う場合に推奨)
- SQLite（標準ライブラリに含まれる）

（requirements.txt は含まれていないため、必要なライブラリを個別に pip でインストールしてください）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## 環境変数（主要なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要なオプション:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレード時の約定モード（instant / partial / never / reject）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログディレクトリ（デフォルト: logs）
- OPENAI_API_KEY — OpenAI を使う場合の API キー
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知（任意）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか（"1" または "0"）

自動 .env 読み込み:
- プロジェクトルートにある .env および .env.local が自動で読み込まれます（OS 環境変数が優先）。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## セットアップ手順

1. リポジトリをクローン
2. Python 仮想環境を準備して必要なパッケージをインストール
   - 例: pip install duckdb psutil openai PyYAML
3. データ・ログディレクトリを作成（通常は自動作成されますが手動で用意することも可）
   - data/, logs/
4. .env を作成
   - 対話式ウィザードを使用:
     ```
     python -m kabusys.config_setup
     ```
   - または .env.example を参考に手動で作成
5. 設定を検証:
   ```
   python -m kabusys.validate_config
   ```
   --strict オプションで警告も失敗扱いにできます。

---

## 使い方（起動・操作）

基本的な実行例（仮想環境をアクティベート済みで .env を適切に設定した前提）。

- ExecutionEngine を起動（注文実行プロセス）
  ```
  python -m kabusys.run_execution
  ```
  補足:
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用して data/paper_trading.db に記録します。
  - 起動前に data/stop_requested.flag が存在すると起動を行わず終了します。
  - 実行中は data/execution.pid が書かれます。停止は stop flag（data/stop_requested.flag）または Kill Switch による kill.flag（data/kill.flag）で行います。

- Monitoring を起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  補足:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定できます（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は KABUSYS_ENV に関係なく本番用の sqlite_path を使用します。
  - 停止はプロジェクトルート/data/stop_requested.flag を作成することで次のポーリング時に終了します。

- ペーパートレード検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  --db オプションで PAPER_TRADING_SQLITE_PATH を上書きできます。

- AI 機能（ニュース NLP / レジーム判定）
  - 環境変数 OPENAI_API_KEY が必要
  - モジュール API を直接呼び出して使用します（例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）

- 設定検証（CLI）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

停止・安全機構:
- Kill Switch（監視が条件を満たすと data/kill.flag を書き込み）により ExecutionEngine を停止できます。
- 管理スクリプトはフラグファイル（data/stop_requested.flag, data/kill.flag）を使って起動/停止の制御を行います。

ログ:
- デフォルトは logs/<app_name>.log（日次ローテーション、30日保持）
- setup_logging 関数により標準出力にも同一ログが出力されます。

プロセス優先度:
- 起動時に set_process_priority("high") を呼び出します（OS によっては権限不足で設定できない場合があります）。

---

## 主要ファイル / コマンドまとめ

- python -m kabusys.config_setup — .env 対話ウィザード
- python -m kabusys.validate_config — 設定検証
- python -m kabusys.run_execution — ExecutionEngine 起動
- python -m kabusys.run_monitoring — Monitoring 起動
- python -m kabusys.tools.paper_verification_report — ペーパートレード検証レポート

---

## ディレクトリ構成（抜粋）

（ソースのルートは src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env の読み込み・Settings
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py             — ログ設定ユーティリティ
    - process_priority.py          — 優先度 / CPU affinity ユーティリティ
  - execution/                      — 注文実行関連（Engine, OrderManager, RiskManager 等）
  - monitoring/
    - monitoring_db.py             — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
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
  - tools/
    - paper_verification_report.py

データ / ログファイル（デフォルトパス）:
- data/kabusys.duckdb
- data/monitoring.db
- data/paper_trading.db
- data/execution.pid
- data/kill.flag
- data/stop_requested.flag
- logs/<app_name>.log

---

## 注意事項 / 運用メモ

- 本番運用（KABUSYS_ENV=live）の際は .env の内容・アクセス権限を厳重に管理してください。
- .env は絶対に VCS にコミットしないでください（config_setup にもその旨の注記あり）。
- run_monitoring は監視用 DB（SQLITE_PATH）を直接操作します。監視は環境にかかわらず本番用 sqlite_path を参照します。
- OpenAI 関連は API 利用料が発生します。API キーは環境変数で安全に渡してください。
- process priority の設定は OS や権限に依存します。権限不足の場合は警告が出てスキップされます。
- データ鮮度／ログ構造は monitoring_db.py に定義されています。DB マイグレーション（カラム追加）は実行時に自動で試みられます。

---

この README はコード内のドキュメント文字列・設計コメントに基づいて作成しています。さらに詳細な導入手順や運用手順（デプロイ、監視ポリシー、回復手順等）が必要であれば、目的に合わせて別途ドキュメントを作成できます。必要なら教えてください。