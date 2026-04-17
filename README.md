# KabuSys

日本株自動売買システムのコードベース。取引実行、監視、ポートフォリオ構築、リサーチ、AI（ニュース/レジーム判定）などを含むモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は以下を目的とした小規模自動売買フレームワークです。

- 注文の発行・状態管理（ExecutionEngine / OrderManager）
- 実行結果のリコンシリエーション（Reconciler）
- システム稼働・注文異常・リスク監視（MonitoringEngine と複数の Monitor）
- ポートフォリオ構築・ポジション配分・リスク調整（portfolio）
- ファクター計算・特徴量探索（research）
- ニュースを LLM でスコアリング / 市場レジーム判定（ai）
- 運用補助ツール（paper trading の検証レポート等）
- 環境設定管理（config）

設計方針の特徴：
- DuckDB / SQLite を用いたローカル DB 中心の処理（外部取引所へのアクセスは BrokerClient 経由）
- Paper Trading モードは本番 DB と完全分離（デフォルトで `data/paper_trading.db`）
- LLM 呼び出しは失敗耐性（リトライやフォールバック）を持つ
- ルックアヘッドバイアスを避けるよう日時参照を扱う

---

## 機能一覧（主な機能）

- Execution
  - OrderManager: 注文作成・重複チェック・ブローカー送信ロジック
  - Reconciler: 再起動時の注文・ポジション突合
  - ExecutionEngine: 実行セッションの起動（run_execution.py）

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス PID / データ鮮度監視
  - TradeMonitor: 滞留注文 / 約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限監視、dashboard 更新
  - KillSwitch: 条件により `data/kill.flag` を書き込み ExecutionEngine を停止
  - AlertManager: LINE Push による通知（クールダウン管理）
  - streamlit_dashboard: 監視ダッシュボードの可視化

- Portfolio
  - 候補選定（select_candidates）
  - 重み算出（等分配 / スコア加重）
  - セクター制約適用
  - ポジションサイズ算出（リスクベース / 等分配 等）

- Research
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算・IC 評価・統計サマリ

- AI
  - news_nlp.score_news: raw_news を集約して OpenAI に投げ、銘柄ごとに ai_scores を保存
  - regime_detector.score_regime: ETF MA200 偏差と LLM マクロ感情を合成して日次レジーム判定

- ツール
  - paper_verification_report: Paper Trading DB を集計して PASS/FAIL 判定のレポート出力

- ユーティリティ
  - config: .env 自動ロード、設定インターフェース（Settings クラス）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順

前提
- Python 3.9+（typing 機能を多用しているため 3.9 以降を想定）
- OS: Linux / macOS / Windows（大半の機能はクロスプラットフォームだが process priority / cpu affinity の扱いに差分あり）

