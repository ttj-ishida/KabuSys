# KabuSys — 日本株自動売買システム（README）

この README はリポジトリ内のコードベースに基づく簡易ドキュメントです。セットアップ、主要機能、基本的な使い方、ディレクトリ構成を日本語でまとめています。

※ 本リポジトリは自動売買、モニタリング、リサーチ、AI（ニュースセンチメント）など複数の機能群で構成されています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムです。主な目的は以下の通りです。

- シグナルに基づいたポートフォリオ構築と発注（ExecutionEngine）
- 発注・約定ログの永続化とリスク監視
- システム稼働性 / データ鮮度の監視（Monitoring）
- DuckDB を用いたファクター計算、リサーチ機能
- OpenAI（LLM）を使ったニュースセンチメント評価（AI）
- ペーパートレード用の完全分離 DB サポートと検証レポート生成

---

## 機能一覧

- Execution
  - ExecutionEngine による注文発行／監視（paper/live/dev モード対応）
  - BrokerClientFactory による実際のブローカー or MockBroker の切替（環境依存）
  - 注文・約定ログ（SQLite / MonitoringDB）保存、リスク管理（RiskManager）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス生存、データ鮮度監視
  - TradeMonitor / RiskMonitor: 滞留注文、約定異常、ドローダウン・ポジション上限監視
  - Kill Switch: 異常時に flag ファイルを書き ExecutionEngine を安全停止
  - MonitoringEngine: 上記モニタを束ねてポーリング通知・kill 判定
- Research / Portfolio
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）評価、統計サマリ
  - ポートフォリオ構築（候補選定、等配分・スコア加重）、ポジションサイジング、セクターキャップ、レジーム乗数
- AI（OpenAI）
  - news_nlp: ニュース記事を集約して LLM で銘柄別センチメントを算出し ai_scores に書き込み
  - regime_detector: ETF（1321）MA200 とマクロニュースを組み合わせて市場レジームを判定・永続化
