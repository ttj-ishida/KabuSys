# KabuSys

日本株自動売買システムのコアライブラリ群と起動スクリプト。  
このリポジトリは、リアル/ペーパー発注、監視・アラート、ポートフォリオ構築、ファクター研究、ニュースNLP（LLM）などを含む自動売買の基盤機能を提供します。

## プロジェクト概要
- 発注エンジン（ExecutionEngine）と監視プロセス（Monitoring）を分離して実行可能。  
- Paper Trading（ペーパートレード）モードをサポートし、本番 DB と完全に分離して動作可能。  
- DuckDB を分析用途に、SQLite を監視・注文ログ用に利用。  
- ニュース記事の LLM ベースセンチメントや市場レジーム判定を実装（OpenAI API を使用）。  
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ）、リスク調整、ポジションサイジングの純粋関数実装あり。  
- 監視周りは監視DB、アラート、Kill Switch（フラグファイルによる停止指示）を備える。

## 主な機能一覧
- Execution（発注）
  - 実取引 / ペーパー取引切替（環境変数 KABUSYS_ENV）
  - RiskManager / OrderManager / Reconciler 等の構成
  - PID ファイル管理、停止フラグ監視

- Monitoring（監視）
  - システムリソース監視（CPU/Memory/Disk）、データ鮮度チェック
  - 取引ログ監視（滞留注文や異常約定の検出）
  - リスク監視（ドローダウン・ポジション上限）
  - Kill Switch による Execution 停止

- Portfolio（ポートフォリオ構築）
  - 候補選定、等重・スコア重みの計算
  - セクター上限適用、レジーム乗数
  - ポジションサイズ算出（リスクベース / 等分 / スコアベース）

- Research（研究用ユーティリティ）
  - ファクター計算（Momentum, Volatility, Value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（LLM 統合）
  - ニュース記事のセンチメントスコア化（OpenAI）
  - 市場レジーム判定（MA200 + マクロセンチメントの合成）

- Tools
  - Paper Trading 検証レポート生成スクリプト（過去期間の稼働率、注文成功率、レイテンシ等）

- 設定・検証
  - .env を対話式に作成するウィザード（config_setup）
  - 起動前設定検証 CLI（validate_config）

## 前提 / 必要環境
- Python 3.10 以上（型ヒントで `X | None` などの構文を使用）
- 必須（プロジェクトで想定される主要依存）:
  - duckdb
  - psutil
  - openai
