# KabuSys

日本株自動売買システムのコアライブラリ群と起動スクリプト群を含むリポジトリ。本ドキュメントはリポジトリ内の主要コンポーネントの概要、セットアップ、使い方、ディレクトリ構成を説明します。

> 注意: 実際に本番環境で動かす場合は各種 API キー・パス・フラグの設定を慎重に行ってください。`.env` に機密情報を含める際は Git 等へコミットしないでください。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能を提供するモジュール群と起動用スクリプトを備えたシステムです。

- 株価データ / 財務データを用いるファクター計算（research）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 実行エンジン（ExecutionEngine）による発注管理（paper_trading モード時は MockBroker 使用）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- ニュースを LLM（OpenAI）でスコアリングして AI スコアや市場レジーム判定を実行
- 各種ユーティリティ（ロギング設定、プロセス優先度設定、設定ウィザード、設定検証）
- ペーパートレード検証レポート生成ツール

設計方針として「本番口座や発注 API に無駄にアクセスしない」「ルックアヘッドバイアスを排除する」「失敗に対してフェイルセーフで継続する」などが採られています。

---

## 主な機能一覧

- 実行関連
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて paper_trading/ live を切替）
    - paper_trading では MockBrokerClient を使用し、`data/paper_trading.db` に記録して本番 DB と分離
    - 停止フラグ（data/stop_requested.flag）を監視して安全に停止
- 監視関連
  - run_monitoring.py: SystemMonitor のポーリングループを起動（デフォルト 60 秒）
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能
    - 監視ログは SQLite（デフォルト `data/monitoring.db`）に永続化
    - 監視は環境にかかわらず production の sqlite_path を利用（意図的挙動）
  - monitoring パッケージ: SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch / MonitoringDB
    - RiskMonitor がドローダウンやポジション上限を検出し、kill.flag を書き込む等の処理を行う
- 研究・ファクター計算
  - research パッケージ: モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB 接続を受ける）
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）等
- AI 関連
  - ai.news_nlp: OpenAI（gpt-4o-mini）を使ったニュースセンチメントスコアリングと ai_scores への書き込み
  - ai.regime_detector: ETF (1321) の MA 乖離 + マクロニュースセンチメントを合成して市場レジーム判定／書き込み
- ポートフォリオ構築
  - portfolio パッケージ: 候補選定、等配分・スコア加重、セクター上限適用、ポジションサイズ計算（単元丸め・集約上限対応）
