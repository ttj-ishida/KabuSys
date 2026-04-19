# KabuSys

日本株向け自動売買システムのリポジトリ（簡易 README 日本語版）。

この README はソースツリー内のモジュール実装に基づき作成しています。実行スクリプト、設定ウィザード、監視・レポート・AI 判定などが含まれます。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したシステム群です。主要な機能群は以下のとおりです。

- Execution Engine：発注ロジック・リスク管理・注文管理（kabuステーションやモックブローカーに接続）
- Monitoring：システム稼働状況・データ鮮度・リスクを監視し、アラートや Kill Switch を発動
- Portfolio Construction：銘柄選定・重みづけ・株数決定・リスク調整用の純粋関数群
- Research：ファクター計算・特徴量探索・IC 計算などの研究用モジュール（DuckDB を使用）
- AI モジュール：ニュースの NLP によるセンチメント評価、マクロセンチメントとETF指標による市場レジーム判定
- CLI ユーティリティ：.env ウィザード（config_setup）、設定検証（validate_config）、Paper Trading 検証レポート生成ツール

主に DuckDB（分析データ）、SQLite（監視・ペーパートレード DB）、OpenAI API（ニュース評価）を利用します。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py：ExecutionEngine を起動（KABUSYS_ENV により paper_trading / live / development を切替）
  - run_monitoring.py：SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可能）
- 設定関連
  - config_setup.py：対話式に .env を生成・更新
  - validate_config.py：起動前の環境変数・設定ファイル検証（--strict あり）
- 監視
  - monitoring_engine / SystemMonitor / TradeMonitor / RiskMonitor：DB へログ記録・Kill Switch 判定・アラート通知
  - monitoring_db：SQLite スキーマ初期化・永続化 API
- Portfolio（純粋関数）
  - 銘柄選定、等比・スコア重み、ポジションサイズ計算、セクター上限適用、レジーム乗数
- Research（DuckDB）
  - モメンタム / ボラティリティ / バリューなどのファクター計算、将来リターン、IC、統計サマリ
- AI
  - news_nlp: OpenAI を用いたニュースセンチメントスコア化（ai_scores へ格納）
  - regime_detector: ETF とマクロニュースの組合せで market_regime を判定・保存
- ツール
  - tools/paper_verification_report.py：Paper Trading の検証レポート作成（稼働率・約定率・レイテンシ等）

---

## セットアップ手順

前提：Python 3.9+（DuckDB / openai / psutil 等が動く環境）

1. リポジトリをクローン
   - git clone <repo>
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS/Linux
   - .venv\Scripts\activate     # Windows
3. 必要パッケージをインストール
   - 推奨パッケージ（最低限）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config ファイル検証に必要）
   - 例:
     - pip install duckdb psutil openai pyyaml
4. .env の用意
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参照）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN（J-Quants API）
     - KABU_API_PASSWORD（kabuステーション API）
   - OpenAI を使う場合:
     - OPENAI_API_KEY を設定（AI 関連機能で必要）
5. 設定検証
   - python -m kabusys.validate_config
   - 問題がある場合は --strict を付けると警告も失敗扱い
6. データディレクトリ
   - デフォルトの DB / ログ / PID / フラグのディレクトリは `data/` / `logs/`
   - 実行前にディレクトリが自動作成されますが、権限や配置を確認してください。

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時に使用、デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログディレクトリ（デフォルト: logs）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

（config_setup.py を使うと主要項目を対話式でセットできます）

---

## 使い方

### .env を作る / 更新する
- python -m kabusys.config_setup
  - 対話に従って .env を作成・上書きします。

### 設定検証
- python -m kabusys.validate_config
  - --strict をつけると警告があると exit(1)

### Execution Engine を起動
- ローカルテスト（development / paper_trading / live に応じて DB・ブローカーが切替）
- 例（直接実行）:
  - python -m kabusys.run_execution
- 注意:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します（本番 DB と分離）
  - 起動時に data/stop_requested.flag が存在するとエンジンは起動しません
  - 実行中は data/execution.pid が使われます

### Monitoring を起動
- 例:
  - python -m kabusys.run_monitoring
- オプション:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
- 停止:
  - data/stop_requested.flag を作成すると監視ループが終了します

### Kill Switch（外部からの停止指示）
- KillSwitch は data/kill.flag を作成して Execution の停止をトリガーします
- kill.flag を明示的に削除するには:
  - 実行中または起動時に設定次第で自動クリアされます（KILL_FLAG_CLEAR_ON_START=1 で自動クリア）

### Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- デフォルト DB: data/paper_trading.db。--db で別パス指定可能。
- レポートは稼働率・約定率・送信率・レイテンシ指標を出力し PASS/FAIL を判定します

### AI 機能
- ニュース NLP（score_news）やレジーム判定（score_regime）は OpenAI API を利用します。OPENAI_API_KEY を設定してください
- 実行例（モジュール関数経由／スクリプト化して使う想定）:
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

---

## 運用上の注意 / ベストプラクティス

- KABUSYS_ENV を production（live）に設定する際は十分に検証を行ってください（validate_config により注意喚起あり）
- 本番での DB パスやログパスはサーバ要件に合わせて設定してください
- OpenAI を使用する場合、API 料金・レート制限に注意。AI 呼び出しはバッチ化／リトライロジックが実装されていますが、実運用では更なる制御を推奨
- ログはデフォルトで logs/<app_name>.log（日時ローテーション）に出力されます
- stop flag / kill flag を用いた停止は冪等性を考慮して実装されています。手動でフラグを操作する場合は注意してください

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ポーリング起動スクリプト
  - config.py                   — Settings クラス（環境変数読み込み）
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 設定検証ツール
  - utils/
    - logging_setup.py          — ログ設定ユーティリティ
    - process_priority.py       — プロセス優先度 / affinity 設定
  - execution/                   — 発注・オーダー関連（Engine, RiskManager 等）
  - monitoring/
    - monitoring_db.py          — SQLite スキーマ + 永続化 API
    - system_monitor.py
    - monitoring_engine.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (アラート送信)
    - trade_monitor.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py        — レジーム判定（ETF + マクロニュース）
  - data/                       — デフォルトの DB / PID / flag を置く想定（例: data/*.db, data/*.flag）
  - tools/
    - paper_verification_report.py

※ 上記は主要モジュールの抜粋です。実際の詳細実装は各ファイルを参照してください。

---

## 依存関係（参考）

- duckdb
- psutil
- openai
- PyYAML（設定ファイル検証に必要、なければ YAML 検証をスキップ）
- 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib, json, math など

インストール例:
- pip install duckdb psutil openai pyyaml

---

## よくあるコマンドまとめ

- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

もし README の内容に追加したい実行例（systemd ユニット、Dockerfile、CI 設定など）があれば、その目的に合わせたサンプルを用意します。