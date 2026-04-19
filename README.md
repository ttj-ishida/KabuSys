# KabuSys

日本株向け自動売買システムのミニマム実装。  
このリポジトリはトレード実行のためのエンジン、監視・アラート、ポートフォリオ構築・リスク管理、リサーチ用ファクター計算、及び AI（ニュース NLP / レジーム判定）関連のユーティリティ群を含みます。

注意: この README はソースコード（src/kabusys 以下）を基に作成しています。

---

## プロジェクト概要

KabuSys は以下を目的とするコンポーネント群を提供します。

- 実取引・ペーパートレードを切り替え可能な ExecutionEngine（発注・リスク管理・注文管理）
- システム稼働状態、注文ログ、リスクログ等の監視（Monitoring）
- ポートフォリオ構築（候補選定・配分・株数決定・セクター制限）
- リサーチ（ファクター計算、将来リターン、IC 等）
- ニュースを用いた AI スコアリング／レジーム判定（OpenAI API 利用）
- 環境設定ウィザード、設定検証ツール、Paper Trading 検証レポート等の CLI ツール

設計上の特徴:
- DuckDB（分析用）と SQLite（監視・発注履歴）を併用
- .env による環境変数管理（config_setup による対話式作成）
- ログは標準出力と日次ローテーションファイルに出力（logs/ 以下）
- Execution と Monitoring はフラグファイルで起動/停止制御可能（data/kill.flag, data/stop_requested.flag）

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine 起動（本番 / ペーパートレード切替）
  - run_monitoring.py — SystemMonitor のポーリングループ起動
