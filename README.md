# KabuSys

日本株向け自動売買システムのモジュール群。ポートフォリオ構築、リスク制御、実行エンジン、監視・アラート、研究用ファクター計算、LLM を使ったニュース分析などを含む設計です。

この README はコードベース（src/kabusys 以下）の使い方・セットアップ・構成を日本語でまとめたものです。

---

## 概要

KabuSys は以下の主要機能を持つモジュール群で構成されています。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理を行う
- 監視（Monitoring）: システム状態・注文履歴・リスクを定期的にチェックしアラートや Kill Switch を管理
- ポートフォリオ構築（portfolio）: 候補選定、重み計算、ポジションサイズ決定、セクター制約など
- 研究（research）: ファクター計算、将来リターン・IC 計算、統計サマリー
- AI（ai）: ニュースの LLM によるセンチメントスコアリング、レジーム判定
- ユーティリティ（utils）: ロギング設定、プロセス優先度設定など
- 各種ツール（tools）: ペーパートレード検証レポート生成など

設計方針の一部:
- 環境変数 / .env による設定管理（自動ロード機能あり）
- DuckDB（分析用）と SQLite（監視・発注ログ）を利用
- Paper Trading（ペーパー口座）と Live（本番）を環境で切替可能
- LLM 呼び出し時はリトライ・バックオフ、レスポンス検証を実装しフェイルセーフ化

---

## 主な機能一覧

- Execution
  - Broker クライアント分離（paper_trading では MockBrokerClient を使用）
  - OrderManager / RiskManager / Reconciler を組合せた実行フロー
  - PID ファイル管理・停止フラグ検出（data/stop_requested.flag, data/execution.pid）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度チェック
  - TradeMonitor: trade_logs の監視（滞留注文・約定異常など）
  - RiskMonitor: ドローダウン・ポジション上限監視、dashboard 更新
  - KillSwitch: 条件で data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: 上記モニタを定期実行しアラート送出
- Portfolio
  - 候補選定、等重/スコア重み、リスクに基づく株数計算、セクター上限適用
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB を用いた SQL）
  - 将来リターン・IC（Spearman）・統計要約
- AI
  - ニュースセンチメント（OpenAI）を銘柄単位で集約し ai_scores に保存
  - レジーム判定（ETF MA + マクロニュースの LLM スコアの合成）
- Tools
  - Paper Trading 検証レポート生成（data/paper_trading.db から指標出力）

---

## セットアップ手順（開発環境）

1. リポジトリをクローン
   - 仮にプロジェクトルートが作成される想定（.git / pyproject.toml がある場所が自動検出の基準）

2. Python 仮想環境の作成と依存関係インストール
   - 推奨: Python 3.10+
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  # Windows: .venv\Scripts\activate
     - pip install -r requirements.txt
   - 依存例（主要）:
     - duckdb, psutil, openai, PyYAML（config 検証で任意）

   ※ requirements.txt がない場合は上記パッケージを個別にインストールしてください。

3. .env の作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは手動で .env を作成（プロジェクトルートに置く）
   - よく使う環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（DEBUG/INFO/...）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - PAPER_FILL_MODE（instant | partial | never | reject） — paper_trading の約定挙動

4. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする strict モード:
     - python -m kabusys.validate_config --strict

5. 初期ディレクトリ
   - 必要に応じて data/ および logs/ ディレクトリが自動作成されますが、権限等で失敗する場合があります。

---

## 使い方（主要な実行コマンド）

- 実行エンジン起動（フォアグラウンド）
  - KABUSYS_ENV によりブローカー・DB が切替
    - 本番（live）: 本番 DB を使用
    - ペーパー（paper_trading）: MockBrokerClient を使用し data/paper_trading.db に記録
  - 例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - KABUSYS_ENV=live python -m kabusys.run_execution

  実行時の注意:
  - data/stop_requested.flag があると起動せず終了（停止フラグ保護）
  - engine は PID ファイル（data/execution.pid）を使用
  - プロセス優先度を高く設定しようと試みます（psutil による設定）

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path を常に使用（環境に依存せず本番 DB を参照する設計）
  - 停止は data/stop_requested.flag を作成（run_monitoring は data/stop_requested.flag を検知して終了）

