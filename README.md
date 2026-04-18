# KabuSys

日本株向け自動売買 / リサーチ基盤ライブラリ（内部ユーティリティ群・起動スクリプトを含む）

このリポジトリは、取引実行エンジン・監視・ファクター計算・ニュースNLP・ポートフォリオ構築など、自動売買システム運用に必要なユーティリティと起動スクリプト群を含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提 / インストール
- セットアップ手順
- 使い方（起動スクリプト／ツール）
- 主要環境変数（要点）
- ディレクトリ構成（主要ファイルの説明）
- 備考 / 運用上の注意

---

## プロジェクト概要

KabuSys は日本株の自動売買システムに必要な以下の領域をカバーするモジュール群です。

- ExecutionEngine（発注・リスク管理・注文管理）起動スクリプト
- Monitoring（プロセス/システム/取引の監視）起動スクリプトと永続化層（SQLite）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
- リサーチ（ファクター計算、将来リターン、IC 計算、特徴量解析）
- AI 関連（ニュースの NLP スコアリング、レジーム検出）
- 運用補助ツール（.env ウィザード、設定検証、Paper Trading レポート生成）
- ロギング・プロセス優先度などユーティリティ

設計方針として、実データアクセス（DuckDB / SQLite）を分離し、LLM 呼び出しはフェイルセーフ（失敗時はデフォルト処理）で継続するようになっています。

---

## 主な機能一覧

- Execution 起動（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し paper_trading DB に分離して記録
  - プロセス優先度設定、PID 管理、停止フラグ対応
- Monitoring 起動（run_monitoring.py）
  - システム負荷、データ鮮度、Execution プロセス状態をポーリングして SQLite に記録
  - MONITOR_POLL_INTERVAL でポーリング間隔を調整可能（デフォルト 60 秒）
- Monitoring 永続化（monitoring_db.py）
  - system_status / trade_logs / positions / risk_logs / dashboard テーブル
  - マイグレーション（不足カラム追加）対応
- RiskMonitor / TradeMonitor / SystemMonitor / KillSwitch / AlertManager 組合せで監視・自動停止
- Portfolio モジュール
  - 候補選定、等配分・スコア加重、リスク調整（セクターキャップ・レジーム乗数）、ポジションサイズ決定
- Research モジュール
  - calc_momentum / calc_volatility / calc_value（DuckDB 上の prices_daily / raw_financials を参照）
  - 将来リターン・IC、ファクター統計サマリ等
- AI モジュール
  - news_nlp.score_news: OpenAI を使ったニュースセンチメント取得・ai_scores 書き込み（DuckDB）
  - regime_detector.score_regime: ETF MA とマクロニュースを合成して market_regime テーブルに書き込み
  - OpenAI 呼び出しはリトライ・バックオフ・レスポンス検証を実装
- 補助ツール
  - python -m kabusys.config_setup: .env 対話ウィザード
  - python -m kabusys.validate_config: 起動前の設定検証
  - python -m kabusys.tools.paper_verification_report: Paper Trading の検証レポート生成

---

## 前提 / インストール

推奨 Python バージョン: 3.10 以上（型アノテーションに | 構文を使用しているため）

主な依存パッケージ:
- duckdb
- psutil
- openai
- PyYAML（config 検証時に YAML 内容をチェックしたい場合に必要。ただし必須ではない）

インストール例（venv 推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（プロジェクトに requirements.txt が無い場合は上記を手動でインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン / ワークツリーに移動
2. 仮想環境を作成して依存をインストール（上記参照）
3. .env を作成
   - 対話式ウィザードを使用する:
     ```bash
     python -m kabusys.config_setup
     ```
   - あるいは手動で `.env` を作成し、最低限以下を設定してください:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development | paper_trading | live）例: development
     - そのほか: DUCKDB_PATH / SQLITE_PATH / LOG_LEVEL / PAPER_TRADING_SQLITE_PATH など
4. 設定検証（必須項目・構成のチェック）:
   ```bash
   python -m kabusys.validate_config
   # --strict を付けると警告もエラー扱いにできます
   python -m kabusys.validate_config --strict
   ```
5. データディレクトリ（data/, logs/）を作る（必要なら自動作成されますが手動作成可）
6. （Paper Trading を使う場合は）PAPER_TRADING_SQLITE_PATH を確認

---

## 使い方

主要なコマンドと動作の説明。

