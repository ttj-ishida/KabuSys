# KabuSys

日本株向け自動売買システムのコードベース（簡易 README）。  
このドキュメントはプロジェクトの概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

注意: 実行に必要な外部ライブラリやインフラは環境によって異なります。ここではソースコード中の依存・挙動に基づく一般的な手順と説明を記載しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を目的としたモジュール群です。主要な機能群は以下の通りです。

- ExecutionEngine（発注実行エンジン）: ブローカークライアントを介して注文を管理・実行
- Monitoring（監視）: システム稼働状況、データ鮮度、注文状態、リスク（ドローダウン/ポジション上限）を定期チェックし、必要に応じてアラートや Kill Switch を発動
- Portfolio construction（ポートフォリオ構築）: 候補選定・重み計算・サイズ決定・セクター制限などの純粋関数
- Research（リサーチ）: ファクター計算、将来リターン計算、IC 計算などの分析ユーティリティ（DuckDB 前提）
- AI（OpenAI を用いたニュースセンチメント / レジーム検出）: ニュースを LLM に送信して銘柄別スコアや市場レジーム判定を生成
- CLI ツール: .env 設定ウィザード、設定検証、Paper Trading の検証レポート生成など

設計上の特徴:
- 本番・ペーパートレード用 DB の分離（paper_trading 環境時）
- .env 自動ロード（プロジェクトルートが検出できる場合）
- ログは統一的なセットアップ（stdout + 日次ローテーションファイル）
- OpenAI 呼び出しはバックオフ・バリデーションを含む堅牢な実装
- 多くのモジュールは副作用を持たない純粋関数（テストしやすい）

---

## 主な機能一覧

- 実行/監視
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV により paper_trading 用の MockBroker を使用）
  - run_monitoring: SystemMonitor をポーリングして system_status などを記録
  - Kill Switch とフラグファイルによる安全停止

- 監視・アラート
  - system_monitor: CPU/Mem/Disk、プロセス生存、データ鮮度をチェック
  - trade_monitor: 注文滞留・約定異常などの検出（モジュール内に該当ロジックあり）
  - risk_monitor: ドローダウンやポジション上限の検出と risk_logs 書込み
  - monitoring_engine / monitoring_db: ポーリングの統合と SQLite 永続化

- ポートフォリオ構築
  - 候補選定（スコア順）/ 等分配・スコア加重配分 / リスクベース発注量計算 / セクターキャップ / レジーム乗数

- リサーチ
  - ファクター計算（momentum / volatility / value）
  - forward return、IC、統計サマリー

- AI（OpenAI）
  - news_nlp: raw_news を集約し LLM で銘柄別センチメントを算出、ai_scores に永続化
  - regime_detector: ETF（1321）の MA200 とマクロニュースを組み合わせ市場レジームを判定

