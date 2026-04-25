# KabuSys

日本株向け自動売買システムのコードベース。戦略・ポートフォリオ構築、発注エンジン、監視・アラート、AI を使ったニュース NLP / レジーム検出、研究用ユーティリティ等を含むモジュール群です。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の役割を持つコンポーネント群から構成されます。

- 発注実行エンジン（ExecutionEngine）
  - 本番／ペーパートレードを切り替え可能。発注・オーダー管理・リスク管理・再整合（reconciler）を担います。
- 監視コンポーネント（Monitoring）
  - システム状態、注文状態、リスク監視、Kill Switch（停止フラグ）の評価とログ永続化（SQLite）。
- ポートフォリオ構築ライブラリ
  - 候補選定、重み計算、ポジションサイズ計算、セクターキャップやレジーム乗数などの純粋関数群。
- リサーチ（research）
  - DuckDB 上の価格・財務データを参照してファクター計算・特徴量解析（Momentum / Volatility / Value 等）。
- AI モジュール
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）。
- ユーティリティ
  - ロギング設定、プロセス優先度設定、設定ウィザードと検証 CLI、運用用ツール（Paper Trading 検証レポート）など。

設計のポイント:
- 本番 DB / ペーパートレード DB を分離（paper_trading モード）。
- DuckDB を分析向けに使用、SQLite を運用ログ（monitoring / trade_logs / positions）用に使用。
- LLM/API 呼び出しはリトライやフォールバックを実装し、失敗時もシステム継続を優先。

---

## 主な機能一覧

- Execution
  - ブローカークライアント抽象化（本番 / Mock）
  - OrderManager / RiskManager / Reconciler を含む発注フロー
  - PID / 停止フラグによる制御
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク/プロセス検知、データ鮮度検査）
  - TradeMonitor（滞留注文・約定異常検出）
  - RiskMonitor（ドローダウン・ポジション上限検出）
  - KillSwitch（条件により data/kill.flag を書き込み、ExecutionEngine を停止）
  - Monitoring DB（SQLite）による永続化とマイグレーション対応
- Portfolio construction
  - 候補選定、等金額 / スコア加重、リスクベースの株数計算、セクターキャップ、レジーム乗数
- Research
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー
- AI
  - ニュース記事の銘柄別センチメントスコア化（OpenAI）
  - マクロニュース + 指標からの市場レジーム判定
- ツール
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト

---

## 要件（代表）

（プロジェクトに requirements.txt がない場合の代表的な依存例）
- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config 検査はオプション）
- sqlite3（Python 標準）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順（クイックスタート）

1. リポジトリを取得して作業ディレクトリをプロジェクトルートにする。
2. 仮想環境を作成し依存ライブラリをインストール（上記参照）。
3. ディレクトリ作成:
   - data/ と logs/ を作成（多くのコードは自動作成しますが事前作成しておくと安心）。
   ```
   mkdir -p data logs
   ```
4. .env の初期作成:
   - 対話式ウィザード（推奨）:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは .env.example を参考に `.env` を作成（.env は絶対に Git にコミットしないこと）。
5. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   - 必須環境変数や config/*.yaml の存在・パスなどをチェックします。
   - `--strict` を付けると警告も失敗として扱い exit(1) になります。
6. DB 初期化は起動スクリプトが行います（monitoring 実行時に init_monitoring_db が呼ばれます）。

---

## 主要な環境変数（抜粋）

注: デフォルト値や説明はコード内 Settings / config_setup のコメントを参照してください。主なもの:

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

セキュリティ:
- .env に API キー / パスワード等を保存する場合は Git に含めないでください。

---

## 実行方法（代表コマンド）

- 設定ウィザード（.env の作成・更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine 起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading に設定すると MockBrokerClient を使用し、ペーパートレード用 DB（data/paper_trading.db）へ記録します。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 実行中は data/execution.pid に PID が書き込まれます（設定で変更可）。

- Monitoring 起動（監視ループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒数で上書き可能（デフォルト 60）。
  - 監視は常に本番用の sqlite_path を使用します（環境にかかわらず）。
  - 停止はプロジェクトルート/data/stop_requested.flag を作成することで行えます。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - オプションで --db に SQLite ファイルを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能）。

- ライブラリ関数の利用（例）
  - リサーチ:
    from kabusys.research import calc_momentum, calc_volatility, calc_value
  - AI:
    from kabusys.ai import score_news
    score_news(duckdb_conn, target_date, api_key="...")

---

## 停止 / Kill Switch

- 手動停止:
  - プロジェクトルートの `data/stop_requested.flag` を作成すると、run_monitoring / run_execution は次のループまでに検知して安全に停止します。
- 自動停止（Kill Switch）:
  - Monitoring の評価結果により `data/kill.flag` が書き込まれます。ExecutionEngine 起動時の `KILL_FLAG_CLEAR_ON_START` により起動時に自動クリアするか制御します（本番では 0 推奨）。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — 共通ロギング設定
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成 / 永続化 API
    - system_monitor.py
    - trade_monitor.py       — （この要約では詳細省略）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信ロジック）
  - execution/
    - execution_engine.py    — ExecutionEngine 実装（起動時に run_session を開始）
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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

（実際のファイル一覧はリポジトリを参照してください）

---

## 開発・運用上の注意

- .env は機密情報を含むため必ず .gitignore に入れて管理してください。
- KABUSYS_ENV が `live` の場合は特に注意して設定を確認してください（validate_config でも警告が出ます）。
- AI 機能は OpenAI API キーが必要です。また大量 API 呼び出しはコストが発生するため運用方針を定めてください。
- ペーパートレードは本番 DB と分離されていますが、設定ミスに注意してください（PAPER_TRADING_SQLITE_PATH）。
- ロギングは logs/<app_name>.log に日次ローテーションで出力されます（デフォルト 30 日保存）。
- DuckDB のテーブルスキーマ（prices_daily, raw_financials, raw_news など）はリサーチ/AI モジュールが前提とするため、テーブル定義に注意してください。

---

必要であれば README をさらに詳しいセットアップ手順（Docker/CI、requirements.txt、サンプル .env テンプレート、起動スクリプト systemd ユニット例 など）に拡張できます。どの項目を充実させたいか教えてください。