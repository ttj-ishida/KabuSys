# KabuSys — 日本株自動売買システム

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリです。  
本 README はコードベース（src/kabusys 以下）を対象に、プロジェクト概要、機能、セットアップ方法、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたモジュール群です。主な責務は次の通りです。

- 取引エンジン（ExecutionEngine）による発注管理（実口座 / ペーパートレード対応）
- 監視コンポーネント（System / Trade / Risk）による稼働監視とアラート/Kill Switch
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- リサーチ用モジュール（ファクター計算、特徴量探索）
- ニュース NLP / レジーム判定（OpenAI を用いたセンチメント評価）
- 各種 CLI ユーティリティ（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計方針の一部：
- DuckDB / SQLite をデータストアとして使用（分析用と監視ログで分離）
- 本番環境とペーパートレードの DB を分離可能
- LLM 呼び出しはフェイルセーフに設計（失敗時はスキップやデフォルト値で継続）
- ファイルフラグ（kill.flag / stop_requested.flag）で外部からプロセス制御

---

## 機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
  - 対話的に .env を作成 / 更新
- 設定検証 CLI（python -m kabusys.validate_config）
  - .env と config/*.yaml の存在・簡易妥当性検証
- Execution 起動スクリプト（python -m kabusys.run_execution）
  - 本番 / ペーパートレード切替
  - ブローカークライアント生成、OrderManager / RiskManager / Reconciler の起動
  - PID ファイル管理・停止フラグ監視
- Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - SystemMonitor のポーリングループ（デフォルト 60 秒）
  - 監視データを SQLite（monitoring.db）に永続化
- Monitoring エンジン（各種 Monitor の統合）
  - KillSwitch 評価、AlertManager 経由の通知
- 監視データ永続化（monitoring_db）
  - system_status、trade_logs、positions、risk_logs、dashboard テーブル
  - マイグレーション（列追加）を含む初期化
- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定 / 等配分・スコア加重 / リスク制約（セクター上限） / ポジションサイズ計算
- 研究用モジュール（research）
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン、IC 計算、統計サマリー
- AI モジュール（ai）
  - news_nlp: ニュース記事の銘柄別センチメントを OpenAI で評価して ai_scores に保存
  - regime_detector: ETF とマクロニュースを組み合わせて市場レジームを判定
- ツール（tools）
  - paper_verification_report: ペーパートレード DB を集計し PASS/FAIL 判定を行うレポート出力

---

## 前提 / 必要要件

- Python 3.10 以上（PEP 604 型ヒントなどの構文を使用）
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml のパースを行う場合）
- OS: Linux / macOS / Windows（プロセス優先度設定はプラットフォーム依存でフォールバックあり）

requirements.txt がない場合は手動でインストールしてください：
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローン・チェックアウト
2. Python 仮想環境を作成して依存をインストール
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
   - pip install duckdb psutil openai PyYAML
3. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードで必要項目（J-Quants トークン、kabu API パスワードなど）を入力
4. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば警告 / エラーに従って修正
5. データディレクトリの作成（logs / data などが必要）
   - mkdir -p data logs

※ .env は絶対に Git にコミットしないでください（APIキー等が含まれるため）。

---

## 主な環境変数（概要）

以下はコード内で参照される主要な環境変数とデフォルト値の一覧です。必須項目は README の「必須」扱いで明記します。

必須（実行に必要）
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

主要（任意・デフォルトあり）
- KABUSYS_ENV — 実行環境（development / paper_trading / live） デフォルト: development
- OPENAI_API_KEY — OpenAI API キー（ai モジュール使用時に必要）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH — 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...） デフォルト: INFO
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant/partial/never/reject） デフォルト: instant
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）

その他、config/*.yaml（system_config.yaml など）を参照します（存在しない場合は警告）。

.env の例（config_setup で自動生成される内容の一部）:
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

---

## 使い方（代表的なコマンド）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い（exit code 1）

- ExecutionEngine を起動（本番/ペーパーは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - ペーパートレード時（KABUSYS_ENV=paper_trading）: data/paper_trading.db を使用して本番 DB とは分離されます。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中は data/execution.pid に PID を書きます。
  - 外部から停止するには data/stop_requested.flag を作成するか、Kill Switch を使います。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - デフォルトで Settings.sqlite_path（monitoring.db）を使い監視ループを行います（MONITOR_POLL_INTERVAL で間隔指定可）。
  - 停止は KeyboardInterrupt（Ctrl+C）または data/stop_requested.flag を作成。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数より優先して指定可能）

- AI モジュール
  - OpenAI API キー（OPENAI_API_KEY または引数）を指定し、関数を呼び出して利用します。
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらはスクリプトではなくライブラリ関数なので、運用スクリプトやジョブから呼んでください。

ログ設定:
- ログは標準出力（stdout）と日次ローテートのファイル（logs/<app_name>.log）へ出力されます。
- ログディレクトリは環境変数 LOG_DIR で上書き可能。

停止フラグと Kill Switch:
- data/stop_requested.flag — run_* スクリプトが定期チェックしている「停止リクエスト」フラグ（手動で作成してプロセスを優雅に停止）
- data/kill.flag — KillSwitch が書き込むファイルで、ExecutionEngine に停止命令を伝える（Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 で自動クリア可能）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイル・パッケージの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py           — 市場レジーム判定（OpenAI + ETF MA）
  - monitoring/
    - monitoring_db.py             — SQLite テーブル初期化・読み書き
    - monitoring_engine.py         — Monitor 群の統合ループ
    - system_monitor.py            — CPU/メモリ/ディスク/データ鮮度チェック
    - trade_monitor.py             — （取引ログの監視：ファイル参照）
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - kill_switch.py               — kill.flag 書込ロジック
    - alert_manager.py             — （通知管理: LINE などへの通知）
  - execution/
    - broker_factory.py
    - execution_engine.py
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
  - utils/
    - logging_setup.py              — ログ初期化ユーティリティ
    - process_priority.py           — プロセス優先度 / CPU affinity 設定
    - __init__.py

data/ と logs/ はリポジトリ外（実行環境）で作成:
- data/
  - monitoring.db（デフォルト SQLITE_PATH）
  - paper_trading.db（PAPER_TRADING_SQLITE_PATH）
  - kill.flag
  - stop_requested.flag
  - execution.pid
- logs/
  - execution.log
  - monitoring.log
  - など

---

## 運用上の注意 / トラブルシュート

- .env の取り扱い:
  - .env は機密情報が含まれるため絶対に Git に含めないこと。
  - config_setup.py で作成・更新してください。
- DB の分離:
  - ペーパートレード（KABUSYS_ENV=paper_trading）は paper_sqlite_path を使い、本番用 sqlite_path と分離されます。一方、監視（run_monitoring）は環境にかかわらず本番 sqlite_path を参照する点に注意。
- OpenAI 利用:
  - OPENAI_API_KEY が未設定だと AI 関連関数は ValueError を投げます。バッチジョブや cron で実行する際は環境変数を確実に渡してください。
- 権限:
  - ログディレクトリや data/ の書き込み権限を確認してください。ログディレクトリの作成失敗時はコンソール出力のみになります。
- モニタリングの停止:
  - run_monitoring / run_execution は stop_requested.flag の存在を監視します。手動停止する場合は stop_requested.flag を作成してください（運用ルールに従ってください）。
- 依存ライブラリ:
  - PyYAML がない場合、validate_config の YAML パース検証はスキップされます（警告が出ます）。
- テスト／開発:
  - 多くの関数は副作用を持たない純粋関数として設計されています（portfolio、research 等）。ユニットテストが書きやすい構成です。

---

## 参考コマンドまとめ

- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

---

この README はコードベースの主要機能・運用フローを簡潔にまとめたものです。細かい挙動（DB スキーマ、各モジュールのパラメータ、LLM の retry ロジック等）はコード内のドキュメント文字列（docstring）を参照してください。必要であれば、個別モジュールの利用例や運用手順書を追加で作成します。