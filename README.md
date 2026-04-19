# KabuSys

日本株自動売買システムのリポジトリ（ライブラリ + 起動スクリプト群）。  
この README はコードベース（src/kabusys 以下）に基づく概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買／研究プラットフォームです。主な機能は以下の通りです。

- 注文実行エンジン（ExecutionEngine） — ブローカークライアントと連携して発注・注文管理を行う（実運用 / ペーパートレード対応）。
- 監視コンポーネント（Monitoring） — システム状態、注文ログ、リスク監視、Kill Switch の管理。
- ポートフォリオ構築（Portfolio） — 候補選定、重み付け、ポジションサイズ計算、セクター制約・レジーム考慮。
- リサーチ機能（Research） — DuckDB を使ったファクター計算（Momentum / Volatility / Value 等）と特徴量解析（IC 等）。
- AI モジュール（AI） — ニュースの NLP センチメントスコアリング（OpenAI API を使用）と市場レジーム判定。
- ユーティリティ群 — ロギング設定、プロセス優先度設定、環境ファイルウィザード、設定検証、および運用用スクリプト群（例: Paper Trading レポート生成）。

設計上のポイント:
- DB（DuckDB / SQLite）を利用したデータ永続化と分析分離。
- Paper Trading と Live を完全に分離（paper_trading 用 SQLite を別ファイルに保存）。
- 外部 API（OpenAI 等）呼び出しはフォールトトレラントに実装（リトライ、フォールバック）。
- できる限りルックアヘッドバイアスを避ける実装方針（例: date.today() を直接参照しない等）。

---

## 主な機能一覧

- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config
- 実行エンジン起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に記録
- 監視ループ起動: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- ポートフォリオ関連:
  - 候補選定: select_candidates
  - 重み算出: calc_equal_weights / calc_score_weights
  - ポジションサイズ算出: calc_position_sizes
  - セクター上限適用: apply_sector_cap
  - レジーム乗数: calc_regime_multiplier
- リサーチ:
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 将来リターン・IC・統計量: calc_forward_returns, calc_ic, factor_summary
- AI:
  - ニュース NLP スコアリング: kabusys.ai.score_news（OpenAI API 必須）
  - 市場レジーム判定: kabusys.ai.regime_detector.score_regime（OpenAI API 必須）
- ユーティリティ:
  - 統一ログ設定: kabusys.utils.logging_setup.setup_logging
  - プロセス優先度設定 / CPU affinity: kabusys.utils.process_priority

---

## セットアップ手順（開発 / 運用向け）

前提: Python 3.9+（パッケージの互換性に合わせて適宜調整してください）。

1. リポジトリをクローン:
   git clone <repo-url> && cd <repo>

2. 仮想環境の作成・有効化（推奨）:
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 依存ライブラリのインストール:
   - 必要な主なパッケージ:
     - duckdb
     - psutil
     - openai (AI 機能を使用する場合)
     - PyYAML (config 検証で YAML を使いたい場合)
   例:
     pip install duckdb psutil openai PyYAML
   ※ requirements.txt がある場合は:
     pip install -r requirements.txt

4. .env の初期作成:
   - 対話式ウィザードで .env を作成:
     python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参照）。

5. 設定検証:
   python -m kabusys.validate_config
   - 警告もエラー扱いにする場合は --strict を付与。

6. データディレクトリ:
   デフォルトの DB / PID / ログ 等は `data/` / `logs/` 配下を使用します。必要に応じて環境変数で上書きしてください（例: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_DIR）。

---

## 必須環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

主な任意/設定系環境変数とデフォルト:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- LOG_LEVEL — デフォルト: INFO
- LOG_DIR — デフォルト: logs/
- OPENAI_API_KEY — OpenAI を使う場合に必須
- MONITOR_POLL_INTERVAL — run_monitoring の秒間隔（デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか (0/1、デフォルト 0)

（config_setup のウィザードで主な項目を対話的に設定できます）

---

## 使い方（主要コマンド）

1. 環境ファイル生成（対話式）
   python -m kabusys.config_setup

2. 設定検証
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict

3. 実行エンジン起動（本番/ペーパートレード両対応）
   python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading にすると paper_trading 用 DB を使用し、MockBroker を利用します。
   - ExecutionEngine は data/execution.pid に PID を書きます。
   - 停止: data/stop_requested.flag を作成するか、プロセスの KeyboardInterrupt。