1. リポジトリをクローンして開く
   - git clone ...（省略）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - pip install -r requirements.txt
   （requirements.txt が無い場合は主な依存を個別に）
   - pip install duckdb psutil requests openai streamlit

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動ロードされます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1`で無効化可）。
   - 主な（必須）環境変数例:
     - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
     - KABUSYS_ENV — 環境: development | paper_trading | live （デフォルト: development）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE — paper trading の fill 動作（instant|partial|never|reject、デフォルト instant）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
     - SQLITE_PATH, DUCKDB_PATH — 監視 / analytics DB のパス（デフォルト: data/monitoring.db, data/kabusys.duckdb）

5. データディレクトリ作成
   - mkdir -p data

初期化は各起動スクリプト（run_monitoring.py / run_execution.py）が必要なテーブルを作成します（init_monitoring_db を実行）。

---

## 使い方

以下は代表的なコマンド例です。プロジェクトルートから実行してください。

1. 監視ループ起動（Monitoring）
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（秒、デフォルト 60）
   - python -m kabusys.run_monitoring
   - 特徴:
     - 常に本番用の sqlite_path（Settings.sqlite_path）を使って監視テーブルを操作します。
     - 停止するにはプロジェクトルートの `data/stop_requested.flag` を作成するか Ctrl+C。

2. 実行エンジン起動（ExecutionEngine）
   - python -m kabusys.run_execution
   - 特徴:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に記録します。本番 DB と完全分離されます。
     - 実行中に停止させるには `data/stop_requested.flag` を作成するか、監視側から `data/kill.flag` を書き込む（KillSwitch）。
     - 起動時に `data/kill.flag` が既にある場合は起動を中止します。

3. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - `--db` オプションで DB パス指定可。環境変数 `PAPER_TRADING_SQLITE_PATH` でも指定できます。

4. Streamlit ダッシュボード（監視）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

5. AI 機能（ニューススコア / レジーム判定）
   - DuckDB 接続を用いてスクリプトやスケジューラから呼び出します。
   - news_nlp.score_news(conn, target_date, api_key=None)
     - api_key 未指定時は環境変数 OPENAI_API_KEY を参照
   - regime_detector.score_regime(conn, target_date, api_key=None)
   - 注意: OpenAI API キーが必要。API 呼び出しはリトライやフォールバックを実装していますが、API 制限やコストに注意してください。

6. 停止 / 強制停止フラグ
   - ExecutionEngine の安全停止: `data/stop_requested.flag`
   - KillSwitch による停止（監視が条件を満たすと `data/kill.flag` を生成）
   - `KillSwitch.clear()` を呼ぶかファイルを削除してクリア

---

## 設定（Settings）に関するメモ

- Settings クラスは環境変数から各種設定を読み込みます。`settings = Settings()` で利用可能。
- 自動 .env 読み込み
  - プロジェクトルートの .env / .env.local を自動的に読み込みます（OS 環境変数が優先）。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 主なプロパティ例
  - settings.env (development | paper_trading | live)
  - settings.sqlite_path, settings.duckdb_path, settings.paper_sqlite_path
  - settings.paper_fill_mode (instant | partial | never | reject)
  - settings.pid_file_path, settings.kill_flag_path

---

## ディレクトリ構成（主要ファイルと役割）

（`src/kabusys` を基準。簡易ツリー）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / Settings 管理
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト

  - execution/
    - execution_engine.py — 実行エンジン本体（起動・セッション管理）
    - order_manager.py — 注文作成・ブローカー送信の高レベル API
    - order_repository.py — DB への注文保存・取得
    - order_record.py — 注文状態定義（OrderState 等）
    - reconciler.py — 再起動時の同期 / ポジション照合
    - broker_factory.py, broker_api.py — ブローカークライアント抽象、Mock 実装等

  - monitoring/
    - monitoring_db.py — SQLite ベースの監視ログ永続化 / API
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - system_monitor.py — システム / データ鮮度監視
    - trade_monitor.py — 注文滞留 / 約定異常検出
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — 停止フラグ制御
    - alert_manager.py — LINE 通知
    - streamlit_dashboard.py — Streamlit ベースのダッシュボード

  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 発注株数・スケーリングロジック
    - risk_adjustment.py — セクター制限・レジーム乗数

  - research/
    - factor_research.py — momentum/volatility/value 計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ

  - ai/
    - news_nlp.py — ニュース記事を LLM でスコアリングし ai_scores に書込
    - regime_detector.py — ETF MA200 とマクロセンチメントで市場レジーム判定

  - tools/
    - paper_verification_report.py — Paper Trading DB の検証レポート出力

  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- data/
  - デフォルト DB やフラグファイルを配置（`data/monitoring.db`、`data/kabusys.duckdb`、`data/paper_trading.db`、`data/kill.flag`、`data/stop_requested.flag` 等）

---

## 開発 / テストのヒント

- ローカル開発で LLM / ブローカーを避けたい場合は以下を活用
  - KABUSYS_ENV=paper_trading を使うと Mock Broker が利用され、paper DB に書き込みます。
  - AI 呼び出しをテストしたい場合は `_call_openai_api` を unittest.mock.patch で差し替え可能（news_nlp.py / regime_detector.py にて想定）。
- DB のスキーマは monitoring_db.init_monitoring_db が冪等的に作成・マイグレーションを行います。
- streamlit ダッシュボードは読み取り専用で `?mode=ro` を使って接続しています（ファイルロック回避）。

---

## よく使う環境変数（まとめ）

- KABUSYS_ENV (development|paper_trading|live)
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- OPENAI_API_KEY
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (instant|partial|never|reject)
- SQLITE_PATH (監視用 SQLite、デフォルト data/monitoring.db)
- DUCKDB_PATH (analytics DB、デフォルト data/kabusys.duckdb)
- MONITOR_POLL_INTERVAL (監視ポーリング秒数、デフォルト 60)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 （自動 .env 読み込みを無効化）

---

必要であれば README に含める内容（運用手順、cron / systemd サービス定義例、Dockerfile、さらなる API ドキュメント等）を追記できます。どの項目を優先して詳述しますか？