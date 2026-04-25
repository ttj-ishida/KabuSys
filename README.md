# KabuSys

日本株自動売買システムのモノリポジトリ（ライブラリ＋起動スクリプト群）。  
本リポジトリには発注エンジン、監視、バックテスト／リサーチ用モジュール、LLM を使ったニュース評価などが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株自動売買ワークフローを支える以下の主要機能を持ちます。

- ExecutionEngine（発注／注文管理／リスク管理）
- Monitoring（システム稼働監視、トレード監視、リスク監視、Kill Switch）
- Portfolio 建設（候補選定・重み付け・銘柄ごとの株数算定）
- Research（ファクター計算、特徴量探索、IC 計算等、DuckDB ベース）
- AI モジュール（ニュースのセンチメント評価 / 市場レジーム判定、OpenAI）
- 運用支援ツール（環境設定ウィザード、設定検証、Paper Trading レポート生成）
- ロギング設定・プロセス優先度ユーティリティ等の補助モジュール

設計方針のポイント:
- 本番用と Paper Trading 用に DB を分離（paper_trading 環境では data/paper_trading.db を使用）
- ルックアヘッドバイアスを避ける実装（日時の扱いに注意）
- フェイルセーフ: 外部 API エラー時はスキップやデフォールト値で継続
- .env による環境変数管理 + 対話式ウィザードと検証ツールあり

---

## 主な機能一覧

- Execution
  - Broker クライアント切替（本番 / Mock for paper_trading）
  - OrderManager / RiskManager / Reconciler / ExecutionEngine
  - PID ファイル、stop フラグによる起動制御
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス有無/データ鮮度
  - TradeMonitor: 注文滞留・約定異常検出（trade_logs を参照）
  - RiskMonitor: ドローダウン・ポジション上限検出（dashboard、positions）
  - KillSwitch: 条件成立で data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: 各 Monitor を束ねてポーリング、AlertManager 経由で通知
- Portfolio
  - 候補抽出、等重・スコア重み、セクター上限フィルタ、ポジションサイズ計算
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Spearman）や統計サマリー
  - DuckDB を用いた高速分析
- AI
  - news_nlp: OpenAI を使った銘柄別センチメントスコア算出（ai_scores テーブル更新）
  - regime_detector: ETF とマクロ記事から市場レジーム（bull/neutral/bear）を判定し DB に書き込み
