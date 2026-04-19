# KabuSys

日本株向け自動売買システムの一部（ライブラリ / 起動スクリプト / ユーティリティ）。  
このリポジトリには取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI 支援モジュールなどの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

## 目次
- プロジェクト概要
- 主な機能
- 必要な依存関係
- セットアップ手順
- 環境変数 / 設定
- 使い方（起動・ユーティリティ）
- 監視・停止フラグの運用
- ログとデータベース
- ディレクトリ構成（主要ファイル一覧）

---

## プロジェクト概要
KabuSys は日本株自動売買のためのモジュール群です。  
主な目的は以下のとおりです。

- 戦略に基づくシグナル生成およびポートフォリオ構築
- 注文実行（本番 / ペーパートレードの分離）
- 実行状況・システム状態の継続監視とアラート
- ニュースの NLP によるセンチメント評価（OpenAI 使用）
- リサーチ用のファクター計算と特徴量解析
- ペーパートレード検証レポート生成

---

## 主な機能（抜粋）
- ExecutionEngine 起動スクリプト（run_execution.py）:
  - KABUSYS_ENV=`paper_trading` の場合は MockBroker を使い、paper_trading 専用 DB に記録して本番 DB と完全分離する設計。
- Monitoring（run_monitoring.py）:
  - システム負荷、データ鮮度、実行プロセスの存在などを定期ポーリングして SQLite に永続化。
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
- Kill Switch / 停止フラグ:
  - リスク条件（ドローダウン、ポジション上限等）で `data/kill.flag` を書き込み、ExecutionEngine に停止を通知。
  - 起動停止制御用フラグファイル（`data/stop_requested.flag`）の存在でスクリプトを安全に停止。
- AI モジュール:
  - news_nlp（OpenAI を利用した銘柄別ニュースセンチメント）
  - regime_detector（ETF の MA200 とマクロニュースを組み合わせて市場レジームを判定）
- リサーチ:
  - factor_research、feature_exploration：DuckDB を使ったファクター計算・評価
- ポートフォリオ構築:
  - 候補選定、等金額/スコア加重配分、ポジションサイズ計算、セクターキャップ、レジーム乗数など

---

## 必要な依存関係（主なもの）
※ 実際の requirements.txt は含まれていないため、環境に応じて調整してください。

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（設定ファイル検証を行う場合に任意）
- その他標準ライブラリ

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順（簡易）
1. リポジトリをクローンする:
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化し依存をインストール:
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install duckdb psutil openai PyYAML
   ```

3. 初期環境変数ファイル（.env）を作成:
   対話式ウィザードで作成できます。
   ```
   python -m kabusys.config_setup
   ```
   ウィザードを使わない場合は `.env.example` を参考に `.env` を作成してください（リポジトリに `.env.example` がある場合）。

4. 設定検証（起動前チェック）:
   ```
   python -m kabusys.validate_config
   ```
   `--strict` をつけると警告も失敗扱いになります。

---

## 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
  - paper_trading の場合、発注はモック実行・専用 DB（PAPER_TRADING_SQLITE_PATH）を使用
- DUCKDB_PATH: DuckDB ファイル。デフォルト `data/kabusys.duckdb`
- SQLITE_PATH: 監視 DB（production 相当）。デフォルト `data/monitoring.db`
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト `data/paper_trading.db`）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant/partial/never/reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ（デフォルト `logs/`）
- OPENAI_API_KEY: OpenAI を利用する AI 機能向け
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（開発用、デフォルト 0）

注意:
- Monitoring は KABUSYS_ENV にかかわらず `sqlite_path`（本番監視 DB）を使用します。Execution（発注処理）は `paper_trading` 時に別 DB を使用して分離します。

---

## 使い方（コマンド例）
- 環境ウィザード（.env の作成・更新）:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動（デーモン管理 / systemd 等で起動することを想定）:
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient が使用され、データは `PAPER_TRADING_SQLITE_PATH` に記録されます。
  - 起動時に `data/stop_requested.flag` が存在すると起動をスキップします。
  - 実行中は `data/execution.pid` が使用されます。

- Monitoring（監視ループ）を起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルトで 60 秒ごとに監視を実行。`MONITOR_POLL_INTERVAL` で上書き可能（秒）。
  - 監視中に `data/stop_requested.flag` が作られると安全にループを終了します。
  - Monitoring は常に `SQLITE_PATH`（監視用 SQLite）を使います（env に依存しない）。

- ペーパートレード検証レポートを生成:
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```
  デフォルト DB パスは `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`。

- AI / レジーム判定・ニューススコア:
  - OpenAI API キー（OPENAI_API_KEY）を設定したうえで、モジュール関数を利用します（ライブラリ呼び出し）。
  - 例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime（スクリプト化は必要に応じて）

---

