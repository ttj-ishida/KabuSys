# KabuSys

日本株向け自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注制御・監視・AI を組み合わせた自動売買基盤の一部を提供します。ここには起動スクリプト、設定ユーティリティ、監視・レポート・研究用モジュールなどが含まれます。

バージョン: 0.1.0

## 主要機能（抜粋）

- 実行エンジン起動スクリプト（run_execution）
  - 本番 / ペーパートレードの分離（KABUSYS_ENV=paper_trading 時は MockBroker を用い、別 SQLite に記録）
  - 発注・注文管理・リスク管理・リコンシリエーション等の組立て
- 監視ループ起動スクリプト（run_monitoring）
  - システム状況・発注ログ・リスクを定期ポーリングして記録・アラート
  - MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）
  - 監視は環境にかかわらず本番用 sqlite_path を使用する点に注意
- 環境設定ウィザード（config_setup）と設定検証ツール（validate_config）
  - .env の生成・更新を対話式で支援
  - 起動前に必須環境変数や config/*.yaml ファイル・パス等を検証
- Paper Trading 検証レポート生成（tools/paper_verification_report）
  - ペーパートレード DB から稼働率・注文成功率・レイテンシ等の指標を算出
- ポートフォリオ構築モジュール（portfolio）
  - 候補選定、等配分 / スコア加重配分、リスク調整（セクター上限・レジーム乗数）、株数算出（単元丸め含む）
- 研究用モジュール（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）、将来リターン、IC（Information Coefficient）等
- AI 補助（ai）
  - ニュースの LLM（OpenAI） によるセンチメントスコアリング（news_nlp）
  - マクロ + ETF MA を合成した市場レジーム判定（regime_detector）

## 必要要件（推奨）

このリポジトリ内の一部機能は外部ライブラリに依存します。最低限の依存例:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使用する場合)
- PyYAML（validate_config の YAML 検証を有効にする場合）

実際の requirements.txt は含まれていないため、必要に応じて上記パッケージをインストールしてください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

## セットアップ手順（ローカル開発 / 実行前チェック）

1. リポジトリをクローンして作業ディレクトリへ移動。
2. 仮想環境作成・依存インストール（上記参照）。
3. .env を作成
   - 推奨: 対話式ウィザードで作成
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - デフォルトのデータベースパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時）
   - .env の自動読み込み:
     - 起動時に .env（および .env.local）を自動で読み込みます（ただし OS 環境変数が優先）。
     - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
4. 設定検証
   ```
   python -m kabusys.validate_config
   # strict モード（警告も失敗扱い）
   python -m kabusys.validate_config --strict
   ```
   - PyYAML がない場合、config/*.yaml の中身検証はスキップされます（警告が出ます）。

## 主要な環境変数（概要）

- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、実行エンジンは専用 paper_sqlite_path を使用して本番 DB と分離します。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60。1 以上であること）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant / partial / never / reject）

## 実行方法（コマンド例）

※ パッケージルートで実行してください（`python -m <module>` を想定）。

- 実行エンジン（ExecutionEngine）起動
  ```
  # 本番 / 開発
  python -m kabusys.run_execution

  # ペーパートレード（.env で KABUSYS_ENV=paper_trading を指定）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  - ペーパートレード時は settings.paper_sqlite_path（data/paper_trading.db など）に記録され、本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が存在すると起動しません（停止フラグ）。

- 監視ループ起動
  ```
  # デフォルトは 60 秒間隔
  python -m kabusys.run_monitoring

  # ポーリング間隔変更（秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 監視は環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します。
  - 停止は data/stop_requested.flag を作成することで実行中のスクリプトに検知させられます。

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```
  # デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

## ログ

- ログ出力は kabusys.utils.logging_setup.setup_logging で統一的に設定されます。
- コンソール出力（stdout）と日次ローテーションされたファイルログ（logs/<app_name>.log）に出力されます。
- デフォルトのログディレクトリは logs/（LOG_DIR 環境変数で変更可能）。

## 停止 / Kill Switch

- 実行エンジンを外部から停止させる仕組み:
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。
  - 監視ロジックが DRAWDOWN やポジション上限を検出すると kill.flag を作成します。
- 手動停止フラグ:
  - data/stop_requested.flag を作成すると run_execution と run_monitoring のループが検出して終了します。
- ExecutionEngine の PID ファイル: data/execution.pid（Settings.pid_file_path で上書き可）

## AI 機能（注意点）

- news_nlp.score_news / regime_detector.score_regime などは OpenAI API を利用します。使用するには OPENAI_API_KEY の設定が必要です。
- LLM 呼び出しはリトライ・バックオフやレスポンスバリデーションを含んでいますが、API レスポンス形式の変更に注意して下さい。
- AI 機能は外部 API（有料）を呼ぶため実行前にコストとレートリミットを確認してください。

## 開発者向けノート

- 設定の自動読み込み順序:
  - OS 環境変数（最優先） > .env.local > .env（.env.example を参照して作成）
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- Settings クラス:
  - アプリ内で設定値を参照するには `from kabusys.config import settings` を使います（プロパティで値を取得）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブル作成/インデックス作成と簡単なカラム追加（マイグレーション）を行います。
- ローカルテスト:
  - PaperTrading 用 DB は本番 DB と分離しているため、ローカル検証は KABUSYS_ENV=paper_trading を使うと安全です。

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要なパッケージ・モジュール構成の抜粋です（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (別ファイル、監視ロジックが含まれる想定)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (アラート送信処理がある想定)
  - execution/
    - (execution エンジンや broker 周りの実装ファイル群)
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/                       — 実行時生成されるデータ・フラグ等（logs/, data/*.db など）

（上記はリポジトリ内の主要モジュールを抜粋して示しています）

## よくある質問 / 注意点

- 監視は「監視用 SQLite（SQLITE_PATH）」を参照します。監視モジュールは環境にかかわらず本番 sqlite_path を用いるため、ペーパートレードと混在させたくない場合はパス設定に注意してください。
- MONITOR_POLL_INTERVAL は 1 以上の整数を指定してください。0 以下や非整数を指定するとデフォルト（60 秒）にフォールバックします。
- 本番（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を必ず確認してください。validate_config は live 環境での不備を警告します。
- AI 機能を実行する際は API キーの漏洩に注意し、.env を Git にコミットしないでください。

---

必要であれば、README に含める具体的な起動シェルスクリプト例・systemd ユニットや docker-compose 設定のテンプレート、あるいは各モジュールの API 使用例（コード片）を追加で作成します。どの情報を詳細化したいか教えてください。