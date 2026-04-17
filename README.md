# KabuSys — 日本株自動売買システム

このリポジトリは日本株を対象とした自動売買システムのコア実装です。戦略の研究／ファクター計算、ポートフォリオ構築、ポジションサイズ算出、発注エンジン（ExecutionEngine）、監視（Monitoring）や運用補助ツール（Paper Trading レポート・設定ウィザード等）を含みます。

---

## プロジェクト概要
- 戦略研究（DuckDB を利用したファクター計算・特徴量解析）
- ポートフォリオ構築（候補選定、重み算出、セクター制約、レジーム乗数）
- ポジションサイズ計算（単元株丸め、リスクベース割当、集約上限調整）
- 発注エンジン（本番またはペーパートレードのブローカークライアントを利用）
- 監視コンポーネント（システム状態、注文滞留・約定異常、リスク監視、Kill Switch）
- AI支援（ニュースセンチメント、レジーム検出：OpenAI API を利用）
- 運用ツール（対話式 .env 作成、設定検証、Paper Trading 検証レポート等）

---

## 主な機能一覧
- 設定管理（.env 自動読み込み・config ウィザード: kabusys.config_setup）
- 設定検証 CLI（kabusys.validate_config）
- Execution Engine 起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用し data/paper_trading.db に記録
- Monitoring 起動スクリプト（kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- 監視コンポーネント
  - SystemMonitor: CPU/MEM/DISK、Execution プロセス生存、株価データ鮮度
  - TradeMonitor: 滞留注文・約定価格異常
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件で data/kill.flag を書き込み ExecutionEngine を停止
  - AlertManager（アラート送信ロジックを集約：LINE 等と連携可能）
- ポートフォリオ関連
  - 候補選定、等重／スコア重み、セクターキャップ、レジーム乗数、ポジションサイズ計算
- 研究用モジュール
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）、将来リターン計算、IC、統計サマリー
- AI モジュール
  - news_nlp: ニュース記事を OpenAI に送り銘柄別センチメントを ai_scores に書込み
  - regime_detector: ETF MA とマクロセンチメントを合成して日次レジーム判定
- ツール
  - Paper Trading 検証レポート（kabusys.tools.paper_verification_report）

---

## 必要要件（推奨）
- Python 3.9+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - pyyaml（設定検証で YAML 検証を行う場合）
- （環境に応じて）kabuステーション API への接続設定、OpenAI API キー 等

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```
（プロジェクトに requirements.txt があればそれを利用してください）

---

## セットアップ手順
1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```
2. 仮想環境を作成して依存ライブラリをインストール（上記参照）
3. .env の作成
   - 対話式ウィザード:
     ```bash
     python -m kabusys.config_setup
     ```
   - または手動で .env を作成（以下は最小の必須項目例）
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     ```
   - 注意: .env は Git にコミットしないでください
4. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告を FAIL とする場合:
   python -m kabusys.validate_config --strict
   ```
5. DB 初期化
   - Monitoring 用 SQLite（monitoring.db）等は起動スクリプトが自動的に必要テーブルを作成します。

---

## 使い方（起動例）
- ExecutionEngine を起動
  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV に従います
  ```bash
  # 例: ペーパートレードで起動
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - ペーパートレード時は settings.paper_sqlite_path（デフォルト data/paper_trading.db）へ記録され、本番 DB と分離されます
  - Execution 実行中は data/execution.pid が生成され、停止は data/stop_requested.flag / data/kill.flag によって行われます

- Monitoring を起動
  ```bash
  # ポーリング間隔を 30 秒に設定したい場合
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - Monitoring は常に本番 sqlite_path（デフォルト data/monitoring.db）を使用します（環境にかかわらず）
  - 停止フラグ: data/stop_requested.flag を作成するとループを終了します

- 設定ウィザード（再掲）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証（再掲）
  ```bash
  python -m kabusys.validate_config [--strict]
  ```

- Paper Trading 検証レポート
  ```bash
  # デフォルト DB: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # 別 DB を指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

---

## 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live、デフォルト development）
- OPENAI_API_KEY（AI モジュール利用時に必要）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、デフォルト data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading 時の約定モード: instant|partial|never|reject、デフォルト instant）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト 60）
- LOG_LEVEL（DEBUG/INFO/...）

注意: .env 作成後に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

---

## ディレクトリ構成（主要ファイルのみ）
src/kabusys/
- __init__.py
- config.py
- config_setup.py
- validate_config.py
- run_execution.py
- run_monitoring.py

サブパッケージ:
- ai/
  - news_nlp.py
  - regime_detector.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py (アラート送信を集約するモジュール)
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - broker_factory.py
  - ...（発注関連実装）
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
  - process_priority.py
- monitoring/（上記に含まれる）

プロジェクトルートに data/（実行時に各種 DB・フラグファイルを配置）
- data/kabusys.duckdb（DuckDB、デフォルト）
- data/monitoring.db（監視 SQLite）
- data/paper_trading.db（ペーパートレード SQLite）
- data/execution.pid
- data/kill.flag
- data/stop_requested.flag

---

## 運用上の注意・トラブルシューティング
- psutil によるプロセス優先度設定や CPU affinity は権限に依存します。権限不足時は警告を出してスキップされます。
- OpenAI API を使うモジュール（news_nlp/regime_detector）は API キーとネットワーク接続を必要とします。API 呼び出しはリトライやフェイルセーフ（失敗時は 0.0 等でフォールバック）を備えていますが、キー未設定時は例外を投げます。
- monitoring は常に sqlite_path（デフォルト data/monitoring.db）を使用します。ペーパートレード DB と完全に分離したい場合は KABUSYS_ENV=paper_trading を利用してください。
- Kill Switch（data/kill.flag）が残っていると ExecutionEngine の起動が阻害されることがあります（KILL_FLAG_CLEAR_ON_START=1 を使うか手動で削除してください）。
- .env の自動ロードはプロジェクトルートが特定できる場合に行われます（.git または pyproject.toml を探索）。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

本 README はコードベースの主要部分と運用フローを簡潔にまとめたものです。各モジュールの詳細な動作や追加の設定項目は該当ソース（src/kabusys 以下）の docstring・コメントを参照してください。必要であれば、各モジュールごとの詳しいドキュメントも作成します。