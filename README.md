# KabuSys

日本株向け自動売買システム（モジュール群）。  
このリポジトリはトレード実行エンジン、監視（Monitoring）、ポートフォリオ構築・調整、リサーチ／ファクター計算、AI（ニュース NLP / レジーム判定）などを含む複合的なコンポーネントで構成されています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- ディレクトリ構成（主要ファイル）

---

## プロジェクト概要

KabuSys は日本株の自動売買向けライブラリ／実行基盤です。  
主に以下の観点をカバーします。

- 発注（ExecutionEngine）／注文管理／リスク管理
- 実行系の監視（System / Trade / Risk の監視）とアラート・Kill Switch
- ポートフォリオ構築（候補選定・重み算出・株数算出）
- リサーチ用モジュール（ファクター計算・特徴量解析）
- AI モジュール（ニュースのセンチメントを LLM でスコア化、レジーム判定）
- ペーパートレード用の分離された DB と検証ツール
- ロギングとプロセス優先度ユーティリティ

設計上の特徴として、DB は DuckDB（分析用）と SQLite（監視・注文ログ）を利用、.env による環境設定、LLM 呼び出しは OpenAI（gpt-4o-mini）を想定しています。

---

## 機能一覧

主要な機能（抜粋）

- Execution
  - Engine を起動して発注処理を行う（本番 / ペーパーの切替可）
  - Broker クライアントファクトリによる Mock / 実ブローカーの切替
  - Order 管理 / Reconciler / RiskManager を組み合わせた発注ロジック

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス状況、データ鮮度チェック
  - TradeMonitor: 発注ログの監視（滞留注文、約定異常等）
  - RiskMonitor: ドローダウン・ポジション上限の監視とリスクログ記録
  - KillSwitch: しきい値超過時に data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: 定期ポーリングの統括

- Portfolio
  - 候補抽出（スコア順）
  - 重み計算（等分・スコア重み）
  - ポジションサイズ算出（リスクベース、単元丸め、aggregate cap）
  - セクター集中制限・レジーム乗数適用

- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算・IC（スピアマン）計算・統計サマリー

- AI
  - news_nlp: raw_news を LLM で解析して ai_scores に書き込み
  - regime_detector: ETF (1321) の MA200 乖離 + マクロニュースセンチメントで市場レジーム判定

- ツール
  - 設定ウィザード（python -m kabusys.config_setup）
  - 設定検証（python -m kabusys.validate_config）
  - Paper Trading 検証レポート出力（python -m kabusys.tools.paper_verification_report）

- ユーティリティ
  - ロギング設定（ログは logs/<app_name>.log に日次ローテーション）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順

前提
- Python 3.10 以上（コードは | 型ヒント等を使用）
- SQLite（標準ライブラリ）
- OS により psutil の一部機能（優先度設定など）が制限される場合があります

1. リポジトリをクローン
   - git clone ... （省略）

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 要件ファイルがある場合:
     - pip install -r requirements.txt
   - ない場合は最低限下記をインストール:
     - pip install duckdb openai psutil pyyaml

   注: OpenAI SDK、duckdb、psutil は必須。PyYAML は config YAML のパース確認用（任意）。

4. 初期環境変数設定（.env）
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（.env.example を参考に）

   主要な環境変数（必須・任意）
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使う任意 / デフォルト
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (ペーパートレード用、デフォルト: data/paper_trading.db)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
     - OPENAI_API_KEY — AI 機能利用時に必要
     - PAPER_FILL_MODE ("instant" | "partial" | "never" | "reject") — デフォルト: instant
     - KILL_FLAG_CLEAR_ON_START (0|1) — 本番では 0 推奨

5. DB / ディレクトリの準備
   - data/ ディレクトリを作る（実行時に自動作成されることが多いが、手動で作成しておくと良い）
   - logs/ ディレクトリ（ログ出力用）も自動作成されるが権限確認

6. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合は --strict を付ける

---

## 使い方

実行系・監視などコマンド例

- ExecutionEngine の起動（常用）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に記録して本番 DB と分離
    - 実行中は data/execution.pid に PID を書き込み、data/stop_requested.flag が作成されると停止検知

- Monitoring の起動（ループ）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path（monitoring DB）を利用して system_status / trade_logs / risk_logs / dashboard を管理
  - run_monitoring は実行時に process priority を high に設定し、監視のポーリングループを実行

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH や --db オプションで指定可）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- AI / プログラム的利用例
  - news_nlp（ニュースをスコア化）を直接呼ぶ場合（スクリプトから）
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

  - regime_detector を使う場合
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

  注意: AI 機能は OPENAI_API_KEY が必要。API エラー時はフェイルセーフ（0.0 等でフォールバック）する実装方針になっていますが、API キーは必ず設定してください。

- Kill Switch / 停止フラグ
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります
  - 手動で停止させたい場合は data/stop_requested.flag を作成／削除してプロセスの開始・停止を制御します
  - 実行時の挙動:
    - run_execution は data/stop_requested.flag が存在する場合は起動せず早期終了します
    - run_monitoring はループ中に stop_requested.flag を検知すると終了します

---

## ディレクトリ構成（主要）

プロジェクトは src/kabusys 以下に配置されています。主要ファイル・モジュールの抜粋:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env ロードロジック含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - execution/                — 発注実行関連（Engine / OrderManager / RiskManager 等）
    - (実装ファイル群)
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュースを LLM でスコアリング
    - regime_detector.py     — レジーム判定（MA200 + マクロセンチメント）
  - data/                    — 実行時に使うファイル（data/*.db, *.flag, *.pid など）
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ（stdout + 日次ファイルローテーション）
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 補足 / 運用メモ

- Python バージョン
  - 型ヒントに | を使用しているため Python 3.10 以上が必要です。

- ログ
  - デフォルトでは logs/<app_name>.log に日次ローテーションで保存されます（30日保持）。
  - setup_logging() を各スクリプトが呼び出して統一管理しています。

- DB の分離
  - 本番／ペーパーは SQLite を分離しています（PAPER_TRADING_SQLITE_PATH）。
  - Monitoring は常に Settings.sqlite_path（監視 DB）を使います。

- 冪等性 / マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブル作成・簡易マイグレーション（カラム追加）を行います。

- セキュリティ
  - .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注意書きあり）。

---

README の内容はコードベースの主要な使い方と構成をまとめたものです。実際の運用では .env の中身、BrokerClient の実装、API キー周り、アクセス権限、バックアップ運用などを十分に確認してから本番で稼働してください。質問や追加で README に載せたい項目があれば教えてください。