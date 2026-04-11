# KabuSys

日本株自動売買システム KabuSys のリポジトリ向け README（日本語）。

以下はコードベースの抜粋からまとめたドキュメントです。実装に依存する設定や実行方法、主要コンポーネントの説明を含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたモジュール群です。主な機能は以下の通りです。

- シグナルに基づく発注エンジン（ExecutionEngine）
- 発注の再突合 / リコンシリエーション（Reconciler）
- 注文管理（OrderManager / OrderRepository）
- リスク管理（RiskManager、ポジション・ドローダウン制御）
- ポートフォリオ構築（候補選定、重み算出、株数決定）
- 監視（SystemMonitor、TradeMonitor、RiskMonitor、MonitoringEngine）
- アラート（LINE への push 通知）
- 研究用ファクター計算・特徴量解析（research パッケージ）
- ニュース NLP（OpenAI を用いたセンチメント評価）とレジーム検出（AI モジュール）
- 監視ダッシュボード（Streamlit）

設計方針としては、DuckDB を用いた研究用分析、SQLite による運用監視ログ、外部ブローカーとのインタフェース分離、フェイルセーフ／冪等性を重視した永続化設計が取られています。

---

## 主な機能一覧

- Execution
  - Signal Queue Pull 型の発注ループ（シグナル処理・プッシュドレイン）
  - 発注の 2 段階永続化（OrderSent 前後のクラッシュ耐性設計）
  - リスクゲート（Gate 1: シグナル、Gate 2: 実行レベル、Gate 3: ドローダウン）
  - Reconciler による再起動時の自動復旧
- Monitoring
  - システムリソース（CPU/メモリ/ディスク）・データ鮮度監視
  - 注文滞留・約定異常の検出
  - ドローダウン / ポジション上限の監視と kill.flag による停止シグナル
  - LINE 通知（AlertManager）
  - Streamlit ダッシュボード（読み取り専用で monitoring DB を参照）
- Portfolio
  - 候補選定（スコア降順）、等金額・スコア重み、リスクベース配分
  - セクター集中チェック、レジームによる資金乗数調整
  - 株数決定（単元株丸め、aggregate cap のスケールダウン）
- Research
  - モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- AI
  - raw_news を LLM（gpt-4o-mini）でスコアリングして ai_scores に保存
  - マクロニュース + ETF MA200 を組み合わせて市場レジーム判定
  - API 呼び出しはリトライ・フォールバック設計（429/5xx 等に対するエクスポネンシャルバックオフ）

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.10+（型注釈や union 表記に準拠しているため）
- Git リポジトリルートで作業することを想定（config の自動 .env ロードが .git / pyproject.toml を探索）

