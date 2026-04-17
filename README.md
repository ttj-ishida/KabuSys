# KabuSys

KabuSys は日本株向けの自動売買・リサーチ・監視フレームワークです。本リポジトリは次の主要機能を備えます：

- 注文発行・状態管理・リコンシリエーションを行う Execution コンポーネント
- 監視（システム稼働、注文滞留、リスク監視）とアラート（LINE への Push）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- リサーチ用ファクター計算（モメンタム / バリュー / ボラティリティ 等）
- ニュース NLP による銘柄センチメント評価（OpenAI API 経由）
- 市場レジーム判定（MA + マクロニュースによる合成）
- Paper Trading の検証レポート生成ツール、Streamlit ダッシュボード

以下、セットアップ方法・使い方・ディレクトリ構成などを記載します。

## 機能一覧（抜粋）

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Broker クライアントファクトリ（本番 / モック切替：KABUSYS_ENV=paper_trading）
  - OrderManager / OrderRepository / Reconciler による状態管理と自動復旧
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine
  - kill_switch（しきい値到達時に ExecutionEngine 停止フラグを書き込み）
  - AlertManager（LINE Messaging API 経由でアラート通知、クールダウン機能付き）
  - Streamlit ベースの監視ダッシュボード（read-only で SQLite を参照）
  - run_monitoring.py によるポーリングループ起動（MONITOR_POLL_INTERVAL で間隔上書き）
- Portfolio construction
  - 候補選定、等配分・スコア加重配分、セクターキャップ、レジーム調整、株数決定（単元丸め）
- Research
  - DuckDB 接続を用いたファクター計算（prices_daily / raw_financials テーブルを参照）
  - forward returns / IC / 統計サマリー等のユーティリティ
- AI
  - news_nlp: raw_news を集約し OpenAI でセンチメントスコアを生成、ai_scores に書き込み
  - regime_detector: ETF (1321) の MA200 乖離とマクロニュースセンチメントを合成して日次レジーム判定
- Tools
  - paper_verification_report: Paper Trading DB を集計して Pass/Fail 判定レポートを出力

## 必要条件（概略）

- Python 3.9+（typing、match 等の言語仕様に合わせて調整してください）
- 外部ライブラリ（代表例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit（ダッシュボード利用時）
- SQLite（標準ライブラリ sqlite3 を利用）
- ネットワーク接続（OpenAI API / LINE API / ブローカー API を使う場合）

依存はプロジェクトに requirements.txt があればそれを利用してください。ない場合は例として：

pip install duckdb psutil openai requests streamlit

※ 実行環境やバージョンによって追加依存が必要になる場合があります。

## 環境変数（主なもの）

アプリは .env / .env.local / OS 環境変数から設定を読み込みます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

必須または重要な変数（例）：

- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
- KABU_API_PASSWORD — kabuステーション API 用パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
- LINE_CHANNEL_ACCESS_TOKEN — LINE push 用トークン（通知利用時）
- LINE_USER_ID — LINE push 先ユーザー ID
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- PAPER_FILL_MODE — Paper Trading の約定挙動（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring で使用）
- PID_FILE_PATH, KILL_FLAG_PATH など（default は data/ 下のパス）

.env 例（抜粋）:
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token
KABU_API_PASSWORD=your_password
OPENAI_API_KEY=sk-...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...

## セットアップ手順（ローカルでの例）

1. リポジトリをクローンしワークディレクトリへ移動
2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt  （requirements.txt があれば）
   - 例: pip install duckdb psutil openai requests streamlit
4. 必要な環境変数を .env または環境にセット
5. データディレクトリ作成
   - mkdir -p data
6. （任意）初回 DB 作成は各コンポーネントが自動で init_monitoring_db を呼びます。monitoring 用 DB のベーススキーマは init_monitoring_db() が作成します。

注意:
- run_monitoring は Monitoring 用 DB（settings.sqlite_path）を常に使用します（KABUSYS_ENV に依存しません）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB を使って実行を分離します。

## 使い方（主要コマンド）

プロジェクトルートから実行することを想定しています（.env 自動ロードが働きます）。

- 監視ループを起動（プロセス優先度を High に設定して実行）:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）

