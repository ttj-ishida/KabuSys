# KabuSys (README)

日本株自動売買システム — 軽量な調査 / シグナル生成 / 発注 / 監視を行うモジュール群のコレクションです。  
この README はリポジトリ内のコード（src/kabusys 以下）を基に、セットアップと基本的な使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株自動売買用のコンポーネント群を提供します。主な責務は以下の通りです。

- データ基盤（DuckDB）を利用したファクター計算・リサーチ（research）
- ポートフォリオ構築、ポジションサイジング、リスク調整（portfolio）
- 発注エンジン（ExecutionEngine）および注文管理、リスク管理（execution）
- 監視モジュール（System/Trade/Risk）と Kill Switch による安全停止（monitoring）
- AI を利用したニュース NLP（OpenAI 経由）のスコアリング（ai）
- ユーティリティ群（ログ設定、プロセス優先度設定、設定ウィザードなど）
- ペーパートレーディング用のレポート生成スクリプト（tools）

設計方針として、ルックアヘッドバイアスを避ける実装、DB の分離（ペーパーと本番）、冪等性を重視した DB 書き込み、安全なフォールバック（API 失敗時は中立化）などが取り入れられています。

---

## 主な機能一覧

- research
  - calc_momentum / calc_volatility / calc_value：DuckDB 上でファクターを計算
  - calc_forward_returns / calc_ic：特徴量探索・相関・IC 計算
- portfolio
  - 候補選定（select_candidates）、重み計算（等金額 / スコア加重）
  - position sizing（calc_position_sizes）、セクター上限（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）
- execution
  - ExecutionEngine（発注実行）、BrokerClientFactory（本番/ペーパー切替）、OrderManager、RiskManager、Reconciler
  - ペーパートレードは MockBroker を使用し DB を分離
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor と MonitoringEngine による定期監視
  - MonitoringDB: SQLite に監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）を永続化
  - KillSwitch: リスクトリガで data/kill.flag を書き込み ExecutionEngine を停止
- ai
  - news_nlp.score_news：OpenAI を用いたニュースセンチメントスコアリング（ai_scores への書込み）
  - regime_detector.score_regime：MA とマクロニュースを合成して市場レジーム判定
