# KabuSys

日本株向けの自動売買システム（ライブラリ & 起動スクリプト群）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買のためのモジュール群です。  
主な目的は以下のとおりです。

- 戦略に基づく銘柄選定・配分・株数決定（ポートフォリオ構築）
- 発注 / 注文管理 / リスク管理を含む実行エンジン
- システム稼働状況や注文ログの監視（監視エンジン）
- リサーチ用のファクター計算・特徴量解析ユーティリティ
- OpenAI を使ったニュース NLP による銘柄・レジーム判定支援
- ペーパートレード検証ツール（集計／レポート）

設計方針として、
- CLI / スクリプトでの起動を想定
- 本番用 DB とペーパートレード用 DB は分離
- .env による環境変数管理と自動ロード機能
- フェイルセーフ（API失敗時はフォールバック）を重視

---

## 主な機能一覧

- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用、専用 SQLite（デフォルト: data/paper_trading.db）に記録
  - PID 管理 / 停止フラグ監視（data/stop_requested.flag / data/kill.flag）
- 監視エンジン起動スクリプト: run_monitoring.py
  - system / trade / risk のモニタリング、kill.flag 書き込みで Execution の停止をトリガ
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔上書き可（デフォルト 60 秒）
- 設定ウィザード: config_setup.py（.env の初期作成・更新）
- 設定検証: validate_config.py（.env と config/*.yaml のチェック）
- Paper Trading 検証レポート: tools/paper_verification_report.py
- ポートフォリオ構築モジュール: portfolio/
  - 銘柄選定、重み計算、単元丸め、セクター制限、レジーム乗数
- リサーチ: research/
  - ファクター計算（モメンタム／バリュー／ボラティリティ）、IC/統計解析
- AI 系:
  - news_nlp.py: OpenAI を用いたニュースセンチメント算出と ai_scores への書き込み
  - regime_detector.py: ma200 + マクロニュースで市場レジーム判定
- ロギング・ユーティリティ: utils/logging_setup.py, utils/process_priority.py
- SQLite / DuckDB を用いた DB 管理（monitoring DB 初期化済み）

---

## 要件（環境）

- Python 3.10+
- 必須 PyPI パッケージ（代表）
  - duckdb
  - psutil
  - openai
- 任意
  - PyYAML（config/*.yaml の検証を行う場合）
- OS: Linux / macOS / Windows（プロセス優先度の扱いは OS に依存）

仮想環境の作成と依存インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil openai
# PyYAML が必要なら:
pip install pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動。

2. 仮想環境を作成して依存ライブラリをインストール（上記参照）。

3. .env の作成（対話ウィザード推奨）:

```bash
python -m kabusys.config_setup
# あるいは手動で .env を作成
```

主要な環境変数（抜粋）:

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI モジュール利用時）
- LOG_LEVEL, LOG_DIR
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag をクリアするか。0/1）

4. 設定検証（重要）:

```bash
python -m kabusys.validate_config
# 警告も FAIL 扱いにしたい場合:
python -m kabusys.validate_config --strict
```

---

## 使い方（主要コマンド）

- 実行エンジン起動

  KABUSYS_ENV によって動作モードが変わります。ペーパートレードでは MockBroker を使い、別 DB に記録します。

  ```bash
  # 通常起動（モジュール実行）
  python -m kabusys.run_execution

  # 環境指定例（ペーパートレード）
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

  実行時は data/execution.pid に PID を書き込み、data/stop_requested.flag で強制停止を指示できます。kill.flag（data/kill.flag）は監視側から実行エンジンを停止させるためのフラグです。

- 監視ループ起動

  ```bash
  python -m kabusys.run_monitoring

  # ポーリング間隔を変更する（秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

  監視は本番 sqlite_path（Settings.sqlite_path）を参照します（環境に依らず）。

- .env 作成/編集ウィザード

  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証（再掲）

  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート

  SQLite（デフォルト: data/paper_trading.db）を解析して PASS/FAIL 判定を出力します。

  ```bash
  # 期間指定例
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # DB パス明示
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI モジュール（プログラム的利用）

  score_news や regime 判定はプログラムから直接呼べます（DuckDB 接続を渡す）:

  ```python
  from kabusys.ai import score_news
  # conn: duckdb connection, target_date: datetime.date
  score_news(conn, target_date, api_key="...")  # または環境変数 OPENAI_API_KEY を使う
  ```

  注意: OpenAI API キーを環境変数 `OPENAI_API_KEY` に設定しておくか、引数で渡してください。API 呼び出しは失敗時にフォールバックする設計ですが、APIキー未設定の場合は例外になります。

---

## 動作上の注意点 / 運用メモ

- ペーパートレード分離: KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH にログを記録します。本番 DB とデータは分離してください。
- Kill Switch:
  - risk_monitor が閾値を超えると KillSwitch が data/kill.flag を書き込み、次回実行エンジンの起動 / 監視で停止トリガに使われます。
  - 本番時は KILL_FLAG_CLEAR_ON_START=0 を推奨。誤って自動クリアすると安全機構が無効化される恐れがあります。
- ログ:
  - デフォルトは logs/<app_name>.log に日次ローテーションで保存（30日分保持）
  - LOG_DIR 環境変数でディレクトリを上書き可能
- 優先度設定:
  - 起動スクリプトは開始時にプロセス優先度を "high" に設定します（set_process_priority）。OS により権限不足で警告が出ることがありますが実害はありません。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は必要なテーブル・カラムを冪等的に作成し、古い DB に対する簡易マイグレーション（カラム追加）も行います。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
    - .env の自動読み込みロジック、Settings クラス
  - config_setup.py
    - 対話式 .env 作成ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py: 統一ログ設定
    - process_priority.py: プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py: SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py: システム状態・データ鮮度監視
    - trade_monitor.py: 発注 / 約定監視（注: 実装ファイルあり）
    - risk_monitor.py: ドローダウン / ポジション上限監視
    - kill_switch.py: kill.flag 書き込みユーティリティ
    - monitoring_engine.py: 各モニタを束ねるエンジン
    - alert_manager.py: 通知管理（LINE 送信等のラッパー）
  - execution/
    - execution_engine.py: ExecutionEngine 本体（発注ループ）
    - broker_factory.py: Broker クライアント生成（Paper vs Live）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py など
  - portfolio/
    - portfolio_builder.py: 候補選定・重み計算
    - position_sizing.py: 株数決定ロジック
    - risk_adjustment.py: セクターキャップ・レジーム乗数
  - research/
    - factor_research.py: ファクター計算（momentum/value/volatility）
    - feature_exploration.py: Forward returns, IC, 統計
  - ai/
    - news_nlp.py: ニュースセンチメント -> ai_scores
    - regime_detector.py: ma200 + マクロニュースでレジーム判定
  - tools/
    - paper_verification_report.py: Paper Trading 検証レポート生成
  - data/ (運用時に生成される)
    - monitoring.db (デフォルト)
    - paper_trading.db (ペーパートレード時)
    - kabusys.duckdb (DuckDB ファイル)
    - execution.pid, kill.flag, stop_requested.flag など

---

## さらに詳しく / 開発者向け

- DuckDB は prices_daily / raw_financials / raw_news 等のテーブルを想定しており、リサーチ・AI モジュールはこれらを参照して計算・判定します。
- AI モジュールは外部 API（OpenAI）の呼び出しを行うため、テスト時は _call_openai_api をモックすることが想定されています。
- 各コンポーネントはできるだけ副作用を小さくするよう設計されています（多くのユーティリティは純粋関数）。
- config/*.yaml のテンプレートは scripts/generate_config.py 等で生成する想定（リポジトリに含まれている設定ファイルを編集してください）。

---

## トラブルシューティング（よくある質問）

- .env が読み込まれない  
  Settings モジュールはプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動ロードします。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。また、明示的に python -m kabusys.config_setup で .env を生成してください。

- Kill Switch が作動して起動できない  
  data/kill.flag が存在する場合、実行エンジンは停止します。安全にクリアするには内容を確認した上で `rm data/kill.flag` で削除するか、KILL_FLAG_CLEAR_ON_START を開発環境のみ `1` に設定してください（本番では推奨しません）。

- OpenAI の呼び出しが失敗する  
  API キーが設定されているか、またはネットワーク／レートリミットの問題を確認してください。AI モジュールは一部リトライ・フォールバックを実装していますが、APIキー未設定は例外になります。

---

README は以上です。追加で詳しい API ドキュメントや実運用手順（Systemd / Supervisor 単位でのデーモン化、バックアップ、DB 管理など）が必要であれば指示ください。