- Execution エンジン起動（実取引または paper_trading）:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定した場合は MockBroker を使用し、データは data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）へ記録されます。
  - 起動前に data/kill.flag が存在すると起動をスキップします（安全停止機能）。

- Paper Trading 検証レポートの生成:
  - python -m kabusys.tools.paper_verification_report
  - オプション例:
    - --from YYYY-MM-DD --to YYYY-MM-DD --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH で既定の DB を指定可能

- Streamlit ダッシュボード（監視）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を read-only で開き各種メトリクスを表示します

- AI 周り（プログラムから利用する API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- 設定自動ロードの無効化（テスト等）
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

## 実行時の注意事項

- プロセス優先度の変更や CPU affinity の設定には権限が必要な場合があります。set_process_priority は psutil を使用し、失敗すると警告を出してスキップします。
- OpenAI / ブローカー API 呼び出しは外部サービス依存であり、API キーやネットワークが必要です。AI 機能はフェイルセーフ設計（異常時はフォールバック動作）になっていますが、API キー未設定時は例外となる関数があります。
- Monitoring / Execution 間はフラグファイル（data/kill.flag, data/stop_requested.flag 等）で連携します。これらのファイルの存在チェック／作成によってプロセスを停止・起動制御します。
- SQLite / DuckDB のパス（settings.sqlite_path, settings.duckdb_path）は Settings クラス経由で取得されます。権限やパスの存在に注意してください。

## ディレクトリ構成

（src/kabusys 以下の主要ファイル・モジュールを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                     — 環境変数 / .env ローダー、Settings クラス
    - run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py              — ExecutionEngine 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py — Paper Trading 検証レポート生成ツール
    - portfolio/
      - portfolio_builder.py        — 候補選定・重み計算
      - position_sizing.py          — 株数決定・資金配分のロジック
      - risk_adjustment.py          — セクターキャップ・レジーム乗数
      - __init__.py
    - research/
      - factor_research.py          — ファクター計算（momentum/value/volatility）
      - feature_exploration.py      — forward returns / IC / 統計サマリ
      - __init__.py
    - ai/
      - news_nlp.py                 — ニュースセンチメント集約 & OpenAI 呼び出し
      - regime_detector.py          — 市場レジーム判定（MA + マクロニュース）
      - __init__.py
    - monitoring/
      - monitoring_db.py            — SQLite スキーマ / DB アクセス層
      - system_monitor.py           — システム・データ鮮度監視
      - trade_monitor.py            — 注文滞留 / 約定異常検出
      - risk_monitor.py             — ドローダウン / ポジション上限監視
      - kill_switch.py              — kill.flag 制御
      - alert_manager.py            — LINE push 通知
      - monitoring_engine.py        — 各 Monitor を束ねるエンジン
      - streamlit_dashboard.py      — Streamlit ダッシュボード
      - __init__.py
    - execution/
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - broker_factory.py
      - execution_engine.py
      - order_record.py
      - order_repository.py
      - order_manager.py
      - (その他 execution 関連)
    - monitoring/monitoring_db.py    — 監視 DB 初期化・ログ系（別ファイル）
    - utils/
      - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ
      - __init__.py
    - research, data, etc.           — DuckDB / データパイプライン関連（prices_daily など）

（上は主要ファイルの要約。リポジトリ内にはさらに多くの補助モジュールが存在します）

## 開発・運用上の補足

- DB マイグレーション：monitoring_db.init_monitoring_db は冪等的にテーブルを作成し、既存カラムの追加（ALTER）などを行います。
- テスト設計：OpenAI 呼び出しなどは内部で呼び出し関数を切り替えられる設計になっており、ユニットテスト時にモック可能です（例: unittest.mock.patch）。
- フェイルセーフ：AI 呼び出し失敗、ブローカー API の一時エラーなどはリトライやフォールバックを行う実装箇所があり、プロダクションでの安定化を意図しています。
- 標準出力ベースのツール（paper_verification_report）により、Paper Trading 結果の簡易的な健全性チェックが可能です。

---

この README はコードベースの主要点をまとめた概要です。各モジュールには docstring / コメントで挙動や設計方針が記載されているため、詳細実装やパラメータは該当ファイルを参照してください。追加で README に入れてほしい運用手順や具体的な .env.example テンプレートがあれば教えてください。