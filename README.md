# KabuSys

日本株向けの自動売買システムのコアライブラリ群（実行エンジン、監視、研究・ファクター計算、AI 補助モジュール等）。  
このリポジトリは実行スクリプトやユーティリティを含み、ローカル開発・ペーパートレード・本番運用を想定した設計になっています。

---

## プロジェクト概要

KabuSys は以下の主要領域で構成されています。

- Execution: 発注エンジンと注文管理（実ブローカー / モック分離）。
- Monitoring: システム稼働・データ鮮度・リスク監視と Kill Switch。
- Research: DuckDB を用いたファクター計算・特徴量解析ツール。
- AI: ニュース NLP（OpenAI）を用いた銘柄センチメントや市場レジーム判定。
- Portfolio: 銘柄選定、重み付け、ポジションサイズ計算、リスク調整。
- Utilities: ログ設定、プロセス優先度、環境設定読み込み等。
- Tools: ペーパートレード検証レポート生成などの補助スクリプト。

主要な設計方針として「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアスの排除」「フェイルセーフ（API失敗時は安全側へフォールバック）」が採用されています。

---

## 機能一覧

- 実行エンジン起動スクリプト（run_execution）
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して `data/paper_trading.db` を利用
  - プロセス優先度の設定、PIDファイル管理、停止フラグ監視
- 監視ループ起動スクリプト（run_monitoring）
  - SystemMonitor を定期ポーリングして system_status に記録
  - MONITOR_POLL_INTERVAL で間隔を調整可能
- 設定ウィザード（config_setup）
  - 対話式に `.env` を生成・更新
