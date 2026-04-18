# KabuSys

日本株向けの自動売買システムのコアライブラリです。  
戦略のリサーチ、ポートフォリオ構築、ポジションサイズ決定、発注エンジン、監視・アラート、AI（ニュースNLP / レジーム判定）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

このリポジトリは、以下のような機能を持つ自動売買システムのコンポーネントで構成されています。

- データ解析（DuckDB を使ったファクター計算・特徴量探索）
- ポートフォリオ構築（候補選定・重み算出）
- ポジションサイズ計算（リスクベース／等分配など）
- 発注エンジン（実口座／ペーパートレード分離）
- 監視（システム・注文・リスク監視）と Kill Switch
- AI モジュール（OpenAI を利用したニュースセンチメント評価、レジーム判定）
- 設定ウィザード、設定検証、検証レポート生成などのユーティリティ

設計方針として、「本番とテストを分離」「ルックアヘッドバイアスを避ける」「フェイルセーフ（API失敗時のフォールバック）」が随所に反映されています。

---

## 主な機能一覧

- settings / .env 管理・自動ロード
- 設定ウィザード: `kabusys.config_setup`
- 設定検証 CLI: `kabusys.validate_config`
- 発注エンジン起動スクリプト: `kabusys.run_execution`
  - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し DB を分離
- 監視ループ起動スクリプト: `kabusys.run_monitoring`
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔上書き可能
- 監視用 DB（SQLite）を初期化するユーティリティ
- MonitoringEngine：System / Trade / Risk 各 Monitor の統合、Kill Switch 評価、アラート発行
- RiskMonitor：ドローダウンやポジション上限の監視とログ化
- AI:
  - News NLP（news_nlp）: OpenAI でセンチメント評価、ai_scores へ書き込み
  - Regime Detector（regime_detector）: MA とマクロニュースを合成して market_regime に書き込み
- Research（factor_research / feature_exploration）: DuckDB を使ったファクター計算、IC 計算、統計サマリ
- Portfolio（portfolio_builder / position_sizing / risk_adjustment）: 候補選定・重み計算・単元丸め・セクター制限・レジーム乗数
- Tools:
  - Paper Trading 検証レポート生成: `kabusys.tools.paper_verification_report`

---

## セットアップ手順（開発 / 実行前）

1. Python と依存パッケージを用意する
   - 推奨 Python 3.10+
   - 必要なパッケージ例:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（設定ファイル検証を行う場合に便利だが必須ではない）
   - 例（pip）:
     ```
     pip install duckdb psutil openai PyYAML
     ```

2. プロジェクトルートに .env を作成する
   - 手動で作るか、対話式ウィザードを利用:
     ```
     python -m kabusys.config_setup
     ```
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要なオプション / デフォルト
     - KABUSYS_ENV=development|paper_trading|live （デフォルト: development）
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
     - LOG_LEVEL (default: INFO)
     - OPENAI_API_KEY（AI 機能を使う場合）

3. 設定検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   # 警告も厳格に扱う場合:
   python -m kabusys.validate_config --strict
   ```

4. データディレクトリの準備（自動作成されることが多いが確認）
   - data/ （DB・フラグファイル）
   - logs/ （ログ出力先）

---

## 使い方（主要コマンド）

- 発注エンジンを起動（モジュール実行）
  - 本番 or 開発:
    ```
    python -m kabusys.run_execution
    ```
  - 注意:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使います。
    - 起動時に data/stop_requested.flag があると起動せず終了します。
    - 実行中は data/execution.pid に PID を書きます。

- 監視ループを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する:
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 監視は環境にかかわらず本番 sqlite_path を使用して監視ログを格納します（Settings.sqlite_path）。

- .env の対話式作成 / 更新
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB パスを明示
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 機能（プログラムから呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは OpenAI API キー（OPENAI_API_KEY 環境変数）または引数での指定が必要です。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — （必須）J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — （必須）kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の MockBroker の約定モード（instant|partial|never|reject）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI を使う場合に必要
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1）

---

## ログ設定

- 共通ユーティリティ: `kabusys.utils.logging_setup.setup_logging`
  - コンソール（stdout）出力と日次ローテートファイルハンドラをルートロガーに設定します。
  - ログディレクトリは `LOG_DIR` 環境変数またはデフォルト `logs/`。
  - 失敗時はコンソール出力のみで継続します。

---

## Kill Switch / 停止フラグの仕組み

- `kabusys.monitoring.kill_switch` が条件を満たすと `data/kill.flag` を書き込みます（発注エンジンに停止シグナル）。
- 発注エンジンおよび監視スクリプトは `data/stop_requested.flag` や `data/execution.pid` を監視／利用します。
- `KILL_FLAG_CLEAR_ON_START=1` の場合、起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理（自動 .env ロード）
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングスクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - portfolio/
    - portfolio_builder.py — 候補選定・重み
    - position_sizing.py — 株数計算（単元丸め・リスク制約）
    - risk_adjustment.py — セクター制限・レジーム乗数
  - monitoring/
    - monitoring_db.py — SQLite 監視 DB 初期化・読み書き層
    - monitoring_engine.py — Monitor の統合ループ
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （注文監視、コードベースに含まれます）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch 実装
    - alert_manager.py — （アラート管理、コードベースに含まれます）
  - execution/ (発注関連モジュール群)
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に生成される想定)
    - monitoring.db（SQLite, デフォルトパス）
    - paper_trading.db（ペーパートレード用 DB）
    - execution.pid / kill.flag / stop_requested.flag

（各ファイルの詳細はソースコメントをご参照ください）

---

## 開発メモ / 注意事項

- DuckDB / SQLite を使用するため、DB パスは Settings で指定可能。環境に応じて分離して使ってください（特に paper_trading）。
- AI（OpenAI）呼び出し部分はネットワークやレート制限で失敗することを想定しており、エクスポネンシャルバックオフやフォールバック（0.0）を組み込んでいます。
- `kabusys.config` はプロジェクトルート（.git または pyproject.toml）を探索して .env を自動ロードします。テスト等で自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ログディレクトリの作成に失敗した場合はファイル出力をスキップし、コンソール出力のみで継続します。
- 本リポジトリは運用上重要な操作（実発注、Kill Switch、ファイル書き込み）を含むため、本番環境では .env の管理・権限設定・バックアップを慎重に行ってください。

---

その他、各モジュールの API や詳細な使い方はソースの docstring / コメントに記載されています。必要であれば特定モジュールの README や使用例を追加で作成します。