- 環境設定
  - config_setup.py — .env の対話式作成/更新ウィザード
  - validate_config.py — .env や config/*.yaml の起動前検証
- 監視関連
  - monitoring_engine.py — 各 Monitor（System/Trade/Risk）を束ねるランナー
  - monitoring_db.py — 監視ログの永続化（SQLite）
  - kill_switch.py — Kill Switch（フラグファイル書き込み）管理
- Execution 関連（発注・リスク管理など）
  - execution/ 以下にエンジン・OrderManager・RiskManager など（詳細はソース参照）
- ポートフォリオ構築
  - portfolio/ — 候補選定・重み計算・株数決定・セクター制限・レジーム乗数など
- リサーチ
  - research/ — ファクター計算（momentum/volatility/value）、特徴量解析ユーティリティ
- AI（OpenAI API を利用）
  - ai/news_nlp.py — ニュース記事の銘柄別センチメントを LLM でスコアリング
  - ai/regime_detector.py — マクロ + ETF MA を合成した市場レジーム判定
- ツール
  - tools/paper_verification_report.py — ペーパートレード検証レポート生成

ユーティリティ:
- utils/logging_setup.py — 統一的なログ設定（コンソール + 日次ローテーション）
- utils/process_priority.py — プロセス優先度 / CPU affinity 設定

---

## セットアップ手順（開発 / ローカル実行向け）

前提:
- Python 3.10 以上（typing の | 演算子などを利用）
- SQLite（Python 標準ライブラリに含まれます）
- 任意で DuckDB、psutil、openai、PyYAML などが必要（下記参照）

1. リポジトリをクローン・チェックアウト

2. 仮想環境の作成と有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール
   （requirements.txt はこのリポジトリに含まれていない想定のため、主要な依存のみ記載）
   - pip install duckdb psutil openai
   - YAML 検証を使う場合: pip install pyyaml
   - （テスト用に mock 等を追加する場合は別途）

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で .env に必要な環境変数を定義

5. 最低限必要な環境変数
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   その他（任意／デフォルトあり）:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH — ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
   - LOG_LEVEL — デフォルト: INFO
   - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番アラート用（任意）
   - OPENAI_API_KEY — AI 機能を使う場合に必須
   - PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject、デフォルト instant）
   - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）。デフォルト 60

6. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付与すると警告も失敗扱いになる: python -m kabusys.validate_config --strict

7. データ・ログディレクトリ
   - ログはデフォルトで logs/ 以下に保存されます（setup_logging が自動作成）
   - DB 等は data/ 以下を使用することが多いです。必要に応じてディレクトリ作成は自動化されています。

---

## 使い方（起動／実行例）

- ExecutionEngine を起動（現地環境に応じて KABUSYS_ENV を設定）
  - 本番/ペーパートレードは KABUSYS_ENV で切替:
    - 本番: export KABUSYS_ENV=live
    - ペーパー: export KABUSYS_ENV=paper_trading
  - 実行:
    - python -m kabusys.run_execution
  - run_execution は起動時に data/stop_requested.flag の存在を確認し、存在する場合は起動を中止します。
  - run_execution は data/execution.pid を使用して PID 管理を行います。

- Monitoring を起動
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
  - 実行:
    - python -m kabusys.run_monitoring

- Kill Switch / 停止
  - ExecutionEngine 停止のためのフラグは data/kill.flag（KillSwitch）を出力します（Monitoring による自動化や手動で書き込み可能）
  - run_monitoring/run_execution は data/stop_requested.flag による強制停止を検出します（このファイルを配置するとループを抜けます）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH （デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- AI 機能
  - OpenAI API を使う機能（news_nlp.score_news, regime_detector.score_regime）は OPENAI_API_KEY を設定してください
  - これらはモジュール関数として呼び出します（CLI ラッパーは現在含まれていないため、スクリプトや REPL から利用）

---

## 重要な環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨／重要:
- KABUSYS_ENV (development | paper_trading | live)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパー専用 DB)
- LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL)
- OPENAI_API_KEY（AI 機能利用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番アラート）
- MONITOR_POLL_INTERVAL（監視ポーリング秒）

（config/ 下の YAML ファイルも存在する想定で、validate_config はそれらの存在・パース検証を行います。PyYAML が無い場合は YAML 検証をスキップします。）

---

## ディレクトリ構成（概観）

以下は src/kabusys 以下の主要なファイル・ディレクトリです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / Settings
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - __init__.py
    - logging_setup.py          — ログ初期化
    - process_priority.py       — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py          — SQLite スキーマ / DB ラッパー
    - system_monitor.py
    - trade_monitor.py          — （存在、TradeCheckResult 等）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py          — （アラート送信ロジック、LINE 等）
  - execution/
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
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/                       — 実行時に使用されるデータ/フラグファイル（例: data/monitoring.db, data/execution.pid, data/kill.flag）
  - logs/                       — デフォルトログ出力先（setup_logging により作成）

（上記はソース内に参照されている主要モジュールを列挙しています。実際のリポジトリには他の補助ファイルやサンプル設定が存在する場合があります。）

---

## 運用上の注意・ヒント

- 本番実行時は KABUSYS_ENV=live に設定してください。validate_config は live の場合に追加の警告（LINE 未設定など）を出します。
- ペーパートレード（paper_trading）は発注ロジックをモックに切り替え、専用の SQLite（PAPER_TRADING_SQLITE_PATH）へ記録します。本番 DB と分離されます。
- ログは標準出力（stdout）と logs/<app_name>.log に日次ローテートで出力されます。logs ディレクトリの作成に失敗した場合はコンソールのみになります。
- run_monitoring.py は MONITOR_POLL_INTERVAL を参照してポーリング間隔を決定します。0 以下等不正な値はデフォルト（60秒）にフォールバックします。
- Kill Switch / stop フラグはファイルベース（data/kill.flag, data/stop_requested.flag）です。CI/運用ツールからファイルを作成してプロセス制御できます。
- AI（OpenAI）呼び出しはレート制限・一時エラー等に対してリトライ実装が施されていますが、API キー管理とコストに注意してください。

---

## よく使うコマンド例

- .env を対話作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- ExecutionEngine 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 最後に

この README はコードコメントおよびモジュール設計に基づき作成しました。実運用前には必ず .env の検証（python -m kabusys.validate_config）および単体テスト・ステージ環境での動作検証を行ってください。安全な運用（特に live モードでの誤発注回避）を最優先に設定・確認を行ってください。