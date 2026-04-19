# KabuSys

日本株自動売買システム（KabuSys）のコードベース README（日本語）

概要、主な機能、セットアップ・起動手順、使い方、ディレクトリ構成をまとめています。

注意: この README は src/kabusys 以下の実装に基づいて作成しています。実運用前に必ず `python -m kabusys.validate_config` などで設定検証を行ってください。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主な役割は次の通りです。

- 発注系の ExecutionEngine（本番 / ペーパートレード対応）
- システム監視とアラート（Monitoring）
- ポートフォリオ構築（候補選定、重み付け、ポジション決定）
- リサーチ（ファクター計算、特徴量探索）
- AI 補助（ニュースのセンチメント解析／レジーム判定、OpenAI 利用）
- 設定ウィザード・設定検証ツール
- 運用補助ツール（Paper Trading 検証レポート等）

設計上の特徴:
- ペーパートレード用 DB と本番 DB を分離（KABUSYS_ENV による切替）
- DuckDB を分析用に、SQLite を監視/トランザクションログ用に利用
- OpenAI（gpt-4o-mini 等）との連携によるニュース解析（任意）
- kill.flag 等のフラグファイルで実行系の安全停止を制御
- ロギング、プロセス優先度設定など運用を考慮したユーティリティを同梱

---

## 主な機能一覧

- 設定管理
  - .env の対話式作成/更新: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config

- 実行 / 監視
  - 実行エンジン起動スクリプト: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 専用 DB に記録
  - 監視ループ起動スクリプト: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
    - 停止制御: data/stop_requested.flag（監視プロセスの停止）、data/kill.flag（Execution 停止トリガ）
  - MonitoringEngine により System / Trade / Risk モニタを連携しアラートや Kill Switch を評価

- ポートフォリオ構築（純粋関数群）
  - 候補選定、等金額/スコア加重の重み計算
  - セクター上限フィルタ、レジームに基づく乗数
  - 株数決定（単元株丸め、リスクベース / equal / score 配分）
  - これらは DB を直接参照せず、メモリ計算のみで使いやすく設計

- リサーチ / 分析
  - ファクター計算（Momentum/Volatility/Value 等）: DuckDB を利用して prices_daily 等から算出
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI（オプショナル）
  - ニュース NLP による銘柄センチメント（ai_scores への書込み）
    - OpenAI API を使用（OPENAI_API_KEY 必須）
    - バッチ送信、レスポンス検証、リトライ、結果クリッピング等を実装
  - 市場レジーム判定（ETF ma200 乖離 + マクロニュースセンチメントの合成）

- 運用ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
    - 注文成功率・レイテンシ・稼働率などを集計し PASS/FAIL を出力

---

## 必要環境 / 依存パッケージ

推奨 Python バージョン: 3.10 以上（PEP 604 の型記法 `X | Y` を使用しているため）

主な依存パッケージ:
- duckdb
- psutil
- openai
- PyYAML（config YAML 検証を行う場合に必要）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（実際の requirements.txt はプロジェクトに合わせて用意してください）

標準ライブラリ: sqlite3, logging, threading, datetime, pathlib 等

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意/設定系:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — 監視 DB（data/monitoring.db デフォルト）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（data/paper_trading.db）
- PAPER_FILL_MODE — ペーパー注文の約定モード（instant|partial|never|reject）
- OPENAI_API_KEY — AI 機能に必要
- LOG_LEVEL — ログレベル（DEBUG/INFO/…）
- LOG_DIR — ログ保存先（デフォルト logs/）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒。run_monitoring 用）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等

設定補助:
- `python -m kabusys.config_setup` で .env を対話式に生成できます
- `python -m kabusys.validate_config` で設定を検証できます

---

## セットアップ手順（開発 / ローカル実行向けの基本）

1. リポジトリをクローンし、作業ディレクトリへ移動
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml
4. .env の作成（対話式）
   - python -m kabusys.config_setup
   - 必須キー（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を設定する
5. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば修正
6. 必要なディレクトリを作成
   - デフォルトで data/ と logs/ を使用します。config に応じて作成してください。
   - 例: mkdir -p data logs
7. （ペーパートレード用）初期 DB ファイルは起動スクリプトが必要に応じて作成/初期化します

---

## 使い方（起動コマンド例）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番 sqlite_path を使います（監視 DB は環境に関係なく同一）

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - ペーパートレードで起動する例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - ペーパートレード時は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH に記録します

- Execution の停止
  - data/stop_requested.flag を作ると監視ループ / 実行スレッドが検知して停止処理を実行します
  - Kill Switch（リスク条件に基づく停止）により data/kill.flag が書かれると Execution 停止を誘発します
  - Execution 実行時の PID は data/execution.pid に保存されます

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）

- AI 機能（プログラムから呼び出す）
  - ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 実行には OPENAI_API_KEY（または api_key 引数）が必要

---

## 運用上の注意 / 実装上のポイント

- 監視用 DB（SQLite）は init_monitoring_db() で必要テーブルを冪等に作成します。スクリプトは起動時に自動で呼び出します。
- run_execution は KABUSYS_ENV=paper_trading によって発注をシミュレートし、本番 DB と完全に分離します。ペーパートレード用 DB のパスは PAPER_TRADING_SQLITE_PATH で指定できます。
- OpenAI 呼び出しはリトライやレスポンス検証を組み込んでいますが、API キー設定やレート制限に注意してください。
- ログは logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- プロセス優先度設定（set_process_priority("high")）を行いますが、権限がない場合は警告が出てスキップされます。
- .env は決してリポジトリにコミットしないでください（config_setup でも明記しています）。

---

## ディレクトリ構成（主要ファイル）

src/
  kabusys/
    __init__.py                     — パッケージ定義
    config.py                       — 環境変数 / 設定管理、自動 .env ロード
    config_setup.py                 — .env 対話式ウィザード
    validate_config.py              — 設定検証 CLI
    run_execution.py                — ExecutionEngine 起動スクリプト
    run_monitoring.py               — SystemMonitor ポーリング起動スクリプト

    utils/
      logging_setup.py              — 統一的なログ設定ユーティリティ
      process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ

    monitoring/
      monitoring_db.py              — SQLite 永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
      system_monitor.py             — システム状態・データ鮮度チェック
      trade_monitor.py              — （参照されるが本稿抜粋になし）取引状態監視
      risk_monitor.py               — ドローダウン・ポジション上限監視
      kill_switch.py                — kill.flag 書き込み / クリア
      monitoring_engine.py          — 各 Monitor を束ねる

    execution/                       — ExecutionEngine 周り（OrderManager, BrokerFactory 等）※抜粋には全ファイルなし
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/
      factor_research.py
      feature_exploration.py
    ai/
      news_nlp.py                    — ニュースセンチメント取得（OpenAI）
      regime_detector.py             — 市場レジーム判定（MA + マクロセンチメント）
    tools/
      paper_verification_report.py   — Paper Trading 検証レポート生成ツール

data/           — 実行時生成: monitoring/DB ファイルや flag ファイル（.gitignore に追加推奨）
logs/           — ログファイル出力先（デフォルト）

---

## 追加リソース / 次のステップ

- .env を作成後、`python -m kabusys.validate_config` を実行して環境に問題がないか確認してください。
- 本番運用時は KABUSYS_ENV=live の設定や LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を入念に確認してください。validate_config は live 時の危険な設定（KILL_FLAG_CLEAR_ON_START=1 など）を警告します。
- OpenAI を有効にする場合、API キーの保管・レート制御・コスト管理に注意してください。

---

質問や README の追加情報（例: サンプル .env、より詳細な起動オプション一覧、CI 設定など）が必要であれば教えてください。必要に応じて例やテンプレートも追加します。