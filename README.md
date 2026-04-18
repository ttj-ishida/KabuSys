# KabuSys

日本株向け自動売買システム（ライブラリ兼実行スクリプト群）

バージョン: 0.1.0

---

この README はリポジトリ内の主要スクリプト・モジュールに基づき、セットアップ方法、使い方、機能説明、ディレクトリ構成を日本語でまとめたものです。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数 / 設定項目
- 停止フラグ・PID の扱い
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計された Python パッケージ群です。以下を含みます：

- 注文実行エンジン（ExecutionEngine）とブローカークライアントの抽象化
- 監視コンポーネント（System / Trade / Risk Monitor）と Kill Switch
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定、セクター制約）
- リサーチ / ファクター計算（DuckDB を使ったオンチェーン計算）
- AI 連携（ニュースのセンチメント解析、レジーム判定） — OpenAI を利用
- 開発運用用 CLI：.env ウィザード・設定検証・ペーパートレード検証レポート 等

設計方針の例：
- 本番データベース・実行プロセスと研究用コード（DuckDB）を分離
- ルックアヘッドバイアスに注意した日付処理
- 外部 API 呼び出し（OpenAI 等）はフェイルセーフで実装（失敗時は安全側にフォールバック）

---

## 主な機能一覧

- 実行（run_execution.py）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカーファクトリ、注文管理、リスク管理、実行エンジンを起動
- 監視（run_monitoring.py）
  - SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL で間隔指定可）
  - SQLite（監視ログ）および DuckDB 接続
- 設定ウィザード（config_setup.py）
  - 対話式に .env を生成・更新
- 設定検証（validate_config.py）
  - .env や config/*.yaml、主要環境変数のチェック
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - ペーパートレード DB から稼働率・約定率・レイテンシ等を集計して PASS/FAIL 判定
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等比重・スコア加重、ポジションサイズ計算、セクター制約、レジーム乗数
- 研究（kabusys.research）
  - Momentum / Volatility / Value 等のファクター計算、IC 計算、特徴量サマリ
- AI（kabusys.ai）
  - news_nlp: ニュース記事を OpenAI でスコアリングして ai_scores に保存
  - regime_detector: ETF とマクロニュースで市場レジーム判定
- ユーティリティ（kabusys.utils）
  - ロギングセットアップ（コンソール + 日次ローテーション）、プロセス優先度 / CPU affinity 設定
- 監視永続層（kabusys.monitoring.monitoring_db）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルを管理

---

## セットアップ手順（ローカル開発向け）

1. Python 環境を用意
   - 推奨: Python 3.10+
   - 仮想環境を作成・有効化:
     ```
     python -m venv .venv
     source .venv/bin/activate   # macOS / Linux
     .venv\Scripts\activate      # Windows
     ```

2. パッケージのインストール
   - requirements.txt がある場合:
     ```
     pip install -r requirements.txt
     ```
   - ない場合は主要依存を手動でインストール:
     - duckdb, psutil, openai, PyYAML（検証機能で必要）
     ```
     pip install duckdb psutil openai pyyaml
     ```

3. .env の作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   もしくは手動でプロジェクトルートに `.env` を作成。

4. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告も失敗扱いになります。

5. データディレクトリ（デフォルト）
   - logs/: ログ出力先
   - data/: データベース・PID・フラグファイル（SQLite / DuckDB / pid / kill.flag）
   必要に応じて .env でパスを上書きしてください（DUCKDB_PATH, SQLITE_PATH など）。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動
  - 本番 / 開発 / paper_trading は KABUSYS_ENV に依存
  - ペーパートレード時は paper 用 DB に分離して記録されます
  ```
  python -m kabusys.run_execution
  ```

- 監視ループ起動（SystemMonitor を継続的に実行）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）指定可能（デフォルト 60 秒）
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート（SQLite DB を指定可能）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を直接指定:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI スコアリング / レジーム判定（スクリプト呼び出し例）
  - これらはライブラリ関数として利用する想定（DuckDB 接続と target_date を与えて実行）
  - OpenAI API キーは環境変数 OPENAI_API_KEY または関数引数で指定可能

---

## 主要な環境変数 / 設定

必須（起動前に .env に設定してください）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード

その他（デフォルト値あり）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- LOG_DIR: ログ保存先ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 実行時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）

注意:
- run_monitoring は KABUSYS_ENV に依らず monitoring 用に設定された sqlite_path（通常 data/monitoring.db）を使用します。
- run_execution は KABUSYS_ENV が `paper_trading` の場合、paper 用 sqlite を使用して本番 DB と分離します。

---

## 停止フラグ / PID の扱い

プロセス停止や外部からの停止要求はファイルで制御する設計です。

- 停止要求（run_monitoring / run_execution の外部停止）
  - data/stop_requested.flag: 存在を検知すると監視ループ・エンジンが安全に停止します（file path は実行スクリプト基準）
- Kill Switch（自動停止）
  - monitoring.kill_switch は条件（ドローダウン超過など）を満たしたときに data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START を 1 に設定していると自動でクリアする動作が可能（本番では 0 推奨）
- PID ファイル
  - data/execution.pid などに PID を書き出すことでプロセスの存在確認や stale PID 検出に利用します。

---

## ディレクトリ構成（抜粋）

以下は `src/kabusys` 以下の主要ファイル / モジュール構成（抜粋）です：

- run_monitoring.py
- run_execution.py
- config.py
- config_setup.py
- validate_config.py
- __init__.py

- kabusys/
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (存在想定)
  - execution/
    - execution_engine.py (存在想定)
    - order_manager.py
    - order_repository.py
    - broker_factory.py
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
  - monitoring/ (監視用永続化層含む)
    - monitoring_db.py
  - data/ (実行時に使用するデフォルトディレクトリ: data/*.db, data/*.flag)
  - logs/ (デフォルトログ出力先)

（注）上記はソース内に現れたファイルを中心に抜粋しています。実際のリポジトリでは追加のファイルやサブモジュールが存在する場合があります。

---

## 開発 / テスト時の補足

- 自動で .env を読み込む仕組みがあり、プロジェクトルートの `.env` と `.env.local` がロードされます（OS 環境変数が優先）。自動ローディングを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- validate_config は `config/*.yaml` の存在・パースチェックを行います（PyYAML がインストールされていない場合は YAML チェックをスキップ）。
- AI 関連処理は OpenAI API に依存するため、テスト時は API 呼び出し箇所をモックすることを推奨します（コード内でもテスト用に差し替え可能な関数を用意しています）。

---

## よくある質問（FAQ）

Q: 監視ループの間隔を変えたい  
A: 環境変数 MONITOR_POLL_INTERVAL を秒数で指定します（例: 30）。不正な値（0 以下や非整数）はデフォルト 60 秒にフォールバックします。

Q: ペーパートレードのログを本番 DB と分離したい  
A: KABUSYS_ENV を `paper_trading` に設定すると run_execution は `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）を使用します。

Q: Kill Switch はどのようにトリガーされますか？  
A: RiskMonitor 等が DB 上のダッシュボード・ポジション数・ドローダウンを評価し、KillSwitch が条件を満たすと data/kill.flag を書きます。ExecutionEngine はこのフラグを検知して停止します。

---

必要に応じてこの README をプロジェクトの実際の README.md として保存・編集してください。実行手順や依存関係は運用環境に合わせて適宜調整してください。