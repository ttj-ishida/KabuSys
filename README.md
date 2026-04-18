# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム（KabuSys）の一部実装を含みます。
主要機能はシグナル生成／ポートフォリオ構築／発注実行／監視／研究ツール（DuckDB を利用）、
およびニュース NLP / レジーム判定のための OpenAI 連携などです。

以下はこのコードベースの概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成の説明です。

注意: README はコードベースに合わせたドキュメントです。実運用では各種設定（API キー／パスワード／
本番/ペーパートレード切替 等）を慎重に扱ってください。

---

目次
- プロジェクト概要
- 機能一覧
- 動作前の準備（依存関係）
- セットアップ手順
- 使い方（起動／停止／ユーティリティ）
- 主要環境変数（代表）
- データ・ログ・フラグファイルの説明
- ディレクトリ構成（主要ファイルの説明）

---

## プロジェクト概要

KabuSys は日本株自動売買のためのモジュール群です。本リポジトリには以下の主要サブシステムが含まれます。

- execution: 発注エンジン（本番は実ブローカー、paper_trading では MockBroker）
- monitoring: システム稼働状況、注文・リスクの常時監視、Kill Switch（異常時に発注停止）
- portfolio: 銘柄選定、重み付け、ポジションサイジング、セクター制約などの計算ロジック
- research: DuckDB ベースのファクター計算・特徴量解析ユーティリティ
- ai: ニュースセンチメント（OpenAI）を用いた ai スコア、レジーム判定
- utils: ロギング設定、プロセス優先度制御などのユーティリティ

設計上の注意点:
- 設定は .env（または環境変数）で管理。`config_setup` ウィザード・`validate_config` による検証を推奨。
- DuckDB / SQLite をローカルファイルに保持して分析・監視データを保存。
- Paper trading（ペーパートレード）モードでは本番 DB と分離して `data/paper_trading.db` を使用（デフォルト）。

---

## 主な機能一覧

- ExecutionEngine（発注処理）
  - 本番は実際のブローカークライアント、ペーパートレードでは MockBroker を利用
  - リスク管理（Rate limit / 最大ポジション / ドローダウン等）
  - OrderManager / Reconciler による注文管理・整合性保持

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態/データ鮮度の監視
  - TradeMonitor: 取引ログの監視（滞留注文／約定異常等）
  - RiskMonitor: ドローダウン・ポジション数の監視とリスクログ化
  - KillSwitch: 条件を満たすと data/kill.flag を書き込み、Execution を停止させる
  - MonitoringEngine: 上記モニタをまとめて定期実行・アラート送出

- Portfolio（純粋関数群）
  - 銘柄選定（スコア順ソート）
  - 重み計算（等金額 / スコア加重）
  - ポジションサイズ計算（リスクベース / アロケーションベース）
  - セクター集中制限・レジーム乗数の適用

- Research
  - ファクター計算（momentum/value/volatility 等）
  - 将来リターン計算、IC（Information Coefficient）などの統計解析ツール

- AI 系
  - news_nlp: raw_news を集計して OpenAI（gpt-4o-mini）でセンチメントを算出 → ai_scores に保存
  - regime_detector: ETF の MA200 とマクロ記事の LLM センチメントを合成して market_regime を判定

