# KabuSys

日本株自動売買システムのサブセット実装（ライブラリ & 起動スクリプト群）。  
このリポジトリは戦略研究、ポートフォリオ構築、発注実行、監視、AI を用いたニュース評価などのコンポーネントを含みます。

注意: 本 README はソースコード（src/kabusys 以下）を元に作成しています。実運用時は各自の運用ルール・法令順守のもとで利用してください。

## 概要
KabuSys は以下の主要な機能を備えた自動売買プラットフォームのコンポーネント群です。

- データ解析 / 研究（DuckDBを用いたファクター計算、特徴量解析）
- ポートフォリオ構築（候補選定・重みづけ・ポジションサイジング）
- ExecutionEngine（発注ロジック、リスク管理、ブローカークライアント抽象化）
- 監視（System / Trade / Risk の監視・アラート・Kill Switch）
- AI モジュール（ニュース NLP によるセンチメント評価、レジーム判定）
- 運用ツール（.env ウィザード、設定検証、Paper Trading レポート生成）

## 主な機能一覧
- 設定管理（`kabusys.config` / `.env` 自動ロード、`config_setup.py` ウィザード）
- 起動スクリプト
  - `run_execution.py`: ExecutionEngine を起動。`KABUSYS_ENV=paper_trading` 時は MockBroker を用い、Paper 専用 DB を使用
  - `run_monitoring.py`: SystemMonitor のポーリングループを起動（環境にかかわらず本番の sqlite_path を使用）
- 監視サブシステム
  - システムリソース・データ鮮度監視（`SystemMonitor`）
  - 注文ログ監視（`TradeMonitor` 等）
  - ドローダウン／ポジション数監視と Kill Switch（`KillSwitch`）
  - 監視データ永続化（SQLite、`monitoring_db`）
- ポートフォリオ構築（`portfolio` パッケージ）
  - 候補選定、スコア重み、等重み、ポジション決定、セクター上限、レジーム乗数
- 研究（`research`）
  - モメンタム・ボラティリティ・バリューファクター計算、将来リターン、IC 計算、統計サマリー
- AI（`ai`）
  - OpenAI を使ったニュースセンチメント（`news_nlp.py`）
  - マクロ + ETF MA によるレジーム判定（`regime_detector.py`）
- 運用ツール（`tools/paper_verification_report.py`）による Paper Trading の検証レポート生成

## 必要環境（推奨）
- Python 3.10+
- SQLite（標準ライブラリで可）
- DuckDB（Python パッケージ: duckdb）
- psutil
- openai（AI 機能を使う場合）
- PyYAML（設定ファイル検証を行う場合; オプション）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（実運用用の requirements.txt がある場合はそれを使ってください）

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境を作成して依存をインストール（上記参照）
3. 初期設定ファイル（.env）を生成
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
   - 生成後、必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を確認してください。
4. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```
5. DB 等のディレクトリを作成（必要に応じて）
   - デフォルトのパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
   - logging 用ディレクトリ: logs/
6. （AI 機能を使う場合）OpenAI API キーを設定:
   - 環境変数 `OPENAI_API_KEY` を .env に設定するか、関数呼び出しで直接指定

## 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- OPENAI_API_KEY（AI モジュール用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（LINE 通知設定）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。開発時のみ 1 を推奨）
- MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト 60）

## 使い方（起動・運用コマンド例）

- ExecutionEngine を起動（通常はプロセス管理ツールから daemon として起動）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、paper_trading 専用 DB に記録されます。
  - 起動時に data/stop_requested.flag が存在すると起動しません。
  - 起動時にプロセス優先度を "high" に設定し、PID ファイル（data/execution.pid）を管理します。

- Monitoring を起動（ポーリング監視）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存しません）。
  - data/stop_requested.flag を作ることでループを停止できます。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- .env の初期作成（対話式）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定の自動検証
  ```bash
  python -m kabusys.validate_config
  ```

## ログ
- ロギングは `kabusys.utils.logging_setup.setup_logging` を通じて統一的に設定されます。
- デフォルト出力:
  - コンソール stdout
  - 日次ローテーションで logs/<app_name>.log（30世代保持）
- app_name 例: "execution", "monitoring"

## 停止・Kill スイッチ（運用上の注意）
- 監視系は以下のフラグファイルを使用します:
  - data/stop_requested.flag: 実行ループ（monitoring / execution の起動ループ）を優雅に終了させるための外部停止フラグ
  - data/kill.flag: KillSwitch が書き込むことで ExecutionEngine に停止シグナルを送る（Execution 側は起動時にこのファイルをチェックし、起動後は定期的に存在確認して停止）
- KillSwitch の条件は主にドローダウン・ポジション上限等の監視ルールに基づきます。`KILL_FLAG_CLEAR_ON_START=1` は本番では危険です（起動時に kill.flag を消してしまうため）。本番は 0 推奨。

## 開発 / テスト
- モジュールはなるべく副作用が少ない純粋関数や DI（依存注入）を使う設計になっています。テスト時は DB を一時ファイルに切り替えたり、OpenAI 呼び出しをモックすることを想定しています（ソース内にモックしやすい関数分離あり）。
- 例:
  - `kabusys.ai.news_nlp._call_openai_api` / `kabusys.ai.regime_detector._call_openai_api` はユニットテストで patch して API 呼び出しを差し替え可能。

## ディレクトリ構成（主要ファイル）
src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定管理（.env 自動ロード、Settings クラス）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュース NLP（OpenAI）によるセンチメントスコア取得
  - regime_detector.py — マクロ + ETF MA による市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite 永続化層（監視ログ）
  - system_monitor.py — システム・データ鮮度監視
  - trade_monitor.py — 注文ログ監視（存在）
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — Kill Switch ロジック
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - alert_manager.py — （アラート送信管理：実装あり）
- execution/
  - execution_engine.py — ExecutionEngine（発注実行ループ）
  - broker_factory.py — ブローカークライアント生成
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注・リスク管理関連
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数計算・スケーリング
  - risk_adjustment.py — セクター制限・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value 計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計
- data/
  - pipeline.py, stats.py, ...（データ読み込み・補助関数群）
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- utils/
  - logging_setup.py — ログ設定
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

（上記は主要ファイルの抜粋です。ソース内に更に細かなモジュールが存在します）

## 実運用上の注意点
- 本番（KABUSYS_ENV=live）では .env の扱いに注意し、API キーやパスワードを漏洩しないこと。
- Kill Switch / monitoring の警告設定は慎重にチューニングしてください（誤発動はトレード損失につながる可能性があります）。
- OpenAI を用いる箇所は API コスト・レイテンシの影響を受けます。API キーの権限管理とレート制限ハンドリングを確認してください。
- ログディレクトリや DB ファイルのバックアップ、ディスク容量監視を行ってください。

---

不明点や追加で README に入れたい情報（例: 実行例のログ、requirements.txt、systemdユニット例など）があれば教えてください。必要に応じて追記・整備します。