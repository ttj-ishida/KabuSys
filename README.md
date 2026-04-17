# KabuSys — README

このリポジトリは日本株自動売買システム「KabuSys」の一部実装です。  
本 README はコードベースの使い方、設定、主要コンポーネントを日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買とそれを支える監視・検証機能を提供するシステムです。  
主な機能は以下の通りです：

- 注文作成・管理、ブローカ連携（ExecutionEngine）
- リコンシリエーション（再起動後の注文・ポジション同期）
- 監視フレームワーク（System / Trade / Risk モニタ）とアラート（LINE）
- Paper Trading 環境（本番と DB を分離して検証可能）
- ニュース NLP（OpenAI を使った銘柄センチメント評価）
- 市場レジーム判定（MA とマクロセンチメントの合成）
- ポートフォリオ構築・ポジションサイズ計算（純粋関数群）
- Research 用のファクター計算・特徴量解析ユーティリティ
- Streamlit による監視ダッシュボード
- 検証用スクリプト（Paper Trading 検証レポート生成）

---

## 主な機能一覧

- Execution
  - 注文作成・送信・状態管理（OrderManager / OrderRepository）
  - リスク管理（RiskManager）
  - Reconciler による自動復旧
  - paper_trading モードで MockBroker を利用し本番 DB と分離

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存チェック、データ鮮度
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン、ポジション上限監視（Kill Switch 発動）
  - AlertManager: LINE Push による通知（クールダウン管理）
  - MonitoringEngine: これらを定期実行するポーリングエンジン
  - SQLite ベースの監視 DB (monitoring.db) とマイグレーション処理

- AI / NLP
  - news_nlp.score_news: raw_news から銘柄別センチメントを生成して ai_scores に格納（OpenAI）
  - regime_detector.score_regime: ma200 乖離 + マクロニュースで市場レジーム判定

- Portfolio
  - 候補選定・重み付け・セクター制約・ポジションサイズ計算（等金額 / スコア加重 / risk_based）

- Research
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ

- Tools
  - paper_verification_report: Paper Trading DB を解析して PASS/FAIL レポートを出力

---

## セットアップ手順

前提
- Python 3.9+ を推奨（各ライブラリの互換性に応じて調整してください）
- SQLite（Python 標準モジュール）、DuckDB（Python パッケージ）を使用

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit

   （本プロジェクトには上記パッケージが主要な外部依存です。実際の要件に応じて追加してください。）

3. プロジェクトルートに `.env` を配置（任意）
   - config.Settings は起動時にプロジェクトルートの `.env` / `.env.local` を自動読み込みします（OS 環境変数が優先）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（Settings.jquants_refresh_token 必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
   - KABUSYS_ENV: 実行環境（development / paper_trading / live）
   - （任意）LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — アラート送信用

5. データディレクトリ（デフォルト）
   - data/monitoring.db         — 監視ログ（SQLite）
   - data/paper_trading.db     — Paper Trading 用 SQLite（paper_trading 時）
   - data/kabusys.duckdb       — DuckDB データベース（prices_daily など）
   - data/execution.pid        — ExecutionEngine PID ファイル
   - data/kill.flag            — Kill flag（監視が書き込む）
   - data/stop_requested.flag  — 実行停止用フラグ（run_monitoring / run_execution が確認）

   必要に応じて `Settings` の環境変数で上書きできます（SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、DUCKDB_PATH 等）。

---

## 使い方

### 監視ループ起動（Monitoring）
- スクリプト:
  - src/kabusys/run_monitoring.py
- 実行例:
  - python -m kabusys.run_monitoring
- オプション的挙動:
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き（デフォルト: 60）。
  - 監視は常に Settings.sqlite_path（本番パス）を使用します（環境に関係なく monitoring 用 DB を使用）。

- 停止:
  - プロジェクトルートの `data/stop_requested.flag` が存在するとループを終了します。

### 実行エンジン起動（Execution）
- スクリプト:
  - src/kabusys/run_execution.py
- 実行例:
  - python -m kabusys.run_execution
- 挙動:
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使い、Paper Trading 用の DB（`PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`）を利用して完全分離します。
  - 起動時に `data/stop_requested.flag` があると起動せず終了します。
  - 実行中は `data/execution.pid` に PID を書き込み、停止時に削除されます（stale PID の検出/削除機能あり）。

