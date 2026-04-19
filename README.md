# KabuSys — README (日本語)

このリポジトリは日本株自動売買システム「KabuSys」のコードベースです。  
本 README はローカルでのセットアップ、主要機能、使い方、ディレクトリ構成などをまとめたものです。

注意: 実際の取引に用いる場合は十分な検証を行い、秘密情報（API トークン等）を絶対に Git にコミットしないでください。

---

## プロジェクト概要

KabuSys は以下のようなコンポーネントを持つ自動売買プラットフォームです。

- 市場データ分析（DuckDB を利用したファクター計算・研究用モジュール）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング）
- ExecutionEngine（発注管理・ブローカークライアントの抽象化）
- 監視（System / Trade / Risk の監視、Kill Switch による強制停止）
- AI モジュール（ニュース NLP による銘柄別センチメント、レジーム判定）
- ツール（ペーパートレード検証レポート生成、設定ウィザード等）

設計方針の一部:
- DuckDB/SQLite を用いたローカル DB（分析用と監視用を分離）
- Paper Trading（ペーパートレード）時は本番 DB と完全分離
- LLM（OpenAI）呼び出しは失敗に強いフェイルセーフ（リトライ・フォールバック）
- 起動スクリプトはプロセス優先度を設定するなど運用を考慮

---

## 主な機能一覧

- 設定管理
  - .env の自動読み込み（プロジェクトルートに .env / .env.local）
  - 対話的な設定ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）

- 実行関連
  - ExecutionEngine 起動スクリプト（run_execution.py）
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用して data/paper_trading.db に記録
  - プロセス優先度 / CPU affinity 設定ユーティリティ

- 監視関連
  - System / Trade / Risk モニタ（定期ポーリング）
  - Kill Switch: 条件により data/kill.flag を書き込み ExecutionEngine を停止
  - 監視ログ永続化（SQLite, monitoring_db.py）
  - monitoring 起動スクリプト（run_monitoring.py）: MONITOR_POLL_INTERVAL でポーリング間隔を指定可能

- ポートフォリオ構築
  - 候補選定（スコア順、上位N）
  - 重み計算（等金額・スコア加重）
  - セクター上限（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）
  - ポジションサイズ計算（calc_position_sizes） — lot 単位処理・コストバッファ・aggregate cap などを考慮

- 研究（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン、IC（Information Coefficient）、統計サマリー

- AI（OpenAI）
  - ニュース NLP による銘柄別センチメント（kabusys.ai.news_nlp）
  - マクロ＋MA200 を合成した市場レジーム判定（kabusys.ai.regime_detector）
  - API 呼び出しはリトライや JSON バリデーションを含む堅牢実装

- ユーティリティ
  - ログ設定ユーティリティ（コンソール + 日次ローテートファイル出力）
  - ペーパートレード検証レポート生成スクリプト（tools/paper_verification_report.py）

---

## セットアップ手順（開発ローカル向け）

1. リポジトリをクローンし、Python 仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストールします（最低限の推奨パッケージ）。
   - 例:
     - pip install duckdb psutil openai PyYAML

   実運用では依存管理ファイル（requirements.txt / pyproject.toml）を参照してください。

3. 環境変数を設定します。
   - 対話式で .env を作成する:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成して次の主要変数を設定してください（例とデフォルト）:

     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
     - PAPER_FILL_MODE (default "instant"; allowed: instant|partial|never|reject)
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO
     - KILL_FLAG_CLEAR_ON_START (0|1) — default: 0
     - OPENAI_API_KEY (AI 機能を使う場合必須)

4. （任意）設定検証を実行:
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります。

5. 必要ディレクトリを作成（logs / data などは起動時に自動作成されることが多いですが、事前に作ると権限問題を避けられます）:
   - mkdir -p data logs

---

## 使い方（起動コマンド例）

- 監視プロセスを起動（デフォルトポーリング間隔 60 秒。MONITOR_POLL_INTERVAL で上書き可）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると paper_trading 用 DB に記録され、MockBrokerClient が使われます。

- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポートの生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連プログラム（プログラム内部 API を呼ぶ想定）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続および OpenAI API キーを必要とします。

- 停止方法（運用）
  - プロセスは data/stop_requested.flag（run_monitoring/run_execution）や data/kill.flag（KillSwitch）で外部から停止できます。
  - ExecutionEngine は data/execution.pid を使用してプロセス管理します。

---

## 環境変数（主要なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV (development|paper_trading|live) — default: development

- DB / ファイルパス
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - LOG_DIR (default: logs)

- ログ・運用
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO
  - MONITOR_POLL_INTERVAL (監視ループ間隔秒; run_monitoring 用; default: 60)
  - KILL_FLAG_CLEAR_ON_START (0|1) — 起動時に kill.flag を自動クリアするか

- AI（OpenAI）
  - OPENAI_API_KEY — AI 機能利用時に必要

- Paper Trading 動作設定
  - PAPER_FILL_MODE (instant | partial | never | reject) — default: instant

---

## ログ

- ログ出力は kabusys.utils.logging_setup.setup_logging で統一管理されています。
  - コンソール（stdout）とファイル（日次ローテーション: logs/<app_name>.log）に出力。
  - デフォルトで logs ディレクトリに出力。LOG_DIR で上書き可能。

---

## 重要なファイル / フラグ

- data/stop_requested.flag
  - run_monitoring/run_execution の外部停止フラグ（存在を検知するとループを終了）
- data/kill.flag
  - KillSwitch が書き込む停止スイッチ（ExecutionEngine 停止用）
- data/execution.pid
  - ExecutionEngine の PID ファイル（起動時に設定）

---

## ディレクトリ構成（主要モジュール）

ソースは src/kabusys 配下にまとまっています。主なサブパッケージ:

- src/kabusys/
  - __init__.py
  - config.py — 環境変数読み込み / Settings
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_monitoring.py — 監視ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト

- src/kabusys/utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py — システム状態・データ鮮度チェック
  - trade_monitor.py — （取引監視: 滞留注文等）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書き込みロジック
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - alert_manager.py — 通知管理（LINE など）※実装参照

- src/kabusys/execution/
  - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py
  - Execution ロジックとブローカー抽象化

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- src/kabusys/research/
  - factor_research.py — ファクター計算（momentum/volatility/value）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー

- src/kabusys/ai/
  - news_nlp.py — ニュース NLP による銘柄別スコアリング（OpenAI 呼び出し）
  - regime_detector.py — マクロ + MA200 ベースのレジーム判定

- src/kabusys/tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

---

## 開発者向けメモ / 運用上の注意

- Monitoring は KABUSYS_ENV にかかわらず monitoring DB（SQLITE_PATH）を使用します。Execution は paper_trading 環境だと paper_sqlite_path を使用して本番 DB と分離します。
- AI 機能（news_nlp / regime_detector）は OpenAI API キーを必要とし、利用に伴う料金・API レート制限に注意してください。失敗時はフォールバック動作がありますが、本番での取り扱いは慎重に。
- ログディレクトリや data ディレクトリの書き込み権限に注意してください。ログハンドラや DB ファイルの作成失敗時はエラーメッセージが出ます。
- .env ファイルは絶対にリポジトリにコミットしないでください（config_setup のヘッダーにも明記）。

---

## 連絡先 / 参考

この README はソースコードのコメントや docstring に基づいて作成しています。各モジュールの詳細な使用法は該当ファイルの docstring / 関数コメントを参照してください。

何か追加してほしいセクション（例: API リファレンス、設計ドキュメント等）があれば教えてください。README を拡張して対応します。