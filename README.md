# KabuSys — README (日本語)

本文書はこのリポジトリ内のコードベース (src/kabusys) の概要、セットアップ、主要な使い方、ディレクトリ構成をまとめた README です。KabuSys は日本株向け自動売買・研究・監視のためのモジュール群を含むプロジェクトです。

注意: 本 README はソースコードに記載された仕様（デフォルト値・振る舞い）に基づいて作成しています。

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件
- セットアップ手順
- 主要な環境変数（抜粋）
- 使い方（コマンド例）
- よく使うファイル / フラグ
- ディレクトリ構成
- トラブルシュート（よくある操作）

---

## プロジェクト概要

KabuSys は日本株自動売買システムのコンポーネント群をモジュール化したコードベースです。主な役割は次の通りです。

- 戦略（ファクター計算・特徴量・ポートフォリオ構築）
- 発注 / 実行エンジン（ExecutionEngine、ブローカークライアント抽象化）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）
- Paper Trading 用の分離された DB と検証レポートの生成
- ニュースの NLP スコアリング（OpenAI を利用）
- 市場レジーム検出（MA と LLM の組合せ）
- 環境設定ウィザードと設定検証ツール

設計方針として、DB や OpenAI API などの外部依存を明示的に扱い、実運用向けのフェイルセーフや冪等性を考慮しています。

---

## 機能一覧（主要コンポーネント）

- config / config_setup / validate_config
  - 環境変数の自動読み込み、.env 作成ウィザード、起動前設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（本番 / paper_trading に応じた DB・Broker 切替）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（監視ログを SQLite に永続化）
- monitoring/* 
  - MonitoringDB（SQLite 操作）、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringEngine、AlertManager 等
- portfolio/*
  - 銘柄選定、重み計算、セクターキャップ、ポジションサイジング等（純粋関数）
- research/*
  - ファクター計算（momentum/value/volatility）・将来リターン・IC 計算・統計
- ai/*
  - news_nlp: OpenAI を使ったニュースのセンチメントスコアリング
  - regime_detector: マクロ + ETF MA を組み合わせた市場レジーム判定
- tools/paper_verification_report.py
  - Paper Trading 用検証レポート生成ツール
- utils/*
  - ロギング設定、プロセス優先度 / CPU affinity ユーティリティ 等

---

## 前提条件

- Python 3.10 以上（型ヒントに | が使われているため）
- 推奨ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時に optional）
- SQLite は標準ライブラリで利用
- ネットワークアクセスが必要な機能（OpenAI 呼び出し、外部 API）は各自 API キーの準備が必要

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

プロジェクト用の追加パッケージ・依存は運用環境に合わせて requirements.txt を用意してください。

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境を作成・有効化し、依存パッケージをインストール
3. .env の作成（対話式ウィザード推奨）
   - 実行:
     ```
     python -m kabusys.config_setup
     ```
   - 対話に従い J-Quants や kabuAPI パスワード、KABUSYS_ENV (development/paper_trading/live) などを設定します。
4. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も失敗扱いになります
5. data / logs ディレクトリが自動作成されますが、権限やパスを事前に確認してください
6. Paper Trading を行う場合は PAPER_TRADING_SQLITE_PATH の確認（デフォルト: data/paper_trading.db）

---

## 主要な環境変数（抜粋）

- 必須（少なくとも実運用で必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- ログ / DB
  - LOG_LEVEL (DEBUG/INFO/...)
  - LOG_DIR: ログ保存先ディレクトリ（デフォルト logs/）
  - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- Paper Trading 固有
  - PAPER_FILL_MODE: instant | partial | never | reject (デフォルト instant)
- OpenAI
  - OPENAI_API_KEY: news_nlp / regime_detector で使用
- その他
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など（監視・停止制御）

（config_setup のウィザードで主要なキーは網羅されます）

---

## 使い方（代表的なコマンド）

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動（本番 / paper_trading を Settings.env が決定）
  ```
  python -m kabusys.run_execution
  ```
  - paper_trading 環境では MockBrokerClient を使用し、Paper DB（PAPER_TRADING_SQLITE_PATH）へ記録されます。
  - 起動時に data/stop_requested.flag が存在すると起動を行わず終了します。
  - 実行中に data/stop_requested.flag が作られるとエンジンへ停止シグナルを送り終了します。

- Monitoring（SystemMonitor）起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視は Settings に関わらず本番 sqlite_path を使用します（監視ログは単一の監視 DB へ）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB の指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI / Regime 検出やニューススコアリング（プログラムから呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OPENAI_API_KEY を設定しておくか api_key を引数に渡してください。

---

## よく使うファイル・フラグ

- data/kill.flag
  - KillSwitch が書き込む停止フラグ。ExecutionEngine を停止させるために使用します。
  - KillSwitch.clear() で削除可能。KILL_FLAG_CLEAR_ON_START=1 の場合起動時に自動クリアされます（本番では 0 推奨）。

- data/stop_requested.flag
  - run_execution / run_monitoring の外部停止トリガー（起動時とループ中にチェック）。存在すると起動しない / ループを終了する。

- data/execution.pid
  - ExecutionEngine が PID を書き込むファイル（プロセス管理用）。

- logs/<app>.log
  - setup_logging によって作成される日次ローテートログ（default: logs/）

---

## ディレクトリ構成（抜粋）

ルート:
- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数読み込み / Settings
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor 起動スクリプト
    - utils/
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py (参照: コードベースに存在)
    - execution/               — 発注・リスク管理・order_repository 等（起動コードから参照）
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - tools/
      - paper_verification_report.py

（上記は主要モジュールの抜粋。完全な構成はリポジトリの src/kabusys 配下を参照してください）

---

## トラブルシュート / 運用メモ

- ログが出力されない / ファイルハンドラの作成に失敗する
  - 権限やパスの問題の可能性があります。環境変数 LOG_DIR を確認、または logs ディレクトリの書込み権限を確認してください。
  - logging_setup はディレクトリ作成に失敗するとコンソール出力のみで継続します（警告を stderr に出します）。

- ExecutionEngine / Monitoring が起動しない
  - data/stop_requested.flag または data/kill.flag が存在する場合は起動しない / 即時停止します。不要なフラグは削除してください。
  - validate_config で設定ミスを検出できます。

- OpenAI を使う機能について
  - OPENAI_API_KEY が未設定だと例外が投げられます。CI やテスト環境ではモック化して呼び出してください。
  - API 呼び出しはリトライやバックオフ処理を行っていますが、API 制限に注意してください。

- Paper Trading と本番 DB の分離
  - KABUSYS_ENV=paper_trading の場合、run_execution は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番 sqlite を汚染しません。

- プロセス優先度 / CPU affinity
  - 起動スクリプト実行時に set_process_priority("high") を呼びます。権限により設定に失敗する場合は警告のみでスキップされます。

---

この README はコードコメント・関数ドキュメンテーションに基づいて要点をまとめたものです。詳細な API ドキュメントや設計仕様（PortfolioConstruction.md, StrategyModel.md 等）が別途ある想定です。機能追加・運用ルールの変更時は該当コードの docstring を合わせて更新してください。