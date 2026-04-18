# KabuSys

日本株向けの自動売買システム（ライブラリ＋起動スクリプト群）。  
戦略の研究・ファクター計算、ポートフォリオ構築、発注（実運用 / ペーパートレード）、監視・アラート、LLMを使ったニュース評価などの機能が含まれます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール群で構成されています。

- DuckDB / SQLite を用いたデータ準備・分析（prices_daily / raw_financials 等）
- ファクター計算（Momentum / Volatility / Value 等）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 実注文エンジン（ExecutionEngine） — 本番/ペーパートレードに対応
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch
- OpenAI を利用したニュースの NLP スコアリング / 市場レジーム判定
- 運用補助ツール（設定ウィザード・設定検証・ペーパートレード検証レポート等）

設計方針の一部：
- 本番 DB とペーパートレード DB を明確に分離
- DuckDB を分析用、SQLite を監視・発注ログ用に利用
- LLM 呼び出しはフェイルセーフ（API失敗時はフォールバック）で設計
- ルックアヘッドバイアスを避ける設計（日時参照は明示的に引数で渡す）

---

## 主な機能一覧

- 環境設定ウィザード: `python -m kabusys.config_setup`
- 設定検証 CLI: `python -m kabusys.validate_config [--strict]`
- 実行エンジン起動: `python -m kabusys.run_execution`
  - `KABUSYS_ENV=paper_trading` なら MockBroker を使い `data/paper_trading.db` に書き込む
- 監視ループ起動: `python -m kabusys.run_monitoring`
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可（デフォルト: 60秒）
- Paper Trading 検証レポート作成: `python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]`
- ポートフォリオ構築ユーティリティ:
  - 候補選定: select_candidates
  - 等金額/スコア加重: calc_equal_weights / calc_score_weights
  - ポジションサイズ計算: calc_position_sizes
  - セクター上限 / レジーム乗数: apply_sector_cap / calc_regime_multiplier
- 研究用モジュール:
  - ファクター計算: calc_momentum / calc_value / calc_volatility
  - 特徴量探索: calc_forward_returns / calc_ic / factor_summary
- AI モジュール:
  - ニュースセンチメント計算: kabusys.ai.score_news
  - 市場レジーム判定: kabusys.ai.regime_detector.score_regime
- 監視 DB 層: MonitoringDB（system_status / trade_logs / positions / risk_logs / dashboard）

---

## 必要条件 / 推奨環境

- Python 3.10+
- 必要なパッケージ（最低限）
  - duckdb
  - psutil
  - openai
- オプション（機能により）
  - PyYAML（`python -m kabusys.validate_config` の YAML 検証）
- SQLite（標準ライブラリ sqlite3 を使用）
- ネットワーク環境（API を使う場合）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

※requirements.txt がある場合は `pip install -r requirements.txt` を使用してください。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要（デフォルトあり / 任意）:
- KABUSYS_ENV: development / paper_trading / live （default: development）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（default: INFO）
- LOG_DIR: ログ格納ディレクトリ（default: logs）
- OPENAI_API_KEY: OpenAI API を使う機能で必要
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（1 または 0。default: 0）

監視関連:
- MONITOR_POLL_INTERVAL: 監視ポーリング秒数（run_monitoring の上書き、default: 60）

ファイルベースの制御:
- data/kill.flag: ExecutionEngine に停止シグナル（Kill Switch）
- data/stop_requested.flag: run_* スクリプトの外部停止フラグ
- data/execution.pid: ExecutionEngine の PID ファイル

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   ```bash
   pip install duckdb psutil openai PyYAML
   ```

4. 環境変数ファイルを作成（対話式ウィザード）
   ```bash
   python -m kabusys.config_setup
   ```
   - ウィザードは `.env` に必要値を保存します。`.env` は絶対にコミットしないでください。

5. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告も厳密にチェックする場合
   python -m kabusys.validate_config --strict
   ```

6. DB ファイルは起動時に必要であれば自動作成／初期化されます（monitoring DB のスキーマは init_monitoring_db が担います）。

---

## 実行方法（基本）

- 実行エンジン（ExecutionEngine）を起動:
  ```bash
  # 本番設定が .env にある想定
  python -m kabusys.run_execution
  ```

  - `KABUSYS_ENV=paper_trading` をセットするとペーパートレード専用 DB を使用します:
    ```bash
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```

- 監視プロセスを起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更したい場合:
    ```bash
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- 設定ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config [--strict]
  ```

- Paper Trading 検証レポート:
  ```bash
  # デフォルト DB を使う
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # 別 DB を指定する場合
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

---

## 停止 / Kill Switch の扱い

- 監視やエンジンはフラグファイルを確認して安全停止を行います:
  - data/stop_requested.flag: run_monitoring / run_execution の外部停止フラグ（存在するとループを抜ける）
  - data/kill.flag: KillSwitch により設定される停止フラグ。ExecutionEngine はこのファイルの存在を検出して停止します。
- `KILL_FLAG_CLEAR_ON_START=1` を設定していると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

---

## 開発者向けメモ

- ロギングは kabusys.utils.logging_setup.setup_logging を通して統一されます。ログは stdout と `logs/<app_name>.log` に日次ローテーションで出力されます。
- プロセス優先度の設定（高優先度化）は起動スクリプト内で行われます（psutil を使用）。権限不足や未対応 OS の場合は警告でスキップされます。
- DuckDB 接続は研究モジュール・AI モジュールで多用します。関数は接続オブジェクトを受け取り SQL と Python を組み合わせて計算します。
- OpenAI を使う機能は API キー（OPENAI_API_KEY）を必要とします。API 呼び出しはリトライ／バックオフやレスポンス検証を備えています。

---

## ディレクトリ構成 (主要ファイル)

- src/kabusys/
  - __init__.py
  - config.py                 — 環境・設定管理（.env 自動読み込み）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (参照用 — 監視ロジック)
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (アラート送信ロジック: LINE等)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py

（実際のリポジトリでは上記に加えて追加モジュール・スクリプトが存在する場合があります）

---

## よくある操作例

- 新規環境構築から監視起動まで（例）
  ```bash
  git clone <repo>
  cd <repo>
  python -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt  # or pip install duckdb psutil openai PyYAML
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  python -m kabusys.run_monitoring
  # 別端末でエンジン（または CI / systemd 等で起動）
  python -m kabusys.run_execution
  ```

---

## 注意事項 / 運用上のヒント

- .env は機密情報を含むため絶対にバージョン管理に含めないでください。
- 本番実行（KABUSYS_ENV=live）の場合、LINE 通知や kill flag の設定を十分確認してください。
- OpenAI API 呼び出しはコストが発生します。スケジュールやバッチサイズ、リトライ設定は目を通してください。
- DuckDB/SQLite のファイルパス（デフォルトは data/ 以下）に対するディスク容量やバックアップ運用を検討してください。

---

この README はコードベース（src/kabusys 以下）を参照して作成しています。さらに詳細なドキュメント（API リファレンスやアーキテクチャ文書）が必要であれば、該当モジュールを指定して追加で作成します。