### Paper Trading 検証レポート
- スクリプト:
  - src/kabusys/tools/paper_verification_report.py
- 実行例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合: --db path/to/paper_trading.db
- 出力:
  - 稼働率、注文成功率、送信率、レイテンシ（P95 など）のサマリと PASS/FAIL 判定

### Streamlit ダッシュボード（監視可視化）
- ファイル:
  - src/kabusys/monitoring/streamlit_dashboard.py
- 実行例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 注意:
  - 既に monitoring.db が存在し読み取り可能であることが前提（read-only URI を使って接続）。

### AI / レジーム判定（プログラム呼び出し）
- 関数:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 備考:
  - OpenAI API キーを引数で与えるか `OPENAI_API_KEY` 環境変数を設定してください。
  - API 呼び出しはリトライ（指数バックオフ）を行い、失敗時は安全側の値（0 など）で継続する実装です。

---

## 主要設定（Settings / 環境変数）

主な環境変数と意味（抜粋）:

- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。run_monitoring 用）
- PAPER_FILL_MODE: Paper Trading の fill モード（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite ファイルパス（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視 DB / 本番 monitoring DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH / KILL_FLAG_PATH 等も Settings で管理可能

設定は .env / .env.local をプロジェクトルートに置くと自動読み込みされます（既存 OS 環境変数は優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

---

## 停止・強制停止フラグ

- data/stop_requested.flag
  - run_monitoring.py / run_execution.py はこのファイルの存在をチェックし、存在すれば安全に終了します（運用上の優先停止手段）。

- data/kill.flag
  - KillSwitch（監視ロジック）が発動した場合に作成され、ExecutionEngine 停止のシグナルとして使われます。KillSwitch は `Settings.kill_flag_path` を使ってファイルを作成します。
  - KillSwitch.clear() で削除（実装上は呼び出し側が利用）。

---

## ディレクトリ構成

以下は src/kabusys 以下の主要ファイル / ディレクトリ構成（抜粋）と簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / 設定管理（.env ロード、自動検証）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（テーブル作成・マイグレーション）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書込みユーティリティ
    - alert_manager.py — LINE 通知クライアント（クールダウン管理）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — 発注・状態遷移管理
    - reconciler.py — 再起動時の自動復旧
    - （その他 broker_factory 等のブローカ関連、order_repository 等が含まれる想定）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・単元丸め・スケーリング
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

---

## マイグレーション / DB 注意点

- monitoring_db.init_monitoring_db(conn) は冪等的にテーブルを作成します。既存 DB に対して必要なカラムが欠落している場合は ALTER TABLE による簡易マイグレーションを行います（例: trade_logs.latency_ms，dashboard.peak_value）。
- DuckDB / SQLite のパスは Settings で指定可能。Paper Trading はデータを分離するよう設計されています。

---

## 運用上の注意・ベストプラクティス

- 実運用（live）では KABUSYS_ENV=live を設定し、適切な API キー・パスワードを環境変数で安全に渡してください。
- Paper Trading（KABUSYS_ENV=paper_trading）では MockBroker を使い、本番 DB と完全に分離することにより安全に検証できます。
- OpenAI を使う機能は外部 API 呼び出しのためレート制限やエラーを考慮する必要があります。API キーの管理、利用量の監視を行ってください。
- LINE のアラートを有効にする場合は channel token と user id を設定してください。トークンが未設定の場合はログ出力のみになります。
- 監視・停止フラグ（kill.flag / stop_requested.flag）を運用ルールとして取り決めることを推奨します。

---

## 追加情報 / 開発者向け

- ログレベル、各種閾値（CPU/MEM/DISK、ドローダウン閾値等）は Settings を通じて環境変数で調整可能です。
- テストコードは含まれていませんが、各コンポーネントは純粋関数（portfolio、research）と副作用を伴うクラス（monitoring_db, OrderRepository 等）に分離されています。ユニットテストは純粋関数に対して容易に書けます。
- OpenAI 呼び出し部は内部でリトライや JSON 検証を行うように設計されています。テスト時には該当関数をモックして API 呼び出しを差し替えてください（モジュール内で _call_openai_api を patch するなどの手法を想定）。

---

この README はコードベースの主要なポイントをまとめたものです。詳細な API 仕様や設計ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）に関しては別途参照してください。ご不明点があれば、どの部分のドキュメントを補強すべきか教えてください。