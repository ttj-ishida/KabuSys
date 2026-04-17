# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買 / 研究 / 監視ユーティリティ群を含む Python パッケージです。  
README ではプロジェクトの概要、機能、セットアップ手順、使い方、主要ディレクトリ構成を日本語でまとめます。

注意: 実行には .env に機密情報（API トークン等）を設定する必要があります。.env は決して Git にコミットしないでください。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群から構成されます。

- ExecutionEngine（発注実行）: 実口座 / ペーパートレード両対応の発注エンジン（`run_execution.py`）
- Monitoring（監視）: システム状態・注文状況・リスク監視とアラート（`run_monitoring.py` / monitoring パッケージ）
- Portfolio construction（ポートフォリオ構築）: 候補選定、重み付け、ポジションサイズ計算などの純粋関数群（portfolio パッケージ）
- Research（リサーチ）: ファクター計算、特徴量探索、IC 計算（research パッケージ）
- AI 補助機能: ニュースのセンチメント解析、レジーム判定（OpenAI API を利用するモジュール）
- ツール: ペーパートレード検証レポート生成スクリプト等（tools パッケージ）
- 設定管理: `.env` ウィザード、設定検証 CLI（`config_setup.py`, `validate_config.py`）

設計方針として、本番データアクセスや発注 API と解析ロジックを明確に分離し、ペーパートレード時は本番 DB と分離して安全に動かせることを重視しています。

---

## 主な機能一覧

- 実行 / ペーパートレードモードの切替
  - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を用い、ペーパートレード用 DB（デフォルト `data/paper_trading.db`）に記録します。
- 監視ループ
  - CPU / メモリ / ディスク使用率、Execution プロセス存否、データ鮮度をポーリングし SQLite にログを残します。
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
- Kill Switch（停止スイッチ）
  - ドローダウン超過やポジション上限超過などのリスク条件で `data/kill.flag` を書き込み、ExecutionEngine を安全に停止させる仕組み。
- リスク監視 / 注文監視
  - ドローダウンアラート・滞留注文・約定価格異常などを検出してログ・アラートを出す。
- ポートフォリオ構築
  - 候補選定（スコア降順）、等重配分・スコア加重、リスクベースのポジションサイズ計算、セクター制限やレジーム係数等を実装。
- リサーチ
  - DuckDB 上の価格・財務データからモメンタム／ボラティリティ／バリューなどのファクターを計算。
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリ。
- AI（OpenAI）
  - ニュースの銘柄別センチメントスコア（news_nlp）
  - マクロニュース + ETF MA を使った市場レジーム判定（regime_detector）
  - API 呼び出しはリトライ・バックオフやレスポンス検証を含む堅牢な実装。
- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティ（psutil を利用）
  - .env 作成ウィザードと設定検証 CLI
  - ペーパートレード検証レポート生成スクリプト

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに `X | None` を使用しているため）
- SQLite（Python 標準ライブラリで同梱）
- システムに応じて psutil の一部機能は管理者権限が必要になる場合があります

1. リポジトリをクローンしてワークディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 最低限の依存例:
     - pip install duckdb psutil openai
     - （設定検証で YAML を検証したい場合）pip install pyyaml
   - その他、ユーティリティやテストに必要なパッケージがあれば適宜追加してください。

4. 初期設定（.env）を作成
   - 対話式ウィザードを実行して .env を生成:
     - python -m kabusys.config_setup
   - もしくは手動で `.env` を作成し、必要な環境変数を設定してください（下記参照）。

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合: python -m kabusys.validate_config --strict

6. データディレクトリ作成
   - デフォルトでは `data/` を使用します。実行前に権限やマウント先を確認してください。

---

## 環境変数（主要）

以下はコードベースで参照される主な環境変数（デフォルトや用途を併記）。必須項目は validate_config でチェックされます。

- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|...、デフォルト: INFO）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知に必要（任意）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールを使う場合必須）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch の flag パス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）