- ツール
  - config_setup: .env 対話ウィザード（初期設定）
  - validate_config: .env と config/*.yaml の事前チェック CLI
  - paper_verification_report: ペーパートレード DB から検証用レポート出力

---

## 前提 / 必要パッケージ

Python 環境（3.9+ を想定）および以下の主要パッケージが必要です（実行する機能により一部のみ必要）。

- duckdb
- psutil
- openai
- PyYAML（config YAML 検証を行う場合）

インストール例（仮）:
```bash
python -m pip install duckdb psutil openai PyYAML
```

パッケージ管理（プロジェクトで requirements.txt がある場合はそちらを利用してください）。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境の作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -U pip
   pip install duckdb psutil openai PyYAML
   ```
3. 環境変数設定
   - 対話式ウィザードで .env を作成する（推奨）
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは `.env` / `.env.local` を手動作成
   - 必須環境変数
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要なオプション（例）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能使用時に必要）
     - LOG_LEVEL（DEBUG/INFO/...）
   - 自動ロード:
     - プロジェクトルートに `.env` または `.env.local` があれば起動時に自動読み込みされます（無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）
4. 設定検証（推奨）
   ```bash
   python -m kabusys.validate_config
   # strict モード（警告も失敗にする）
   python -m kabusys.validate_config --strict
   ```
5. ログディレクトリ
   - デフォルトは `logs/`。`LOG_DIR` 環境変数で変更可能。
   - 各スクリプトは日次ローテーションで `logs/<app_name>.log` に出力します。

---

## 使い方（実行例）

- ExecutionEngine の起動（メイン実行エントリ）
  - ペーパートレードは KABUSYS_ENV=paper_trading を設定すると MockBroker を使い、専用の paper_trading DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  ```bash
  # そのまま実行
  python -m kabusys.run_execution

  # 環境変数を明示して実行例
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- Monitoring の起動（ポーリング監視）
  - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  ```bash
  python -m kabusys.run_monitoring
  # 例: 30秒間隔
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- コンフィグウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート生成
  ```bash
  # デフォルト DB を使用
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # DB パスを直接指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI（ニューススコアリング / レジーム判定）を Python REPL やスクリプトから呼ぶ例
  - DuckDB 接続を用意して関数を呼び出します。OPENAI_API_KEY が必要です。
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai import score_news
  # duckdb_conn: duckdb.connect("data/kabusys.duckdb")
  conn = duckdb.connect("data/kabusys.duckdb")
  # score_news は ai_scores に書き込みます（戻り値は書き込み銘柄数）
  count = score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
  ```

- Kill / Stop フロー
  - 実行中のループ（監視 / エンジン）はプロジェクトの `data/stop_requested.flag` または `data/kill.flag` を検知して停止します。
  - ExecutionEngine は起動時に `data/execution.pid` を書き、kill.flag の検出で停止する仕組みになっています。

---

## 主要環境変数（まとめ）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能時に必須）
- MONITOR_POLL_INTERVAL（監視ループ間隔, 秒, デフォルト 60）
- LOG_LEVEL（ログレベル）
- LOG_DIR（ログ保存ディレクトリ）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1）

---

## ディレクトリ構成（抜粋）

以下はソースツリーの主要ファイル／モジュール構成（抜粋）です。

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py                # 環境変数・.env 自動ロード・Settings
   ├─ config_setup.py          # .env 対話ウィザード CLI
   ├─ validate_config.py       # 設定検証 CLI
   ├─ run_execution.py         # ExecutionEngine 起動スクリプト
   ├─ run_monitoring.py        # SystemMonitor 起動スクリプト
   ├─ utils/
   │   ├─ logging_setup.py     # ログ設定ユーティリティ
   │   └─ process_priority.py  # プロセス優先度設定ユーティリティ
   ├─ monitoring/
   │   ├─ monitoring_db.py
   │   ├─ system_monitor.py
   │   ├─ trade_monitor.py
   │   ├─ risk_monitor.py
   │   ├─ kill_switch.py
   │   └─ monitoring_engine.py
   ├─ execution/                # Execution 系の実装（Engine, OrderManager, BrokerFactory 等）
   ├─ portfolio/
   │   ├─ portfolio_builder.py
   │   ├─ position_sizing.py
   │   └─ risk_adjustment.py
   ├─ research/
   │   ├─ factor_research.py
   │   └─ feature_exploration.py
   ├─ ai/
   │   ├─ news_nlp.py           # ニュース NLP（OpenAI 呼び出し）
   │   └─ regime_detector.py   # レジーム判定（MA200 + マクロセンチメント）
   └─ tools/
       └─ paper_verification_report.py
```

（注）execution パッケージ以下や一部補助モジュールはここで全てを列挙していません。実際のコードを参照してください。

---

## 開発上の注意点 / 運用メモ

- .env は決して Git にコミットしないでください（config_setup も README に書いてあるように .env を生成します）。
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する実装箇所があるため、監視用の DB パス設定に注意してください（コード内にコメントあり）。
- Paper Trading は本番 DB と分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を利用）。
- OpenAI の呼び出しはリトライや 5xx/429 のハンドリングを組み込んでいますが、API キーのレート制限に注意してください。
- psutil を用いてプロセス優先度や CPU affinity を設定します。権限がない場合は警告を出してスキップします。
- DuckDB のバージョン依存（executemany の空リストなど）に注意が必要な箇所が実装に残っています。環境の DuckDB バージョンで問題が発生する場合はログやエラーを参照してください。
- 監視の停止・強制停止は data/stop_requested.flag、data/kill.flag を利用します。運用手順をあらかじめ文書化しておくと安全です。

---

## サポート / 参考

- 各モジュールにドキュメント文字列（docstring）が多数含まれており、関数ごとの挙動・引数・戻り値についてはコード内コメントを参照してください。
- config_setup と validate_config の組み合わせで初期設定と事前チェックが可能です。まずはそれらを利用して環境整備を行ってください。

---

この README は主要機能と実行手順の概要をまとめたものです。各機能の詳細な設計ドキュメント（PortfolioConstruction.md や StrategyModel.md 等）はリポジトリ内の別ファイルを参照してください（存在する場合）。不足点や追記希望があれば教えてください。