- ツール
  - config_setup: .env を対話的に作成/更新するウィザード
  - validate_config: .env / config/*.yaml の事前検証
  - paper_verification_report: ペーパートレード DB を解析して検証レポートを出力

---

## 動作前の準備（依存関係）

最低限の Python パッケージ（例）:
- Python 3.9+
- duckdb
- psutil
- openai
- pyyaml（config の検証を行う場合に推奨）
- （その他、実際のブローカークライアント等が別途必要）

インストール例（環境に合わせて仮想環境作成後に実行）:
```bash
pip install duckdb psutil openai pyyaml
```
※ リポジトリに requirements.txt があれば `pip install -r requirements.txt` を推奨します。

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト

2. 仮想環境を作る（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb psutil openai pyyaml
   ```

3. .env を作成
   - 対話ウィザードで作成:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは `.env.example` を手動でコピーして編集

4. 設定を検証
   ```bash
   python -m kabusys.validate_config
   # 警告をエラー扱いにする場合
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリの作成（自動で作成される場合あり）
   - デフォルトの DB / ログパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログ: logs/<app>.log
   - 必要なら手動作成:
     ```bash
     mkdir -p data logs
     ```

6. OpenAI を使う場合は環境変数を設定:
   - OPENAI_API_KEY=<your_key>
   - または score_news / score_regime の api_key 引数で渡す

---

## 使い方

基本的なコマンド（パッケージルートで実行）:

- 環境設定ウィザード（.env の作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Execution Engine の起動
  - 本番 / ペーパートレードは KABUSYS_ENV で切り替え
  ```bash
  # 本番（KABUSYS_ENV=live を .env で設定）
  python -m kabusys.run_execution

  # ペーパートレード（.env で KABUSYS_ENV=paper_trading または環境変数で指定）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

  特記事項:
  - paper_trading 時は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用するため本番 DB と完全分離されます。
  - 起動時に data/stop_requested.flag が存在すると起動を拒否します（停止・メンテ用のフラグ）。

- Monitoring の起動
  ```bash
  # デフォルト 60 秒間隔
  python -m kabusys.run_monitoring

  # 環境変数でポーリング間隔を変更（秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

  特記事項:
  - MONITOR_POLL_INTERVAL が不正な値（<=0 や非整数）の場合はデフォルト 60 秒にフォールバックします。
  - Monitoring は KABUSYS_ENV にかかわらず `Settings.sqlite_path`（デフォルト data/monitoring.db）を監視 DB として使用します（監視ログは本番用 DB に書かれる仕様）。

- kill.flag / stop リソース
  - KillSwitch: 異常検出時に `data/kill.flag` を書き込み、ExecutionEngine を停止させるためのシグナルを送ります。
  - stop_requested.flag: 外部から監視やエンジンを停止させたいときに `data/stop_requested.flag` を作成すると起動中ループを抜けます（run_execution/run_monitoring がこのフラグを監視します）。
  - pid ファイル: `data/execution.pid`（ExecutionEngine の PID が書かれます）

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（例）
  - ニュース NLP スコア付け（プログラムから呼び出す API）
    - kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OpenAI API キー（OPENAI_API_KEY または api_key 引数）が必要

---

## 主要な環境変数（代表）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API 用（必須）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定モード: instant / partial / never / reject（デフォルト: instant）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで必要）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動でクリアするか（"1" でクリア、デフォルト "0"）

補足:
- .env の自動ロードはルートに .git または pyproject.toml がある場合に行われます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## データ / ログ / フラグファイルの説明

- data/
  - monitoring.db（デフォルト）: MonitoringDB（system_status / trade_logs / positions / risk_logs / dashboard）
  - paper_trading.db: ペーパートレード用 SQLite（KABUSYS_ENV=paper_trading 時に使用）
  - kabusys.duckdb（デフォルトパス）: 分析用 DuckDB データベース（価格データや raw_financials 等を格納）
  - kill.flag: KillSwitch が書く停止フラグ（ExecutionEngine 停止のトリガー）
  - stop_requested.flag: 外部的にループを停止させたいときに作成するフラグ（起動・ループを抜ける）
  - execution.pid: 実行中の ExecutionEngine の PID（管理用）

- logs/
  - <app_name>.log: 日次ローテーション（logs ディレクトリが作成できない場合はコンソールのみ出力）

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — Settings クラス（環境変数/.env の読み込み・validation）
  - config_setup.py — .env 対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py — 起動前設定検証 CLI（python -m kabusys.validate_config）
  - run_execution.py — ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト（python -m kabusys.run_monitoring）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（Stream + TimedRotatingFileHandler）
    - process_priority.py — psutil を用いたプロセス優先度・CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite スキーマと永続化ユーティリティ
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （コード内に実装あり）取引ログ監視（滞留注文など）
    - risk_monitor.py — ドローダウン・ポジション上限チェック
    - kill_switch.py — フラグファイルによる停止シグナル発行
    - monitoring_engine.py — 各 Monitor を束ねて定期実行（run_loop）
    - alert_manager.py —（呼び出し箇所あり）アラート送信管理（LINE など）
  - execution/
    - execution_engine.py — 実際の ExecutionEngine （起動・セッション管理）
    - broker_factory.py — ブローカークライアントのファクトリ（Mock / Live 切替）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注関連の実装
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け関数
    - position_sizing.py — 株数計算・スケーリング・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum / value / volatility 等の DuckDB ベース計算
    - feature_exploration.py — forward returns / IC / 統計サマリー
  - ai/
    - news_nlp.py — raw_news をまとめて OpenAI に送りセンチメントを ai_scores に保存
    - regime_detector.py — マクロセンチメント + MA200 でレジーム判定
  - data/ （実行時に生成される想定）
    - *.db, kill.flag, stop_requested.flag, execution.pid
  - logs/ （実行時に生成される想定）
    - execution.log, monitoring.log, ...

---

## 運用上の注意（簡潔）

- 本番環境（KABUSYS_ENV=live）では kill.flag や KILL_FLAG_CLEAR_ON_START 設定に十分注意してください。
- .env を絶対にリポジトリにコミットしないでください（config_setup でも警告）。
- OpenAI を利用する箇所は API 呼び出し失敗時に安全側のフォールバックを行う設計ですが、API キーと料金管理は運用上重要です。
- Monitoring は監視 DB に直接書き込みます。運用開始前に validate_config で DB パス等を確認してください。

---

この README はコードの要点をまとめたものです。各モジュール・関数にはドキュメンテーション文字列が付与されていますので、詳細な挙動は該当ソースの docstring を参照してください。必要があれば起動スクリプトや各モジュール用の詳細ドキュメントを追加で作成します。