# KabuSys

日本株自動売買システムのコードベース（ライブラリ + 起動スクリプト群）の README（日本語）。

以下はこのリポジトリの概要、主要機能、セットアップ手順、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株自動売買に関する以下の主要コンポーネントを含む Python パッケージです。

- 発注 / Execution エンジン（実際のブローカー接続またはペーパートレード）
- 監視（System / Trade / Risk のポーリング・アラート・Kill Switch）
- ポートフォリオ構築・ポジションサイズ計算（純粋関数群）
- リサーチ（ファクター計算、特徴量分析）
- AI 系ユーティリティ（ニュースの NLP スコアリング、レジーム判定）
- 運用補助ツール（設定ウィザード、設定検証、ペーパー検証レポート生成）

設計方針の例：
- 本番とペーパートレードを DB 等で分離
- 外部 API（OpenAI 等）呼び出しは明示的に API キーを要求し、安全にリトライ / フェイルセーフ
- 多くの機能は純粋関数または DB 層と分離された設計

---

## 主な機能一覧

- Execution
  - Broker クライアントの抽象化（本番 / モック）
  - Order 管理 / Risk 管理 / Reconciler / ExecutionEngine
  - ペーパートレード時は専用 SQLite（デフォルト: `data/paper_trading.db`）を使用

- Monitoring
  - SystemMonitor: CPU/Memory/Disk・プロセス存否・データ鮮度チェック
  - TradeMonitor: 注文の滞留・約定異常検出（trade_logs）
  - RiskMonitor: ドローダウン / 保有数上限監視、ダッシュボード更新
  - KillSwitch: 条件に応じて `data/kill.flag` を書いて Execution を止める
  - MonitoringEngine: 各モニターを束ねてポーリング（アラート送信経路は AlertManager を使用）

- Data / Research
  - DuckDB 接続を用いたファクター計算（momentum、volatility、value 等）
  - 将来リターン計算 / IC（Information Coefficient）計算 / 統計サマリ

- Portfolio
  - 銘柄候補選定、重み付け（等配分・スコア加重）
  - セクター制限、レジーム乗数
  - ポジションサイズ計算（単元丸め、aggregate cap、コストバッファ処理）

- AI
  - news_nlp: raw_news を LLM（gpt-4o-mini 等）でスコアリングし `ai_scores` に格納
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM スコアを合成して市場レジーム判定

