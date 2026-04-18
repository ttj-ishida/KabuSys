# KabuSys

日本株向けの自動売買 / 研究基盤ライブラリ。  
システム監視、Execution エンジン（発注ループ）、ポートフォリオ構築、ファクター計算、ニュース NLP（LLM を使ったセンチメント評価）などを含むモジュール群です。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の用途を想定したモジュール群です。

- 発注エンジン（ExecutionEngine）による自動発注（本番 / ペーパートレード対応）
- システム監視（CPU / メモリ / ディスク / データ鮮度 / 実行プロセス監視）
- リスク監視（ドローダウン、ポジション上限など）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- リサーチ（ファクター計算、将来リターン、IC 計算など）
- ニュース NLP（OpenAI を使った銘柄別センチメント）
- 各種ツール（ペーパートレード検証レポート等）
- 設定ウィザード / 設定検証 CLI

設計方針として、DB（SQLite / DuckDB）を用いたデータ管理、外部 API は抽象化し必要に応じてモック可能、ログは統一的に管理されるようになっています。

---

## 主な機能一覧

- Execution
  - 本番/ペーパートレード切替（環境変数 KABUSYS_ENV）
  - ペーパートレード時は MockBrokerClient を使用し DB を分離（data/paper_trading.db）
  - 停止フラグ / PID ファイルでプロセス制御
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、Execution プロセスの生存確認、データ鮮度
  - TradeMonitor / RiskMonitor：注文滞留やドローダウン・ポジション上限の監視
  - KillSwitch：条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine：複数監視を統合してポーリング実行
- Portfolio
  - 候補選定（スコア順）
  - 等重 / スコア重み付け
  - ポジションサイズ計算（リスクベース、単元調整、aggregate cap）
  - セクター上限フィルタ、レジーム乗数
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を参照）
  - 将来リターン、IC 計算、統計サマリ
- AI（OpenAI）
  - ニュース記事の銘柄別センチメント（gpt-4o-mini 等）
  - マクロニュース + ETF MA200 乖離による市場レジーム判定
- ツール
  - ペーパートレードの検証レポート生成（期間指定可）
- 設定関連
  - 対話式 .env 生成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）

---

