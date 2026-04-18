# KabuSys

日本株向け自動売買システムのライブラリ／実行スクリプト群です。  
このリポジトリは、戦略・ポートフォリオ構築、発注エンジン、監視、研究ツール、LLM を使ったニュース解析などを含むモジュールで構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能群を持つ自動売買プラットフォームのコア実装です。

- データ取得・分析（DuckDB を想定）
- ファクター計算 / 特徴量探索（research）
- ポートフォリオ構築（銘柄選定・重み・サイズ計算）
- 発注（ExecutionEngine） — 本番 / ペーパートレード分離
- 監視（System / Trade / Risk）と Kill Switch（停止フラグ）
- AI（OpenAI）を用いたニュースセンチメント解析・市場レジーム判定
- 運用支援ツール（.env ウィザード・設定検証・ペーパートレード検証レポート 等）

設計方針の一部:
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV による切替）
- 重要処理は冪等に実装（設定・DB マイグレーション等）
- LLM 呼び出しはフェイルセーフ（失敗時はスキップ or デフォルト値）

---

## 主な機能一覧

- 実行 (Execution)
  - run_execution: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い `data/paper_trading.db` に記録。
- 監視 (Monitoring)
  - run_monitoring: SystemMonitor のポーリングループを起動。監視ログは SQLite（デフォルト `data/monitoring.db`）へ保存。
  - MonitoringEngine、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、AlertManager 等。
- 設定管理
  - config_setup: `.env` を対話式に生成 / 更新するウィザード。
  - validate_config: `.env` と `config/*.yaml` の整合性チェック CLI。
- 研究・分析
  - research: ファクター計算（momentum/value/volatility）や特徴量解析、IC 計算など（DuckDB を利用）。
- AI
  - ai.news_nlp: raw_news を OpenAI に送って銘柄ごとのセンチメントを ai_scores に書き込み。
  - ai.regime_detector: マクロニュース＋ETF MA を組み合わせて市場レジームを判定・保存。
- ツール
  - tools.paper_verification_report: ペーパートレード DB を解析して検証レポートを生成。

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン / 作業ディレクトリへ移動

2. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須（主なもの）:
     - duckdb
     - psutil
     - openai
   - オプション:
     - PyYAML（`validate_config` の YAML 検証用）
   - （requirements.txt がない場合は手動で pip install duckdb psutil openai pyyaml）

4. .env の用意
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは `.env` をプロジェクトルートに作成して環境変数を設定してください。

5. 設定検証（必須項目が揃っているか確認）
   - python -m kabusys.validate_config
   - 本番環境チェックを厳密にする場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリ作成（必要に応じて）
   - logs/ や data/ は自動作成されますが権限等の問題があれば事前に作成してください。

---

## 主要環境変数（よく使うもの）

- JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）デフォルト: development
  - paper_trading 時は Execution が専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
- PAPER_FILL_MODE: paper_trading の Mock ブローカーでの約定挙動（instant/partial/never/reject）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト `data/paper_trading.db`）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / regime_detector で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH: 監視用 SQLite（デフォルト `data/monitoring.db`）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力ディレクトリ（デフォルト `logs`）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env をロードする機構を無効化

注意: `.env` の自動ロードはプロジェクトルート（.git または pyproject.toml 存在）を基準に行われます。

---

## 使い方（実行例）

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ExecutionEngine 起動（本番 / ペーパートレードは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution

- 設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告をエラー扱い）:
    - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI スコア生成 / レジーム判定（ライブラリ API）
  - ai.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を渡して呼び出します。API キーは引数または OPENAI_API_KEY 環境変数で指定。

- 停止方法
  - プロセスを直接停止（Ctrl+C）
  - またはプロジェクトルート `data/stop_requested.flag` を作成すると run_monitoring/run_execution が検知して順次終了します。
  - KillSwitch はリスク条件を満たすと `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送ります。

---

## ログ

- ログはデフォルトで stdout とファイル（logs/<app_name>.log）に出力されます。
- ログ設定は `kabusys.utils.logging_setup.setup_logging(app_name=...)` で統一的に処理しています。
- 日次ローテーション（30 日保持）。

---

## ディレクトリ構成（主なファイル／フォルダ）

読みやすいように主要部分を抜粋します（実際は `src/kabusys/` 以下に配置）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py        — 監視用 SQLite の永続層
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - system_monitor.py       — システム状態・データ鮮度監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 制御
    - ...（trade_monitor, alert_manager 等）
  - execution/
    - execution_engine.py     — 発注エンジン本体（EngineConfig / run_session 等）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/
    - pipeline.py              — データパイプライン（prices_daily 取得等）
    - stats.py                 — 統計ユーティリティ（zscore 等）
  - utils/
    - logging_setup.py
    - process_priority.py
    - ...（その他ユーティリティ）

- config/
  - （設定 YAML テンプレート群）
    - system_config.yaml
    - data_config.yaml
    - strategy_config.yaml
    - risk_config.yaml
    - execution_config.yaml
    - monitoring_config.yaml
  - ※ validate_config はこれらの存在や YAML のパースをチェックします（PyYAML が必要）

---

## 注意点 / 運用上のポイント

- DB 分離:
  - 監視ログ（monitoring）は Settings.sqlite_path（デフォルト `data/monitoring.db`）を使用します。run_monitoring は環境にかかわらず本番 sqlite_path を使用する点に注意してください。
  - 発注（Execution）は KABUSYS_ENV=paper_trading 時に paper_sqlite_path（デフォルト `data/paper_trading.db`）に切替えます。
- .env の自動読み込み:
  - プロジェクトルートが特定できる場合、自動的に `.env` と `.env.local` を読み込みます。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- OpenAI:
  - ai モジュールは OpenAI API を利用します。API キー未設定時は ValueError を送出する関数があります（呼び出し側で捕捉してください）。
  - レート制限や一時的失敗に対してはリトライ／フォールバック実装あり。
- 権限:
  - ログディレクトリ・data ディレクトリに書き込み権限が必要です。権限不足時はコンソールのみ出力になる場合があります。
- 優先度設定:
  - 起動時にプロセス優先度（high）へ切り替える処理があります（psutil を使用）。権限不足で失敗することがあるため警告ログのみになります。

---

## 開発者向け補足

- 単体関数群は副作用を極力避ける設計（純粋関数）になっています（例: portfolio/* は DB を参照しない）。
- DB スキーマは `monitoring_db.init_monitoring_db` で冪等的に作成・マイグレーションされます。
- LLM 呼び出し部分はテスト時に差し替えやすいように `_call_openai_api` をラップしています（unittest.mock.patch が使えます）。

---

もし README に追加したい具体的な使用例（環境変数のテンプレート、起動スクリプトの systemd ユニット例、依存関係の固定化ファイル など）があれば教えてください。必要に応じてサンプル .env.example も作成できます。