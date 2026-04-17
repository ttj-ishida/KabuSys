# KabuSys

日本株向け自動売買 / 研究プラットフォームのリポジトリ。  
戦略のリサーチ、ポートフォリオ構築、発注エンジン、監視・アラート、AI を使ったニュース判定などのコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムとデータ研究ツールを統合したパッケージです。主な役割は以下の通りです。

- 価格・財務データを使ったファクター計算・研究（research）
- ポートフォリオ構築・ポジションサイジング（portfolio）
- 発注実行エンジン（execution） — 本番/ペーパートレード切替対応
- 監視サブシステム（monitoring） — システム状態、注文の滞留・異常、リスク監視、Kill Switch
- AI モジュール（ai） — ニュースのセンチメント、マクロレジーム判定（OpenAI 利用）
- CLI ツール（tools） — ペーパー検証レポートなど
- 環境設定ユーティリティ（config_setup、validate_config）

設計方針として、発注系と研究系は分離され、ペーパー取引は本番 DB と完全に分離されるようになっています（環境変数で切替）。

---

## 主な機能一覧

- 環境設定ウィザード（.env 生成 / 更新）
- 設定検証 CLI（.env および config/*.yaml の簡易チェック）
- ExecutionEngine（発注実行）：
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、`data/paper_trading.db` に記録
  - PID ファイル / 停止フラグにより外部から停止可能
  - リスク管理（リスクマネージャ）、注文管理、照合（reconciler）
- Monitoring（監視）：
  - SystemMonitor：CPU/メモリ/Disk、データ鮮度、Execution プロセスの生存確認
  - TradeMonitor：注文滞留、約定価格の異常検出
  - RiskMonitor：ドローダウン・ポジション上限のチェック、ダッシュボード更新
  - KillSwitch：条件に応じて `data/kill.flag` を書き込み、Execution を停止
  - AlertManager 経由で通知（LINE 等は将来的に接続）
- 研究（research）：
  - momentum / volatility / value ファクター計算（DuckDB を直接参照）
  - 将来リターン計算、IC 計算、統計サマリー
- AI：
  - news_nlp：raw_news を集約し OpenAI（gpt-4o-mini 等）で銘柄別センチメントをスコア化して ai_scores に書込
  - regime_detector：マクロ系 LLM と ETF（1321）の MA200 乖離を合成して日次レジーム判定
- ツール：
  - paper_verification_report：ペーパートレーディング DB から期間指定の検証レポートを出力

---

## セットアップ手順（ローカル開発向け）

前提：Python 3.10+ を想定。（本リポジトリに具体的な requirements.txt がない場合は必要なパッケージを個別にインストールしてください）

推奨パッケージ（最低限）:
- duckdb
- psutil
- openai
- PyYAML（設定検証で config/*.yaml 検証する場合に必要）

例（pip）:
```bash
python -m pip install duckdb psutil openai PyYAML
```

1. リポジトリをクローン／配置し、作業ディレクトリをプロジェクトルートにする。

2. `.env` の作成
   - 対話式ウィザードで作成するのが簡単です：
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくはプロジェクトルートに `.env` を手動で作成してください（以下に主要キーのサンプルを示します）。

3. 設定検証
   ```bash
   python -m kabusys.validate_config      # 警告は OK
   python -m kabusys.validate_config --strict  # 警告も FAIL
   ```

4. データディレクトリ作成（必要なら）
   ```bash
   mkdir -p data
   ```

5. DuckDB / SQLite DB の初期化は各モジュールが起動時に必要に応じて作成・マイグレーションを行います。prices_daily などのテーブルはデータ投入スクリプト/ETL が別途必要です（このリポジトリ内の pipeline 等を参照）。

注意: .env は絶対に Git にコミットしないでください。

---

## 主要環境変数（一部）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - development: ローカル開発（発注なし）
  - paper_trading: ペーパートレード（MockBrokerClient、別 DB）
  - live: 本番（実発注）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールが必要な場合）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant/partial/never/reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring 用、デフォルト 60）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: KillSwitch のフラグパス（デフォルト data/kill.flag）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化できます

サンプル .env（最低限の必須項目を置いた例）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## 使い方（実行例）

- 環境設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config         # exit 0/1 で判定
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine（実行エンジン）起動
  - 起動:
    ```bash
    python -m kabusys.run_execution
    ```
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、書き込み先は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
    - 起動前に `data/stop_requested.flag` が存在すると起動しません
    - 実行中は PID ファイル（デフォルト data/execution.pid）が作られます
    - 外部から停止させるには監視モジュールが `data/kill.flag` を書くか、手動で ExecutionEngine.stop() 呼び出しする仕組みを利用

- Monitoring（監視）起動
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定（デフォルト 60）
  - 監視は Settings.sqlite_path（monitoring.db）にログを記録します（環境に依らず本番 sqlite_path を使用）

- Paper Trading 検証レポート（CLI）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI モジュール（プログラムから）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI キーは引数で渡すか OPENAI_API_KEY 環境変数を用いる

- 研究・ファクター計算（プログラムから）
  - research.calc_momentum(conn, target_date)
  - research.calc_volatility(conn, target_date)
  - research.calc_value(conn, target_date)
  - research.calc_forward_returns(...), calc_ic(...), factor_summary(...)

---

## 停止／Kill Switch の仕組み

- run_execution と run_monitoring の両方でプロジェクト内の `data/stop_requested.flag` を監視します。これを作成するとループは終了します（手動停止用）。
- KillSwitch（監視側）は条件（ドローダウンやポジション上限）を満たした場合に `data/kill.flag` を書き込みます。ExecutionEngine は起動時にこのフラグの存在をチェックし、発見時は停止します。
- Settings.kill_flag_clear_on_start=1 を .env で設定すると起動時に kill.flag を自動で消去します（本番では危険なので通常は 0 推奨）。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 配下の主要モジュール一覧と簡単な説明です。

- kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数・設定読み込みロジック（.env 自動ロード含む）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書込
    - regime_detector.py — マクロ + MA200 による市場レジーム判定

  - monitoring/
    - monitoring_db.py — SQLite への永続化層（system_status, trade_logs, positions, risk_logs, dashboard 等）
    - system_monitor.py — CPU/メモリ/Disk、データ鮮度、PID チェック
    - trade_monitor.py — 注文の滞留・約定異常検出
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — （通知処理、実装ファイル末尾に続く予定）

  - execution/
    - execution_engine.py — ExecutionEngine（エンジン本体）
    - order_manager.py, order_repository.py, order_record.py, reconciler.py, risk_manager.py, broker_factory.py など（発注処理）
    - MockBrokerClient（paper_trading 用）は broker_factory 経由で生成

  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 発注株数計算・制限・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py — momentum/value/volatility 等のファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート CLI

  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

（注）上記は主要ファイルの抜粋です。細かい補助モジュールや実装ファイルも存在します。

---

## 開発上の注意事項 / 運用メモ

- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- AI モジュールを利用するには OpenAI API キーが必要です。利用時のコスト管理に注意してください。
- Monitoring は sqlite（monitoring.db）にログを永続化します。run_monitoring は環境にかかわらず Settings.sqlite_path を使用します（監視用 DB は本番 DB を参照する設計）。
- ExecutionEngine は KABUSYS_ENV=paper_trading のときに paper_sqlite_path（デフォルト data/paper_trading.db）を使用して、本番 DB と完全に分離されます。
- DuckDB（分析用）はデータ投入とスキーマ整備が必要です（prices_daily, raw_financials, raw_news 等）。研究モジュールはこれらのテーブルを前提としています。
- process_priority.set_process_priority により起動時に優先度を上げようとしますが、権限不足で失敗することがあります（警告ログのみ）。

---

## よく使うコマンド（まとめ）

- 環境ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動
  ```bash
  python -m kabusys.run_execution
  ```

- 監視起動（ポーリング間隔指定例）
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- ペーパー検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば、README に追加で以下の情報を追記できます:
- 必要パッケージの厳密な requirements.txt（バージョン固定）
- データベーススキーマの詳細（DuckDB / SQLite のテーブル定義）
- ExecutionEngine / Broker 周りの API ドキュメント（使い方、MockBroker の振る舞い）
- AlertManager の実装・LINE 通知設定方法

追記希望があれば、用途に合わせてドキュメントを拡張します。