- .env の対話式作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い: python -m kabusys.validate_config --strict

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ニューススコア / レジーム判定）
  - OPENAI_API_KEY 環境変数を設定して使用
  - モジュール関数:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - DuckDB 接続オブジェクトを渡して呼び出します（直接コマンドライン用エントリは未実装のためスクリプト等から呼ぶ設計）

---

## 設定（主要環境変数）

- KABUSYS_ENV: development | paper_trading | live（default: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（default: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイル（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL: ログレベル（default: INFO）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default: 60）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant/partial/never/reject）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START: 監視 / 停止関連

---

## ログとデータファイル

- ログ: logs/<app_name>.log（TimedRotatingFileHandler による日次ローテーション、30日保持）
- データ:
  - DuckDB: data/kabusys.duckdb（分析用）
  - SQLite（監視）: data/monitoring.db
  - SQLite（paper_trading）: data/paper_trading.db
- 停止フラグ:
  - data/stop_requested.flag — 実行プロセスの停止トリガ（run_execution/run_monitoring が監視）
  - data/kill.flag — KillSwitch が書き込むファイル（ExecutionEngine 停止を要求）

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要なファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/.env の自動読み込み・Settings クラス
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py             — ログ設定ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py             — SQLite テーブル作成・読み書き層
    - system_monitor.py            — システム状態・データ鮮度監視
    - trade_monitor.py             — 注文ログ監視（存在）
    - risk_monitor.py              — ドローダウン/ポジション上限監視
    - kill_switch.py               — kill.flag 管理
    - monitoring_engine.py         — 各 monitor を束ねる
    - alert_manager.py             — アラート送出（存在）
  - execution/
    - execution_engine.py          — 実行エンジン本体（存在）
    - order_manager.py             — 注文管理
    - order_repository.py          — DB 操作
    - risk_manager.py              — 発注リスク管理
    - broker_factory.py            — ブローカークライアント生成
    - reconciler.py                — 執行整合性処理
  - portfolio/
    - portfolio_builder.py         — 候補選定 / 重み計算
    - position_sizing.py           — 株数決定・制約・スケーリング
    - risk_adjustment.py           — セクター上限・レジーム乗数
  - research/
    - factor_research.py           — Momentum / Volatility / Value 等
    - feature_exploration.py       — 将来リターン・IC・統計
  - ai/
    - news_nlp.py                  — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py           — 市場レジーム判定（ETF MA + マクロ LLM）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール

---

## 運用上の注意 / ベストプラクティス

- 本番（KABUSYS_ENV=live）での運用時は .env の内容・LINE 通知設定・Kill Switch 設定を必ず確認してください（validate_config にて注意喚起あり）。
- OpenAI を使う処理は API キー必須・リクエストコストがかかります。使用頻度やバッチサイズを制御してください。
- Paper Trading は本番 DB と完全に分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を設定）。
- ロギングディレクトリ / data ディレクトリの権限に注意。ログが作成できない場合、コンソール出力のみになります。
- process_priority の設定は管理者権限が必要な場合があります。権限不足時は警告を出して継続します。
- kill.flag / stop_requested.flag 等はファイルベースのシンプルな制御ですが、誤操作による停止に注意してください。

---

## 開発者向けメモ

- DuckDB 接続オブジェクトをテストで差し替えれば研究モジュールや AI モジュールの単体テストが可能です。
- OpenAI 呼び出しは内部で _call_openai_api を切り分けているため、単体テスト時はモックを注入してレスポンス制御できます（例: unittest.mock.patch）。
- monitoring_db.init_monitoring_db は冪等でスキーマのマイグレーション（カラム追加）を扱います。既存 DB への変更に注意。

---

必要であれば、README の英語版や、Quick Start（短い起動手順）・運用チェックリスト（デプロイ時チェック項目）も作成します。どの内容を優先して追加しますか？