- ユーティリティ
  - 環境設定ウィザード (`python -m kabusys.config_setup`)
  - 設定検証 CLI (`python -m kabusys.validate_config`)
  - Paper Trading 検証レポート生成ツール (`python -m kabusys.tools.paper_verification_report`)

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして Python 仮想環境を作成／有効化します。

   ```
   git clone <repo-url>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 必要なパッケージをインストールします（project の setup.py/pyproject を使う場合はそちらを参照）。最低限必要なもの（例）:

   ```
   pip install duckdb psutil openai
   # 設定 YAML の検証を行いたい場合:
   pip install pyyaml
   ```

3. データ / ログ ディレクトリを作成（通常は自動作成されますが手動でも可）:

   ```
   mkdir -p data logs
   ```

4. .env を作成・編集
   - インタラクティブウィザードで作る場合:

     ```
     python -m kabusys.config_setup
     ```

   - あるいは手動でプロジェクトルートに `.env` を作成します。主要な環境変数（例）:

     ```
     # 必須
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here

     # 任意 / デフォルト有り
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO

     # OpenAI を使う場合
     OPENAI_API_KEY=sk-...
     ```

   - 自動ロード:
     - デフォルトで `.env`（と `.env.local`）は自動読み込みされます。
     - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 設定検証を実行:

   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

6. （任意）DuckDB / SQLite の初期化は各スクリプト実行時に自動で行われます（monitoring は `init_monitoring_db` によるテーブル作成／マイグレーションを実施）。

---

## 使い方（起動スクリプト・代表例）

- 監視ループを起動（SystemMonitor のポーリング）

  ```
  python -m kabusys.run_monitoring
  ```

  - ポーリング間隔を秒単位で上書きするには環境変数 `MONITOR_POLL_INTERVAL` を指定（デフォルト 60 秒）。
    - 例: `MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring`

  - 監視は常に本番の sqlite_path（`SQLITE_PATH`）を使用します（環境に依らず）。

  - 停止するにはプロジェクトルート `data/stop_requested.flag` を作成するか Ctrl+C。

- ExecutionEngine（注文エンジン）を起動

  ```
  python -m kabusys.run_execution
  ```

  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、ペーパートレード専用 DB（`PAPER_TRADING_SQLITE_PATH` またはデフォルト `data/paper_trading.db`）に記録され、本番 DB と分離されます。
  - 起動時に `data/stop_requested.flag` が存在すると起動をスキップします。
  - 実行中の PID は `data/execution.pid` に書き込まれます（デフォルト）。

- .env の対話式作成（ウィザード）

  ```
  python -m kabusys.config_setup
  ```

- 設定検証

  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成（SQLite DB を指定可能）

  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 関連（ニューススコア／レジーム判定）
  - OpenAI API を使うため `OPENAI_API_KEY` を `.env` か環境に設定してください。
  - 直接関数を呼ぶ API:
    - kabusys.ai.score_news(...)
    - kabusys.ai.regime_detector.score_regime(...)

---

## 主要環境変数（よく使うもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード時の DB（デフォルト: data/paper_trading.db）
- PID_FILE_PATH — デフォルト: data/execution.pid
- KILL_FLAG_PATH — Kill Switch のファイルパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY — OpenAI を使う場合に必須

.env 自動ロード:
- プロジェクトルートに `.env` / `.env.local` があると自動で読み込まれる（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

---

## 運用上の注意点

- Monitoring はプロセス優先度を高く設定します（`set_process_priority("high")` を呼ぶ）。
- Execution 起動時に kill.flag の自動クリア設定 (`KILL_FLAG_CLEAR_ON_START`) を誤って 1 にすると本番で危険です（デフォルトは 0）。
- Paper Trading（ペーパー）は本番 DB と完全に分離されることを意図しています。設定を必ず確認してください（`KABUSYS_ENV`）。
- OpenAI 呼び出しはリトライやフェイルセーフを組み込んでいますが、API キーやコスト管理に注意してください。

---

## ディレクトリ構成（主要ファイル説明）

（`src/kabusys` 配下を抜粋）

- __init__.py
  - パッケージのバージョン/エクスポート定義

- config.py
  - 環境変数読み込み・設定管理（Settings クラス）
  - 自動 .env ロードロジック、必須チェックヘルパなど

- config_setup.py
  - `.env` を対話的に生成・更新するウィザード

- validate_config.py
  - 起動前の設定検証 CLI（必須環境変数、config/*.yaml 存在チェック等）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL で間隔上書き可能

- run_execution.py
  - ExecutionEngine 起動スクリプト
  - paper_trading 環境時は MockBrokerClient を使用し別 DB に記録

- monitoring/
  - monitoring_db.py: SQLite に対する永続化層（テーブル作成・読み書き）
  - system_monitor.py: CPU/メモリ/disk・プロセス・データ鮮度監視
  - trade_monitor.py: 注文ログ監視（滞留・異常約定等）
  - risk_monitor.py: ドローダウン・ポジション数監視
  - kill_switch.py: kill.flag 書き込みロジック
  - monitoring_engine.py: 各モニターの統合・ポーリングループ
  - alert_manager.py: （アラート送信の責務、実装に応じて LINE などへ送れる）

- execution/
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
  - 発注/注文管理の主要ロジック（ブローカー抽象、リスク設定等）

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 発注株数計算（単元丸め、aggregate cap）
  - risk_adjustment.py: セクターキャップ、レジーム乗数

- research/
  - factor_research.py: momentum/volatility/value 等のファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン、IC、統計サマリ

- ai/
  - news_nlp.py: ニュース記事を LLM でセンチメント化して ai_scores に保存
  - regime_detector.py: マクロニュース + ETF MA200 を使ったレジーム判定

- tools/
  - paper_verification_report.py: ペーパートレードの検証レポート生成スクリプト

- utils/
  - logging_setup.py: ロギング初期化ユーティリティ（console + 日次ローテーション file）
  - process_priority.py: プロセス優先度 / CPU affinity 設定ラッパー

- data/
  - （実行時に生成されるファイル例）
    - monitoring.db（または sqlite path で指定されたファイル）
    - paper_trading.db（ペーパートレード用）
    - kabusys.duckdb
    - execution.pid
    - kill.flag / stop_requested.flag

- logs/
  - デフォルトのログ保存先（`logging_setup` が使用）

---

## 開発・貢献

- コーディング規約やテスト方針は別途 CONTRIBUTING.md / docs を参照してください（無ければ簡単な PR で相談してください）。
- 外部 API（kabuステーション / J-Quants / OpenAI）キーは `.env` に保存し、決して Git にコミットしないでください。

---

必要であれば以下の補足を追加できます：
- 依存パッケージ一覧（requirements.txt / pyproject.toml から生成）
- 初期 DB のサンプルスキーマ / ダミーデータ挿入手順
- 各サービス（Execution / Monitoring）の systemd / supervisor 用サンプルユニットファイル

ほかに README に追記したい内容があれば教えてください。