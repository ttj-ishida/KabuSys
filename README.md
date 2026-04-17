# KabuSys

日本株向けの自動売買 / リサーチ基盤ライブラリ群（KabuSys）。  
このリポジトリは取引エンジン、監視（モニタリング）、ポートフォリオ構築、リサーチ、AI 補助機能などを含みます。  
以下はコードベースに基づく README（日本語）です。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムの基盤モジュール群です。主な責務は以下のとおりです。

- ExecutionEngine: 注文作成・送信・状態管理、リコンシリエーション（再起動時の同期）
- Monitoring: システム状態、注文滞留・約定異常、ドローダウン等の監視・ログ保存・アラート
- Portfolio construction: 候補選定、重み計算、単元丸め、リスク調整
- Research: DuckDB を用いたファクター計算・特徴量解析
- AI ユーティリティ: ニュースのセンチメントスコアリング、レジーム判定（OpenAI）
- 運用ツール: Paper Trading 検証レポート生成、Streamlit ダッシュボード

設計方針として、運用（live）と検証（paper_trading）を明確に分離し、データベースやブローカークライアントの分離、ルックアヘッドバイアス対策、フェイルセーフ（API失敗時のフォールバック）等に配慮しています。

---

## 機能一覧（抜粋）

- Execution
  - 注文作成・管理（OrderManager）
  - 注文リポジトリ（SQLite）への永続化（OrderRepository）
  - 起動時リコンシリエーション（Reconciler）
  - RiskManager による執行前リスクチェック
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度の監視
  - TradeMonitor: 滞留注文、約定価格異常の検知
  - RiskMonitor: ドローダウン監視・ポジション数監視とログ化
  - KillSwitch: しきい値到達時に停止フラグを書き込み ExecutionEngine を停止
  - AlertManager: LINE によるプッシュ通知（クールダウン管理）
  - MonitoringEngine: 各モニタをまとめてポーリング実行
  - Streamlit ダッシュボード（data/monitoring.db を参照）
- Portfolio
  - 候補選定（スコア順）、等配分 / スコア加重、リスクベース発注量計算
  - セクター集中の抑止、レジーム乗数適用
- Research
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI
  - ニュース記事を LLM（OpenAI）でセンチメント評価して ai_scores に保存
  - マクロ + ETF MA200 を用いた市場レジーム判定
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
  - 実行用スクリプト: run_execution.py（エンジン起動）、run_monitoring.py（監視ループ起動）

---

## セットアップ手順

以下はローカルで動かす際の最小セットアップ例です。

1. Python（推奨: 3.10+）を用意
2. 仮想環境作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール  
   ※リポジトリに requirements.txt がない場合は下記を個別にインストールしてください（代表例）。
   - pip install duckdb psutil requests openai streamlit
   - （運用環境に応じて他の依存がある場合があります）
4. データディレクトリ作成
   - mkdir -p data
5. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くことが可能（config.Settings が自動ロードする）。
   - 必須環境変数の例:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 実行に便利な環境変数（主要なもの）:
     - KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager 用（オプション）
     - SQLITE_PATH: 監視 DB path（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB path（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト: data/paper_trading.db）
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング秒（デフォルト 60）
     - PID_FILE_PATH, KILL_FLAG_PATH など（必要に応じて）
   - サンプル .env（最低限の例）
     - JQUANTS_REFRESH_TOKEN=your_jquants_token
     - KABU_API_PASSWORD=your_kabu_password
     - OPENAI_API_KEY=sk-...
     - KABUSYS_ENV=development

注意:
- 実稼働時は適切な権限で psutil によるプロセス優先度設定が必要（set_process_priority）。
- run_execution は paper_trading の場合 mock ブローカーを使い DB を分離します（data/paper_trading.db）。

---

## 使い方（主なスクリプト／コマンド例）

1. 監視ループ起動（Monitoring）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
   - 監視は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（環境に関係なく本番 DB を参照する点に注意）。

2. 実行エンジン起動（ExecutionEngine）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録されます。
   - 実行中、data/stop_requested.flag を作成すると起動済みのループにより安全に停止します。
   - 起動時に Kill Flag を検査しているため、既に停止フラグがあるとエンジンは起動しません。

3. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD  （レポート開始日）
     - --to   YYYY-MM-DD  （レポート終了日）
     - --db PATH          （SQLite DB パス。環境変数 PAPER_TRADING_SQLITE_PATH より優先）
   - 例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

4. Streamlit ダッシュボード（監視データ閲覧）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - read-only モードで SQLite を開きます。MonitoringEngine が data/monitoring.db を更新していることを前提とします。