4. 監視ループ起動
   python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定可能。
   - 監視は本番用 sqlite_path を常に参照（環境にかかわらず）。
   - 停止: data/stop_requested.flag を作成するか、KeyboardInterrupt。

5. Kill Switch（運用上の停止）
   - KillSwitch は条件に応じて data/kill.flag を書き込みます。
   - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると自動クリアします（本番では推奨しません）。

6. Paper Trading 検証レポート
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH と併用可）。

7. AI 機能（ニュース NLP / レジーム）
   - ニューススコアリング:
     from kabusys.ai import score_news
     score_news(duckdb_conn, target_date, api_key=OPENAI_API_KEY)
   - レジーム判定:
     from kabusys.ai.regime_detector import score_regime
     score_regime(duckdb_conn, target_date, api_key=OPENAI_API_KEY)
   - OpenAI API Key が必要。失敗時は安全側にフォールバックする実装です。

---

## 運用上の注意

- Paper Trading（KABUSYS_ENV=paper_trading）では本番 DB を汚さないよう paper_trading 用 SQLite を使用します。設定を必ず確認してください。
- 本番環境（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を必ず確認してください。
- ログ: デフォルトは logs/ 以下に日次ローテートで保存されます（TimedRotatingFileHandler）。
- Kill Switch / stop_requested.flag / execution.pid 等のファイルは data/ 以下に保持されます。運用時はこれらの状態を監視してください。
- OpenAI API 利用部分は料金が発生します。API キーとコストに注意してください。
- DuckDB のクエリは prices_daily / raw_financials / raw_news 等のテーブルを参照します。適切なデータ投入が前提です。

---

## ディレクトリ構成（主要ファイル・モジュール説明）

（リポジトリの src/kabusys を想定）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — Settings クラス（環境変数読み込み・デフォルト・検証）、.env 自動ロード
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 簡易設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py — ニュース文章の LLM を使ったスコアリングロジック
    - regime_detector.py — マクロ + ETF MA を合成した市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — （注文ログ監視: 注文滞留・約定異常検出 — 実装ファイル存在）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の作成 / 評価
    - monitoring_engine.py — 複数 Monitor を束ねるエンジン
    - alert_manager.py — （通知管理: LINE 等 — 実装ファイル存在）
  - execution/
    - execution_engine.py — ExecutionEngine 本体（実行ループ等）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py — 発注周りのコンポーネント
  - portfolio/
    - portfolio_builder.py — 候補選定・スコアソート
    - position_sizing.py — 株数算出・集約キャップ処理
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - utils/
    - logging_setup.py — ルートロガー設定（stdout + 日次ローテートファイル）
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - data/ (実行時に使用/作成される想定)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - execution.pid / stop_requested.flag / kill.flag

---

## 開発者向け補足

- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動で読み込みます（OS 環境変数は上書きされません）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DB スキーマ:
  - monitoring_db.init_monitoring_db() は冪等にテーブル・インデックスを作成し、必要なマイグレーション（カラム追加等）を行います。
- テストとモック:
  - OpenAI 呼び出し周りは _call_openai_api をパッチ/モックすることでテストが容易になるよう設計されています。

---

## トラブルシューティング（よくある質問）

- 起動時に .env が読み込まれない:
  - プロジェクトルートが特定できない（.git / pyproject.toml が存在しない）場合は自動ロードをスキップします。手動で .env を置くか `--env-file` 相当のフローで指定してください。
- ログファイルが作成されない:
  - LOG_DIR の権限やディレクトリ作成失敗でファイルハンドラはスキップされ、コンソール出力のみになります。実行ユーザーに書き込み権限があるか確認してください。
- OpenAI API 呼び出しで失敗する:
  - OPENAI_API_KEY の設定を確認。速度制限やネットワーク障害はリトライ実装がありますが、極端な失敗は結果が欠損する可能性があります。

---

必要があれば README にサンプル .env、運用手順（systemd ユニット例や Dockerfile の雛形）、CI テスト手順、詳細な API ドキュメント（各モジュールの公開関数）などを追加で作成します。どの情報を優先して追加しますか？