## 必要依存パッケージ（代表例）

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config/*.yaml のパース検証を行う場合）
- （SQLite は標準ライブラリで提供）

インストール例（プロジェクトに requirements.txt がない場合の例）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

※ 実際のパッケージ管理はプロジェクトの配布方法（pyproject.toml / requirements.txt）に従ってください。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化する。

2. 必要パッケージをインストールする（上記参照）。

3. .env を作成する
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードでは J-Quants トークン、kabu API パスワード、KABUSYS_ENV（development|paper_trading|live）等を設定できます。
   - 手動で作成する場合は .env.example を参考に `.env` に必須項目を設定してください。

4. 設定の検証:
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. DB / ディレクトリ
   - デフォルトの DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
   - ログディレクトリ（デフォルト）: logs/
   - 必要なディレクトリは起動時に自動生成される場合がありますが、権限等を確認してください。

---

## 主な環境変数（抜粋）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- システム / 動作:
  - KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL
  - LOG_DIR : ログ出力先ディレクトリ（デフォルト: logs）
- DB 関連:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
- ペーパートレード:
  - PAPER_FILL_MODE : instant | partial | never | reject（デフォルト: instant）
- Monitoring:
  - MONITOR_POLL_INTERVAL : 監視ループのポーリング間隔（秒・デフォルト: 60）
- Kill / PID:
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START : 1 にすると起動時に kill.flag を自動クリア（注意: 本番では 0 推奨）
- OpenAI:
  - OPENAI_API_KEY : ニュース NLP / レジーム判定で必要

.env の自動ロード:
- プロジェクトルートに基づき `.env` と `.env.local` を自動的に読み込みます（OS 環境変数を上書きしない）。
- 自動ロードを無効にするには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方

- ExecutionEngine（発注ループ）起動:
  ```
  python -m kabusys.run_execution
  ```
  説明:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
  - 起動時に data/stop_requested.flag や data/kill.flag が存在する場合は起動を抑止または停止処理を行う実装になっています。
  - 実行中は pid ファイル（data/execution.pid）を書きます。

- Monitoring（監視ループ）起動:
  ```
  python -m kabusys.run_monitoring
  ```
  説明:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60秒）。
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を参照してログを書きます（環境にかかわらず）。
  - stop_requested.flag を検知するとループを終了します。

- 設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- OpenAI を使う機能（ニュース NLP / レジーム判定）:
  - 環境変数 OPENAI_API_KEY を設定してください（または関数呼び出し時に api_key を渡す）。
  - API 呼び出しはリトライやクリップ等が組み込まれており、失敗時は安全側でフォールバックします（例: macro_sentiment=0.0）。

---

## ロギング

- kabusys.utils.logging_setup.setup_logging を通じて一元管理されます。
- 出力:
  - コンソール（stdout）
  - ファイル（ログディレクトリ内 `<app_name>.log`、日次ローテーション、既定で 30 日分保持）
- ログ設定:
  - LOG_LEVEL 環境変数または setup_logging の引数で指定
  - LOG_DIR 環境変数でログ出力先を変更可能

---

## 停止制御 / Kill Switch

- KillSwitch はリスク条件（ドローダウン、ポジション上限等）に基づき data/kill.flag を書き込み、ExecutionEngine 側はこれを検出して安全に停止します。
- 手動で停止するには stop フラグ / kill.flag を作成しても良い（実装により stop_requested.flag も利用）。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では推奨されません）。

---

## ディレクトリ構成（主要ファイル）

以下はソースツリー内の主要なパッケージとファイルの概要（src/kabusys 以下）です:

- __init__.py
  - パッケージ初期化、__version__ 定義

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL で間隔指定可能

- run_execution.py
  - ExecutionEngine 起動スクリプト
  - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB を使用

- config.py
  - Settings クラス: 環境変数読み取り・検証、.env 自動ロードロジック

- config_setup.py
  - 対話式 .env 作成ウィザード

- validate_config.py
  - 起動前チェック（必須環境変数、パス、config/*.yaml の存在/パース等）

- utils/
  - logging_setup.py : ログハンドラ設定ユーティリティ
  - process_priority.py : プロセス優先度 / CPU affinity の設定ユーティリティ

- monitoring/
  - monitoring_db.py : SQLite を使った監視ログ永続化層（テーブル作成 / マイグレーション含む）
  - system_monitor.py : CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - risk_monitor.py : ドローダウン / ポジション上限監視
  - trade_monitor.py : （注文監視、ファイルに含まれる）
  - monitoring_engine.py : 各 Monitor を束ねる実行ループ
  - kill_switch.py : kill.flag 書込みロジック
  - alert_manager.py : LINE 等への通知管理（実装参照）

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - 発注ロジック・リスクチェック・ブローカー抽象化層

- portfolio/
  - portfolio_builder.py : 候補選定・重み計算
  - position_sizing.py : 発注株数計算（単元調整、aggregate cap）
  - risk_adjustment.py : セクター上限・レジーム乗数

- research/
  - factor_research.py : Momentum / Volatility / Value 等のファクター計算（DuckDB 使用）
  - feature_exploration.py : 将来リターン / IC / 統計サマリ

- ai/
  - news_nlp.py : ニュース記事から銘柄別センチメントを OpenAI で算出し ai_scores に書込
  - regime_detector.py : マクロ + ETF MA200 を使った日次レジーム判定

- tools/
  - paper_verification_report.py : ペーパートレード検証レポート生成スクリプト

- data/
  - 実行時に使用されるフラグ / DB / PID ファイル類（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag）

（注）上記は主要ファイルの抜粋です。実際の全ファイル構成はリポジトリ内を参照してください。

---

## よくある注意点 / 運用メモ

- KABUSYS_ENV を `live` にすると本番動作になります。LINE 通知や kill flag の設定など運用設定を十分確認してください。
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup でも注意書きがあります）。
- OpenAI を使う部分は API 呼び出しにネットワークと料金が発生します。API キー管理とコストに注意してください。
- DuckDB / SQLite のファイルのバックアップ・保全、ログローテーション先のディスク容量には注意してください。
- process_priority.set_process_priority は権限によって失敗する可能性があります（警告ログに留める実装）。

---

## 貢献 / 開発

- ローカル開発は仮想環境推奨。単体モジュールは DB をモックしてテスト可能な構造になっています。
- 既存の CLI:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring
  - python -m kabusys.tools.paper_verification_report

---

この README はコードベース（src/kabusys）を参照して作成しています。追加でドキュメント化したい箇所（API 詳細、設計ドキュメント、運用手順、デプロイ例等）があれば教えてください。