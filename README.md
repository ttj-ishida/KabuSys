# KabuSys

日本株自動売買システム（KabuSys）リポジトリの README。  
本ドキュメントはソースコード（src/kabusys 以下）を元に作成しています。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株向けの自動売買システム（研究・ポートフォリオ構築・実行・監視・AI 補助）を目的としたモジュール群です。  
主な構成要素は次のとおりです。

- 研究（research）: DuckDB 上の過去価格・財務データからファクターを計算・解析するモジュール
- ポートフォリオ構築（portfolio）: 候補選択、重み付け、リスク調整、株数決定
- 実行（execution）: ブローカークライアント経由の注文発行を担う ExecutionEngine（paper_trading モードあり）
- 監視（monitoring）: システム状態、注文ログ、リスク監視と Kill Switch（停止フラグ）生成
- AI（ai）: OpenAI を使ったニュースセンチメント評価やレジーム判定
- ツール（tools）: ペーパートレード検証レポート等の CLI スクリプト
- 設定ユーティリティ: .env ウィザード、設定検証 CLI

設計方針の一部:
- DuckDB を分析用 DB、SQLite を監視・発注履歴用に使用
- Paper Trading モードは本番 DB と完全に分離して専用の SQLite を使う
- LLM（OpenAI）呼び出しは失敗時にフォールバックする等のフェイルセーフを備える
- プロセス優先度・ログは起動スクリプトから統一的に設定

---

## 主な機能一覧

- ファクター計算: Momentum / Volatility / Value 等（kabusys.research）
- 特徴量探索: 将来リターン計算、IC（Information Coefficient）など（kabusys.research）
- ポートフォリオ構築: 候補選定・等重・スコア重み・リスクベース配分（kabusys.portfolio）
- ポジションサイジング: lot 単位丸め、aggregate cap、コストバッファ対応
- セクター上限適用・レジーム乗数（risk_adjustment）
- ExecutionEngine: ブローカークライアント、OrderManager、RiskManager 等（kabusys.execution）
- 監視: SystemMonitor / TradeMonitor / RiskMonitor、KillSwitch、アラート発行（kabusys.monitoring）
- AI モジュール: ニュース NLP スコアリング（news_nlp）、市場レジーム判定（regime_detector）
- 設定管理: .env ウィザード（config_setup）、設定検証（validate_config）
- ツール: Paper Trading 検証レポート生成（tools.paper_verification_report）

---

## 前提（依存関係）

ソースに明示されている主な外部依存（少なくとも次をインストールしてください）:

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config 検証時に optional）
- その他標準ライブラリ

インストールはプロジェクトに requirements.txt が用意されていればそれを使うのが望ましい（本リポジトリには含まれていない可能性があるため、以下は一例）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置

2. 仮想環境作成・依存インストール（上記参照）

3. .env の作成（ウィザード推奨）
   - 対話式で .env を作成/更新するには:
     ```bash
     python -m kabusys.config_setup
     ```
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（主なもの）
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視 SQLite（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（paper_trading 時）
     - OPENAI_API_KEY: OpenAI を使う機能で必要
     - PAPER_FILL_MODE: instant|partial|never|reject（paper_trading の挙動）
     - LOG_LEVEL, LOG_DIR 等

