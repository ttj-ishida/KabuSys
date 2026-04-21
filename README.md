# KabuSys — README

日本株自動売買システムのサブセット実装リポジトリ（モジュール概要、起動スクリプト、監視・検証ツールなど）。  
この README はコードベース（`src/kabusys`）の利用方法、主要機能、設定方法、ディレクトリ構成をまとめたものです。

重要: 実際の運用では .env に API トークンやパスワード等の機密情報を格納します。`.env` をバージョン管理に含めないでください。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関連する以下の責務を分離して実装したモジュール群です（本リポジトリはフルシステムの一部を示す実装）:

- ExecutionEngine 起動スクリプト（発注・注文管理・リスク管理の起動）
- Monitoring（システム・注文・リスクの監視ループ）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 研究用モジュール（ファクター計算・将来リターン・IC 等）
- AI 関連（ニュース NLP によるセンチメント、レジーム判定）
- 開発者向けユーティリティ（.env ウィザード、設定検証、検証レポート）

設計方針：
- DB（SQLite / DuckDB）をローカルファイルで管理
- env ベースで設定（`.env` / OS 環境変数）
- 実行スクリプトは `python -m kabusys.<module>` で起動可能
- フェイルセーフ（API 失敗時のフォールバック、監視からの Kill Switch）

---

## 機能一覧（主なコンポーネント）

- 起動スクリプト
  - `kabusys.run_execution` : ExecutionEngine を起動（`KABUSYS_ENV=paper_trading` なら Mock ブローカーを使用し、paper DB に記録）
  - `kabusys.run_monitoring` : SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔調整）
- 設定関連
  - `kabusys.config` : 環境変数読み込み・設定クラス（`Settings`）
  - `kabusys.config_setup` : 対話式 .env 作成ウィザード（`python -m kabusys.config_setup`）
  - `kabusys.validate_config` : 設定検証 CLI（`python -m kabusys.validate_config`）
- 監視（monitoring）
  - `MonitoringEngine`, `SystemMonitor`, `TradeMonitor`, `RiskMonitor`
  - `KillSwitch` : 条件で data/kill.flag を書き込み ExecutionEngine を停止させる
  - 永続化: `monitoring_db`（SQLite） — テーブル作成・簡易マイグレーション実装済み
- 発注・実行（execution）
  - ブローカーファクトリ・OrderManager・RiskManager 等（起動スクリプトから組み立て）
- ポートフォリオ（portfolio）
  - 候補選定、重み計算、ポジションサイズ計算、セクターキャップ、レジーム乗数
- 研究（research）
  - ファクター計算（momentum, volatility, value）、forward returns、IC 計算、統計サマリ
- AI（ai）
  - `news_nlp.score_news` : OpenAI を用いたニュースセンチメント → `ai_scores` へ書き込み
  - `regime_detector.score_regime` : ETF MA とマクロ記事でレジーム判定（DB へ書き込み）
- ユーティリティ
  - `utils.logging_setup` : 統一的なログ設定（stdout + 日次ローテートファイル）
  - `utils.process_priority` : プロセス優先度／CPU affinity 設定
- ツール
  - `kabusys.tools.paper_verification_report` : Paper Trading の検証レポート生成

---

## 前提（推奨）パッケージ

以下はコード中で参照されている主要ライブラリ（例）です。requirements.txt は本リポジトリに含まれていないため、必要に応じてインストールしてください。

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（設定ファイル検証オプション）
- （任意）その他プロジェクト特有パッケージ（実際の ExecutionEngine のブローカー実装等）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリ取得・仮想環境作成
   - 上述の仮想環境を作ることを推奨

2. 必要パッケージをインストール
   - 上記参照（duckdb, psutil, openai, PyYAML 等）

3. .env 作成（対話式ウィザード推奨）
   - 実行:
     ```
     python -m kabusys.config_setup
     ```
   - 生成される `.env` の例（機密情報は実際の値に置き換える）:
     ```
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0
     ```
   - 自動ロードについて:
     - デフォルトで起動時にプロジェクトルートの `.env` と `.env.local` が自動読み込みされます
     - OS 環境変数より .env の値が優先されます（優先順位: OS env > .env.local > .env）
     - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

4. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   # 警告を失敗扱いにする:
   python -m kabusys.validate_config --strict
   ```

5. ディレクトリ作成
   - `.env` で指定した DB や `logs/`、`data/` ディレクトリは起動時に自動作成される場合がありますが、必要に応じて手動作成してください。

---

## 使い方（起動例）

- ExecutionEngine 起動
  - 本番 / 開発 / ペーパートレードは `KABUSYS_ENV` で切替（`KABUSYS_ENV=paper_trading` なら paper DB を使用）
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - 停止:
    - `data/stop_requested.flag` を作成すると起動ループが早期終了します（実行スクリプトは起動時にこのファイルをチェック）
    - Execution 側は `data/execution.pid` を PID ファイルとして扱います

- Monitoring 起動
  - 監視ループを起動します（監視は常に本番 sqlite_path を使用）
  - 起動:
    ```
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- Paper Trading 検証レポート生成
  - 起動:
    ```
    python -m kabusys.tools.paper_verification_report
    # 期間指定例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DB パスは `--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）

- .env 作成ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- AI モジュール呼び出し（プログラム的に）
  - ニュース NLP:
    - 関数: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`
    - OpenAI API キーは `OPENAI_API_KEY` 環境変数、または引数 `api_key` で与える
  - レジーム判定:
    - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

---

## 主要な環境変数（抜粋）

- 認証・API
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - OPENAI_API_KEY (AI 機能を使う場合必須)
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)

- 動作モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: MockBroker を使い `data/paper_trading.db` に記録
    - live: 本番

- DB / ファイルパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 SQLite、デフォルト: data/paper_trading.db)
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
  - LOG_DIR (デフォルト: logs/)

- ロギング / 監視
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO)
  - MONITOR_POLL_INTERVAL (監視ループの間隔、秒。デフォルト: 60)

- その他
  - KILL_FLAG_CLEAR_ON_START (0/1、本番で 1 を使うと危険)

---

## 動作上の注意点 / 実装の重要ポイント

- Monitoring は KABUSYS_ENV にかかわらず「本番 sqlite_path（SQLITE_PATH）」を使用します（run_monitoring の仕様）。
- ExecutionEngine は `KABUSYS_ENV=paper_trading` の場合、MockBroker を使用して paper DB を分離します（data/paper_trading.db を利用）。
- `.env` 自動読み込みはデフォルトで有効。テスト等で無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- Kill Switch:
  - 監視が条件（ドローダウン超過等）を満たすと `data/kill.flag` を書き込み、Execution 側に停止シグナルを送ります。
  - 手動で Kill をクリアするには `KillSwitch.clear()` またはファイル削除。
- 起動時にプロセス優先度（high）を設定しようとしますが、権限不足の場合は警告を出して継続します（psutil の AccessDenied をハンドリング）。
- `monitoring_db.init_monitoring_db` は冪等でテーブル作成・簡易マイグレーション（カラム追加）を行います。

---

## ディレクトリ構成（抜粋）

src/kabusys の主要ファイルとサブパッケージ:

- run_monitoring.py
- run_execution.py
- config.py
- validate_config.py
- config_setup.py
- __init__.py

サブパッケージ / モジュール:
- ai/
  - news_nlp.py
  - regime_detector.py
- monitoring/
  - monitoring_db.py
  - monitoring_engine.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py (参照されるがここに一覧されている)
- execution/
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
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - logging_setup.py
  - process_priority.py
- monitoring/
  - monitoring_db.py (監視ログの SQLite 永続化)
- tools/
  - paper_verification_report.py

（上記はリポジトリ内に示されている主要ファイルの抜粋です）

---

## よくある運用フロー（例）

1. 初回セットアップ
   - 仮想環境作成、パッケージインストール
   - `python -m kabusys.config_setup` で `.env` を作成
   - `python -m kabusys.validate_config` で設定確認

2. データベース初期化
   - 監視 DB は `run_execution` / `run_monitoring` 実行時に自動でテーブルを作成します。
   - DuckDB に過去価格データ等をロードしておくと research / ai モジュールが利用可能になります。

3. 運用
   - `python -m kabusys.run_execution` をサービスで常時実行（systemd / supervisor 等で管理）
   - `python -m kabusys.run_monitoring` を別プロセスで常時実行（監視・KillSwitch を管理）
   - Paper 検証は随時 `python -m kabusys.tools.paper_verification_report` で評価

---

## トラブルシューティング / 注意

- ファイルパーミッション: PID ファイル・logs・data ディレクトリに対するファイル書き込み権限を確認してください。
- OpenAI API 周り: リクエスト失敗（429/5xx/タイムアウト）はリトライ実装がありますが、API キーと利用制限の管理は必須です。
- ログ: `logs/<app_name>.log` に日次ローテートで出力されます（`LOG_DIR` で変更可能）。ログディレクトリの作成に失敗するとコンソール出力のみになります。
- psutil による優先度／CPU affinity の設定は OS に依存します（権限不足や未対応 OS では警告が出ます）。

---

問い合わせ / 貢献

- 本 README はコード片から自動的にまとめた概要です。詳細な実装や未記載のユーティリティ関数はソース内ドキュメント（各モジュールの docstring）を参照してください。