- ツール
  - config_setup: .env の対話式ウィザード生成
  - validate_config: 起動前に環境設定 / config/*.yaml を検証
  - tools.paper_verification_report: ペーパートレードの検証レポート生成

---

## 依存関係（主なもの）

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config YAML の詳細検証を行う場合、なくても動作するが検証はスキップされます）

必要パッケージはプロジェクトの Poetry/requirements 等に合わせてインストールしてください。

---

## セットアップ手順

1. リポジトリをクローンし、Python 環境を作成（venv / conda 等）し依存をインストール。

   例（pip）:
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. .env の作成（対話式ウィザード推奨）:
   ```
   python -m kabusys.config_setup
   ```
   ウィザードでは必須項目（J-Quants トークン、kabu API パスワード等）を尋ねられます。完了するとプロジェクトルートに `.env` が保存されます。

3. 設定検証（起動前チェック）:
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする（--strict）
   python -m kabusys.validate_config --strict
   ```

4. データディレクトリの作成（必要に応じて）:
   - デフォルト DB / ログ / data ディレクトリが生成されますが、手動で作成して権限確認しておくと安全です。
   - ログ：デフォルト logs/（環境変数 LOG_DIR で変更可能）

5. （AI 機能を使用する場合）OpenAI API キーを環境に設定:
   ```
   export OPENAI_API_KEY="sk-..."
   ```
   または .env に追記。

---

## 環境変数（主要なものとデフォルト）

Settings クラスで扱う主要な環境変数（デフォルト値や意味）を抜粋します。

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN (任意、通知用)
- LINE_USER_ID (任意、通知用)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db) — 監視 DB（本番）
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — ペーパートレード専用 DB
- PAPER_FILL_MODE (ペーパー時の約定挙動: instant|partial|never|reject, デフォルト "instant")
- KABUSYS_ENV (development|paper_trading|live, デフォルト "development")
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト "INFO")
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0|1, デフォルト 0)
- LOG_DIR (ログ出力先ディレクトリ、setup_logging で使用)

自動で .env を読み込む機能は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト用途）。

簡易 .env 例（実運用では秘密値は必ず保護）:
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

---

## 使い方（主要なスクリプト / 実行コマンド）

- 環境作成（.env ウィザード）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動（デモ / 本番 / ペーパーは KABUSYS_ENV で切替）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使い PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録され本番 DB とは分離されます。
  - run_execution は data/stop_requested.flag を検出するとエンジンを停止します。PID ファイル（デフォルト data/execution.pid）を生成します。

- Monitoring（監視ループ）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔の上書き: 環境変数 MONITOR_POLL_INTERVAL を秒数で指定（デフォルト 60）
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 監視は monitoring DB (Settings.sqlite_path; 監視テーブルは常に本番 sqlite_path を使用) と DuckDB を使用します。
  - data/stop_requested.flag を検出するとループを終了します。

- Kill Switch（手動書き込みで Execution を停止）
  - monitoring により条件が満たされると data/kill.flag が書き込まれ、Execution 側で検出され停止します。
  - 手動でクリアするには:
    ```
    # 注意：本番では慎重に扱う
    rm -f data/kill.flag
    ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB は data/paper_trading.db。--db でパス指定可。
  - レポートは稼働率、注文成功率、送信率、レイテンシなどを算出し PASS/FAIL を出力します。

- AI 機能（ニュース NLP / レジーム判定）
  - ai.news_nlp.score_news や ai.regime_detector.score_regime は OpenAI API キー (OPENAI_API_KEY) が必要です。
  - スクリプトから呼ぶ場合は API キーを環境変数に設定してください。

---

## 実行時のログ

- ログ設定は kabusys.utils.logging_setup.setup_logging を統一的に使用します。
- デフォルトで stdout（コンソール）と日次ローテーションファイル（logs/<app_name>.log）へ出力されます。ログディレクトリは LOG_DIR 環境変数で変更可能。
- ログレベルは LOG_LEVEL で制御します。

---

## 停止・制御フラグ

- data/stop_requested.flag
  - run_execution/run_monitoring はこのファイルをチェックしてプロセスの安全な停止を行います（スクリプトディレクトリ下の data に配置されます）。
- data/kill.flag
  - KillSwitch が危険と判断した場合に作成され、ExecutionEngine に対する停止シグナルになります。
- PID ファイル:
  - 実行時に data/execution.pid を生成する（デフォルト）。プロセス管理のために利用。

---

## トラブルシューティングのヒント

- .env 自動読み込みを無効にしたい場合は:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 関連のエラー:
  - OPENAI_API_KEY が未設定の場合、明示的なエラーや例外が発生します。API 呼び出しは一定のリトライ・フォールバックメカニズムを持ちますが、キーは必須です。
- DB ファイルやログディレクトリの権限を確認してください（書き込み権限が必要）。
- validate_config の出力を参考に、欠落環境変数や設定ファイル不足を解消してください。
- ペーパートレードと本番の DB は分離されています。ペーパー環境で本番 DB を上書きしないように KABUSYS_ENV を確認してください。

---

## ディレクトリ構成（抜粋）

プロジェクトルート下 src/kabusys の主要ファイル・ディレクトリ:

- kabusys/
  - __init__.py
  - config.py                    — 環境変数／設定読み込み（Settings）
  - config_setup.py              — .env 対話ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/ (モジュール未表示、DuckDB 用 SQL 等想定)
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (存在前提)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (存在前提)
  - execution/
    - execution_engine.py (存在前提)
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上記はコードベースから抽出した主要ファイルの一覧です。実際のリポジトリではさらに補助スクリプトやモジュールが存在します。）

---

## 開発・拡張メモ

- DB スキーマは MonitoringDB.init_monitoring_db で冪等に初期化されます。既存 DB に対する軽微なマイグレーション（カラム追加）をコード内で行う設計になっています。
- AI モジュールは API 呼び出し部分をテスト容易に差し替えられるよう作られています（内部関数を patch してモック可能）。
- position sizing / risk adjustment 等は純粋関数として実装されており、ユニットテストが書きやすくなっています。

---

必要であれば具体的な起動例、.env の完全なテンプレート、あるいは systemd / Supervisor 用の Unit ファイル例を追加で作成できます。どの情報がさらに必要か教えてください。