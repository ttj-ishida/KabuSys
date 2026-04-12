# KabuSys

日本株向けの自動売買 / 研究基盤プロジェクト（コードベースの抜粋）。  
このリポジトリは以下の主要コンポーネントを含みます：注文実行エンジン、監視サブシステム、ポートフォリオ構築ロジック、ファクター計算・リサーチモジュール、そしてニュースNLP / レジーム検出などの AI 補助機能。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- 注文生成 → 発注 → 約定管理 を行う Execution Engine（本番 / Paper Trading をサポート）
- 実行中のプロセス・リソース・データ鮮度・注文滞留等を監視する Monitoring サービス
- ポートフォリオ構築（候補選定・重み付け・株数決定・セクター制限など）の純粋関数群
- DuckDB を用いたファクター計算・研究用ユーティリティ
- OpenAI（gpt-4o-mini）を用いたニュースのセンチメントスコアリングと市場レジーム判定
- Paper Trading 用の検証レポート生成ツール
- Streamlit ベースの監視ダッシュボード

設計上のポイント：
- 本番と Paper Trading は DB を分離（Paper の場合 data/paper_trading.db を使用）
- ルックアヘッドバイアスを防ぐ設計（target_date を明示し datetime.today() を直接参照しない等）
- フェイルセーフ（API 失敗時はフォールバックして継続する挙動が多く組み込まれています）

---

## 主な機能一覧

- Execution
  - OrderManager: 注文の作成 / 送信 / 同期ロジック
  - Reconciler: 再起動時の注文・ポジション突合
  - RiskManager（設定により実行）等（コードベースに含まれる関連モジュール群）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセスの監視、データ鮮度確認
  - TradeMonitor: 滞留注文・約定価格異常の検出
  - RiskMonitor: ドローダウン / ポジション上限の監視とリスクログ出力
  - KillSwitch: フラグファイル経由で ExecutionEngine 停止シグナル
  - AlertManager: LINE Messaging API による通知（クールダウン管理）
  - Streamlit ダッシュボード（監視データ可視化）
- Portfolio
  - 候補選定、等金額/スコア加重、リスクベースのサイズ決定、セクター制限、レジーム乗数
- Research
  - ファクター計算（Momentum/Volatility/Value 等）
  - 将来リターン計算・IC（スピアマン順位相関）・統計サマリ
- AI
  - news_nlp: ニュース記事の銘柄別センチメントスコア計算（OpenAI）
  - regime_detector: ETF MA とマクロセンチメントの合成による日次レジーム判定
- Tools
  - paper_verification_report: Paper Trading DB を集計して検証レポートを標準出力に表示

---

## セットアップ手順

以下は一般的なセットアップ手順の例です。実際の依存関係はプロジェクトの requirements.txt を参照してください（存在する場合）。

1. リポジトリをクローン
   - git clone <repository-url>
2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - 主要ライブラリ（例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 主要な環境変数とデフォルト:
     - KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
     - JQUANTS_REFRESH_TOKEN: 必須（J-Quants API 用）
     - KABU_API_PASSWORD: 必須（kabu API 用）
     - OPENAI_API_KEY: OpenAI 呼び出しに必要（AI モジュールを使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager の通知に使用
     - DUCKDB_PATH: data/kabusys.duckdb (デフォルト)
     - SQLITE_PATH: data/monitoring.db (デフォルト)
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (Paper Trading 用)
     - PAPER_FILL_MODE: instant | partial | never | reject (デフォルト: instant)
     - PID_FILE_PATH: data/execution.pid
     - KILL_FLAG_PATH: data/kill.flag
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
5. データベース初期化
   - Monitoring 用 SQLite はスクリプト実行時に必要なテーブルを作成します（init_monitoring_db）。

注意:
- .env パーサはシェル風の export 対応、クォート処理、インラインコメント許容などのルールに従います。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全分離して data/paper_trading.db を使用します。

---

## 使い方（主なコマンド例）

- ExecutionEngine を起動（本番・Paper 共通エントリポイント）
  - python -m kabusys.run_execution
  - Paper Trading にする場合:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 実行開始時にプロセス優先度を "high" に設定します（権限によってはスキップされることがあります）。

