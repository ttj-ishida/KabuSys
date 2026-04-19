# KabuSys

日本株向け自動売買システムのリポジトリ（抜粋）。この README はリポジトリ内の主要スクリプト／モジュールに基づいて作成されています。

> 注意: 実際の運用では .env に機密情報を含めないこと。サンプルや `.env.example` を参照して適切に環境変数を管理してください。

---

## プロジェクト概要

KabuSys は日本株のアルゴリズム売買システムの基盤ライブラリ群です。主要な責務は次の通りです。

- 注文実行エンジン（ExecutionEngine） — ブローカーとのやり取り、注文管理、リスク管理、再整合（reconciler）等。
- 監視（Monitoring） — システム状態、注文・約定ログ、リスク指標監視、Kill Switch による自動停止。
- ポートフォリオ構築（Portfolio） — シグナル選別、重み付け、ポジションサイズ計算、セクター制限。
- リサーチ（Research） — ファクター計算、将来リターン・統計解析。
- AI モジュール — ニュース NLP によるセンチメント評価、レジーム判定（OpenAI 利用）。
- ユーティリティ — ロギング設定、プロセス優先度設定、設定ウィザード/検証スクリプトなど。

設計方針として、DB（DuckDB/SQLite）を使ったデータ処理、外部 API 呼び出しは明示的に inject できるように分離し、ルックアヘッドバイアスを避ける工夫がされています。

---

## 主な機能一覧

- 実行スクリプト
  - run_execution: ExecutionEngine 起動（KABUSYS_ENV=paper_trading なら MockBrokerClient と専用 DB を使用）
  - run_monitoring: SystemMonitor をポーリング（MONITOR_POLL_INTERVAL で間隔指定）

