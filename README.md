# KabuSys

日本株向け自動売買システムのコアライブラリ群と起動スクリプト群です。  
このリポジトリは、戦略・ポートフォリオ構築、発注エンジン、監視・アラート、AI を用いたニュース解析／レジーム判定、研究用ユーティリティなどを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の主要機能を持つモジュール群の集合です。

- 発注（Execution）エンジン（本番 / ペーパートレード対応）
- システム監視（リソース、プロセス、生データ鮮度）
- リスク監視（ドローダウン、ポジション上限など）と Kill Switch（自動停止）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出）
- 研究/ファクタ計算（モメンタム、ボラティリティ、バリュー等）
- AI モジュール（ニュースセンチメントによる銘柄スコア付与、マクロセンチメントと ma200 を合成したレジーム判定）
- 運用支援スクリプト（.env 設定ウィザード、設定検証、検証レポート生成）
- ロギング・プロセス優先度設定などのユーティリティ

設計上の注意点：
- .env による設定を想定（`config_setup.py` の対話ウィザードで生成可能）
- DuckDB／SQLite をデータ格納に利用
- OpenAI（gpt-4o-mini）を利用する機能は API キーが必要
- ペーパートレードは本番 DB と分離（別 SQLite ファイル）

---

## 機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine の起動（KABUSYS_ENV により paper_trading を分離）
  - run_monitoring.py — SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）

- 環境設定・検証
  - config_setup.py — .env 初期作成/更新ウィザード（対話式）
  - validate_config.py — .env および config/*.yaml に対する起動前検証（`--strict` オプションあり）

- 運用ツール
  - tools/paper_verification_report.py — ペーパートレード検証レポート生成（期間指定可）

- ポートフォリオ構築
  - portfolio.portfolio_builder — 候補選定 / スコア重みなど
  - portfolio.position_sizing — 株数算出、利用現金に基づくスケーリング
  - portfolio.risk_adjustment — セクターキャップ、レジーム乗数

- 研究用
  - research.factor_research — momentum / volatility / value 等のファクター計算（DuckDB）
  - research.feature_exploration — 将来リターン、IC、統計サマリー等

- AI 関連
  - ai.news_nlp — raw_news を LLM に送り銘柄別センチメントを ai_scores に書込む
  - ai.regime_detector — ETF ma200 とマクロニュースセンチメントの合成によるレジーム判定

- 監視・運用
  - monitoring.* — MonitoringDB、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringEngine、アラート管理
  - monitoring/monitoring_db.py — SQLite による履歴 / ダッシュボード / ログの永続化レイヤ

- ユーティリティ
  - utils.logging_setup — 統一的なログ設定（コンソール + 日次ローテーション）
  - utils.process_priority — プロセス優先度 / CPU アフィニティ設定（Windows / POSIX 対応）

---

## 必須依存パッケージ（例）

プロジェクトは以下を想定しています（バージョンは用途に応じて固定してください）。

- Python 3.10+（型記法や union 型 | を使用）
- duckdb
- psutil
- openai（AI 機能利用時）
- PyYAML（`validate_config.py` の YAML 検証を利用する場合）
- sqlite3（標準ライブラリ）

インストール例（仮の requirements）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（リポジトリに requirements.txt がある場合はそちらを利用してください。）

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動。
2. 仮想環境を作成して依存ライブラリをインストール（上記参照）。
3. .env の作成
   - 対話式ウィザードを利用:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは J-Quants トークンや kabuAPI パスワード等の入力を促します。
   - もしくは .env を手動作成（.env.example を参考に）。

4. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリやログディレクトリの確認（通常は自動作成されますが権限に注意）。
   - デフォルト DB パス:
     - DuckDB: data/kabusys.duckdb
     - monitoring SQLite: data/monitoring.db
     - paper trading SQLite: data/paper_trading.db
   - ログ: logs/<app_name>.log（`LOG_DIR` 環境変数で変更可能）

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB (monitoring)（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant / partial / never / reject）
- LOG_LEVEL: ログ出力レベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力先ディレクトリ
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（"1" で有効）

注意: config モジュールはプロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` / `.env.local` を自動ロードします。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（起動例）

- 監視プロセス起動（SystemMonitor ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可能（例: 30 秒）
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視スクリプトはプロセス優先度を高く設定し、`data/stop_requested.flag` の存在でループを終了します。

- Execution エンジン起動
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  # または本番
  KABUSYS_ENV=live python -m kabusys.run_execution
  ```
  - `paper_trading` の場合は MockBrokerClient を使用し、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）へ記録されます。
  - 起動前に `data/stop_requested.flag` が存在する場合は起動しません。
  - 実行中に `data/stop_requested.flag` を作成するとエンジンは停止します。
  - PID ファイル: `data/execution.pid`（設定により変更可）

- .env 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ペーパートレード検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（プログラムから利用）
  - ニューススコアリング
    ```py
    from kabusys.ai.news_nlp import score_news
    # DuckDB 接続を渡して使用
    ```
  - レジーム判定
    ```py
    from kabusys.ai.regime_detector import score_regime
    ```

---

## 停止・Kill Switch の仕組み

- stop_requested.flag（data/stop_requested.flag）
  - run_monitoring / run_execution はこのファイルの存在をチェックし、存在すればループを終了またはエンジンを停止します。
  - 手動で停止したい場合はこのファイルを作成してください。

- kill.flag（デフォルト: data/kill.flag）
  - Monitoring 側の KillSwitch がリスク閾値（ドローダウン等）を超えた際にこのファイルを書き込みます。
  - ExecutionEngine 側はこのファイルを参照して安全に停止する設計になっています（Settings.kill_flag_path でパス指定可）。
  - 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると自動クリアされます（本番では 0 を推奨）。

---

## ディレクトリ構成

以下は主要ファイル・ディレクトリの一覧（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - config_setup.py          — .env ウィザード（CLI）
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - (trade_monitor.py, alert_manager.py などの補助モジュールが想定)
  - execution/                (発注エンジン関連のモジュール群)
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py

（実際のファイル構成はリポジトリのルート構造に依存します。上は src 配下の主要モジュール例です。）

---

## 開発・運用における注意事項

- 本番（KABUSYS_ENV=live）では設定・環境変数を慎重に扱ってください（validate_config はライブ環境チェックも行います）。
- .env は決して Git にコミットしないでください（config_setup のヘッダにも注意書きがあります）。
- AI 機能を利用する場合は API 使用料が発生します。エラーハンドリングやレートリミットに配慮済みですが、運用前に十分なテストを行ってください。
- DuckDB/SQLite のファイルアクセス権限、ログディレクトリへの書き込み権限に注意してください。
- プロセス優先度設定や CPU affinity は環境（OS, 権限）によって失敗する可能性があるため、警告ログによりフォールバックします。

---

README はここまでです。必要であれば次の点について README に追記します：
- 具体的な設定例（.env.example の内容）
- 詳細な起動・デバッグ手順（systemd ユニット例、Dockerfile など）
- API（関数）別の詳細ドキュメント（docstring からの自動生成準備）

どの情報を追加したいか教えてください。