- 設定検証 CLI（validate_config）
  - 環境変数・config/*.yaml の存在や基本チェック
- Paper Trading 検証レポート（tools.paper_verification_report）
  - ペーパートレード DB から稼働率・成功率・レイテンシ等の指標を出力
- Research モジュール
  - モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB）
  - 将来リターン・IC（Information Coefficient）計算
- AI モジュール
  - ニュース NLP（OpenAI）で銘柄ごとのセンチメントスコアを生成（ai.news_nlp）
  - マクロニュース + ETF MA200 を用いた市場レジーム判定（ai.regime_detector）
- Portfolio モジュール
  - 候補選定、等重・スコア重み、位置サイズ決定、セクターキャップ・レジーム乗数適用
- Logging / process utilities
  - 統一ロギング設定（ファイル・コンソール、日次ローテーション）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 前提 / 必要環境

- Python 3.10 以上（型ヒントで `|` を使用）
- 推奨パッケージ（最低限必要なもの）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（validate_config で YAML 検証を行う場合）
- SQLite（Python 標準ライブラリに同梱）
- ネットワークアクセス：kabuステーション API / OpenAI を利用する場合は外部接続必須

インストール例（仮の requirements がない場合）:
```
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンして、仮想環境を作成・有効化します。
2. 依存パッケージをインストールします（上記参照）。
3. 環境変数（.env）を作成します。対話式ウィザード推奨：
   ```
   python -m kabusys.config_setup
   ```
   主要な環境変数（代表）:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV（development / paper_trading / live）
   - DUCKDB_PATH（例: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB、例: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、例: data/paper_trading.db）
   - OPENAI_API_KEY（AI 機能利用時）
   - LOG_LEVEL / LOG_DIR
   - その他は `python -m kabusys.config_setup` の案内に従ってください。

4. 設定検証:
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリを作成（必要に応じて）:
   - data/ （デフォルトで DB や flag を格納）
   - logs/ （ログ出力先）

---

## 使い方（起動例）

- 監視ループ起動
  - デフォルトポーリング間隔 60 秒。環境変数で変更可能:
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 監視は常に本番 sqlite_path（settings.sqlite_path）を使用します。
  - 停止はプロジェクトルートの `data/stop_requested.flag` を作成すると検知して終了します。

- 実行エンジン起動
  - paper_trading モード（MockBrokerClient、ペーパートレード DB 使用）:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - live / development での動作は各環境に応じたブローカークライアントを使用します。
  - 起動・停止制御:
    - 起動時に `data/execution.pid` を使用（PID ファイル）
    - 停止は `data/stop_requested.flag` を作成または Kill Switch により `data/kill.flag` が作成されると停止判定になります。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）

- AI モジュール（プログラムから利用）
  - ニュースのスコアリング:
    from kabusys.ai.news_nlp import score_news
  - 市場レジーム判定:
    from kabusys.ai.regime_detector import score_regime

- ログ設定
  - すべての起動スクリプトは `kabusys.utils.logging_setup.setup_logging` を使用します。
  - デフォルトログディレクトリ: `logs/`。環境変数 `LOG_DIR` や `setup_logging` 引数で上書き可能。
  - 各アプリごとに `logs/<app_name>.log`（日次ローテーション、30 日保持）

---

## 重要ファイル / フラグ

- data/stop_requested.flag — run_*.py が監視する停止フラグ
- data/kill.flag — KillSwitch が作成する停止フラグ（ExecutionEngine 停止トリガ）
- data/execution.pid — ExecutionEngine 用 PID ファイル（run_execution が使用）
- DB:
  - data/monitoring.db（監視ログ、Settings.sqlite_path）
  - data/paper_trading.db（ペーパートレード時の SQLite、Settings.paper_sqlite_path）
  - DuckDB ファイル（分析用）： data/kabusys.duckdb（Settings.duckdb_path）

---

## .env / 環境変数の自動読み込み

- config.py により自動で `.env` / `.env.local` をプロジェクトルートから読み込みます（OS 環境変数が優先）。
- 自動ロードを無効化するには:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## ディレクトリ構成（概観）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境設定読み込み
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI 経由）
    - regime_detector.py      — 市場レジーム判定（MA200 + マクロ NLP）
    - __init__.py
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（監視用テーブル）
    - system_monitor.py
    - trade_monitor.py        — （存在: トレード監視ロジック）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py        —（存在: アラート管理）
    - monitoring_engine.py
  - execution/
    - execution_engine.py     — 実行エンジン本体
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
  - tools/
    - paper_verification_report.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                     — デフォルトで使用される DB / flag / pid 等（リポジトリルートに配置）
  - logs/                     — ログ出力先（設定で変更可能）

（実際の細かいファイル・サブモジュールは上記以外にもあります。コードを参照してください。）

---

## 運用上の注意 / ヒント

- ペーパートレードと本番は DB を分離してください（KABUSYS_ENV により自動分離）。
- 本番（KABUSYS_ENV=live）では Kill Switch 設定や LINE 通知設定を必ず確認してください。
- OpenAI を利用する機能は API レートやコストに注意して運用してください。API エラー時はフォールバック挙動を取りますが、ログを確認することを推奨します。
- ログディレクトリ作成に失敗した場合、コンソールログのみで継続します（setup_logging の挙動）。
- process_priority.set_process_priority は権限の関係で失敗することがあります（警告ログのみ）。

---

## よく使うコマンドまとめ

- .env 作成（ウィザード）
  ```
  python -m kabusys.config_setup
  ```
- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- 監視起動
  ```
  export MONITOR_POLL_INTERVAL=60
  python -m kabusys.run_monitoring
  ```
- 実行エンジン起動
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

## 参考 / 追加情報

- 各モジュールのドキュメント文字列（docstring）に詳細な設計意図やパラメータ説明があります。実装やチューニング時は該当ソースを参照してください。
- DuckDB のスキーマ（prices_daily, raw_financials, raw_news, ai_scores など）や config/*.yaml のテンプレートはリポジトリ内の他スクリプト（例: scripts）で生成される想定です。validate_config は不足ファイルを警告します。

---

README に記載してほしい追加の項目（例: 実際の config/*.yaml の雛形、requirements.txt、運用 runbook など）があれば教えてください。必要に応じて追記します。