# KabuSys

日本株自動売買システムのモジュール群の README（日本語）。

バージョン: 0.1.0（src/kabusys/__init__.py の __version__ に準拠）

---

## プロジェクト概要

KabuSys は日本株の自動売買やそれに付随する監視・検証・リサーチ機能を提供するパッケージ群です。  
主な機能は以下の通りです。

- ExecutionEngine（発注エンジン）: 実際のブローカーあるいはペーパートレード用のモック経由で注文を管理・実行
- Monitoring（監視）: システム稼働性、注文滞留、リスク（ドローダウン・ポジション数）を定期チェックしログ化／アラート／KillSwitch を制御
- Portfolio construction（銘柄選定・配分・株数決定）: 候補選定・重み付け・単元丸め・レジーム調整
- Research（ファクター計算・特徴量解析）: Momentum/Value/Volatility 等のファクター、将来リターン・IC 計算
- AI（ニュース NLP / レジーム判定）: OpenAI を使ったニュースセンチメントやマクロセンチメント評価
- Tools（検証レポート出力など）: ペーパートレード検証レポートの生成等
- 設定管理ツール: .env 対話式ウィザード、設定検証 CLI

この README はリポジトリに含まれる主要モジュールの使い方とセットアップ手順をまとめたものです。

---

## 主な機能一覧（ハイライト）

- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 実行エンジン起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
- 監視ループ起動: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可（デフォルト 60 秒）
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- AI: ニュースセンチメント（kabusys.ai.news_nlp.score_news）、市場レジーム（kabusys.ai.regime_detector.score_regime）
- ポートフォリオ構築: 候補選定、重み付け、ポジションサイズ計算、セクター上限適用など
- 監視 DB（SQLite）用ユーティリティ: テーブル作成・永続化ロジック（monitoring_db）

---

## 必要条件 / 依存パッケージ

主に以下が必要です（プロジェクトにより追加パッケージが必要な場合があります）。

- Python 3.10+
- 必須ライブラリ（実行環境に応じてインストール）:
  - psutil
  - duckdb
  - openai（AI 機能を使う場合）