- ツール
  - config_setup: .env を対話式で作成・更新
  - validate_config: .env や config/*.yaml の静的チェック
  - paper_verification_report: Paper Trading の検証レポート生成

---

## 前提 / 必要要件

- Python 3.10 以上（コード内での型ヒントに `|` 演算子等を使用）
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証で YAML を検証したい場合）
- OS: Windows / Linux / macOS に一部対応（プロセス優先度などで差分あり）

インストール例（仮の requirements がない場合）:
```bash
python -m pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 環境を準備（仮想環境推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   pip install duckdb psutil openai PyYAML
   ```

3. .env を作成
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
   - あるいは `.env.example` がある場合はコピーして値を編集（このリポジトリには .env.example が無い可能性があります）。

   必須環境変数（最低限設定が必要）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   主要な環境変数（デフォルト値や説明）
   - KABUSYS_ENV = development | paper_trading | live（デフォルト: development）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE（paper_trading のフィルモード: instant|partial|never|reject）
   - LOG_LEVEL（INFO 等）
   - OPENAI_API_KEY（AI 機能を使う場合）

4. 設定検証（任意）
   ```bash
   python -m kabusys.validate_config        # 警告は表示するが終了コードは 0
   python -m kabusys.validate_config --strict  # 警告も FAIL 扱いで非0終了
   ```

5. データディレクトリの作成（必要に応じて）
   - data/, logs/ 等は自動作成される場合がありますが、手動で作ることも可:
     ```bash
     mkdir -p data logs
     ```

---

## 使い方（起動 / 実行）

- ExecutionEngine（発注エンジン）を起動
  - 通常起動:
    ```bash
    python -m kabusys.run_execution
    ```
  - 動作概要:
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使い、paper_trading 用 SQLite（data/paper_trading.db）に記録します。
    - 起動時に PID ファイル (data/execution.pid) を作成し、data/stop_requested.flag が存在すると起動しません。
    - 停止は data/stop_requested.flag の作成で行います（監視プロセスや手動で作成可能）。

- Monitoring（監視ループ）を起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更できます（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を使用（環境にかかわらず監視用 DB を参照）。
  - 停止は data/stop_requested.flag を出すことで監視ループを終了します。

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB パス: data/paper_trading.db。--db オプションまたは PAPER_TRADING_SQLITE_PATH 環境変数で指定可。

- 環境設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

---

## ライブラリ的な利用例（簡単なスニペット）

- DuckDB 接続を渡してファクター計算:
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  results = calc_momentum(conn, date(2026, 4, 10))
  ```

- OpenAI を使ったニューススコアリング（ai モジュール）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,4,10), api_key="sk-xxx")
  ```

- 市場レジーム判定:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,4,10), api_key="sk-xxx")
  ```

- Portfolio モジュール関数:
  ```python
  from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  ```

---

## 運用・制御ファイル（停止 / Kill Switch）

- data/stop_requested.flag
  - run_execution / run_monitoring が監視している停止フラグ。存在するとループを抜けます（manual stop 用）。
- data/kill.flag
  - KillSwitch が危険検出時に書き込むファイル。ExecutionEngine はこれを検知して安全に停止します。
  - Settings.kill_flag_clear_on_start=1 にすると起動時に自動でクリアされます（本番では 0 推奨）。
- PID ファイル
  - data/execution.pid: ExecutionEngine の PID 保持

注意: これらは単純なファイル存在チェックで制御するため、運用手段（systemd / supervisor 等）との組み合わせで安全に扱ってください。

---

## ログ

- デフォルトのログ出力先: logs/<app_name>.log（日次ローテーション、30 日保持）
- 環境変数
  - LOG_LEVEL（例: INFO、DEBUG）
  - LOG_DIR（ログ保存ディレクトリ）
- 起動スクリプトは共通の logging 設定ユーティリティを利用します（kabusys.utils.logging_setup.setup_logging）。

---

## ディレクトリ構成（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/Settings 管理（.env 自動ロード含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照用)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                      — (運用時に作成される) DB / PID / フラグファイル 等
  - logs/                      — ログ

（リポジトリの全ファイル一覧は src/kabusys 以下を参照してください）

---

## 注意事項 / 運用上のヒント

- .env は決して Git にコミットしないこと（シークレットを含む）。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します。
- Paper Trading と本番 DB は分離されています。paper_trading モードでは paper_sqlite_path を使うため、本番データを上書きする心配は基本的にありません。
- OpenAI API を利用する機能は API キーが必要です（OPENAI_API_KEY または関数引数）。
- psutil の一部 API は権限やプラットフォーム依存で失敗する可能性があるため、ログを確認してください（優先度設定・CPU affinity 等）。
- DuckDB / SQLite のスキーマ変更は init_monitoring_db でマイグレーション処理が行われますが、運用前にバックアップを取ること。

---

## さらに進めること（提案）

- systemd / supervisor などでプロセス管理を行い、ログローテーション・自動再起動を設定する。
- config/*.yaml（戦略・リスク等）のテンプレートを作成し、validate_config でチェックを通すワークフローを確立する。
- モニタリングの AlertManager を LINE や Slack と連携して運用監視を自動化する。
- テストケース（ユニットテスト）を追加して各モジュールの信頼性を高める。

---

この README はコードベースの現状に基づいて作成しています。実際の運用やデプロイ手順は環境に合わせて調整してください。質問や特定モジュールの詳しいドキュメント化が必要であればお知らせください。