- 設定関連
  - config_setup: 対話式ウィザードで .env を生成/更新
  - validate_config: .env / config/*.yaml の整合性チェック（--strict あり）

- 監視・アラート
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine
  - SQLite ベースの監視 DB（data/monitoring.db デフォルト）

- ポートフォリオ構築
  - 候補選択、等重・スコア重みづけ、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ決定（単元株丸め含む）

- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 使用）
  - 将来リターン計算、IC（情報係数）、統計サマリ

- AI（OpenAI）連携
  - ニュース記事を LLM で評価して ai_scores テーブルへ書き込み（kabusys.ai.news_nlp）
  - マクロニュースを元に市場レジーム判定（kabusys.ai.regime_detector）

- レポート
  - tools.paper_verification_report: Paper Trading 検証レポート生成（SQLite DB を読み取り）

---

## 必要条件（主な依存ライブラリ）

- Python 3.9+
- duckdb
- psutil
- openai （AI 機能を使う場合）
- PyYAML（validate_config の YAML 検証に必要、無ければスキップされる）

インストール例:
```
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをチェックアウトして作業ディレクトリをプロジェクトルートにする。

2. 仮想環境を作成・有効化し、依存をインストールする（上記参照）。

3. 環境変数を用意する
   - 対話式で作る（推奨）:
     ```
     python -m kabusys.config_setup
     ```
     このウィザードは `.env` を生成 / 更新します。

   - 手動で作成する場合は以下の最低必須キーを `.env` に設定してください:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (任意: DEBUG/INFO/...)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB。デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を利用する場合）

   - config.py は起動時にプロジェクトルートの `.env` と `.env.local` を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

4. データディレクトリ等を作成（多くは自動作成されますが、手動で準備する場合）:
```
mkdir -p data logs
```

5. 設定検証（任意）
```
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

---

## 使い方（主要スクリプト・コマンド）

- ExecutionEngine 起動（通常）
```
python -m kabusys.run_execution
```
- Monitoring 起動（ポーリング）
```
python -m kabusys.run_monitoring
```
- 環境設定ウィザード（.env 作成）
```
python -m kabusys.config_setup
```
- 設定検証
```
python -m kabusys.validate_config
```
- Paper Trading 検証レポート（オプションで期間指定）
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を直接指定する場合:
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

### 監視・停止フラグ
- run_* スクリプトはプロジェクトルート直下の data/stop_requested.flag を監視し、存在するとループを終了します（手動で停止を指示したい場合にファイルを作成してください）。
- Kill Switch は data/kill.flag を書き込み（あるいは存在確認）して ExecutionEngine を停止する仕組みです。KillSwitch クラス経由で作成・クリアできます。
- 実行中の ExecutionEngine は data/execution.pid に PID を書きます（run_execution が使用）。

### モニタリングのポーリング間隔
- 環境変数 `MONITOR_POLL_INTERVAL` に秒数を指定可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックします。

### Paper Trading（ペーパートレード）
- KABUSYS_ENV=paper_trading にすると、run_execution は MockBrokerClient を使い、紙上の履歴は `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）へ記録します。本番用の monitoring SQLite DB とは分離されます。
- `PAPER_FILL_MODE` でペーパー約定動作を指定できます（instant | partial | never | reject）。

### AI 機能
- OpenAI API を利用する機能（ニュースセンチメント、レジーム判定）は `OPENAI_API_KEY` を必要とします。API 呼び出しは耐障害性を考慮してリトライやフォールバック（失敗時は安全な既定値）を行います。
- ニュース NLP: kabusys.ai.news_nlp.score_news(...) / モジュール経由: `from kabusys.ai import score_news`
- レジーム判定: kabusys.ai.regime_detector.score_regime(...)

### ロギング
- 共通のロギング設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` を各起動スクリプトから呼び出しています。
- デフォルトでコンソール（stdout）と `logs/<app_name>.log` に日次ローテーションで出力（30日保持）。
- 環境変数で `LOG_LEVEL` / `LOG_DIR` を上書き可能。

---

## 主な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- PAPER_FILL_MODE — instant / partial / never / reject（デフォルト: instant）
- OPENAI_API_KEY — AI 機能で必要
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL
- LOG_DIR — ログ保存先ディレクトリ
- MONITOR_POLL_INTERVAL — 監視のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" で有効。production では推奨されない）

---

## ディレクトリ構成（抜粋）

リポジトリの主要なモジュール構成（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数・.env の読み込み／Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py        — 共通ロギング設定
    - process_priority.py     — プロセス優先度 / CPU affinity
  - execution/                — Execution エンジン／Order 関連（実装ファイル群）
  - monitoring/
    - monitoring_db.py        — SQLite ベースの監視 DB ヘルパ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
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
  - tools/
    - paper_verification_report.py

その他：
- data/           — デフォルト DB / flag / pid の保存先（実行時に自動作成されます）
- logs/           — ログファイル保存先（デフォルト）

---

## 運用上の注意点・ベストプラクティス

- 本番環境（KABUSYS_ENV=live）での設定は慎重に。validate_config は live の場合に追加警告を出します。
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup も README にその旨を明示しています）。
- Kill Switch / stop flag の挙動を理解した上で、誤って本番を停止しない運用フローを設計してください（KILL_FLAG_CLEAR_ON_START を 1 にするのは本番では危険）。
- DuckDB / SQLite のパスは DB ファイルの格納先ディレクトリに注意してください（容量・バックアップ）。
- AI 機能は外部 API 呼び出しを伴うためコスト・レイテンシに注意。API キーは適切に管理してください。

---

## 参考コマンドまとめ

- .env 作成（ウィザード）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- 実行エンジン起動
  ```
  python -m kabusys.run_execution
  ```

- 監視エンジン起動
  ```
  python -m kabusys.run_monitoring
  ```

- Paper Trading レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

この README はコードベースの抜粋に基づく要約です。詳細な仕様・設計文書（PortfolioConstruction.md や StrategyModel.md 等）が別に存在する前提です。追加で README に記載したい内容（例: 環境変数の完全な一覧、運用手順、デプロイ手順など）があれば教えてください。必要に応じて追記・整形します。