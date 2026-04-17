# KabuSys

日本株向けの自動売買システム（KabuSys）。  
戦略の研究・ファクター計算、ポートフォリオ構築、発注実行、監視、AI（ニュース NLP / レジーム判定）などのコンポーネントを備えたモジュール式の実装です。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群で構成されています。

- データ分析・リサーチ（DuckDB を利用したファクター計算、特徴量解析）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制約等）
- ExecutionEngine（ブローカーとのやり取り、発注管理、リスク管理、再整合）
- Monitoring（システム稼働状況、注文滞留・約定異常、ドローダウン等の監視）
- AI モジュール（ニュースセンチメント / レジーム判定：OpenAI API を利用）
- 開発用ツール（.env ウィザード、設定検証、Paper Trading レポート生成 等）

設計上、各モジュールは可能な限り副作用を抑え、テスト可能な純粋関数（リサーチ / ポートフォリオ）と、DB 書き込み等の永続化層を分離しています。

---

## 機能一覧

主な機能

- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- Execution
  - 実際のブローカー接続 or Paper Trading の Mock Broker（KABUSYS_ENV に依存）
  - リスク管理（ポジション上限、最大ドローダウンなど）
  - 発注・注文管理・約定ログの永続化（SQLite）
- Monitoring
  - システム状態監視（CPU/Memory/Disk、execution プロセス監視）
  - 注文滞留・約定異常検出
  - ドローダウン監視と Kill Switch（data/kill.flag を書き込んで ExecutionEngine を停止）
  - MonitoringEngine によるポーリング
- Research / Tools
  - ファクター計算（Momentum / Value / Volatility）
  - 特徴量探索・IC 計算
  - Paper Trading 検証レポート生成スクリプト（python -m kabusys.tools.paper_verification_report）
- AI（OpenAI）
  - ニュース記事を LLM でスコアリングして ai_scores に格納
  - マクロニュース＋ETF MA を用いた市場レジーム判定

---

## セットアップ手順

1. 必要条件
   - Python 3.9+
   - SQLite（標準で同梱）
   - 推奨ライブラリ（pip インストール）
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証時に config/*.yaml のパースを行う場合）
   - （任意）venv の作成
     ```
     python -m venv .venv
     source .venv/bin/activate  # Linux / macOS
     .venv\Scripts\activate     # Windows
     ```

2. 依存パッケージインストール（例）
   ```
   pip install duckdb psutil openai pyyaml
   ```

3. .env の作成
   - 対話式ウィザードで生成:
     ```
     python -m kabusys.config_setup
     ```
   - 手動で作成する場合はプロジェクトルートに `.env` を置く。自動ロードは OS 環境変数 → .env.local（上書き）→ .env の順で行われます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   - 最低限必要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live。デフォルト: development）
     - OPENAI_API_KEY（AI 機能を使う際に必要）
   - デフォルトの DB パス:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用): data/paper_trading.db

   サンプル .env（抜粋）:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=your_token_here
   KABU_API_PASSWORD=your_password_here
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   LOG_LEVEL=INFO
   OPENAI_API_KEY=sk-...
   ```

4. 設定検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   # --strict を付けると警告も終了コード 1 扱いになります
   python -m kabusys.validate_config --strict
   ```

---

## 使い方

実行系・監視系・ツールの基本的な起動方法を示します。

- ExecutionEngine を起動（本番 / ペーパートレード切替）
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し、SQLite は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。本番は通常のブローカークライアントを使用します。
  ```
  python -m kabusys.run_execution
  ```
  - 起動時、プロセス優先度が "high" に設定されます（失敗しても継続）。
  - 停止はプロジェクトルートの data/stop_requested.flag を作成することで実行中スレッドに検知させて停止します。
  - 実行時の PID は data/execution.pid に書き込まれます。

- Monitoring を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - Poll 間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。
  - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に依存しない）。
  - 停止は data/stop_requested.flag を作成することで行います。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示したい場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```
  - デフォルトの DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。

- AI 関連
  - ニュース NLP（ai_scores への書き込み）やレジーム判定はライブラリ関数として提供されています。
    - 例（スクリプトや REPL から）:
      ```
      from kabusys.ai.news_nlp import score_news
      # duckdb_conn は duckdb.connect(...) で得る
      score_news(duckdb_conn, target_date, api_key="sk-...")
      ```
    - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を使用します。
    - API 呼び出しはリトライやフォールバックを備えていますが、キー未設定時は ValueError が発生します。

- 設定クリア / Kill Switch
  - Kill Switch は監視側で評価されると data/kill.flag に理由を書き込みます。ExecutionEngine は起動時にこのファイルを確認・クリアする設定（KILL_FLAG_CLEAR_ON_START）があり得ますが、本番では自動クリアを無効にすることが推奨されています。

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — execution / paper_trading / live（デフォルト development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時）
- OPENAI_API_KEY — OpenAI 使用時に必要
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（"1" でクリア）

設定の読み込み順序: OS 環境変数 > .env.local > .env（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化）

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主なファイル・モジュール構成（提供されたコードベースに基づく抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 起動前の設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py         — プロセス優先度 / CPU affinity 設定ユーティリティ
  - portfolio/
    - __init__.py
    - portfolio_builder.py        — 候補選定・重み計算
    - position_sizing.py          — 株数決定・制限・丸め
    - risk_adjustment.py          — セクターキャップ・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py         — momentum/value/volatility 計算
    - feature_exploration.py     — 将来リターン、IC、統計サマリー
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py         — 市場レジーム判定（OpenAI 統合）
  - monitoring/
    - monitoring_db.py           — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py          — システム状態・データ鮮度監視
    - trade_monitor.py           — 注文滞留・約定異常監視
    - risk_monitor.py            — ドローダウン / ポジション上限監視
    - monitoring_engine.py       — 各 Monitor を束ねるエンジン
    - kill_switch.py             — Kill Switch 実装（flag file 書き込み）
    - alert_manager.py           — （アラート送信の管理。未表示コード）
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート出力

（data / config ディレクトリはプロジェクトルートに生成・配置される想定です）

---

## 運用上の注意・ベストプラクティス

- 本番（KABUSYS_ENV=live）時は .env や設定を慎重に管理し、LINE 通知や Kill Switch 設定を確認してください（validate_config に警告を出します）。
- OpenAI API を利用する機能は外部 API に依存するため、API キー管理・レート制限・課金に注意してください。
- データベースファイル（DuckDB / SQLite）はバックアップやパーミッション管理を行ってください。
- Execution と Monitoring は別プロセスで動かすことを想定しています。PID / flag ファイルの配置先（data/）に注意してください。
- Paper Trading を活用するときは paper_trading 用 DB が本番 DB と完全分離されることを確認してください（Settings.is_paper の実装により分離）。

---

## 開発・テスト

- 研究・ポートフォリオ関数群は副作用がなく単体テストが容易です（pure functions）。
- MonitoringEngine.run_once を利用すると単発のチェックが実行でき、ユニットテストや手動テストに便利です。
- OpenAI API 呼び出し部分は内部で分離され、テスト時は _call_openai_api をモックすることが想定されています。

---

問題や不明点があれば、どのコマンドを実行したいか / どの機能を詳しく知りたいかを教えてください。必要に応じて .env のテンプレートや起動スクリプトの例も用意します。