- Monitoring を起動（ポーリング監視）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB は読み取り専用 URI で開かれます。MonitoringEngine を先に起動してデータを生成してください。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（プログラムから呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OPENAI_API_KEY か api_key 引数が必要

- 注意点
  - 実行時に必要な環境変数が未設定だと Settings クラス内のプロパティで ValueError を投げます（必須項目に注意）。

---

## 重要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（動作モード）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI 呼び出し用キー（AI 機能利用時必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動）
- PID_FILE_PATH: Execution Engine の PID ファイル（default data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（default data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループ間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（INFO 等）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（1 に設定）

---

## ディレクトリ構成（主なファイルと説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（.env 自動ロードのロジック含む）
  - run_execution.py
    - ExecutionEngine の起動スクリプト（KABUSYS_ENV により Paper と本番で DB を分離）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
      - Paper Trading DB を集計して検証レポートを出力
  - portfolio/
    - portfolio_builder.py
      - 候補選定（スコア順）・等金額 / スコア重み算出
    - position_sizing.py
      - 株数計算・投下資金上限・lot rounding・aggregate cap スケールダウンロジック
    - risk_adjustment.py
      - セクターキャップ適用・レジーム乗数算出
  - research/
    - factor_research.py
      - Momentum / Volatility / Value のファクター計算（DuckDB 接続を受ける）
    - feature_exploration.py
      - 将来リターン計算、IC（Spearman）計算、統計サマリ
  - ai/
    - news_nlp.py
      - raw_news を集約して OpenAI に投げ、銘柄別センチメントを ai_scores テーブルに書き込む
    - regime_detector.py
      - ETF MA とマクロセンチメントを合成して market_regime テーブルに書き込む
  - monitoring/
    - monitoring_db.py
      - SQLite のテーブル初期化と CRUD（MonitoringDB クラス）
    - system_monitor.py
      - CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py
      - 滞留注文・約定価格異常の検出
    - risk_monitor.py
      - ドローダウン・ポジション上限の監視とリスクログ出力
    - kill_switch.py
      - kill.flag の生成／判定
    - alert_manager.py
      - LINE Push による通知（クールダウン制御）
    - monitoring_engine.py
      - 各モニタを束ねてポーリング/アラート判定を行う
    - streamlit_dashboard.py
      - Streamlit ベースの監視ダッシュボード（read-only で監視 DB を表示）
  - execution/
    - order_manager.py
      - 注文状態遷移・送信・同期ロジック（OrderManager）
    - reconciler.py
      - 起動時の注文・ポジション突合ロジック
    - order_repository.py, order_record.py, broker_factory.py, broker_api.py 等（発注/履歴保存関連）
  - utils/
    - process_priority.py
      - psutil を利用したプロセス優先度 / CPU affinity 設定ユーティリティ

その他:
- data/
  - デフォルトの DB 保存場所（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db 等）
- pyproject.toml / requirements.txt（プロジェクトルートにあることを想定）

---

## 運用上の注意点 / ベストプラクティス

- Paper Trading は本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を確認）。
- OpenAI を利用する機能は API キーと利用料が必要です。API 呼び出しはリトライやフォールバックが組み込まれているものの、コストやレート制限に注意してください。
- run_execution / run_monitoring はプロセス優先度の変更や PID / kill.flag の取り扱いを行うため、実行権限や filesystem の書き込み権に注意してください。
- monitoring の閾値（CPU/MEM/DISK/ドローダウン閾値等）は Settings で環境変数から調整可能です。
- 監視やアラートは過剰通知を防ぐためクールダウンや重複排除の仕組みがある一方で、重要なイベントが欠落しないよう設定を確認してください。

---

## 開発者向けメモ

- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に行われます。テストなどで自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 接続は research / ai / pipeline 系で利用されます。prices_daily / raw_financials / raw_news 等のテーブルを前提としているため、データ投入フロー（ETL）は別途必要です。
- テスト時には OpenAI 呼び出し等をモックすることを推奨します（コード中で外部呼び出しをラップしているため patch が容易です）。

---

必要であれば、README に依存パッケージ一覧（requirements.txt からの抜粋）や、よくあるトラブルシュート（DB が開けない / OpenAI レスポンスエラーの対処など）を追記できます。どの情報を優先的に追加したいか教えてください。