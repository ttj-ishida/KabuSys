# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ + 実行スクリプト群）です。本リポジトリは取引実行、監視、ポートフォリオ構築、リサーチ、AI を使ったニュースセンチメントなどの機能を含みます。

---

## プロジェクト概要

KabuSys は以下のような役割を持つモジュール群で構成されています。

- Execution: ブローカークライアントを通じた注文作成・送出、リコンシリエーション（再同期）
- Monitoring: システム稼働状況、注文滞留、ドローダウン等の監視とアラート送出（LINE）
- Portfolio: 候補選定、配分重み計算、単元丸め等のポートフォリオ構築ロジック
- Research: DuckDB を用いたファクター計算・特徴量探索
- AI: OpenAI を用いたニュースセンチメント付与と市場レジーム判定
- Tools: 検証用スクリプト（Paper Trading 検証レポート等）
- Utilities: プロセス優先度設定、設定読み込み等の共通ユーティリティ

本 README はこのコードベースの主要な使い方（セットアップ、実行方法、主要ファイル説明）をまとめたものです。

---

## 主な機能一覧

- SystemMonitor：CPU/メモリ/Disk、Execution プロセスの生存確認、データ鮮度チェック
- TradeMonitor：滞留注文（stale order）、約定価格異常の検出とログ化
- RiskMonitor：ドローダウン監視（ハイウォーターマーク追跡）、ポジション上限監視
- KillSwitch：リスクトリガー時にフラグファイルを書き ExecutionEngine を停止させる
- AlertManager：LINE Messaging API へのプッシュ通知（クールダウン管理）
- ExecutionEngine 起動スクリプト：ブローカー接続、リスク管理、オーダー管理、リコンシリエーションを含む実行エンジン
- MonitoringEngine：複数モニタの統合ループ実行（ポーリング）
- AI モジュール：ニュースをまとめて LLM（gpt-4o-mini）へ投げ、銘柄別スコアを生成して保存
- Research：モメンタム／ボラティリティ／バリュー等のファクター計算、IC 等の統計指標
- Tools：Paper Trading の検証レポート生成スクリプト

---

## 必要要件

- Python 3.9+
- 必須パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- SQLite は標準ライブラリとして利用
- ネットワーク接続（LINE/API/OpenAI を使う場合）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install duckdb psutil requests openai streamlit
```

必要に応じて他の依存（ブローカー専用クライアント等）を追加してください。

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. Python 仮想環境を作成して依存をインストール（上記参照）
3. 環境変数を設定（.env / .env.local をプロジェクトルートに置くことができる）
   - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると無効化
4. データディレクトリの準備（デフォルトは `data/`）
   - デフォルト DB: `data/monitoring.db`（monitoring）、`data/kabusys.duckdb`（DuckDB）
   - PID / フラグ: `data/execution.pid`, `data/kill.flag`
5. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN — J-Quants API（必要な場合）
   - KABU_API_PASSWORD — kabuステーション API パスワード
   - OPENAI_API_KEY — OpenAI API を使う場合
   - KABUSYS_ENV — one of `development`, `paper_trading`, `live`（デフォルト: development）
   - その他は下記の「環境変数一覧」を参照

モニタリング / 実行スクリプト実行時には DB 初期化（テーブル作成）が自動で行われます（冪等）。

---

## 環境変数一覧（代表）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能で使用)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（AlertManager 用）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定振る舞い）
- PID_FILE_PATH（デフォルト: data/execution.pid）
- KILL_FLAG_PATH（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト: 60）
- LOG_LEVEL（DEBUG/INFO/...）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視しきい値）

※ .env/.env.local はプロジェクトルート（.git か pyproject.toml のある場所）から自動読み込みされます（OS 環境変数が優先されます）。

---

## 使い方（実行例）

- 監視ループを起動（Monitoring）:
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒で上書き可能（デフォルト 60）
  - 実行:
    ```bash
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は常にプロダクションの sqlite_path を使用（KABUSYS_ENV に依存せず監視 DB を記録）

- 実行エンジンを起動（Execution）:
  - paper_trading モード（本番とは分離して `data/paper_trading.db` を使用）:
    ```bash
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 本番実行（live）では `KABUSYS_ENV=live`、適切なブローカークレデンシャルが必要

- Streamlit ダッシュボード（監視の可視化）:
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート生成ツール:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```
  または DB パスを環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