その他、config や YAML 設定ファイル（config/*.yaml）も存在し、用途別に読み込まれます。

---

## 使い方（主要コマンド）

- .env の作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit(1)）

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され `PAPER_TRADING_SQLITE_PATH`（既定 `data/paper_trading.db`）に記録され、本番 DB とは分離されます。
    - 実行中は pid ファイル（デフォルト `data/execution.pid`）を作成します。
    - 停止は監視側の kill.flag、もしくは stop フラグファイル `data/stop_requested.flag` によって実現できます（run_execution は stop flag をチェックして終了します）。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 備考:
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を変更可能。
    - 監視は monitor によって SQLite（monitoring DB）へログを書き、必要に応じて kill.flag を作成します。
    - 停止は `data/stop_requested.flag` を作成するか Ctrl+C。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD --db /path/to/paper_trading.db
  - `--db` を指定しない場合は環境変数 `PAPER_TRADING_SQLITE_PATH` またはデフォルト `data/paper_trading.db` を使います。

- AI 関連（プログラムから利用）
  - ニューススコアリング: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは OpenAI API を使うため `OPENAI_API_KEY` を設定するか、api_key を明示的に渡して呼び出してください。

停止フラグ / Kill Switch の運用メモ
- 手動で ExecutionEngine を停止したい場合: `data/kill.flag` を作成すると監視側で条件により ExecutionEngine に停止を促します（KillSwitch ロジックに従う）。
- run 系スクリプトは同梱の stop フラグ `data/stop_requested.flag` を監視しており、存在するとループを抜けて終了します。

---

## 主要ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数 / 設定読み込みロジック（.env 自動読み込み含む）
- config_setup.py — 対話式 .env 作成ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — Monitoring 起動スクリプト

subpackages:
- ai/
  - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書く
  - regime_detector.py — マクロ + ETF MA で市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite の永続化層（テーブル初期化と簡易 DAO）
  - system_monitor.py — システム状態 & データ鮮度チェック
  - trade_monitor.py — 注文滞留・約定異常チェック
  - risk_monitor.py — ドローダウン/ポジション上限監視
  - kill_switch.py — kill.flag 書き込み・評価ロジック
  - monitoring_engine.py — 複数モニタを束ねる実行ループ
  - alert_manager.py —（アラート周り。実装は該当ファイル参照）
- execution/
  - 実行エンジン関連モジュール（OrderManager, OrderRepository, ExecutionEngine 等）
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 発注株数計算、リスク/上限対応
  - risk_adjustment.py — セクター制限・レジーム乗数
- research/
  - factor_research.py — モメンタム・バリュー・ボラティリティ等の計算
  - feature_exploration.py — 将来リターン計算、IC、統計サマリ
- tools/
  - paper_verification_report.py — ペーパートレードの検証レポート生成
- utils/
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

データ / 制御ファイル（プロジェクトルート）
- data/monitoring.db（既定の監視 SQLite）
- data/paper_trading.db（ペーパートレード DB）
- data/kabusys.duckdb（DuckDB）
- data/execution.pid（ExecutionEngine の PID）
- data/kill.flag（Kill Switch）
- data/stop_requested.flag（run スクリプトの停止要求）

---

## 注意事項 / 運用上のヒント

- .env の管理は厳重に。API キーやパスワードは公開しないでください。
- 本番（KABUSYS_ENV=live）では kill_flag や各種アラート設定を十分に確認してください。validate_config は live 時に追加チェックを行います。
- OpenAI の呼び出しは外部 API を利用するため料金とレイテンシに注意してください。`OPENAI_API_KEY` は環境変数で設定するか関数引数で渡します。
- psutil や OS 権限によりプロセス優先度や CPU affinity の設定が失敗することがあります。ログの警告を確認してください。
- DuckDB / SQLite のファイルパスは環境変数で変更可能。デフォルトの `data/` 配下に書き込む前にバックアップや容量を確認してください。

---

README はここまでです。より具体的な部分（ExecutionEngine の設定や OrderRepository の仕様、AlertManager の外部通知先（LINE 等）の設定方法）が必要であれば、その対象箇所にフォーカスしたドキュメントを別途作成します。どのトピックを優先しますか？