1. クローンと仮想環境
   ```
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

2. インストール（必要なパッケージ）
   依存例（実際の pyproject.toml / requirements.txt を参照してください）:
   ```
   pip install duckdb psutil requests streamlit openai
   ```
   - duckdb: 研究用データ / ai モジュールで使用
   - psutil: プロセス優先度・CPU 使用率取得等
   - requests: LINE API 呼び出し
   - streamlit: ダッシュボード
   - openai: LLM 呼び出し（news_nlp / regime_detector）

3. 環境変数（.env または .env.local に記載）
   - 必須（本番機能を使う場合）
     - JQUANTS_REFRESH_TOKEN — J-Quants API トークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
   - OpenAI 関連
     - OPENAI_API_KEY — OpenAI API キー（AI 機能で必須）
   - その他（デフォルト値あり）
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE — paper_trading の約定モード（instant|partial|never|reject、デフォルト: instant）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（未設定時は送信せずログのみ）
     - PID_FILE_PATH / KILL_FLAG_PATH — 実行制御用ファイルパス
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
   - 起動時に .env/.env.local を自動ロード（プロジェクトルートが検出される場合）。自動ロードを無効化するには:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. データディレクトリ作成
   ```
   mkdir -p data
   ```

（注）SQLite / DuckDB は起動時に必要テーブルを自動作成するコードが含まれているため、手動でのスキーマ初期化は基本不要です（monitoring_db.init_monitoring_db が呼ばれます）。

---

## 使い方（実行例）

コードはパッケージ化された状態を想定した実行を例示します。ソース直下から実行する場合は `python src/kabusys/run_execution.py` 等でも動きますが、パッケージ参照を想定して紹介します。

1. ExecutionEngine を起動（本番 / テスト）
   - 通常実行:
     ```
     python -m kabusys.run_execution
     ```
   - Paper trading（本番 DB と分離、専用 SQLite を使用）
     ```
     export KABUSYS_ENV=paper_trading
     python -m kabusys.run_execution
     ```
   - 起動処理:
     - プロセス優先度を "high" に設定（psutil）
     - SQLite / DuckDB に接続（paper_trading 時は専用 DB）
     - BrokerClientFactory でブローカークライアントを生成（KABUSYS_ENV により Mock など）
     - ExecutionEngine.run_session() を実行（シグナル処理とプッシュドレイン）

2. Monitoring を起動（ポーリング）
   ```
   python -m kabusys.run_monitoring
   ```
   - デフォルトポーリング間隔: 60 秒
   - 環境変数で上書き:
     ```
     export MONITOR_POLL_INTERVAL=30
     ```
   - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視は本番 DB を参照する想定）。

3. Monitoring ダッシュボード（Streamlit）
   ```
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```
   - ダッシュボードは監視用 SQLite を読み取り専用で開きます（起動前に MonitoringEngine を動かしておくこと）。

4. AI 機能（ニューススコア / レジーム判定）をプログラムから呼ぶ
   - news_nlp.score_news(conn, target_date, api_key=None)
     - DuckDB 接続を渡し、target_date のタイムウィンドウの記事をスコアリングして ai_scores に書き込む。
     - api_key を渡さない場合は環境変数 OPENAI_API_KEY を参照。
   - regime_detector.score_regime(conn, target_date, api_key=None)
     - マクロニュースと ETF MA200 を組み合わせて market_regime を更新。

5. kill.flag による停止
   - KillSwitch は監視が条件を満たすと `data/kill.flag` に理由を書き込みます。
   - ExecutionEngine は起動時やループ内で kill.flag をチェックし、検出時に安全停止処理を行います。

---

## 重要な環境変数（主なもの）

- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須で使用時に必要）
- KABU_API_PASSWORD: kabuステーション API（必須で使用時に必要）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject）
- SQLITE_PATH: 監視 DB（data/monitoring.db default）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（data/paper_trading.db default）
- DUCKDB_PATH: DuckDB ファイル（data/kabusys.duckdb default）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイル（data/execution.pid default）
- KILL_FLAG_PATH: kill.flag パス（data/kill.flag default）
- MONITOR_POLL_INTERVAL: monitoring 起動時のポーリング間隔（秒。デフォルト 60）

---

## ディレクトリ構成（主要ファイル説明）

（リポジトリ内 `src/kabusys` に相当する主なモジュールと役割）

- src/kabusys/
  - __init__.py — パッケージ宣言（バージョン等）
  - config.py — 環境変数読み込み / Settings クラス（.env 自動ロード、必須キーチェック）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

- src/kabusys/execution/
  - execution_engine.py — ExecutionEngine（シグナル処理 + push ドレイン）
  - order_manager.py — OrderManager（OrderState machine 外向き API）
  - order_repository.py — SQLite ベースの注文永続化（ファイル未掲載だが存在を想定）
  - reconciler.py — 再起動時の照合 / 復旧ロジック
  - risk_manager.py — リスクゲート（構成は参照元コードに依存）

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite スキーマ初期化 + MonitoringDB（永続化 API）
  - system_monitor.py — システム状態・データ鮮度チェック
  - trade_monitor.py — 注文滞留・約定異常チェック
  - risk_monitor.py — ドローダウン・ポジション上限チェック
  - kill_switch.py — kill.flag 書き込み / 判定
  - alert_manager.py — LINE Push 通知
  - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py — Streamlit による監視ダッシュボード

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・aggregate cap のスケール調整
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- src/kabusys/research/
  - factor_research.py — momentum/value/volatility ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリー等

- src/kabusys/ai/
  - news_nlp.py — raw_news を LLM でスコアリングして ai_scores に保存
  - regime_detector.py — マクロニュース + ETF MA200 によるレジーム判定

- src/kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- その他
  - data/ — データファイル（デフォルトの DB ファイル等を配置）
  - pyproject.toml / setup.cfg 等（パッケージ化設定、存在する場合）

---

## 運用上の注意・設計上のポイント

- データ鮮度チェックや監視はルックアヘッドバイアスを避ける設計（target_date 未満のデータのみ使用等）。
- Order 永続化はクラッシュ耐性を考慮して段階的にコミットされる（OrderSent の永続化等）。
- Monitoring は本番監視 DB を参照する設計のため、KABUSYS_ENV にかかわらず監視 DB は本番パスを使用します。
- AI（OpenAI）呼び出しはリトライとフォールバック（失敗時は 0.0 を採用する等）を備え、レスポンス検証を厳密に行います。
- kill.flag による停止は冪等に実装（存在する場合は再書き込みしない）されているため、安全に停止指示を出せます。
- LINE 通知はトークン/ユーザー未設定時は送信せずログに留め、同一カテゴリのクールダウンをメモリで管理します。

---

## 開発・テストに関するメモ

- config._find_project_root は .git または pyproject.toml を探索してプロジェクトルートを特定するため、テスト環境で .env 自動ロードを無効化しておくと安定します（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
- OpenAI 呼び出し等は外部 API に依存するためユニットテスト時は該当内部呼び出しをモックしてください（コード内でもテスト用に _call_openai_api 等を差し替え可能にしてあります）。
- DuckDB を利用したクエリはローカルの prices_daily / raw_financials / raw_news テーブルを前提にしているため、研究用データのロード手順を別途用意してください。

---

この README はコードベースの要旨をまとめたものであり、実際の運用では pyproject.toml / requirements.txt、運用手順書、.env.example 等の正式ドキュメントを併用してください。必要があれば、具体的な環境変数の .env.example やデプロイ手順（systemd ユニット、コンテナ化等）も作成できます。ご希望があれば追加します。