# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買 / 研究 / 監視ユーティリティ群をまとめた Python パッケージです。  
以下はこのコードベースの概要、機能、セットアップと使い方、および主要なディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群から構成されます。

- 発注エンジン（ExecutionEngine）とブローカー抽象化（本番/ペーパートレード対応）
- モニタリング（システム健全性、取引ログ、リスク監視、Kill Switch）
- ポートフォリオ構築（候補選定・重み算出・株数決定・リスク調整）
- リサーチ（ファクター計算、特徴量探索、IC 計算）
- AI 支援（ニュース NLP によるセンチメント評価、レジーム判定）
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポートなど）

設計方針の一例：
- 本番口座 API と分析・研究コードを明確に分離
- DB は DuckDB（分析用）と SQLite（監視 / 発注履歴）を併用
- OpenAI など外部 API はキーを環境変数で注入し、失敗時はフェイルセーフ動作を採用

---

## 主な機能一覧

- 環境設定ウィザード：対話式で `.env` を生成 / 更新（python -m kabusys.config_setup）
- 設定検証 CLI：.env / config/*.yaml の整合性チェック（python -m kabusys.validate_config）
- Execution 起動スクリプト：本番/ペーパートレード切替・PID / stop フラグ対応（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、data/paper_trading.db に記録
- Monitoring 起動スクリプト：SystemMonitor をポーリング（MONITOR_POLL_INTERVAL で間隔指定可）（python -m kabusys.run_monitoring）
- Monitoring コンポーネント：
  - SystemMonitor（CPU/メモリ/Disk、データ鮮度、プロセス存在チェック）
  - TradeMonitor（滞留注文や異常約定検出）
  - RiskMonitor（ドローダウン・ポジション上限の監視）
  - KillSwitch（条件に応じて data/kill.flag を書き込み Execution を停止させる）
  - MonitoringDB（SQLite 経由でログ永続化）
- ポートフォリオ構築ユーティリティ：
  - 候補選定（スコア / ランクベース）
  - 重み計算（等配分・スコア加重）
  - ポジションサイズ計算（リスクベース・ロット丸め・aggregate cap）
  - セクター上限とレジーム乗数
- リサーチ：
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー
- AI：
  - news_nlp.score_news: raw_news を集約して OpenAI に送り、銘柄ごとにセンチメントを ai_scores に書き込み
  - regime_detector.score_regime: ETF MA とマクロセンチメントを合成して market_regime を更新
- 運用ツール：
  - tools.paper_verification_report: ペーパートレード DB を集計し PASS/FAIL レポートを生成

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（例: requirements.txt がある場合）
   ```bash
   pip install -r requirements.txt
   ```
   主要な依存例：
   - duckdb
   - psutil
   - openai
   - PyYAML（config YAML 検証に任意）
   - その他（プロジェクトにより追加）

   ※ SQLite は標準ライブラリで提供されます。

4. 環境変数（.env）を作成
   対話式ウィザードで推奨：
   ```bash
   python -m kabusys.config_setup
   ```
   重要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN : J-Quants API のリフレッシュトークン
   - KABU_API_PASSWORD      : kabuステーション API パスワード

   よく使う任意 / 推奨設定例：
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
   - DUCKDB_PATH — デフォルト data/kabusys.duckdb
   - SQLITE_PATH — デフォルト data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH — デフォルト data/paper_trading.db
   - OPENAI_API_KEY — OpenAI API を使う機能で必要
   - LOG_LEVEL — (DEBUG/INFO/...)
   - LOG_DIR — デフォルト logs/

   自動ロードについて：
   - 起動時、プロジェクトルートに .env/.env.local があれば自動的に読み込まれます。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（主要コマンド）

- 設定ウィザード（.env の作成・更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証（.env と config/*.yaml のチェック）
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict   # 警告も FAIL 扱い
  ```

- Execution エンジン起動
  ```bash
  python -m kabusys.run_execution
  ```
  挙動のポイント：
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 実行中に stop フラグが作られるとエンジンが停止します。
  - PID ファイルは Settings.pid_file_path（デフォルト data/execution.pid）に出力されます。

- Monitoring 起動（ポーリング）
  ```bash
  # デフォルトポーリング間隔は 60 秒。環境変数で上書き可能:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  挙動のポイント：
  - MONITOR_POLL_INTERVAL 環境変数で間隔（秒）を指定できます（整数、1 秒以上）。不正値の場合は 60 秒にフォールバックします。
  - 停止はプロジェクトルートの data/stop_requested.flag（run_monitoring の _STOP_FLAG）で検出されます。

- ペーパートレード検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB ファイル指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```
  出力は標準出力のテキストレポート（PASS/FAIL 判定や各種指標）です。

- AI / プログラム的な利用例（ライブラリ API）
  - ニュースのスコアリング（DuckDB 接続が必要）
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, target_date=date(2026, 4, 11), api_key="sk-...")
    ```
  - レジーム判定
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 4, 11), api_key="sk-...")
    ```
  - リサーチ / ファクター計算
    ```python
    from datetime import date
    import duckdb
    from kabusys.research import calc_momentum

    conn = duckdb.connect("data/kabusys.duckdb")
    records = calc_momentum(conn, target_date=date(2026,4,11))
    ```

---

## ログ・ファイル配置（デフォルト）

- SQLite（監視 / 発注履歴）
  - monitoring DB: data/monitoring.db（Settings.sqlite_path）
  - paper trading DB: data/paper_trading.db（Settings.paper_sqlite_path）
- DuckDB（分析用）: data/kabusys.duckdb（Settings.duckdb_path）
- ログファイル: logs/<app_name>.log（デフォルト daily ローテーション、30 日保持）
  - app_name 例: execution, monitoring
- フラグ / PID ファイル:
  - 止めるためのファイル: data/stop_requested.flag（起動スクリプトで参照）
  - Kill Switch フラグ: data/kill.flag（Execution を停止するために monitoring が書き込む）
  - Execution PID: data/execution.pid（デフォルト）

注意: .env は絶対に Git にコミットしないでください（config_setup でも注意書きあり）。

---

## 環境変数一覧（主なもの）

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API 用

運用 / 動作に影響するもの
- KABUSYS_ENV — execution のモード（development / paper_trading / live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ保存ディレクトリ
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY — OpenAI を利用する機能で必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込み抑止（1=無効）

---

## ディレクトリ構成（主要ファイル／モジュール）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py           — .env ウィザード（対話式）
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート generator
  - utils/
    - logging_setup.py        — 共通ログ設定（stdout + 日次ファイルローテーション）
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ初期化 + DB 操作ラッパー
    - system_monitor.py       — システム健全性・データ鮮度監視
    - trade_monitor.py        — （取引監視。コード参照）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — Kill Switch（flag ファイル書き込み）
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — （アラート送信管理。コード内参照）
  - execution/
    - execution_engine.py     — ExecutionEngine（セッション管理）
    - order_manager.py        — 発注管理
    - order_repository.py     — 発注履歴操作
    - broker_factory.py       — ブローカークライアント生成（Mock 対応）
    - reconciler.py           — 注文とポジションの整合処理
    - risk_manager.py         — 発注前リスクチェック
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数計算・ロット丸め・aggregate cap
    - risk_adjustment.py      — セクター上限・レジーム乗数
  - research/
    - factor_research.py      — ファクター計算（モメンタム・バリュー等）
    - feature_exploration.py  — IC / forward returns / 統計
  - ai/
    - news_nlp.py             — ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py      — ETF MA + マクロセンチメントで市場レジーム判定

（注）上記は主要ファイルの抜粋です。細かい補助モジュールや未表示のファイルも含まれます。

---

## 運用上の注意

- .env を含む機密情報は決して公開リポジトリにコミットしないでください。
- KABUSYS_ENV=live の設定は本番発注につながります。設定（API パスワード・LINE 通知等）を慎重に確認してください。validate_config は本番時のガードを含みます。
- OpenAI など外部 API 呼び出しは料金やレート制限の影響を受けます。API キーの取り扱いに注意してください。
- Monitoring により発生した Kill Switch は data/kill.flag を生成します。実運用での自動クリア設定（KILL_FLAG_CLEAR_ON_START）は本番では避けることを推奨します。
- ロギングは stdout と logs/ に出力されます。ログディレクトリ作成に失敗した場合はコンソールのみで継続します。

---

## よくある操作フロー（例）

1. .env を作成
   ```bash
   python -m kabusys.config_setup
   ```

2. 設定を検証
   ```bash
   python -m kabusys.validate_config
   ```

3. 分析用 DB（DuckDB）にデータをロード（本リポジトリ側に ETL スクリプトがある場合はそちらを実行）

4. Monitoring を起動（別プロセス）
   ```bash
   MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
   ```

5. Execution を起動（別プロセス）
   ```bash
   python -m kabusys.run_execution
   ```

6. ペーパートレードの検証レポートを生成
   ```bash
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```

---

必要なら README に含めるコマンドの詳細・API ドキュメントの自動生成・サンプル .env のテンプレートなども追加できます。どの情報を優先して追加しますか？