4. 設定検証
   - 自動検証スクリプトで設定や config/*.yaml の有無をチェック:
     ```bash
     python -m kabusys.validate_config
     ```
   - 警告も厳密に扱う (--strict):
     ```bash
     python -m kabusys.validate_config --strict
     ```

5. DB / ディレクトリの準備
   - デフォルトでは data/ 以下にファイルを配置します。アプリ起動時に自動作成する箇所もありますが、必要なら手動でディレクトリを作成してください。
   - ログはデフォルト logs/ に出力されます。

---

## 使い方（起動・操作）

主要な起動スクリプトはモジュールとして実行します。

- ExecutionEngine（注文実行）起動
  - 通常:
    ```bash
    python -m kabusys.run_execution
    ```
  - Paper Trading（env を切り替えて起動）:
    - .env で KABUSYS_ENV=paper_trading を設定するか、実行時に環境変数を上書き:
      ```bash
      KABUSYS_ENV=paper_trading python -m kabusys.run_execution
      ```
    - paper_trading の場合、MockBrokerClient を使用しデータは data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）に保存され、本番 DB と完全分離されます。

  - 停止方法:
    - 実行中に data/stop_requested.flag が作成されると Engine は停止処理を行います（run_execution がこのフラグを監視）。
    - 実行時は /data/execution.pid に PID が書き込まれます（設定により変更可）。

- Monitoring（監視ループ）起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を環境変数で上書き:
    ```bash
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
    デフォルトは 60 秒。0 以下や不正値は無視されデフォルトにフォールバックします。
  - Monitoring は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用して監視ログを残します。
  - 終了は data/stop_requested.flag を作成するか、Ctrl+C（KeyboardInterrupt）。

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定できます。

- 設定ウィザード / 検証
  - ウィザード:
    ```bash
    python -m kabusys.config_setup
    ```
  - 検証:
    ```bash
    python -m kabusys.validate_config
    ```

- OpenAI を用いる機能
  - news_nlp（ニュース NLP）や regime_detector は OPENAI_API_KEY が必要です。
  - これらの関数は DuckDB 接続と target_date を受け取り、結果を DB に書き込みます（フォールバックやリトライ機構あり）。

---

## 停止・Kill Switch 等の運用メモ

- stop flag
  - run_execution/run_monitoring はプロジェクトルートの data/stop_requested.flag を監視します。これを作成すると安全に停止します。

- kill flag
  - Kill Switch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります（KillSwitch モジュール）。
  - KillSwitch はリスク条件（ドローダウン、ポジション上限）に基づいて flag を書きます。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 にすると自動クリアしますが、本番では 0 を推奨します。

- PID ファイル
  - run_execution は data/execution.pid を利用します（設定で変更可）。プロセスの存在チェックや stale PID 判定に使用されます。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル / ディレクトリ（src/kabusys を基準）:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（.env 自動ロードロジック含む）
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py — ログ設定共通化
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数決定、aggregate cap
    - risk_adjustment.py — セクター上限、レジーム乗数
  - research/
    - factor_research.py — Momentum/Value/Volatility 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py — ニュース記事を OpenAI でスコアリングして ai_scores に書き込む
    - regime_detector.py — レジーム判定と market_regime への書き込み
  - monitoring/
    - monitoring_db.py — SQLite に対する永続化層（テーブル初期化含む）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （発注ログの監視、滞留注文検出 等）※ファイルは存在（コード参照）
    - risk_monitor.py — ドローダウン、保有数監視
    - kill_switch.py — Kill Switch 制御
    - monitoring_engine.py — 各 Monitor を束ねる実行エンジン
  - execution/
    - execution_engine.py — 実行ロジック（Engine）
    - broker_factory.py — ブローカークライアント生成（paper_trading 用 Mock 対応）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py 等
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - data/ (運用時に生成される想定)
    - *.db, pid/flag ファイルなど
  - logs/ (デフォルトログ出力先)

（上記は主要ファイルの抜粋です。細かい実装は各モジュール内の docstring を参照してください。）

---

## 注意事項 / 運用上のヒント

- KABUSYS_ENV = live に設定する際は十分に設定を確認（validate_config が warn を出します）。本番では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します。
- Paper Trading は本番 DB と分離されていますが、外部 API キーなどの取り扱いは .env を厳重に管理してください（.env は絶対に Git にコミットしない）。
- OpenAI を利用する機能は API レートリミットや費用を考慮して運用してください。news_nlp と regime_detector はリトライ・バックオフやフォールバックを導入していますが、呼び出し頻度は管理してください。
- ログは logs/<app_name>.log に日次ローテートで保存されます。ログディレクトリ作成失敗時はコンソール出力のみで継続します。

---

この README はコードベースから抽出した情報をまとめたものです。実運用や拡張の前に各モジュール内の docstring とコードを参照してください。必要であれば起動シーケンス図や設定テンプレートの README 追補作成も対応します。