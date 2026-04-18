# KabuSys

日本株自動売買システムの Python パッケージ（抜粋）。  
この README は、このリポジトリ内の主要スクリプト・モジュールの使い方、セットアップ手順、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関する以下の機能群を提供するモジュール群です（抜粋）:

- 実行エンジン（ExecutionEngine）と発注周りの管理（paper/live 切替対応）
- 監視コンポーネント（System / Trade / Risk モニター、Kill Switch、アラート）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出・セクター制約）
- 研究用モジュール（ファクター計算、特徴量解析）
- AI 支援モジュール（ニュースセンチメントによるスコアリング、レジーム判定）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード・検証ツール）
- 運用支援ツール（Paper Trading の検証レポート生成など）

設計上の特徴：
- 本番 DB とペーパートレード DB は分離（環境変数で切替）
- .env を用いた環境変数管理（対話ウィザードあり）
- OpenAI を用いた NLP 機能は任意（APIキーが必要）

---

## 主な機能一覧

- run_execution.py: ExecutionEngine 起動。KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper DB に記録。
- run_monitoring.py: SystemMonitor のポーリングループを起動し system_status / trade_logs / risk_logs / dashboard を更新。
- config_setup.py: 対話式 .env 作成 / 更新ウィザード。
- validate_config.py: .env と config/*.yaml の起動前検証（--strict オプションあり）。
- monitoring/*: 監視系コンポーネント群（MonitoringDB、SystemMonitor、RiskMonitor、KillSwitch、MonitoringEngine、AlertManager など）。
- portfolio/*: 銘柄選定、重み計算、ポジション決定、セクター制約、レジーム乗数。
- research/*: ファクター計算（momentum/value/volatility）、特徴量探索（forward returns, IC, summary）。
- ai/*: news_nlp（OpenAI を使ったニュースの銘柄別センチメント）、regime_detector（市場レジーム判定）。
- tools/paper_verification_report.py: Paper Trading の検証レポート出力。
- utils/*: ロギング設定、プロセス優先度 / CPU affinity 設定、その他ユーティリティ。

---

## 前提・依存パッケージ

少なくとも以下パッケージが必要です（プロジェクトの要求に応じて追加）:

- Python 3.9+
- duckdb
- psutil
- openai （AI 機能を使う場合）
- PyYAML（validate_config の YAML 検証を有効にする場合）

例（pip）:
```
pip install duckdb psutil openai PyYAML
```

開発環境では requirements.txt を用意している場合はそれを利用してください。

---

## セットアップ手順

1. リポジトリをクローン / 展開する
2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb psutil openai PyYAML
   ```
4. .env を生成または編集
   - 対話式ウィザードで生成:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは J-Quants トークンや kabu API パスワード等の必須項目を対話で入力して .env を作成します。
   - 手動で作成する場合は `.env.example` を参考に `.env` をプロジェクトルートに配置してください。
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用）。
5. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能使用時)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視用 DB、デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading の約定動作
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- LOG_DIR (ログ格納ディレクトリ、デフォルト logs/)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔、秒。デフォルト 60)
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（監視・停止フラグ関連）

---

## 使い方

### ログの設定
各起動スクリプトは内部で `kabusys.utils.logging_setup.setup_logging(app_name=...)` を呼び出します。ログは標準出力（stdout）と `logs/<app_name>.log` に日次ローテーションで出力されます。

### 実行エンジン（Execution）
- 起動:
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使い、paper DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動時に `data/stop_requested.flag` が存在すると起動を中止します。
  - 実行中は `data/execution.pid` に PID を書きます。

- 停止:
  - 監視側や運用者は `data/kill.flag` を書くことで ExecutionEngine に停止シグナルを送る仕組み（KillSwitch）があります。
  - `data/stop_requested.flag` を作成すると run_execution / run_monitoring のループは検知して終了します。

### 監視プロセス（Monitoring）
- 起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60秒）。
  - Monitoring は常に本番用の sqlite_path（Settings.sqlite_path）を使用して監視ログを記録します。
  - 監視は SystemMonitor.check_once() を定期実行し system_status / risk_logs / trade_logs / dashboard を更新します。

### 設定ウィザード・検証
- .env 作成:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

### Paper Trading 検証レポート
- ローカルの paper_trading DB から検証レポートを生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db PATH` で DB を指定、または環境変数 `PAPER_TRADING_SQLITE_PATH` を利用可能。
  - 出力は標準出力に人間向けレポート（稼働率、成立率、P95 レイテンシ等）。

### AI 機能
- ニュースセンチメント（銘柄別スコア）:
  - 関数: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`
  - OpenAI API キーが必要（引数か環境変数 OPENAI_API_KEY）。
  - raw_news / news_symbols を参照して ai_scores テーブルに書き込みます。
- レジーム判定:
  - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

---

## 停止・Kill Switch の運用

- KillSwitch（kabusys.monitoring.kill_switch）は RiskMonitor / SystemMonitor / TradeMonitor の結果を評価して `data/kill.flag` を書くことで ExecutionEngine に停止シグナルを送ります。
- `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアしますが、本番では危険なため推奨されません（デフォルト 0）。

---

## 開発・テスト時の便利なポイント

- 自動 .env ロードを無効化:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- ログディレクトリを指定:
  ```
  export LOG_DIR=/var/log/kabusys
  ```
- Process priority / CPU affinity の設定は utils.process_priority を通して行われ、スクリプト冒頭で High に設定する呼び出しがあります。権限がない場合は警告が出てスキップされます。

---

## ディレクトリ構成（抜粋）

以下はリポジトリ内の主要なモジュール・ファイルの構成です（`src/kabusys` をルートとして示す）:

- __init__.py
- config.py                      — 環境変数/設定読み込み
- config_setup.py                — .env 対話ウィザード
- validate_config.py             — 起動前検証 CLI
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor ポーリング起動スクリプト

- ai/
  - news_nlp.py                   — ニュース NLP / OpenAI 呼び出し
  - regime_detector.py            — レジーム判定
- monitoring/
  - monitoring_db.py              — SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py (想定)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

運用時のデータ・ログ配置（デフォルト）:
- data/monitoring.db              — 監視 SQLite DB（Settings.sqlite_path）
- data/paper_trading.db           — ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）
- data/execution.pid              — Execution PID（デフォルト PID_FILE_PATH）
- data/kill.flag                  — Kill Switch フラグ
- data/stop_requested.flag        — run_* が検知する停止要求フラグ
- logs/<app>.log                  — アプリケーションログ（TimedRotatingFileHandler）

---

## 例: 最小セットアップ例（手順まとめ）

1. 仮想環境作成・有効化
2. 依存インストール:
   ```
   pip install duckdb psutil openai PyYAML
   ```
3. .env 作成:
   ```
   python -m kabusys.config_setup
   ```
4. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
5. 監視起動（別プロセスで）:
   ```
   MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
   ```
6. 実行エンジン起動:
   ```
   python -m kabusys.run_execution
   ```

---

## 補足・注意事項

- 本リポジトリは重要な運用ロジック（発注等）を含みます。`KABUSYS_ENV=live` で起動すると実際に発注が行われるため、設定は慎重に行ってください。
- `.env` は絶対にリポジトリにコミットしないでください（秘密情報を含みます）。
- AI 機能は OpenAI API を使用するため、API 利用コストとレート制限に注意してください。
- DuckDB / SQLite のバージョン依存や executemany の空リスト挙動等、実行環境による差異に注意（コード内に互換性対策が含まれています）。

---

必要であれば、README に含めたいサンプル .env 内容や各 CLI の詳細なオプション説明、よくあるトラブルシュート（ログの読み方、データベースの初期化方法など）を追加で作成します。どの内容を詳しく書きますか？