5. AI 機能（ニューススコア / レジーム判定）
   - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を DuckDB 接続と日付を与えて呼び出します（プログラム的に使用）。
   - これらは OPENAI_API_KEY を参照するか引数で API キーを渡してください。

注意と運用上のヒント:
- stop/kill フラグ:
  - data/stop_requested.flag: run_* スクリプトはこのファイルの存在を検査して安全終了します。
  - data/kill.flag: KillSwitch が書き込む停止指示（ExecutionEngine に対する外部停止シグナル）。
- データベースマイグレーション:
  - monitoring_db.init_monitoring_db は冪等にテーブルとインデックスを作成し、既存列の追加（マイグレーション）処理も行います。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールと説明（抜粋）です。

- src/kabusys/
  - __init__.py: パッケージ定義、バージョン
  - config.py: 環境変数読み込み、Settings クラス（全設定をここから取得）
  - run_execution.py: ExecutionEngine 起動スクリプト
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
- src/kabusys/execution/
  - execution_engine.py (存在): 実行エンジン本体（取引セッション管理）
  - order_manager.py: 注文作成・外向き API
  - order_repository.py: 注文永続化（SQLite）
  - reconciler.py: 再起動時の同期・ポジション差分検出
  - risk_manager.py: 執行前リスク判定
  - broker_factory.py / broker_api.py: ブローカークライアント生成・抽象 API（Mock/実ブローカー切替）
- src/kabusys/monitoring/
  - monitoring_db.py: SQLite による監視ログ永続化層（init / MonitoringDB）
  - system_monitor.py: システム状態チェック（CPU/メモリ/ディスク / データ鮮度 / プロセス）
  - trade_monitor.py: 注文滞留・約定価格異常チェック
  - risk_monitor.py: ドローダウン / ポジション上限監視
  - kill_switch.py: 停止フラグ書込ユーティリティ
  - alert_manager.py: LINE Push 通知
  - monitoring_engine.py: 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py: 監視ダッシュボード（Streamlit）
- src/kabusys/portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 発注株数計算（単元丸め・リスク制限・aggregate cap）
  - risk_adjustment.py: セクターキャップ・レジーム乗数
- src/kabusys/research/
  - factor_research.py: momentum / volatility / value ファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン・IC・統計サマリー等
- src/kabusys/ai/
  - news_nlp.py: ニュース NLU（OpenAI）による銘柄センチメント付与
  - regime_detector.py: マクロ + ETF MA200 を組み合わせた市場レジーム判定
- src/kabusys/tools/
  - paper_verification_report.py: Paper Trading 検証レポート生成

その他ユーティリティ:
- src/kabusys/utils/process_priority.py: プロセス優先度 / CPU affinity 設定
- src/kabusys/data, src/kabusys/data.pipeline etc.（データ取得・DuckDB 関連モジュールが存在）

（注）上記はリポジトリ内の主要ファイルを抜粋した説明です。完全なファイル一覧はソースツリーを参照してください。

---

## 典型的な運用例（まとめ）

- 開発 / 検証フロー
  1. 仮想環境を作成して依存パッケージをインストール
  2. .env に必要なキーを設定（JQUANTS_REFRESH_TOKEN 等）
  3. DuckDB / SQLite のデータファイルを準備または初回実行で自動作成
  4. KABUSYS_ENV=paper_trading にて run_execution を実行して動作確認
  5. paper_verification_report で検証結果を出力

- 本番運用の注意点
  - KABUSYS_ENV=live の時は実口座・本番 DB を使用するため環境変数の取り扱いに注意
  - プロセス優先度設定やファイル権限は OS レベルの考慮が必要
  - KillSwitch / stop フラグ運用を運用手順に明記する（安全停止方法）

---

## 参考（主要環境変数一覧）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルト http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (アラート用)
- KABUSYS_ENV: development | paper_trading | live (デフォルト development)
- SQLITE_PATH (監視 DB, default data/monitoring.db)
- DUCKDB_PATH (DuckDB file, default data/kabusys.duckdb)
- PAPER_TRADING_SQLITE_PATH (paper_trading DB, default data/paper_trading.db)
- PAPER_FILL_MODE (paper_trading の約定挙動: instant | partial | never | reject)
- MONITOR_POLL_INTERVAL (監視ポーリング秒, default 60)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- LOG_LEVEL (DEBUG/INFO/... )

---

必要であれば README を実際の環境（運用手順書）向けにもう少し展開（サービス unit ファイル、監視アラートの定義、より詳細な .env.example、依存パッケージ固定の requirements.txt）して作成できます。どの部分を拡張したいか教えてください。