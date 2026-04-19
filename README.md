# KabuSys

日本株自動売買システムのコアライブラリ / 起動スクリプト群です。  
この README はリポジトリ内の主要モジュール（実行エンジン、監視、設定ツール、研究用ユーティリティなど）の概要と使い方、セットアップ手順をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。主な目的は以下です。

- シグナル生成 → ポートフォリオ構築 → 発注（ExecutionEngine）
- 発注・約定に関する監視（Monitoring）
- Paper Trading（模擬売買）を本番 DB と分離して検証
- DuckDB を用いた研究・ファクター計算機能
- OpenAI を用いたニュース NLP（センチメント）やレジーム判定の補助
- ロギング・プロセス管理・リスクガード（Kill Switch）などの運用機能

設計方針として、実運用コードと研究コードは明確に分離されています。多くの処理は副作用を持たない純粋関数で実装され、DB の永続化層は専用モジュールで抽象化されています。

---

## 主な機能一覧

- ExecutionEngine（発注エンジン）
  - 実口座 / ペーパートレードの切り替え（KABUSYS_ENV）
  - ブローカークライアント抽象化（BrokerClientFactory）
  - 注文管理・リスク管理・再整合（OrderManager / RiskManager / Reconciler）

- Monitoring（監視）
  - SystemMonitor：CPU / メモリ / ディスク / プロセス生存確認、データ鮮度チェック
  - TradeMonitor：注文滞留・約定異常などの監視（実装ファイル参照）
  - RiskMonitor：ドローダウン・ポジション上限監視、リスクイベント記録
  - KillSwitch：閾値超過時に data/kill.flag を書き込んで ExecutionEngine を安全停止
  - MonitoringEngine：上記を束ねてポーリング（run_monitoring スクリプト）

- 研究（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）などの統計解析ユーティリティ

- ポートフォリオ構築（portfolio）
  - 候補選定、重み計算、ポジションサイズ決定、セクターキャップ・レジーム乗数適用

- AI（ai）
  - news_nlp: OpenAI を用いたニュースセンチメント集計 → ai_scores へ保存
  - regime_detector: ETF/ニュースを組み合わせて市場レジーム判定

- ユーティリティ
  - 設定ファイル（.env）ウィザード（config_setup.py）
  - 設定検証ツール（validate_config.py）
  - ログ設定ユーティリティ（utils.logging_setup）
  - プロセス優先度・CPU affinity 設定（utils.process_priority）
  - Paper Trading 向け検証レポート生成ツール（tools.paper_verification_report）

---

## 前提 / 必要要件

