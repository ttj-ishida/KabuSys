# KabuSys

日本株向け自動売買フレームワーク（プロトタイプ）。  
シグナル生成・ポートフォリオ構築・発注エンジン・監視・AI を組み合わせ、実運用・ペーパートレード双方に対応する設計を持ちます。

バージョン: 0.1.0

---

## 概要

KabuSys は次のような機能群を含むモジュール式の自動売買基盤です。

- データ解析 / リサーチ（DuckDB を用いたファクター計算）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出）
- ExecutionEngine（ブローカークライアント経由での発注、ペーパートレード分離）
- 監視サブシステム（システム状態・注文・リスクの定期チェック、Kill Switch）
- AI モジュール（ニュースセンチメント、レジーム判定。OpenAI API 利用）
- 運用支援ツール（設定ウィザード、構成検証、ペーパートレード検証レポート）

設計方針として、DB は DuckDB（分析）と SQLite（監視・履歴）を分離。ペーパートレード時は監視用 DB を別ファイルに分けて完全分離する仕組みがあります。

---

## 主な機能一覧

- 環境設定ウィザード（`kabusys.config_setup`）で .env を対話的に作成
- 設定検証 CLI（`kabusys.validate_config`）で起動前に必須環境変数やファイルのチェック
- Execution 起動スクリプト（`run_execution.py`）
  - KABUSYS_ENV=paper_trading 時は Mock ブローカーを使用し、paper_trading 専用 DB に記録
  - プロセス優先度設定、PID 管理、停止フラグ対応
- Monitoring 起動スクリプト（`run_monitoring.py`）
  - 定期ポーリング（環境変数で間隔設定可能）
  - system / trade / risk モニタリング、Kill Switch 評価、アラート送信フック
- ポートフォリオ構築（選定・重み・ポジションサイズ計算）
- Research（Momentum / Volatility / Value 等のファクター計算）
- AI: ニュース NLP スコアリング（OpenAI）と市場レジーム判定
- ユーティリティ: ログ設定（ローテート）、プロセス優先度 / CPU affinity 設定
- 運用レポート: Paper Trading 検証レポート生成ツール

---

## 必要条件

- Python >= 3.10
- SQLite（標準ライブラリ）
- 推奨パッケージ（pip インストール）:
  - duckdb
  - psutil
  - openai
  - PyYAML（validate_config の YAML 検証用、オプション）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

プロジェクトに requirements.txt があればそちらを利用してください。

---

## セットアップ手順（簡易）

1. リポジトリをクローンしてワークディレクトリに移動
2. 仮想環境を作成して依存ライブラリをインストール（上の「必要条件」を参照）
3. 設定ファイル（.env）作成
   - 対話ウィザードを利用:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動で .env を作成（キーは下の「環境変数」を参照）
4. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   必須環境変数が未設定の場合はエラーになります。`--strict` を付けると警告も失敗扱いになります。
5. データディレクトリを作成（必要に応じて）
   ```
   mkdir -p data logs
   ```

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD (必須)
  - kabuステーション API パスワード
- KABUSYS_ENV (default: development)
  - 値: development | paper_trading | live
  - paper_trading の場合は発注実行がモック化され DB を分離
- DUCKDB_PATH (default: data/kabusys.duckdb)
  - DuckDB ファイルパス（分析用）
- SQLITE_PATH (default: data/monitoring.db)
  - 監視用 SQLite DB パス（本番用）
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - paper_trading 用 SQLite DB（KABUSYS_ENV=paper_trading で使用）
- PAPER_FILL_MODE (default: instant)
  - ペーパートレード時の約定挙動: "instant" | "partial" | "never" | "reject"
- LOG_LEVEL (default: INFO)
- LOG_DIR (default: logs/)
- OPENAI_API_KEY
  - AI 機能（ニュース NLP / レジーム判定）で必要
- MONITOR_POLL_INTERVAL (monitoring 起動時に利用, default: 60)
  - ポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START (default: 0)
  - 本番で 1 にすると起動時に kill.flag を自動クリア（危険: 本番は 0 推奨）

---

## 使い方（起動例）

- 実行エンジン（Execution）を起動:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い `PAPER_TRADING_SQLITE_PATH` に記録します。
  - 実行中に停止させるには data/stop_requested.flag を作成するか、Kill Switch を利用して data/kill.flag を作成します。

- 監視ループを起動:
  ```
  # ポーリング間隔を環境変数で上書き（秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 監視は常に本番の sqlite_path を使用します（monitoring は環境にかかわらず本番監視 DB を参照します）。
  - 監視は data/stop_requested.flag の検出でループを終了します。

- 設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db（`--db` または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能）

- AI モジュール（コード呼び出し例）
  - OpenAI API キーを設定してからモジュール関数を呼ぶ:
    ```py
    from kabusys.ai.news_nlp import score_news
    # duckdb 接続を用意して date を渡す
    score_news(conn, target_date, api_key="sk-...")
    ```

---

## ログ

- ログ設定は `kabusys.utils.logging_setup.setup_logging` を通じて統一されます。
- デフォルトは stdout とファイル出力（logs/<app_name>.log、日次ローテート、30日保持）。
- app_name（例: "execution", "monitoring"）に応じてログファイルが切られます。

---

## 停止 / Kill Switch / フラグファイル

- data/stop_requested.flag
  - run_execution / run_monitoring が検出すると安全に停止するために使用されます（スクリプト内で参照）。
- data/kill.flag
  - KillSwitch が書き込み、ExecutionEngine 停止をトリガーします。書き込みは冪等。
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると自動でクリアされます（本番では危険な設定）。

---

## ディレクトリ構成（抜粋）

以下は主要モジュールのツリー（src/kabusys 配下）です。実際のリポジトリに合わせて補完してください。

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (参照される)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照される)
  - execution/ (発注エンジン関連、参照モジュール)
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
  - tools/
    - paper_verification_report.py
    - __init__.py
  - data/ (runtime: DB・PID・フラグファイルなどを置く想定)
  - logs/ (デフォルトログ出力先)

---

## 開発メモ / 注意点

- Python の型ヒントで `X | Y` を使用しているため Python >= 3.10 が必要です。
- validate_config は PyYAML があれば config/*.yaml のパース検証を行います（未インストール時は警告）。
- AI 機能を使う場合は OpenAI API の利用費用とレート制限に注意してください。失敗時はフォールバック（スコア 0.0 等）する実装です。
- Monitoring は監視 DB（SQLite）を永続化します。スキーマの互換性維持のためマイグレーション処理（カラム追加）を含みます。
- ペーパートレード（paper_trading）は本番 DB と完全分離するよう設計されています。必ず `KABUSYS_ENV=paper_trading` をセットして動作検証してください。

---

## テスト / 監査

- 各サブシステムは run_once 相当のテスト API を提供している箇所があります（例: MonitoringEngine.run_once）。
- AI 呼び出し部分は内部 API 呼び出し関数をモックして単体テスト可能な設計になっています（例: `_call_openai_api` を patch）。

---

以上。必要であれば README にサンプル .env のテンプレートや起動 systemd / supervisor の設定例、より詳細なディレクトリツリーを追加します。どの情報を追記しましょうか？