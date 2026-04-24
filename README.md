# KabuSys

KabuSys は日本株向けの自動売買 / リサーチ基盤のミニマル実装です。本リポジトリは以下の主要機能を含みます。

- 注文実行エンジン（ExecutionEngine）と監視プロセス（Monitoring）
- Paper Trading（モックブローカー）による検証用分離DB
- ポートフォリオ構築・ポジションサイズ計算の純関数群
- ファクター計算・特徴量探索（DuckDB を利用）
- ニュース NLP（OpenAI）を用いたセンチメントスコアリング
- 各種ユーティリティ（ログ設定・プロセス優先度設定・設定ウィザード等）

バージョン: 0.1.0（src/kabusys/__init__.py の __version__）

---

## 主要な機能一覧

- 実行コンポーネント
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - Paper Trading モードでは MockBroker を使用し data/paper_trading.db に記録
- 監視コンポーネント
  - System / Trade / Risk モニタリング（python -m kabusys.run_monitoring）
  - Kill Switch（リスク基準で ExecutionEngine を停止するためのフラグファイル書き込み）
- 設定管理
  - 対話式 .env ウィザード（python -m kabusys.config_setup）
  - 起動前設定検証 CLI（python -m kabusys.validate_config）
- リサーチ / ツール
  - DuckDB を用いたファクター計算・特徴量解析（kabusys.research）
  - ニュース NLP による銘柄スコアリング（kabusys.ai.news_nlp）
  - Paper Trading の検証レポート生成ツール（python -m kabusys.tools.paper_verification_report）
- ユーティリティ
  - 統一的ログ設定（kabusys.utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（kabusys.utils.process_priority）
  - 監視ログの永続化（SQLite via kabusys.monitoring.monitoring_db）

---

## 必要な依存パッケージ

最低限のランタイム依存（抜粋）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config ファイルの検証に必要だがオプション）

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（実際の運用では requirements.txt を整備して pip install -r で管理してください）

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動

   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成 & 依存インストール

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil openai pyyaml
   ```

3. .env ファイルの作成（対話式ウィザード推奨）

   ```bash
   python -m kabusys.config_setup
   ```

   ウィザードはデフォルト値を提示します。必須項目：
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   重要:
   - .env は絶対に Git にコミットしないでください（トークン・パスワードを含みます）。
   - 本番環境では KABUSYS_ENV を `live` に設定し、設定を慎重に確認してください。

4. 設定検証（起動前チェック）

   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いにする:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリの確認（デフォルト）

   - DuckDB: data/kabusys.duckdb
   - SQLite (監視): data/monitoring.db
   - Paper Trading SQLite: data/paper_trading.db
   - ログディレクトリ: logs/
   - PID / フラグ： data/execution.pid, data/kill.flag, data/stop_requested.flag

   必要なら先にディレクトリを作成してください（実行時に自動作成される箇所もあります）。

---

## 簡単な使い方 / コマンド

- ExecutionEngine を起動（本番・paper_trading は KABUSYS_ENV に依存）

  ```bash
  # デフォルト環境は .env の KABUSYS_ENV に従う
  python -m kabusys.run_execution
  ```

  動作ポイント:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）
  - 起動時に data/stop_requested.flag が既に存在すると起動を中止
  - 実行中は data/execution.pid に PID を書き出す

- Monitoring を起動（監視ループ）

  ```bash
  # MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

  動作ポイント:
  - 監視は監視用 sqlite (settings.sqlite_path) を使用（環境にかかわらず本番 sqlite_path を参照）
  - process 停止検知やデータ鮮度チェック、RiskMonitor 等を実行
  - data/stop_requested.flag が存在するとループを終了

- 設定ウィザード（.env 作成/更新）

  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）

  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポートを生成

  ```bash
  # デフォルト DB は data/paper_trading.db。範囲指定も可能:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # 任意 DB を使う:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI ベースの処理（ニューススコア / レジーム判定）
  - ニューススコアリング: kabusys.ai.news_nlp.score_news(conn, target_date, api_key)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key)

  これらは OpenAI API キー（OPENAI_API_KEY 環境変数または引数）を必要とします。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — PaperTrading の fill モード (instant|partial|never|reject)（デフォルト: instant）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH — ExecutionEngine が使用する pid ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — KillSwitch のフラグパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- LOG_DIR — ログ保存先ディレクトリ（デフォルト: logs/）

注意: .env 自動読み込みはプロジェクトルートを検出して行われますが、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効にできます。

---

## ログと監視ファイル

- ログ:
  - logs/execution.log
  - logs/monitoring.log
  - ローテート: 日次（TimedRotatingFileHandler）、30 日分保持
  - コンソール出力は stdout に出ます

- フラグ / PID:
  - data/execution.pid — ExecutionEngine の PID（起動時に設定）
  - data/stop_requested.flag — 手動で存在させると run_* スクリプトが終了するトリガー
  - data/kill.flag — KillSwitch によって書き込まれる停止トリガー（Execution 停止用）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール構成（本リポジトリに含まれるファイルの抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                     — 環境変数 / Settings
    - config_setup.py               — 対話式 .env ウィザード
    - validate_config.py            — 起動前設定検証 CLI
    - run_execution.py              — ExecutionEngine 起動スクリプト
    - run_monitoring.py             — Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py                 — ニュース NLP / OpenAI 呼出し
      - regime_detector.py          — 市場レジーム判定
    - monitoring/
      - monitoring_db.py            — SQLite スキーマ & 抽象
      - system_monitor.py
      - trade_monitor.py (参照される)
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py (参照される)
    - execution/
      - execution_engine.py (参照される)
      - broker_factory.py (参照される)
      - order_manager.py (参照される)
      - order_repository.py (参照される)
      - reconciler.py (参照される)
      - risk_manager.py (参照される)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - data/                          — 実行時に作成されることが多い（DB / flags / pid）

（注）一部ファイルは上記で参照のみされるモジュールが存在します。プロジェクトに含まれる全ファイルはリポジトリを参照してください。

---

## 運用上の注意 / ベストプラクティス

- 秘密情報 (.env) は必ず Git などにコミットしないこと。
- 本番 (KABUSYS_ENV=live) では KILL_FLAG_CLEAR_ON_START を 0 に設定すること（誤って Kill Switch をクリアしないため）。
- psutil によるプロセス優先度設定は OS の権限に依存します（権限不足で警告が出ますが動作継続します）。
- OpenAI を利用する処理は API 料金・レートリミットに注意してください。API エラーは多くの場合フェイルセーフで継続する設計になっていますが、運用面での監視を推奨します。
- Paper Trading と本番 DB は分離されています（settings.is_paper により paper_sqlite_path を使用）。

---

## 開発者向けメモ

- ログ設定は kabusys.utils.logging_setup.setup_logging で統一されています。起動スクリプトはこれを呼び出してログを初期化します。
- DuckDB は分析用のローカル列指向 DB として使用しています（prices_daily / raw_financials 等のテーブルを想定）。
- ポートフォリオ構築 / ポジションサイズ計算は純粋関数として実装されており、ユニットテストが容易です。
- news_nlp / regime_detector は外部 API へのコール箇所を明確に分離しており、テスト時は該当関数をモックしやすく設計されています。

---

README は以上です。必要があれば、以下の点についてさらに詳しいドキュメント（アーキテクチャ図、DB スキーマの詳細、実行フローチャート、運用 runbook など）を作成します。どのトピックを優先しますか？