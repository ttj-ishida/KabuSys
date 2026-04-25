# KabuSys

日本株向け自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、売買シグナル生成・ポートフォリオ構築・発注実行・監視・研究用ユーティリティを含む自動売買基盤の一部実装です。主な特徴はフェイルセーフ設計（ペーパートレード分離、Kill Switch、監視ログ）、DuckDB を用いたファクター計算・研究機能、LLM を使ったニュースセンチメント評価などです。

バージョン: 0.1.0

---

## 主要機能（概要）

- 実行エンジン起動スクリプト
  - run_execution.py: ExecutionEngine を起動。`KABUSYS_ENV=paper_trading` の場合は MockBroker + 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
- 監視プロセス起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループを実行。ポーリング間隔は環境変数で調整可能。
- 環境設定支援
  - config_setup.py: 対話式ウィザードで `.env` を生成 / 更新。
  - validate_config.py: `.env` と config/*.yaml の設定検証 CLI。
- 監視・Kill Switch 機能
  - monitoring パッケージ: system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, monitoring_db 等。監視ログは SQLite に永続化。
- ポートフォリオ構築ユーティリティ（純粋関数）
  - portfolio パッケージ: 候補選定、等配分/スコア配分、セクター制限、ポジションサイズ計算（単元丸め・リスク制限等）。
- 研究 / ファクター計算
  - research パッケージ: momentum/value/volatility 等のファクター計算、将来リターン、IC 計算、統計サマリ。
  - DuckDB 接続を受けて SQL＋Python で計算。
- AI（LLM）連携
  - ai.news_nlp: raw_news をまとめて OpenAI に送り銘柄ごとのセンチメントを ai_scores テーブルへ書き込む。
  - ai.regime_detector: ETF（1321）MA200 乖離＋マクロニュースで市場レジーム判定し market_regime に書き込み。
- ユーティリティ
  - utils.logging_setup: stdout + 日次ローテートファイルでログを統一的に設定。
  - utils.process_priority: プロセス優先度 / CPU affinity 設定。

---

## セットアップ手順（ローカル開発環境向け）

前提:
- Python 3.9+（コードは型注釈等を含むため 3.9 以上を想定）
- Git リポジトリをクローン済みであること

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 最小: duckdb, psutil, openai
   - オプション: PyYAML（validate_config の YAML 検証に使用）
   - 例:
     - pip install duckdb psutil openai
     - pip install pyyaml  # 任意

   （プロジェクトに requirements ファイルがなければ上記を個別インストールしてください）

3. .env の作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - または `.env` を手動作成（リポジトリルートに配置）
     - 主要な環境変数（例）:
       - JQUANTS_REFRESH_TOKEN=your_token_here
       - KABU_API_PASSWORD=your_password_here
       - KABUSYS_ENV=development | paper_trading | live
       - DUCKDB_PATH=data/kabusys.duckdb
       - SQLITE_PATH=data/monitoring.db
       - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
       - LOG_LEVEL=INFO
       - LINE_CHANNEL_ACCESS_TOKEN= (任意)
       - LINE_USER_ID= (任意)
       - KILL_FLAG_CLEAR_ON_START=0
       - PAPER_FILL_MODE=instant | partial | never | reject

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリの作成（ログ・DB 用）
   - mkdir -p data logs

---

## 使い方

以下は代表的な実行例です。各コマンドはプロジェクトルート（pyproject.toml もしくは .git がある場所）で実行してください。

- 実行エンジンを起動（本番設定 or ペーパートレード）
  - 環境変数で切り替え:
    - 本番: export KABUSYS_ENV=live
    - ペーパートレード: export KABUSYS_ENV=paper_trading
  - 起動:
    - python -m kabusys.run_execution
  - 補足:
    - paper_trading の場合、MockBrokerClient を使い data/paper_trading.db を使用します（本番 SQLite と分離）。
    - 実行中は data/execution.pid（デフォルト）が作成される可能性があります。
    - 停止は stop フラグファイル data/stop_requested.flag の作成で検知されます（外部から書き込んで停止させる）。

- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）。不正値はデフォルトへフォールバック。
  - 監視は monitoring DB（Settings.sqlite_path）へ書き込みます。Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する実装です。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数の代替）

- AI 系処理（プログラムから呼び出す）
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
    - OPENAI_API_KEY 環境変数または api_key 引数を渡す必要あり
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 同上
  - これらは DuckDB 接続を受け取り、結果を ai_scores / market_regime テーブル等へ書き込みます。

- .env の生成・確認
  - python -m kabusys.config_setup  （対話ウィザード）
  - python -m kabusys.validate_config  （検証）

- ログ
  - ログは stdout と logs/<app_name>.log（日次ローテーション、30日保持）へ出力されます。
  - LOG_DIR 環境変数でログディレクトリを変更できます。

- Kill Switch / 停止フラグ
  - KillSwitch は data/kill.flag を書き込み、ExecutionEngine に停止を命令します（KillSwitch API を使うかファイルを作成）。
  - monitoring 側は kill.flag の検知・書き込みを行います。
  - kill.flag を削除してクリアする: ファイルを手動で削除するか KillSwitch.clear() を呼ぶ。

---

## 重要な環境変数（まとめ）

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABUSYS_ENV — execution のモード（development | paper_trading | live）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — AI 機能用（news_nlp, regime_detector）
- MONITOR_POLL_INTERVAL — 監視プロセスのポーリング間隔（秒、デフォルト 60）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト logs/）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

---

## ディレクトリ構成（主なファイル・モジュール）

リポジトリの主要なモジュール/ファイルを抜粋しています（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
- src/kabusys/utils/
  - logging_setup.py       — ログ初期化ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity 設定
- src/kabusys/monitoring/
  - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard 等）
  - system_monitor.py      — システム状態・データ鮮度チェック
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - trade_monitor.py       — （取引ログ/注文監視）※実装参照
  - kill_switch.py         — kill.flag の生成 / 判定
  - monitoring_engine.py   — 各 Monitor を束ねるループ
  - alert_manager.py       — 通知管理（LINE など）※実装参照
- src/kabusys/execution/
  - execution_engine.py    — 発注エンジン（EngineConfig, run_session 等）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py
- src/kabusys/portfolio/
  - portfolio_builder.py   — 候補選定・重み計算
  - position_sizing.py     — 株数算出・リスク・単元丸め
  - risk_adjustment.py     — セクター上限・レジーム乗数
- src/kabusys/research/
  - factor_research.py     — momentum/volatility/value 等の計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリ
- src/kabusys/ai/
  - news_nlp.py            — ニュースセンチメント集約・OpenAI 呼び出し
  - regime_detector.py     — 市場レジーム判定（MA200 + macro sentiment）
- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

---

## 開発・運用上の注意点

- .env は機密情報を含むため、絶対に Git にコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します（誤って Kill Switch を自動クリアすることを防ぐため）。
- ペーパートレードは本番用 DB と分離されていますが、設定ミスに備えて validate_config を用いてパスや設定を事前検証してください。
- OpenAI を使う処理は API 呼び出しに失敗した場合フェイルセーフ（スコア 0 にフォールバック、あるいは処理をスキップ）を採っていますが、API キーの管理・レート制限には留意してください。
- logs/ ディレクトリに充分な容量を確保してください（ファイルは日次ローテーションで 30 日保持）。

---

## よく使うコマンドまとめ

- 対話式 .env 生成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
- DuckDB/SQLite のパスを環境変数で上書き:
  - export DUCKDB_PATH=/path/to/kabusys.duckdb
  - export SQLITE_PATH=/path/to/monitoring.db

---

README は実装の要点をまとめたものです。各モジュールの詳細な仕様や追加の設定項目は該当するソースコードの docstring / コメントを参照してください。必要であれば、各モジュールごとの詳細ドキュメント（API 仕様・設定例・設計メモ）も作成できます。