- 開発 / 一部機能:
  - PyYAML（validate_config で config/*.yaml の検証を行う場合に必要）

インストール例（pip）:
```
pip install psutil duckdb openai pyyaml
```

---

## 環境変数（重要）

主要な環境変数と説明（.env で設定する想定）:

必須
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）

運用 / オプション
- KABUSYS_ENV: 実行環境。`development` | `paper_trading` | `live`（デフォルト: development）
  - paper_trading の場合、実取引は行わず MockBrokerClient を使用し専用 SQLite に記録
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知設定（任意）
- OPENAI_API_KEY: OpenAI API を使う機能のためのキー（AI 機能利用時に必須）
- MONITOR_POLL_INTERVAL: 監視のポーリング間隔（秒）。run_monitoring で上書き可（デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（"1" で有効。デフォルト "0"）

注意:
- .env ファイルは絶対に Git にコミットしないでください。

---

## セットアップ手順（推奨ワークフロー）

1. リポジトリをクローン／配置
2. 仮想環境を作成して依存をインストール
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -r requirements.txt もしくは必要パッケージを個別にインストール
3. 環境変数を用意
   - 対話式: python -m kabusys.config_setup
     - .env ファイルを生成・更新できます（対話形式）
   - もしくは .env を手動で作成（.env.example を参照）
4. 設定の自動検証:
   - python -m kabusys.validate_config
   - 問題がある場合はメッセージに従って設定を修正。--strict を付けると警告も失敗扱いになります
5. DB 初期化
   - 監視 DB / ペーパートレード DB は起動時に必要テーブルが存在しなければ自動作成されます（init_monitoring_db を利用）
6. （AI 機能を使う場合）OPENAI_API_KEY を .env に設定

---

## 使い方（主要コマンド例）

- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録
  - 起動前に data/stop_requested.flag が存在すると起動せず終了
  - 実行中に data/stop_requested.flag を作成するとエンジンに停止シグナルが送られ安全に停止します
  - 実行時に data/execution.pid に PID を書きます

- Monitoring 起動（監視ループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可（例: MONITOR_POLL_INTERVAL=30）
  - 監視は本番 sqlite_path（KABUSYS_ENV に依存せず production の sqlite_path を使用）
  - data/stop_requested.flag を作成すると監視ループは終了します

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB パス: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）
  - レポートは稼働率、成功率、送信率、P95 レイテンシなどを出力し PASS/FAIL 判定を行います

- AI 機能（ニュース NLP / レジーム判定）
  - ニューススコアリング: kabusys.ai.score_news（内部で OpenAI を呼出し ai_scores テーブルに書込）
  - レジーム判定: kabusys.ai.regime_detector.score_regime
  - いずれも OPENAI_API_KEY が必要。Fail-safe の設計で API 失敗時はフォールバック挙動がありますが、キーは必須

---

## 停止 / Kill Switch 制御

- graceful stop:
  - run_monitoring と run_execution はプロジェクトルート/data/stop_requested.flag（run_monitoring では _STOP_FLAG）を参照します。これを作成するとループ・スレッドが安全に終了します。
  - 例: touch data/stop_requested.flag
- Kill Switch:
  - KillSwitch（kabusys.monitoring.kill_switch）は監視結果に基づいて data/kill.flag を書き込み、ExecutionEngine を停止させるトリガーを提供します。kill.flag は存在するだけで ExecutionEngine による起動抑止や停止判定に使用されます。
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動的に kill.flag をクリアします（本番では通常 0 を推奨）
- PID:
  - 実行エンジンの PID は data/execution.pid に書き込まれます。SystemMonitor はこの PID を見てプロセス稼働判定を行います。

---

## 主要ファイル / ディレクトリ構成

以下は src/kabusys 以下の主要モジュールと役割（簡易ツリー）です。実際のパッケージは src/kabusys に配置されています。

- src/kabusys/
  - __init__.py — パッケージ定義（__version__）
  - config.py — 環境変数/.env ロードと Settings クラス（アプリ設定）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - execution/  — 発注周り（OrderManager, BrokerFactory, ExecutionEngine 等）※詳細モジュールはリポジトリ内に存在
  - monitoring/
    - monitoring_db.py — SQLite の監視ログ用永続化層
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 各 Monitor を束ねるランナー
    - alert_manager.py —（通知管理、実装は該当ファイル参照）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数算出・丸め・キャップ処理
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum/Value/Volatility 等
    - feature_exploration.py — 将来リターン計算・IC・統計サマリー
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）
    - regime_detector.py — 市場レジーム判定（OpenAI + MA200）
  - data/ (実行時に使用されることが多いディレクトリ)
    - monitoring.db（デフォルト）
    - kabusys.duckdb（デフォルト）
    - paper_trading.db（ペーパートレード用、KABUSYS_ENV=paper_trading の場合）

（実際のリポジトリにはさらに細かなモジュール／サブパッケージが含まれます。上は主要コンポーネントの一覧です。）

---

## 実装上の注意点 / 運用のヒント

- run_monitoring は KABUSYS_ENV に依存せず「本番の sqlite_path」を使用して監視ログを書きます。監視は常に本番 DB を見て稼働を評価する設計です。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。
- process priority: 起動時に set_process_priority("high") を試みます（psutil を使用）。権限や OS により失敗する場合はログに警告が出てスキップされます。
- AI 機能は OpenAI API を利用します。API 呼び出しはリトライ・バックオフやレスポンス検証を備え、失敗時はフォールバック (例: macro_sentiment=0.0) する設計です。ただしキーは必須です。
- SQLite / DuckDB のファイルパスは .env で変更できます。テスト環境・本番環境で DB を分離することを強く推奨します（特に PAPER_TRADING_SQLITE_PATH）。
- validate_config は PyYAML がない場合、YAML の中身検証はスキップしますがファイル存在は警告します。

---

## 開発者向けメモ

- .env 自動読み込み: config.py はリポジトリルート（.git もしくは pyproject.toml）を基に .env/.env.local を自動でロードします。テスト等で自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DB マイグレーション: monitoring_db.init_monitoring_db は簡単なマイグレーションロジック（カラム追加など）を含みます。既存 DB に対する破壊的操作を避けるために注意してください。
- テスト: AI 呼び出し箇所は _call_openai_api をラップしているため unittest.mock.patch で差し替えてテスト可能です。
- ロギング: 多くのモジュールは logging モジュールを使っています。LOG_LEVEL で出力レベルの調整が可能です。

---

これで README の簡易版を終わります。必要であれば以下を追加可能です：
- 具体的な .env.example（ファイル内容）
- 各 CLI / 関数の詳細 API ドキュメント（引数・戻り値・例外）
- Unit テストの実行方法・CI 設定例

追加で記載したい項目があれば教えてください。