- 環境設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Execution エンジン起動（取引エンジン）
  - 通常:
    ```bash
    python -m kabusys.run_execution
    ```
  - Paper Trading モード:
    ```bash
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
    paper_trading の場合は MOCK Broker を使い、デフォルトで data/paper_trading.db に記録されます（本番 SQLite とは分離）。

- Monitoring 起動（ポーリングループ）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する:
    ```bash
    export MONITOR_POLL_INTERVAL=30  # 秒
    python -m kabusys.run_monitoring
    ```
  - stop のためのフラグ:
    - プロジェクトの data/stop_requested.flag を作成するとポーリングループが検知して終了します（run_execution / run_monitoring が参照）。
    - Kill Switch（監視ロジックにより自動で停止するためのフラグ）は Settings.kill_flag_path（デフォルト data/kill.flag）を使用します。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # --db で DB パスを明示的に指定可
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI / リサーチ関数の利用
  - モジュール関数としてインポートして使用します（例: news_nlp.score_news, regime_detector.score_regime, research.calc_momentum 等）。
  - OpenAI を用いる関数は OPENAI_API_KEY が必要（引数で渡すことも可）。

ログ:
- logs/ に日次ローテーションされたログが出力されます（デフォルト）。
- 環境変数 LOG_DIR / LOG_LEVEL で調整可能。

プロセス優先度:
- 起動スクリプトは start 時に set_process_priority("high") を呼びプロセス優先度を可能なら上げます（psutil の権限に依存）。

停止フロー:
- 運用上は kill.flag を手動で作成して ExecutionEngine に停止信号を送ることができます（KillSwitch を通じた自動書き込みもあり）。

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / 重要:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時の上書き）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_PATH: kill.flag の格納パス（デフォルト data/kill.flag）
- PID_FILE_PATH: execution.pid など（デフォルト data/execution.pid）

詳しくは kabusys.config.Settings のプロパティを参照してください。

---

## ディレクトリ構成（抜粋）

以降は src/kabusys 以下の主要なファイルと簡単な説明です。

- src/kabusys/__init__.py
  - パッケージ定義、__version__。

- 起動スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するメインスクリプト。paper_trading モード対応、プロセス優先度設定、PID・stop フラグ管理。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL により間隔を制御。

- 設定管理
  - src/kabusys/config.py
    - .env 自動読込・Settings クラス（環境変数ラッパー）
  - src/kabusys/config_setup.py
    - 対話式 .env 作成ウィザード
  - src/kabusys/validate_config.py
    - 起動前チェック CLI（必須 env / config/*.yaml / パス整合性等）

- monitoring（監視関連）
  - src/kabusys/monitoring/monitoring_db.py
    - SQLite テーブル作成・永続化用 API（system_status, trade_logs, positions, risk_logs, dashboard）
  - src/kabusys/monitoring/system_monitor.py
    - CPU/メモリ/ディスク/データ鮮度/プロセス状態のチェック
  - src/kabusys/monitoring/risk_monitor.py
    - ドローダウン・ポジション上限監視
  - src/kabusys/monitoring/kill_switch.py
    - kill.flag 管理
  - src/kabusys/monitoring/monitoring_engine.py
    - 各 Monitor を束ねて走らせるエンジン

- execution（発注関連） — 実装ファイルは省略（起動と統合するためのファクトリ等が参照される）
  - BrokerClientFactory / ExecutionEngine / OrderManager / Reconciler / RiskManager / OrderRepository 等を参照する起動スクリプト側の構成

- portfolio（ポートフォリオ構築）
  - src/kabusys/portfolio/portfolio_builder.py
  - src/kabusys/portfolio/position_sizing.py
  - src/kabusys/portfolio/risk_adjustment.py

- research（ファクター・解析）
  - src/kabusys/research/factor_research.py
  - src/kabusys/research/feature_exploration.py
  - src/kabusys/research/__init__.py

- ai（LLM 関連）
  - src/kabusys/ai/news_nlp.py
    - ニュースを集約して OpenAI に投げ、ai_scores テーブルへ書き込む機能
  - src/kabusys/ai/regime_detector.py
    - ETF MA とマクロニュースを組み合わせてレジーム判定し、market_regime テーブルへ書き込み

- utils（共通ユーティリティ）
  - src/kabusys/utils/logging_setup.py
    - 一貫したログ設定（stdout + 日次ローテーションファイル）
  - src/kabusys/utils/process_priority.py
    - プロセス優先度・CPU affinity の設定

- tools
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプト

---

## 備考 / 運用上の注意

- 本番（KABUSYS_ENV=live）で稼働する場合は LINE 通知設定、KILL_FLAG_* の動作、ログ出力先など運用パラメータを慎重に確認してください。
- .env は機密情報を含むため決して Git にコミットしないでください（config_setup.py のヘッダにも明記）。
- OpenAI を使う機能は API キーとコストに注意して運用してください。API 呼び出しはリトライなどの保護はありますが、API 利用はメトリクス監視下で行ってください。
- Monitoring は run_monitoring が Settings.sqlite_path を使用します。Paper Trading モードであっても監視の DB は本番用の sqlite_path を参照する実装になっています（意図的な設計に注意）。

---

必要に応じて README に記載したコマンドや設定をベースに運用ドキュメントや runbook を作成してください。質問や補足があればご連絡ください。