- 任意／用途により:
  - PyYAML（config/*.yaml の内容検証に使用）
  - 他に発注関連のライブラリなど（Broker クライアント実装に依存）

インストール例（仮）:
```bash
python -m pip install duckdb psutil openai PyYAML
```

※ 実際の requirements.txt がある場合はそちらを使ってください。

## 環境変数（主なもの）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / よく使う:
  - KABUSYS_ENV: execution モード（development / paper_trading / live）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading モード）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/…）
  - LOG_DIR: ログ保存先（既定は logs/）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
  - PAPER_FILL_MODE: ペーパートレードの充填挙動（instant/partial/never/reject）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（デフォルト 0）

設定はルートの `.env` / `.env.local` に置くか、OS 環境変数で指定します。自動ロード機能はデフォルトで有効です（無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

## セットアップ手順（推奨フロー）
1. リポジトリを取得
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell など)
   ```

3. 依存パッケージをインストール
   ```bash
   python -m pip install --upgrade pip
   python -m pip install duckdb psutil openai PyYAML
   ```

4. 環境変数ファイルの作成（対話式ウィザード）
   ```bash
   python -m kabusys.config_setup
   ```
   - ウィザードは `.env` を生成します。生成後に `python -m kabusys.validate_config` で設定検証を行ってください。

5. データディレクトリやログディレクトリを作成（必要に応じて）
   ```bash
   mkdir -p data logs
   ```

6. 必要な DB 初期化やデータ投入はケースに応じて実施してください（DuckDB の prices_daily などは別途パイプラインで投入する想定）。

## 使い方（起動・ユーティリティ）
- ExecutionEngine（発注エンジン）起動
  - 本番 / ペーパー / 開発は KABUSYS_ENV で切替
  - 実行:
    ```bash
    python -m kabusys.run_execution
    ```
  - 動作:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB と分離）。
    - 起動時に stop flag（data/stop_requested.flag）が存在する場合は起動しません。
    - 停止は kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）を書き込むか stop_requested.flag を置くことで行えます。

- Monitoring（監視プロセス）起動
  - 実行:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - 動作:
    - デフォルトで 60 秒間隔でポーリング。環境変数で上書き可:
      - MONITOR_POLL_INTERVAL (秒)
    - 監視は常に本番 sqlite_path を使用して監査ログを記録します（設定に依らず）。

- 設定検証 CLI
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または環境変数で DB を指定
  PAPER_TRADING_SQLITE_PATH=data/paper_trading.db python -m kabusys.tools.paper_verification_report
  ```

- ニュース NLP / レジーム判定（プログラムから）
  - duckdb 接続を用意して関数を呼ぶ:
    ```python
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, date(2026, 4, 1), api_key="sk-xxxx")
    ```
  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を使用。

## ログ/監視/停止
- ログ: kabusys.utils.logging_setup により logs/<app_name>.log に日次ローテーションで出力（デフォルト 30 日保持）。
- PID / フラグ:
  - ExecutionEngine の PID ファイル: data/execution.pid（Settings.pid_file_path）
  - Kill Switch: data/kill.flag（存在すると ExecutionEngine に停止を促す）
  - run_monitoring / run_execution は stop_requested.flag を見てループを終了する（内部的な停止操作用）。

## 開発者向けメモ
- 設定の自動ロード順序: OS 環境 > .env.local > .env（プロジェクトルート検出に .git または pyproject.toml を使用）
- validate_config は .env および config/*.yaml の存在と基本的一貫性をチェック（PyYAML がない場合は YAML の検証はスキップ）
- DuckDB 側のテーブル（prices_daily / raw_financials / raw_news など）は外部のデータパイプラインで準備する前提

## ディレクトリ構成
主要ファイル／モジュールを抜粋した構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring 起動スクリプト
  - config.py                     — Settings / .env 自動ロード
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 起動前設定検証 CLI
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（OpenAI）
    - regime_detector.py           — 市場レジーム判定（LLM + MA200）
  - monitoring/
    - monitoring_db.py             — SQLite テーブル初期化・永続化層
    - monitoring_engine.py         — 各 Monitor の統合ループ
    - system_monitor.py            — システム・データ鮮度監視
    - trade_monitor.py             — （取引監視：ファイルに存在）
    - risk_monitor.py              — ドローダウン・ポジション数監視
    - kill_switch.py               — フラグファイルで Execution 停止
    - alert_manager.py             — （アラート送信：ファイルに存在）
  - portfolio/
    - __init__.py
    - portfolio_builder.py         — 候補選定・重み
    - position_sizing.py           — 株数算出
    - risk_adjustment.py           — セクター上限・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算
    - feature_exploration.py       — 将来リターン・IC・統計
  - utils/
    - __init__.py
    - logging_setup.py             — ログ初期化ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity
  - monitoring/ (上記)
  - execution/ (実際の ExecutionEngine 実装一式はこの配下に存在します)
  - data/ (実行時に作成される data/ 以下の DB / flag / pid 等)

（リポジトリ全体の完全な tree はプロジェクトのルートで `tree` 等を使って確認してください）

---

この README はリポジトリ内のコードから読み取れる設計意図・実行方法を要約したものです。導入や運用の前に `python -m kabusys.validate_config` を実行して設定不備がないか確認してください。実運用（KABUSYS_ENV=live）では kill flag 等の安全措置・ログ監査を十分に検討してください。