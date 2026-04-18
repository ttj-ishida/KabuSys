# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README（日本語）

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコアライブラリ群です。  
主な責務は以下を含みます。

- バックテスト／リサーチ用のファクター計算（DuckDB を利用）
- ポートフォリオ構築・ポジションサイズ計算
- ExecutionEngine（発注）と Monitoring（監視）コンポーネント
- Paper Trading（ペーパートレード）と本番環境の分離
- ニュース NLP（OpenAI）を使ったセンチメント評価・レジーム判定
- 運用補助ツール（設定ウィザード、設定検証、検証レポート等）

設計上のポイント：
- 設定は .env ファイル / 環境変数で管理
- DuckDB（分析用）、SQLite（監視・orders 用）を併用
- AI モジュールは OpenAI（gpt-4o-mini）を利用（APIキー必須）
- Paper Trading は本番データベースと完全分離（data/paper_trading.db を使用）

---

## 機能一覧（抜粋）

- 設定管理
  - .env 自動ロード、対話式ウィザード（config_setup）、設定検証（validate_config）
- 実行エンジン
  - run_execution: ExecutionEngine の起動スクリプト（Paper / Live 切替対応）
- 監視
  - run_monitoring: SystemMonitor のポーリングループ起動
  - MonitoringEngine、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、AlertManager（ログ・DB連携）
- ポートフォリオ構築
  - 銘柄選定、重み付け、ポジションサイズ計算、セクター制約、レジーム乗数
- リサーチ
  - ファクター計算（momentum/value/volatility）、先行リターン、IC 計算、統計サマリー
- AI（OpenAI）
  - ニュースから銘柄別センチメント算出（news_nlp）
  - マクロニュース + ETF MA200 を用いた市場レジーム判定（regime_detector）
- ツール
  - paper_verification_report: Paper Trading の検証レポート生成ツール

---

## 前提（推奨）

- Python 3.10+
- 主な外部ライブラリ
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- SQLite（標準ライブラリで使用）
- ネットワーク接続（OpenAI を利用する場合）

requirements.txt は本リポジトリに含まれていない場合があるため、下記を参考にインストールしてください：

例:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

2. 依存パッケージをインストール
   ```
   pip install duckdb psutil openai PyYAML
   ```

3. 環境変数（.env）の初期作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは `.env`（デフォルト）に必要なキーを対話式で書き込みます。作成後は設定検証を実行してください。

4. 設定検証
   ```
   python -m kabusys.validate_config
   # 厳密モード（警告を失敗扱い）:
   python -m kabusys.validate_config --strict
   ```

5. 必要なデータディレクトリを作成（通常はスクリプトで自動作成されますが確認推奨）
   - data/
   - logs/

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）  
  - paper_trading の場合、専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必須）
- PAPER_FILL_MODE: Paper Trading のフィルモード（instant/partial/never/reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
- PID_FILE_PATH / KILL_FLAG_PATH: pid ファイル・kill flag のパス（デフォルト data/ 以下）

自動 .env ロード:
- デフォルトでプロジェクトルートの `.env` および `.env.local` を自動読み込みします。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 実行方法（コマンド例）

- ExecutionEngine を起動（通常はデーモン化せず CLI で実行）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV により paper_trading と live の動作が切り替わります。
  - paper_trading では MockBrokerClient を使用し DB は data/paper_trading.db に記録されます。

- Monitoring（ポーリング）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書きできます（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を常に参照します（環境に依らず）。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート出力
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パス指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

---

## 運用に関する注意点

- kill.flag / stop_requested.flag
  - 停止シグナルはフラグファイル（デフォルト: data/kill.flag、data/stop_requested.flag）でやり取りします。KillSwitch が設定条件を満たすと `kill.flag` を作成します。
  - `KILL_FLAG_CLEAR_ON_START` を 1 にすると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨します。

- ログ
  - ログは `kabusys.utils.logging_setup.setup_logging` により stdout と `logs/<app_name>.log` に日次ローテーションで出力されます（30 日保持）。

- Paper Trading と本番の分離
  - `KABUSYS_ENV=paper_trading` の場合、専用の SQLite（PAPER_TRADING_SQLITE_PATH）に書き込まれ、本番 DB と分離されます。

- OpenAI 利用
  - AI コンポーネント（news_nlp, regime_detector 等）は OpenAI API（gpt-4o-mini）を利用します。API キーは `OPENAI_API_KEY` または関数引数で指定してください。
  - API 呼び出しはレート制限や障害に備えリトライやフェイルセーフ実装が入っていますが、API 料金と利用制限に注意してください。

- プロセス優先度
  - 実行スクリプトは起動時にプロセス優先度を "high" に設定しようとします（psutil による）。権限が不足する場合は警告でスキップされます。

---

## ディレクトリ構成（主要ファイル / モジュール）

- src/kabusys/
  - __init__.py: パッケージ定義
  - config.py: 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py: 対話式 .env ウィザード
  - validate_config.py: 起動前設定検証 CLI
  - run_execution.py: ExecutionEngine 起動スクリプト
  - run_monitoring.py: SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py: Paper Trading 検証レポート
  - portfolio/
    - portfolio_builder.py: 銘柄選定・重み計算
    - position_sizing.py: 発注株数決定・リスク制限
    - risk_adjustment.py: セクターキャップ、レジーム乗数
  - research/
    - factor_research.py: ファクター計算（momentum/value/volatility）
    - feature_exploration.py: IC・統計・将来リターン計算
  - ai/
    - news_nlp.py: ニュース NLP（OpenAI）による銘柄スコアリング
    - regime_detector.py: レジーム判定（ETF MA200 + マクロ NLP）
  - monitoring/
    - monitoring_db.py: SQLite テーブル作成・簡易永続層
    - monitoring_engine.py: 各モニタの統合ループ
    - system_monitor.py: システム状態・データ鮮度監視
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - kill_switch.py: kill.flag の制御
    - ...（TradeMonitor / AlertManager 等の実装が想定されます）
  - utils/
    - logging_setup.py: 共通ログ設定
    - process_priority.py: プロセス優先度 / CPU affinity 設定
  - portfolio, research, ai, monitoring の詳細実装ファイル

- data/ (デフォルト DB / flag / pid 等が配置される想定)
  - monitoring.db (デフォルト)
  - paper_trading.db (paper trading 用)
  - kabusys.duckdb (DuckDB)
  - kill.flag, stop_requested.flag, execution.pid

- logs/
  - execution.log, monitoring.log, ...（日次ローテート）

---

## 開発・テストに関するヒント

- 設定検証（validate_config）は起動前チェックに便利です。`--strict` で警告も失敗扱いにできます。
- AI モジュールは OpenAI SDK のエラー（429, timeouts, 5xx）をリトライする設計ですが、ユニットテストではネットワークを呼ばないようにモック（patch）してテストすることを推奨します（コード内にも patch 対応箇所あり）。
- DuckDB を用いたリサーチ関数は接続を引数として受け、テスト時は小規模な in-memory DB を用意して検証できます。

---

## 最後に（運用上の注意）

本システムは実際の発注を行う可能性があるため、`KABUSYS_ENV=live` 設定での起動は慎重に行ってください。特に `KILL_FLAG_CLEAR_ON_START=1` や未設定の通知先（LINE）など、本番運用で危険になり得る設定は validate_config で警告が出ます。

不明点や追加ドキュメントが必要であれば、関心のあるモジュール（例: ExecutionEngine, OrderManager, BrokerClientFactory）のソースファイルを指定して頂ければ、詳細な README / 使用例を追記します。