- 開発・運用補助
  - config_setup: .env を対話式で生成・更新するウィザード
  - validate_config: 環境変数や config/*.yaml の簡易検証 CLI
  - tools.paper_verification_report: Paper Trading の検証レポート生成

---

## セットアップ手順（開発/実行前の準備）

以下は一般的な手順例です。実行環境に合わせて適宜調整してください。

1. Python の準備
   - 推奨: Python 3.10 以上（コードは型注釈等を使用）
   - 仮想環境を作成して有効化することを推奨します:
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - ソースに requirements.txt がない場合、最低限以下が必要になります:
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - pyyaml（validate_config の YAML 検証を使う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

3. プロジェクトルートに .env を作成
   - 自動で .env をロードする仕組みがあるため、プロジェクトルートに .env を置きます。
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 重要な環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - OPENAI_API_KEY（AI 機能を使用する場合）
   - 自動ロードを無効にする:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みをスキップします（テスト用）

4. データディレクトリの作成
   - デフォルトでは `data/`、ログは `logs/` に出力されます。必要なら作成してください。多くのコードは起動時に自動作成しますが、明示的に:
     - mkdir -p data logs

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

6. DB 初期化
   - run_monitoring / run_execution は起動時に監視 DB スキーマ（monitoring_db.init_monitoring_db）を作成します。特段の初期化手順は不要です。

---

## 使い方（実行例）

基本的にはモジュールを直接実行します（パッケージとして実行できるように if __name__ == "__main__" があるファイル）。

- 実行エンジン（ExecutionEngine）を起動
  - デフォルト（KABUSYS_ENV に基づく動作）
    - python -m kabusys.run_execution
  - ペーパートレードで起動するには .env で KABUSYS_ENV=paper_trading を設定
    - この場合、MockBrokerClient が使用され、デフォルトで data/paper_trading.db に記録されます

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更するには環境変数 MONITOR_POLL_INTERVAL（秒）を設定
    - 例: export MONITOR_POLL_INTERVAL=30
    - 不正な値（0以下・非整数）はデフォルト 60 秒にフォールバック

- 停止（運用上の停止）
  - 実行中のプロセスはプロジェクトルートの `data/stop_requested.flag` が存在すると早期終了します（run_* スクリプトでチェック）。
  - ExecutionEngine の安全停止は kill.flag により行う（Kill Switch ロジック）。Kill Switch は `data/kill.flag` を書き込んでエンジン停止を誘発します。
  - ExecutionEngine の PID は `data/execution.pid` に書き込まれます（このファイルを使った外部監視も可能）。

- Paper Trading の検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルトの DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で変更可）

- 環境設定ウィザード / 検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

- AI 機能
  - news_nlp.score_news / regime_detector.score_regime は OpenAI API を利用します。実行前に OPENAI_API_KEY を設定してください。
  - 呼び出しはプログラム内 API を通じて行うため、直接 CLI は用意されていません（必要ならラッパースクリプトを追加可能）。

- ログ
  - ログは stdout とファイル（logs/<app_name>.log）に出力されます。
  - ローテーションは日次、30 ファイル分保持。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- LOG_DIR（ログディレクトリ、デフォルト: logs）
- OPENAI_API_KEY（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリア、0/1）

config_setup.py のウィザードや validate_config.py を使うと主な変数の検証・生成ができます。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイルと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数/.env の自動ロードと Settings クラス（アプリ設定取得）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じて behavior が変わる）
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを LLM でスコアリングし ai_scores に書き込む処理
    - regime_detector.py — マクロ + MA200 を組み合わせたレジーム判定
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 発注株数計算（単元丸め・リスク制約）
    - risk_adjustment.py — セクター制限・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー算出
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
    - __init__.py
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化層（スキーマ作成・読み書きユーティリティ）
    - system_monitor.py — CPU/Mem/Disk / データ鮮度 / Execution プロセス監視
    - trade_monitor.py — 注文ログの監視（滞留・異常等）
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 書き込み（Execution 停止トリガ）
    - monitoring_engine.py — 各 Monitor をまとめるエンジン
    - alert_manager.py — （アラート送信管理、LINE 等を想定。実装箇所を参照）
  - execution/
    - broker_factory.py — ブローカークライアント生成（本番 or mock）
    - execution_engine.py — 発注セッションの実行ロジック
    - order_manager.py — 注文管理
    - order_repository.py — 発注履歴の永続化（SQLite 等）
    - reconciler.py — 差分解消・再試行ロジック
    - risk_manager.py — 実行時リスク制御
  - utils/
    - logging_setup.py — ログの統一セットアップ（stdout + 日次ファイル）
    - process_priority.py — プロセス優先度 / CPU アフィニティ設定（psutil 使用）
    - __init__.py

（実際にはさらに細かい実装ファイルが存在します。上は主だったモジュールの一覧です）

---

## 運用メモ / 注意点

- .env は絶対にリポジトリにコミットしないでください（秘密情報を含む）。config_setup は .env を生成しますが、生成した .env を Git 管理下に置かないようにしてください。
- KABUSYS_ENV=live の場合は本番 API に接続されます。LINE 通知設定や kill flag の設定など本番運用に必要なガードが入っているか validate_config で確認してください。
- MONITORING（監視）は本番・開発に関わらず production 用 sqlite_path を参照する設計の箇所があるため、実行前に path を確認してください（run_monitoring 内コメント参照）。
- OpenAI を利用する機能はネットワークと API コストがかかります。API キー管理と呼び出し頻度に注意してください。news_nlp と regime_detector はリトライ・クリッピング・部分失敗保護を入れて堅牢化していますが、運用ポリシーに基づく制御が必要です。
- process_priority / cpu_affinity の設定は権限に依存します（Linux/Windows 差異あり）。失敗時は警告が出てスキップされます。

---

必要に応じて README を拡張し、実行例（systemd unit / Dockerfile / docker-compose 構成）、ユニットテストの実行方法、CI/CD の手順、詳細な設定項目の説明（config/*.yaml の仕様）を追加してください。もし README に追加してほしい具体的な例（起動スクリプト、systemd ユニット、Dockerfile など）があれば教えてください。