注意:
- run_execution は起動時にブローカークライアント生成、OrderRepository、RiskManager、Reconciler 等を組み立て ExecutionEngine を起動します。paper_trading 時は MockBrokerClient を使用して発注結果を専用 DB に記録します（本番 DB と分離）。

---

## 監視 / 停止機構

- pid ファイル: `Settings.pid_file_path`（デフォルト data/execution.pid）に実行中の ExecutionEngine の PID を書きます。SystemMonitor はこの PID を参照してプロセス存否をチェックします。
- kill.flag: `Settings.kill_flag_path`（デフォルト data/kill.flag）を KillSwitch が書き込むことで ExecutionEngine に停止シグナルを送ります。KillSwitch はドローダウンやポジション上限トリガーで書き込みます。ExecutionEngine 側は起動時にフラグクリアや存在チェックの処理を行うことを想定しています（設定: KILL_FLAG_CLEAR_ON_START）。

---

## 開発者向けメモ

- 設定読み込み:
  - .env と .env.local の自動読み込みをサポート（OS 環境変数が保護される）
  - テストや CI 等で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
- DB 初期化:
  - `init_monitoring_db` が監視用 DB のテーブル作成と簡単なマイグレーションを行います。run_* スクリプトで自動実行されます
- テストの際は各モジュールの public 関数を直接インポートしてユニットテストが可能です（AI 呼び出し部は _call_openai_api をモック可能）

---

## ディレクトリ構成（抜粋）

（ルートは `src/kabusys/` 想定）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動読み込み含む）
  - run_monitoring.py — SystemMonitor のポーリング起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite 永続化層（system_status/trade_logs/positions/risk_logs/dashboard）
    - system_monitor.py — CPU/メモリ/Disk、Execution PID、データ鮮度チェック
    - trade_monitor.py — 滞留注文・約定異常チェック
    - risk_monitor.py — ドローダウン／ポジション数監視（ハイウォーターマーク管理）
    - kill_switch.py — kill.flag 書き込みロジック
    - alert_manager.py — LINE への通知送信
    - monitoring_engine.py — 各 Monitor を束ねるループ
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py — 注文状態遷移 / send 発行等の外向き API
    - reconciler.py — 起動時のリコンシリエーション（注文・ポジション突合）
    - order_repository.py, order_record.py, broker_factory.py ...（注文関連）
    - execution_engine.py, risk_manager.py ...（実行・リスク管理）
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - risk_adjustment.py — セクター上限、レジーム乗数
    - position_sizing.py — 発注株数計算、単元丸め、aggregate cap
  - research/
    - factor_research.py — momentum/value/volatility 等ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリ等
  - ai/
    - news_nlp.py — ニュース集約・OpenAI で銘柄別センチメントを作成して ai_scores に書込
    - regime_detector.py — ETF MA とマクロニュースで市場レジーム判定、market_regime 書込
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

（上記は主要ファイルの抜粋です。細部の実装や追加モジュールはソースを参照してください。）

---

## よくある運用フロー（例）

1. データパイプラインで DuckDB（prices_daily / raw_financials / raw_news 等）を更新
2. 毎朝 regime_detector を実行して market_regime を更新（OpenAI キーが必要）
3. ExecutionEngine を起動（live / paper_trading）
4. MonitoringEngine（run_monitoring）を常時稼働させて system/trade/risk を監視
5. 異常時は LINE に通知、重大リスク時は kill.flag が書き込まれ ExecutionEngine 停止

---

## トラブルシュート

- DB が見つからない / ロックできない:
  - デフォルトパスは `data/monitoring.db`。権限やパスを確認してください。
  - Streamlit は read-only URI で開くため、DB が存在しないとエラー表示されます。
- OpenAI / LINE API 呼び出しに失敗する:
  - 環境変数（OPENAI_API_KEY, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）を確認
  - ネットワーク・レート制限はモジュール側でリトライ・フォールバック処理あり
- PID / kill.flag 関連:
  - stale PID ファイルは SystemMonitor により検出・削除され、risk_log に記録されます
  - 起動時に kill.flag をクリアしたい場合は `KILL_FLAG_CLEAR_ON_START=1` を利用（実装に準ずる）

---

## 最後に

この README はコードベースの概要と運用に必要な最小限の説明を目的としています。モジュール内部の詳細挙動（例えば ExecutionEngine の具体的な注文ステップや broker API の挙動、DuckDB のスキーマ等）はソースコード（各モジュール）および関連ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）を参照してください。

追加で README に載せたい項目（例: requirements.txt、CI 手順、デプロイ手順、詳細設定例）があれば教えてください。必要に応じて追記します。