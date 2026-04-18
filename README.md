# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム（KabuSys）の一部実装です。
主要なコンポーネント（実行エンジン、監視、ポートフォリオ構築、リサーチ、AIベースのニュース評価など）を含み、ローカル開発 / ペーパートレード / 本番（live）を想定した設計になっています。

バージョン: 0.1.0

---

## 概要（Project overview）

- DuckDB を分析用データストア、SQLite を監視・取引ログ用 DB に利用する構成。
- 本番環境・ペーパートレード環境を切り替え可能（KABUSYS_ENV）。
- 実行エンジン（ExecutionEngine）と監視プロセス（SystemMonitor / MonitoringEngine）を別プロセスで動かすアーキテクチャ。
- LLM（OpenAI）を使ったニュースのセンチメント評価（ai.news_nlp）や、市場レジーム判定（ai.regime_detector）を提供。
- ペーパートレードは本番 DB と分離され、MockBrokerClient を利用して `data/paper_trading.db` に記録される（KABUSYS_ENV=paper_trading）。

---

## 機能一覧（Features）

- 環境設定ウィザード（.env 作成）: `kabusys.config_setup`
- 設定検証 CLI（.env と config/*.yaml のチェック）: `kabusys.validate_config`
- 実行エンジン起動スクリプト: `kabusys.run_execution`
  - KABUSYS_ENV によりペーパートレード用クライアント選択
  - 停止フラグ / PID 管理
- 監視プロセス起動スクリプト: `kabusys.run_monitoring`
  - SystemMonitor によるリソース・データ鮮度監視
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能
- 監視データ永続化（SQLite）: `monitoring.monitoring_db`
- リスク監視（ドローダウン、ポジション上限）: `monitoring.risk_monitor`
- Kill Switch（kill.flag）：重大リスク発生時に ExecutionEngine を停止させる仕組み
- ポートフォリオ構築（候補選定・配分・位置サイズ計算）: `portfolio/*`
- リサーチ（ファクター算出、IC 計算、統計）: `research/*`（DuckDB 前提）
- AI ニュース NLP（OpenAI で銘柄ごとのセンチメント算出）: `ai/news_nlp.py`
- 市場レジーム判定（MA + マクロニュース LLM 評価）: `ai/regime_detector.py`
- ペーパートレード検証レポート出力ツール: `tools/paper_verification_report.py`
- ロギング設定ユーティリティ、プロセス優先度設定ユーティリティ等のユーティリティ群

---

## 必要条件（Requirements）

- Python 3.9+
- 推奨ライブラリ（抜粋）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（`validate_config` で YAML 検証を行う場合）
- （実行環境に応じた）kabuステーション API クライアント等（BrokerClient 実装に依存）

インストール例（仮）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
# または requirements.txt があれば: pip install -r requirements.txt
```

---

## セットアップ手順（Setup）

1. プロジェクトルートに移動（.git または pyproject.toml が存在する場所がプロジェクトルート判定に使われます）。

2. .env を作成する（推奨: 対話ウィザードを利用）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードで `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD` など必須項目を設定してください。

   自動ロード:
   - デフォルトで `.env` と `.env.local` は自動読み込みされます。
   - 自動ロードを無効化する場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

3. 設定検証（必須項目やファイルパスのチェック）
   ```
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

4. データディレクトリ作成（ログ / DB 保存先）
   - デフォルト:
     - DuckDB: `data/kabusys.duckdb`
     - SQLite (monitoring): `data/monitoring.db`
     - Paper trading DB: `data/paper_trading.db`
     - ログ: `logs/`
   - 必要に応じて `.env` の `DUCKDB_PATH` / `SQLITE_PATH` / `PAPER_TRADING_SQLITE_PATH` を変更してください。

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用
  - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
  - LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- DB パス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- AI
  - OPENAI_API_KEY（ai.news_nlp / ai.regime_detector を利用する場合）
- 監視・プロセス
  - MONITOR_POLL_INTERVAL（監視ポーリング秒、デフォルト: 60）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など（Settings 参照）
- PAPER_FILL_MODE（paper_trading の約定モード: instant / partial / never / reject）

注意: `.env` ファイルは絶対に Git にコミットしないでください（config_setup にもその注意書きあり）。

---

## 実行方法（Usage）

- 実行エンジン（ExecutionEngine）を起動:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper DB に記録します。
  - 起動時に `data/stop_requested.flag` があると起動を行いません。
  - 実行中は `data/execution.pid` を出力します。

- 監視プロセスを起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルトポーリング間隔: 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で上書き可。
  - 監視は Settings の sqlite_path（本番 DB）を常に使用します。
  - 停止するには `data/stop_requested.flag` を作成するか、Ctrl+C。

- ペーパートレード検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- 設定ウィザード / 検証:
  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

- AI 機能（スコア算出 / レジーム判定）
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続と OPENAI_API_KEY が必要です。
  - API 呼び出しが失敗した場合はフェイルセーフ（代替値で継続）する設計です。

---

## 停止・Kill Switch の挙動

- KillSwitch は監視中に重大なリスク（ドローダウン超過やポジション上限超過など）を検出した場合に `data/kill.flag` を書き込みます。ExecutionEngine はこのフラグを検出して安全に停止します。
- 強制停止・シャットダウンシグナルとして `data/stop_requested.flag` を用意しています。監視・実行スクリプトはこのファイルの存在を確認してループを止めます。

---

## ディレクトリ構成（Directory structure）

（重要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - config_setup.py — .env 作成ウィザード（対話式）
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI 経由のセンチメント）
    - regime_detector.py — 市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite テーブル定義・CRUD
    - system_monitor.py — システム状態・データ鮮度監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - trade_monitor.py (参照あり) — 注文関連監視（コード内参照）
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねる
    - alert_manager.py (参照あり) — 通知管理（LINE 等）
  - portfolio/
    - portfolio_builder.py — 候補選定 / スコア処理
    - position_sizing.py — 株数決定 / 単元丸め
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum / volatility / value）
    - feature_exploration.py — 将来リターン / IC / 統計
  - monitoring/ (上記)
  - utils/
    - logging_setup.py — ロギング設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity
  - data/ および logs/ は実行時に使用

（実際のファイル一覧はリポジトリ内を参照してください）

---

## 開発・運用上の注意（Notes & Troubleshooting）

- .env ファイルは機密情報を含みます。絶対にリポジトリにコミットしないでください。
- validate_config は PyYAML が無い場合、YAML の内容検証をスキップします（警告）。
- DuckDB / SQLite のパスに指定したディレクトリが存在しない場合、validate_config は警告を出しますが起動時に自動作成されることがあります。ログディレクトリ作成に失敗するとファイルロギングをスキップしてコンソールのみになります。
- OpenAI を使う機能は API キー（OPENAI_API_KEY）が必要です。API 呼び出しは再試行ロジックを備えていますが、制限やコストに注意してください。
- process priority / CPU affinity の設定は OS 権限に依存します。権限が無い場合は警告ログが出てスキップされます。
- MONITOR_POLL_INTERVAL を 0 や負の値にするとデフォルト（60 秒）にフォールバックします（安全設計）。
- DB マイグレーション（monitoring_db.init_monitoring_db）は起動時に自動で行われ、小さな拡張（カラム追加など）には対応しています。

---

## 参考コマンド一覧

- 環境設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```
- 監視プロセス起動:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- ペーパートレード検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

この README はコードベースから抽出した情報に基づいて作成しています。追加の詳細（ExecutionEngine の内部挙動や BrokerClient の実装など）は対応するモジュールのドキュメントや実装を参照してください。必要であれば各モジュール向けの詳細なドキュメント（API 仕様、例、ユニットテスト例など）も作成します。