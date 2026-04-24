# KabuSys

KabuSys は日本株向けの自動売買システム（プロトタイプ）です。戦略の研究・ファクター計算、ポートフォリオ構築、注文実行（本番 / ペーパートレード）、監視、AI を使ったニュースセンチメント評価などのコンポーネントを備えています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- 環境変数 / 設定
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下の関係コンポーネントにより構成されます。

- ExecutionEngine（発注エンジン）
  - 本番では kabuステーション API、ペーパートレード時は MockBrokerClient を使用し、ペーパートレード用 DB は本番 DB と分離されます。
- Monitoring（監視）
  - システム稼働状況、データ鮮度、取引ログ、リスク（ドローダウン・ポジション上限）を監視し、Kill Switch / アラートを発動します。
- Research / Factor 計算
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value 等）や将来リターン・IC 計算など。
- Portfolio（銘柄選定・配分・ポジションサイズ算出）
  - 候補選定、等重/スコア重み、リスクベースの株数算出、セクター制限など。
- AI（ニュース NLP / レジーム判定）
  - OpenAI を用いたニュースセンチメント、マクロニュースを使った市場レジーム判定。
- Tools
  - ペーパートレード結果の検証レポート生成など。
- 設定補助
  - .env の対話式ウィザード、起動前の設定検証 CLI。

---

## 機能一覧

主な機能（抜粋）:

- 実行環境切替: development / paper_trading / live
  - KABUSYS_ENV により挙動を切り替え（paper_trading では実際発注せず専用 DB を使用）
- 発注・注文管理（OrderManager / ExecutionEngine）
- リスク管理（RiskManager / Reconciler）
- 監視コンポーネント
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス監視、データ鮮度
  - TradeMonitor: 注文滞留・約定異常検出（trade_logs）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新、risk_logs
  - KillSwitch: 条件を満たすと data/kill.flag を作成して ExecutionEngine に停止シグナル
  - MonitoringEngine: 各モニタを束ねたポーリングループ
- データ永続化
  - SQLite（監視 / ペーパートレード DB）および DuckDB（分析 / prices_daily / raw_financials 等）
- 研究用ユーティリティ
  - ファクター計算、forward returns、IC、統計サマリ
- AI 関連
  - ニュース記事を OpenAI でスコアリングして ai_scores に保存
  - マクロニュース + ETF MA200 による市場レジーム判定
- ユーティリティ
  - 対話式 .env 作成（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成ツール

---

## セットアップ手順

前提
- Python 3.10 以上（コードは Union 型 `|` を使用）
- Git クローン済みのプロジェクトルートにいること

例: 仮想環境を作成して依存をインストールする手順（依存はプロジェクトの実行環境に応じて調整してください）。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化
   (例)
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール
   最低限想定されるパッケージ:
   - duckdb
   - openai
   - psutil
   - PyYAML (設定検証時に YAML を検証する場合)
   ```
   pip install duckdb openai psutil PyYAML
   ```
   （requirements.txt がある場合はそちらを使用してください）

4. 初期設定
   - 対話式ウィザードで .env を作成:
     ```
     python -m kabusys.config_setup
     ```
   - 設定検証:
     ```
     python -m kabusys.validate_config
     # 警告も厳密に扱いたい場合:
     python -m kabusys.validate_config --strict
     ```

5. データ / ログ用ディレクトリを確認
   - デフォルト DB / ログ:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - ペーパートレード SQLite: data/paper_trading.db
     - ログ: logs/
   - 必要なら作成:
     ```
     mkdir -p data logs
     ```

---

## 使い方

基本的な起動方法・よく使うコマンド。

1. ExecutionEngine を起動
   - 本番 / ペーパートレードの切り替えは KABUSYS_ENV 環境変数で行います。
   - ペーパートレード時は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録します。

   例:
   ```
   # ペーパートレード
   export KABUSYS_ENV=paper_trading
   python -m kabusys.run_execution

   # 本番
   export KABUSYS_ENV=live
   python -m kabusys.run_execution
   ```

   実行時の挙動:
   - 起動時にプロセス優先度を High に設定しようとします（psutil の権限に依存）。
   - PID ファイル（デフォルト: data/execution.pid）を利用します。
   - data/stop_requested.flag が存在した場合は起動を中止 / 実行停止します。

2. Monitoring を起動
   ```
   python -m kabusys.run_monitoring
   ```
   - デフォルトのポーリング間隔は 60 秒。環境変数で上書き:
     ```
     export MONITOR_POLL_INTERVAL=30
     ```
   - 監視は本番の sqlite_path を環境にかかわらず使用します（monitoring 用 DB は Settings.sqlite_path により決定）。
   - 停止は data/stop_requested.flag を作成するか Ctrl+C。

3. 設定ウィザード / 検証
   - .env の作成:
     ```
     python -m kabusys.config_setup
     ```
   - 設定検証:
     ```
     python -m kabusys.validate_config
     ```

4. Paper Trading 検証レポート
   - デフォルト DB: data/paper_trading.db。--db で上書き可。
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```

5. AI モジュール（プログラム内部から呼び出す）
   - OpenAI API キーは環境変数 OPENAI_API_KEY または関数引数で渡します。
   - 例（Python スクリプト内）:
     from kabusys.ai import score_news
     score_news(conn, target_date, api_key="sk-...")

6. ログ
   - setup_logging により logs/<app_name>.log に日次ローテーションで出力されます（デフォルトログディレクトリ: logs/）。
   - コンソールは stdout に出力されます。

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要なオプション:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant | partial | never | reject）

Kill / Stop フラグ:
- data/kill.flag — KillSwitch により書き込まれるファイル（ExecutionEngine に停止命令を与える）
- data/stop_requested.flag — run_* スクリプトが監視するグローバル停止フラグ

注意: .env は絶対にリポジトリにコミットしないでください（機密情報を含むため）。

---

## ディレクトリ構成（主要ファイル）

以下はソースツリー（src/kabusys）内の主要ファイルとディレクトリの概観です:

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / 設定読み込みロジック
    - config_setup.py              — .env 対話式ウィザード
    - validate_config.py           — 起動前設定検証 CLI
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py (実装ファイルあり)
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py (実装ファイルあり)
    - execution/
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - その他実装
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - data/                         — 実行時に使用するファイル（DB、flag、PID 等）
    - logs/                         — ログ出力先（デフォルト）

（プロジェクトルートには .env / .env.local / config/*.yaml 等が置かれます）

---

## その他・運用に関する注意

- ペーパートレードは本番 DB と分離されています。KABUSYS_ENV=paper_trading のときは MockBrokerClient を利用し、デフォルトで data/paper_trading.db に記録されます。
- OpenAI を利用する機能（ニュース NLP / レジーム判定）は API キー（OPENAI_API_KEY）が必須です。API エラー時はフォールバックロジックで安全に継続する設計です。
- 監視は kill.flag や stop_requested.flag によって外部から制御できます。デフォルトで起動時に kill.flag を自動クリアする設定は無効（KILL_FLAG_CLEAR_ON_START=0 を推奨）。
- ログディレクトリの作成に失敗した場合はコンソール出力のみで継続します。

---

必要に応じて README に追記します。特定の実行例、設定サンプル、あるいは各モジュールの詳細な API ドキュメントが欲しい場合はその旨を教えてください。