- ユーティリティ
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 設定検証 CLI（.env や config/*.yaml の簡易チェック）
  - tools.paper_verification_report: Paper Trading 検証レポート生成（稼働率、成功率、レイテンシ等）
  - utils.logging_setup: 統一的なロギング設定（stdout + 日次ローテートファイル）
  - utils.process_priority: プロセス優先度・CPU affinity の設定

---

## セットアップ手順（開発用の簡易手順）

以下はローカルで実行するための一般的な手順です。実際の依存関係は pyproject.toml / requirements.txt を参照してください。

1. Python 仮想環境の作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - pip install -r requirements.txt
   - もし requirements.txt がない場合は、少なくとも次を入れてください:
     - duckdb, psutil, openai, PyYAML（config 検証用）
   - 開発インストール（パッケージとして参照したい場合）
     - pip install -e .

3. 初期設定ファイルの作成（推奨: 対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは `.env` を作成します。完成後は設定の検証を行ってください:
     - python -m kabusys.validate_config
     - `--strict` を付けると警告も失敗扱いになります

4. データディレクトリやログディレクトリの準備
   - デフォルトでは `data/`、`logs/` を使用します。自動で作成される場合もありますが、権限等を確認してください。

5. OpenAI を利用する場合
   - 環境変数 `OPENAI_API_KEY` を設定するか、API キーを該当関数に渡してください。

---

## 環境変数（主要項目）

- 必須（運用に必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 主要オプション（デフォルト値）
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — (paper_trading 用) デフォルト: data/paper_trading.db
  - LOG_LEVEL — デフォルト: INFO
  - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知用（任意）
  - OPENAI_API_KEY — OpenAI を使う場合に必要
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか (0/1、デフォルト 0)

設定は `.env` で管理できます（config_setup にて対話式生成可能）。自動ロードはプロジェクトルート（.git または pyproject.toml）を検出した場合に `.env` / `.env.local` を読み込みます。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 実行／使い方

- ExecutionEngine の起動（通常の実行）
  - python -m kabusys.run_execution
  - 動作モードは `KABUSYS_ENV` によって切り替わります
    - paper_trading → MockBrokerClient を使用、データベースは paper_sqlite_path（分離）
    - live / development → 実ブローカー等の設定に従う
  - 停止制御
    - 実行中は `data/stop_requested.flag` の存在を監視します。ファイルが作成されるとエンジンは停止します。
    - `pid` ファイルは `data/execution.pid`（デフォルト）へ書き込まれます

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - デフォルトは 60 秒間隔で SystemMonitor.check_once() を呼び続けます
  - 環境変数 `MONITOR_POLL_INTERVAL` で間隔を秒単位で上書き可能（1 以上の整数）
  - 監視は監視用 SQLite（settings.sqlite_path）へ書き込みを行います（監視は env に関係なく本番 sqlite_path を使う仕様に注意）

- 設定ウィザード
  - python -m kabusys.config_setup
  - 対話式に `.env` を生成します

- 設定検証
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`

- AI / レジーム判定（スクリプト API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.connect(...)）を受け取り内部でテーブルを参照して書き込みを行います
  - OpenAI API キーは `OPENAI_API_KEY` または引数 `api_key` で指定

- ロギング
  - すべての起動スクリプトは共通の setup_logging を使います（stdout と logs/<app_name>.log を日次ローテート）
  - デフォルトログディレクトリは `logs/`（環境変数 `LOG_DIR` で変更可）

---

## 停止 / Kill Switch について

- Kill Switch は `data/kill.flag` に理由文を保存することで ExecutionEngine 停止を促します（monitoring の評価結果に基づく）
- MonitoringEngine は RiskMonitor の判定やその他のアラートにより KillSwitch.evaluate() を呼び、必要なら kill.flag を書き込みます
- ExecutionEngine 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアしますが、本番では危険なためデフォルトは 0（クリアしない）が推奨されます

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定の解決と Settings クラス
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）でのスコアリング
    - regime_detector.py — 市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — システム状態確認（CPU/メモリ/ディスク・データ鮮度・プロセス生存）
    - trade_monitor.py — （実装ファイル群: 滞留注文等の監視。リポジトリ内に存在）
    - risk_monitor.py — ドローダウン・ポジション上限の監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — （通知管理。リポジトリ内に存在）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数計算・スケーリング・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム・バリュー・ボラティリティ計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - utils/
    - logging_setup.py — 統一ロギング設定
    - process_priority.py — プロセス優先度 / CPU affinity の設定
  - monitoring_db.py, other helpers...

リポジトリのルートには `data/`（デフォルトの DB やフラグファイル）、`logs/`（ログファイル）が使われます。

---

## 開発 / デバッグのヒント

- ログは stdout と logs/<app_name>.log に出力されるため、起動時のログ/エラーを確認してください。
- validate_config.py を先に実行して設定漏れやパスの問題を検出できます。
- Paper Trading（paper_trading）モードは実 DB と分離しているため、安全に振る舞いを確認できます。
- OpenAI を使う処理（ニュース NLP / レジーム判定）は API 利用制限や異常応答を考慮して設計されていますが、API キー管理と呼び出し制御（レートやリトライ）を適切に設定してください。
- モジュール単位で動作を確認する場合は、DuckDB 接続にローカルの small な `data/kabusys.duckdb` を用意してテストデータを読み込むと良いです。

---

## 付記

この README はソース内のドキュメント（docstring）や CLI ヘルプを元に作成しています。より詳細なチュートリアルや運用手順は別途ドキュメント（運用手順書）を作成してください。

不明点があれば、どの機能について README を補完すべきか教えてください。必要に応じて起動例や .env のサンプルを追加で生成します。