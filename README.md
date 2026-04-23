# KabuSys

日本株自動売買システムの一部を切り出した Python パッケージです。本リポジトリには監視（Monitoring）、注文実行（Execution）、ポートフォリオ構築、リサーチ／ファクター計算、AI（ニュースセンチメント・レジーム判定）などのコンポーネントが含まれます。

---

## プロジェクト概要

KabuSys は次のような責務を持つモジュール群で構成されています。

- 実際の注文発行を担う ExecutionEngine（本番 / ペーパートレード切替対応）
- システム稼働状況・データ鮮度・注文異常・リスク指標を定期的に監視する Monitoring
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出、セクター制限等）
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ等）／特徴量解析ツール
- OpenAI を用いたニュース NLP（銘柄ごとのセンチメント評価）および市場レジーム判定
- スクリプト群：環境設定ウィザード、設定検証、ペーパートレード検証レポート等

設計上の特徴：
- 本番 DB とペーパートレード用 DB は分離（環境 `KABUSYS_ENV=paper_trading` 時は paper DB を使用）
- .env ファイル自動読み込み（ただし無効化可能）
- ログはコンソール + 日次ローテーションファイル出力（logs/）
- OpenAI 呼び出しはリトライやレスポンス検証を伴う安全設計

---

## 主な機能一覧

- run_monitoring: SystemMonitor を定期ポーリングして監視ログを記録・アラート判定
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を使用（環境に依存せず監視 DB を参照）
- run_execution: ExecutionEngine の起動スクリプト
  - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し paper_trading DB（data/paper_trading.db）へ記録
  - 停止用フラグファイル（data/stop_requested.flag）や PID 管理をサポート
- config_setup: インタラクティブな .env 作成ウィザード
- validate_config: .env と config/*.yaml の簡易検証 CLI（--strict オプションあり）
- tools/paper_verification_report: ペーパートレード DB を集計して PASS/FAIL 判定のレポートを生成
- portfolio: 候補選定・重み付け・ポジションサイズ計算・リスク調整（純粋関数群）
- research: DuckDB を使ったファクター計算 / 将来リターン・IC 計算など
- ai: OpenAI を使ったニュースセンチメント（news_nlp）／市場レジーム判定（regime_detector）

---

## 前提 / 必要パッケージ（代表例）

（環境によってバージョンを合わせてください）

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config YAML 検証を行う場合）
- （任意）その他 DB / broker 関連の依存（実行環境により）

インストール例（pip）:
pip install duckdb psutil openai pyyaml

※ リポジトリに requirements.txt がない場合はプロジェクト側の指示に従ってください。

---

## 環境変数（主要項目）

必須（最低限設定が必要なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

推奨 / よく使うもの（デフォルト値を持つ）
- KABUSYS_ENV — 実行環境（development / paper_trading / live。デフォルト: development）
  - paper_trading: 発注はモック（別 DB を使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...。デフォルト: INFO）
- OPENAI_API_KEY — OpenAI を使う機能を利用する際に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番での通知（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0 推奨）

run_monitoring / run_execution に影響するファイル・フラグ:
- data/stop_requested.flag — 実行中プロセスがこのファイルの存在を検知すると正常終了（停止）する
- data/execution.pid — ExecutionEngine の PID（デフォルト配置）
- data/kill.flag — Kill Switch が書き込む停止指示ファイル（ExecutionEngine 側で監視）

.env はツール `python -m kabusys.config_setup` で対話的に作成できます。

---

## セットアップ手順（簡易）

1. リポジトリをクローン / 解凍
2. 必要パッケージをインストール
   - 例: pip install -r requirements.txt （存在すれば）
   - または個別: pip install duckdb psutil openai pyyaml
3. .env を作成
   - 対話式: python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成（.env は絶対にコミットしない）
4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする: python -m kabusys.validate_config --strict
5. 初回起動時に data ディレクトリ等が自動作成されます。必要な DB はスクリプト実行時に初期化されます（monitoring 用テーブルは init_monitoring_db による冪等作成）。

---

## 使い方（主要コマンド例）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - オプション: 環境変数 MONITOR_POLL_INTERVAL=30 を設定してポーリング間隔を変更可

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合はペーパートレード用の MockBrokerClient を使用し、paper_trading DB に記録されます。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB を直接指定: --db /path/to/paper_trading.db

- AI 関連（ニューススコア・レジーム判定）は API キーが必要
  - python -c "from kabusys.ai.news_nlp import score_news; ..."
  - または呼び出し元のアプリケーション経由で利用

停止方法（安全なシャットダウン）
- 監視・実行プロセスは data/stop_requested.flag の存在を検出して終了します。停止を要求するにはこのファイルを作成してください（運用上の手順に従ってください）。

ログ
- デフォルト: stdout（コンソール）および logs/<app_name>.log（日次ローテーション）
- LOG_DIR 環境変数でログ出力先を変更可能
- LOG_LEVEL で出力レベルを指定

---

## ディレクトリ構成（抜粋）

以下はパッケージ内の主要なファイル／ディレクトリ（src/kabusys）です：

- kabusys/
  - __init__.py
  - config.py               — 環境変数・設定取得ユーティリティ（Settings クラス）
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py   — ペーパートレード検証レポート
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py      — 監視用 SQLite 永続化層
    - system_monitor.py     — システム・データ鮮度監視
    - trade_monitor.py      — 注文・約定監視（コードベースに含まれている想定）
    - risk_monitor.py       — ドローダウン / ポジション上限監視
    - monitoring_engine.py  — 複数 Monitor を束ねるエンジン
    - kill_switch.py        — kill.flag 管理
    - alert_manager.py      — アラート発行（実装依存）
  - execution/
    - execution_engine.py   — ExecutionEngine（依存関係あり）
    - broker_factory.py     — ブローカークライアントファクトリ
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py           — ニュースセンチメント（OpenAI 呼び出し含む）
    - regime_detector.py    — 市場レジーム判定（OpenAI 呼び出し含む）
  - data/                   — 実行時に作成される DB / フラグ置き場（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag）
  - logs/                   — ログ出力先（デフォルト）

（上記は実装の主要部分を抜粋したものです。実際のリポジトリにはさらにユーティリティや補助スクリプトが含まれる可能性があります。）

---

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）では設定ミスが重大な影響を与えるため、validate_config を用いて事前チェックしてください。LINE 通知設定の確認などのガードもあります。
- OpenAI API を利用する機能は API キーが必要であり、呼び出し・課金に注意してください。API エラー時はフェイルセーフで継続する設計ですが、期待したデータが得られない可能性があります。
- .env は機密情報を含むため絶対にバージョン管理にコミットしないでください。
- 停止は基本的に data/stop_requested.flag を用いて行います。kill.flag は KillSwitch によって書き込まれ、ExecutionEngine 側で停止トリガーになります。

---

## 開発・拡張ポイント（参考）

- portfolio.position_sizing: lot_size やコストバッファを考慮したスケーリングロジック
- research.*: DuckDB を用いた高速なファクター計算、リサーチ用途に最適化
- ai.*: OpenAI のレスポンス検証、バッチ処理、リトライ実装が含まれる
- monitoring.*: 監視ログの永続化とアラート連携（LINE など）を繋げることで運用監視を強化可能

---

README はここまでです。追加で以下を生成できます：
- requirements.txt の候補
- .env.example（全キーと説明付き）
- システム図 / 起動フローの図解

必要な場合はどれを出力するか教えてください。