- Python 3.10 以上（型ヒントに `X | Y` を使用）
- 推奨パッケージ（requirements.txt がある場合はそちらを使用）
  - duckdb
  - psutil
  - openai
  - (オプション) PyYAML（config/*.yaml を検証する場合）
- SQLite（標準ライブラリ）
- 環境変数の設定（下記参照）

インストール例（仮）:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# または最低限:
pip install duckdb psutil openai
```

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
  - paper_trading: MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に書き込む
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）。デフォルト: INFO
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必要）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant / partial / never / reject）
- LOG_DIR: ログファイル保存先（デフォルト: logs/）

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` が自動で読み込まれます。
- テスト等で自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順（簡易ガイド）

1. リポジトリをクローンしてワークディレクトリに移動
2. 仮想環境作成 & 有効化（推奨）
3. 依存パッケージをインストール
4. .env の作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは .env.example を参考に手動で作成
5. 設定検証（オプション）:
   ```
   python -m kabusys.validate_config
   # 警告をエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```
6. データベースディレクトリを作成（.env で指定している場合）
   ```
   mkdir -p data
   mkdir -p logs
   ```

---

## 使い方 / 実行方法

※ いずれもプロジェクトルートから実行してください（.env の自動ロードが働きます）。

- 実行エンジン（ExecutionEngine）を起動:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用します（paper_trading DB に記録）。
  - 起動時に data/execution.pid が作成されます。停止は data/stop_requested.flag を作るか kill.flag の運用に従ってください。

- 監視ループを起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を環境変数で上書き:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は .env の KABUSYS_ENV に関わらず本番用 sqlite_path（デフォルト: data/monitoring.db）を使用します。
  - 停止: プロジェクトルートの data/stop_requested.flag を作成するとループが終了します。

- 設定ウィザード / 検証:
  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定例:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # --db オプションで DB を指定することも可能:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- 研究 / AI 関数の利用（ライブラリとして）:
  - DuckDB 接続を生成して、research/ai 関数を呼び出す:
    ```py
    import duckdb
    from kabusys.research import calc_momentum
    conn = duckdb.connect("data/kabusys.duckdb")
    results = calc_momentum(conn, target_date)
    ```
  - OpenAI を利用する関数（news_nlp.score_news, regime_detector.score_regime 等）は環境変数 OPENAI_API_KEY または引数で API キーを渡してください。

---

## ログ・監視・停止フロー

- ログ: logs/<app_name>.log に日次ローテーションで出力されます（デフォルト 30日保持）。stdout へも出力されます。
- PID / stop フラグ:
  - run_execution は data/execution.pid を作成（path は Settings.pid_file_path）。
  - run_monitoring / run_execution の停止は data/stop_requested.flag を作成することで促すことができます（スクリプトは stop フラグを検出して終了）。
- Kill Switch:
  - リスク条件を満たすと Monitoring 側が data/kill.flag を作成し、ExecutionEngine が停止する仕組みです（Settings.kill_flag_path を使用）。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動クリアされますが、本番では 0 を推奨します。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主なファイルと概要です。

- kabusys/
  - __init__.py (パッケージ定義)
  - config.py (設定管理、.env 自動読み込み)
  - config_setup.py (対話式 .env ウィザード)
  - validate_config.py (設定検証 CLI)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor ポーリングループ起動スクリプト)
  - tools/
    - paper_verification_report.py (Paper Trading レポート生成)
  - ai/
    - news_nlp.py (ニュース NLP スコアリング)
    - regime_detector.py (市場レジーム判定)
  - research/
    - factor_research.py (ファクター計算)
    - feature_exploration.py (特徴量探索・IC 等)
  - portfolio/
    - portfolio_builder.py (候補選定・重み付け)
    - position_sizing.py (ポジションサイズ計算)
    - risk_adjustment.py (セクター制限・レジーム乗数)
    - __init__.py
  - monitoring/
    - monitoring_db.py (SQLite 永続化層)
    - system_monitor.py
    - trade_monitor.py (※実装ファイル参照)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (※実装ファイル参照)
  - execution/ (Execution に関する多数のモジュール: Engine、OrderManager、BrokerFactory 等)
  - utils/
    - logging_setup.py (ロギング初期化)
    - process_priority.py (プロセス優先度 / CPU affinity)
    - __init__.py

（リポジトリ全体の詳細はツリーを参照してください）

---

## よくある運用上の注意

- 本番（KABUSYS_ENV=live）では LINE 通知や Kill Switch 設定などを事前に確認してください（validate_config が警告を表示します）。
- Paper Trading は本番 DB と完全に分離されます。PAPER_TRADING_SQLITE_PATH を適切に設定してください。
- OpenAI を使用する機能は API コストが発生します。API キー管理と使用頻度に注意してください。
- DuckDB のスキーマ（prices_daily / raw_financials / raw_news 等）やデータ投入は別途データパイプラインが必要です（kabusys.data.pipeline 等の利用を想定）。

---

## サポート / 次のステップ

- 初期設定: `python -m kabusys.config_setup` → `python -m kabusys.validate_config`
- ローカル検証: Paper Trading を使って挙動を確認
- 本番運用: KABUSYS_ENV=live に切替える前に必ず設定を再確認

フィードバックやバグ報告はリポジトリの Issue へお願いします。

--- 

この README はコードベース（src/kabusys/*）に基づいて作成しています。実運用の細かい手順（データ投入、ブローカ接続情報、Docker / systemd によるサービス化等）はプロジェクトの運用ドキュメントに従ってください。