## 監視・停止フラグの運用
- kill.flag (data/kill.flag):
  - RiskMonitor 等が危険事象を検知するとこのファイルを書き込み、ExecutionEngine に「停止」を促します。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動クリアされます（本番では 0 推奨）。
- stop_requested.flag (data/stop_requested.flag):
  - 手動でこのファイルを作成すると run_monitoring/run_execution が検知して安全に停止または起動を抑止します。
  - スクリプトを停止したいときはこのファイルを作成してください（systemd や運用スクリプトからも使用可能）。
- PID ファイル:
  - `data/execution.pid` は ExecutionEngine の実行管理に使用されます。

ファイル操作例（停止フラグ作成 / 削除）:
```
# 停止要求を発行
mkdir -p data
echo "stop" > data/stop_requested.flag

# 停止要求を取り消す
rm -f data/stop_requested.flag

# kill.flag を手動で削除（注意: 本番では慎重に）
rm -f data/kill.flag
```

---

## ロギングと永続化
- ログ:
  - `kabusys.utils.logging_setup.setup_logging` により stdout ストリームと日次ローテートのファイルログ（logs/<app_name>.log）を設定します。
  - 環境変数 `LOG_DIR` または `log_dir` 引数でログ保存場所を指定できます。
- 永続化:
  - DuckDB（分析用）: `DUCKDB_PATH`（デフォルト `data/kabusys.duckdb`）
  - SQLite（監視/発注ログ）: `SQLITE_PATH`（監視）、`PAPER_TRADING_SQLITE_PATH`（ペーパートレード）
  - `monitoring_db.init_monitoring_db` はテーブル作成およびマイグレーション（列追加）を冪等で実行します。

---

## ディレクトリ構成（主要ファイル）
以下は `src/kabusys` 配下の主要モジュールと説明です。

- __init__.py
  - パッケージ定義、バージョン

- config.py
  - 環境変数/.env の読み込みと Settings クラス（設定値アクセス）

- config_setup.py
  - .env を対話式に生成・更新するウィザード

- validate_config.py
  - 起動前チェック CLI（必須環境変数や config/*.yaml の検証）

- run_execution.py
  - ExecutionEngine 起動スクリプト（本番 / ペーパートレードの切り分け）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で制御）

- utils/
  - logging_setup.py : ログ設定ユーティリティ
  - process_priority.py : プロセス優先度 / CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py : 監視ログ用 SQLite 永続化層（テーブル定義 / 操作）
  - system_monitor.py : システム負荷・データ鮮度・プロセス監視
  - trade_monitor.py : （注文の滞留検出等；本コードベース内にある想定モジュール）
  - risk_monitor.py : ドローダウン・ポジション上限監視
  - kill_switch.py : kill.flag の生成・状態管理
  - monitoring_engine.py : 各 Monitor を束ねるエンジン
  - alert_manager.py : （通知管理、LINE などの送信を担う想定モジュール）

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - （発注処理・リポジトリ・ブローカー抽象化等）

- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - 候補選定、重み計算、数量計算、セクター割当など

- research/
  - factor_research.py, feature_exploration.py
  - DuckDB を使ったファクター計算・IC 等の解析

- ai/
  - news_nlp.py : ニュースを OpenAI でセンチメント評価して ai_scores に書き込む
  - regime_detector.py : ETF の MA200 とマクロニュースの LLM 評価を組み合わせレジーム判定

- tools/
  - paper_verification_report.py : ペーパートレード結果の検証レポート生成

（実際のリポジトリには上記以外の補助モジュールやスクリプトも含まれます）

---

## 運用上の注意
- 本番（KABUSYS_ENV=live）では `LINE_CHANNEL_ACCESS_TOKEN` / `LINE_USER_ID` を設定してアラート送信先を確実にしておくことを推奨します。
- kill.flag の自動クリア設定（KILL_FLAG_CLEAR_ON_START）は本番では危険です。通常は `0` を推奨します。
- OpenAI を使う機能は API キーとネットワークアクセスが必要です。API の利用料金とレート制限にご注意ください。
- run_monitoring は監視データを常に本番 `SQLITE_PATH` に書き込みます。テスト時はファイルパスに注意してください。
- ログディレクトリの作成に失敗した場合はファイル出力を行わず stdout のみになります。

---

## 参考コマンド（起動例）
- 監視をバックグラウンドで実行（簡易例）:
  ```
  nohup python -m kabusys.run_monitoring > run_monitoring.out 2>&1 &
  ```

- 実行エンジンをデバッグ実行:
  ```
  KABUSYS_ENV=development python -m kabusys.run_execution
  ```

---

README はここまでです。必要があれば以下を追記できます：
- 各モジュール（ExecutionEngine, OrderManager 等）の詳細な API ドキュメント
- systemd ユニットファイルのテンプレート
- テスト実行方法 / CI 設定
- requirements.txt の推奨内容

追加で追記したい項目や、特に詳しく説明してほしいモジュール名があれば教えてください。