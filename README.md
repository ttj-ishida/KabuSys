# KabuSys

KabuSys は日本株の自動売買／リサーチ／監視を目的とした小規模なプロジェクトです。本リポジトリはトレード実行エンジン、監視コンポーネント、ポートフォリオ構築ユーティリティ、研究用ファクター計算、AI を用いたニュース解析などを含みます。

以下はこのコードベースの README（日本語）です。

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（実行例）
- 主要環境変数（.env）
- ファイル / ディレクトリ構成（抜粋）

---

## プロジェクト概要

KabuSys は以下の役割を持つモジュール群で構成されています。

- Execution（発注）: Broker クライアント経由で注文を作成・管理するエンジン（ExecutionEngine、OrderManager、Reconciler 等）。
- Monitoring（監視）: システム状態、注文滞留、ドローダウン等を定期的にチェックしログ・アラートや Kill Switch を管理（MonitoringEngine、SystemMonitor、TradeMonitor、RiskMonitor、AlertManager）。
- Portfolio（ポートフォリオ構築）: 候補選定、配分重み計算、ポジションサイジング、セクター制限、レジーム調整等（純粋関数群）。
- Research（リサーチ）: DuckDB 上の時系列データを用いたファクター計算や将来リターン、IC 計算など。
- AI（ニュース NLP / レジーム判定）: OpenAI API を使ったニュースのセンチメント評価（ai.news_nlp）、マクロセンチメント合成による市場レジーム判定（ai.regime_detector）。
- Tools: Paper Trading の検証レポート生成や Streamlit ベースの監視ダッシュボードなどのユーティリティ。

設計上の特徴
- DuckDB と SQLite を併用（時系列・分析は DuckDB、監視やトレードログは SQLite）。
- paper_trading（検証）モードでは本番 DB と分離して data/paper_trading.db を使用する仕組みあり。
- .env / .env.local から設定を自動読み込み（必要に応じて無効化可）。
- フェイルセーフ（API失敗時はスキップ、Kill Switch による安全停止など）。

---

## 主な機能（抜粋）

- SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / Execution プロセス生存チェック
- TradeMonitor: 注文の滞留（stale orders）、約定価格異常の検出
- RiskMonitor: ドローダウン監視・ポジション上限監視、リスクログ記録
- KillSwitch: しきい値超過時に data/kill.flag を作成して Execution を停止させる
- AlertManager: LINE Messaging API でのプッシュ通知（オプション）
- Portfolio: 候補選定 / 等配分・スコア配分 / リスクベースサイジング / セクター制限
- Research: モメンタム・ボラティリティ・バリュー系ファクター計算、IC・統計サマリ
- AI: ニュース記事を LLM でスコアリングして ai_scores に保存、マクロセンチメントと MA200 乖離を合成して market_regime に記録
- Tools:
  - streamlit_dashboard.py: 監視ダッシュボード（Streamlit）
  - paper_verification_report.py: Paper Trading の検証レポート出力

---

## セットアップ手順

前提
- Python 3.10+ を推奨（typing|Path 等の利用を考慮）
- SQLite、DuckDB は Python パッケージ経由で利用します

1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 例（requirements.txt が無い場合の代表的パッケージ）:
     - pip install duckdb psutil requests openai streamlit

   代表的な依存:
   - duckdb — 分析用 DB
   - psutil — プロセス/リソース情報
   - requests — LINE API 呼び出し
   - openai（OpenAI Python SDK）— AI モジュール
   - streamlit — ダッシュボード

4. .env の用意
   - プロジェクトルートに .env（および任意で .env.local）を置きます。自動読み込みはデフォルトで有効。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 初期データディレクトリ
   - data/ ディレクトリ（DB、フラグファイルなど）を作成してください。多くのスクリプトは存在しない場合に自動作成します。

---

## 主要環境変数（.env 例）

必須（最低限）
- JQUANTS_REFRESH_TOKEN=...         # J-Quants API（研究用）
- KABU_API_PASSWORD=...             # kabuステーション API のパスワード

OpenAI（AI 機能を使う場合）
- OPENAI_API_KEY=...

運用 / オプション
- KABUSYS_ENV=development|paper_trading|live  # 実行モード（paper_trading で検証用 DB を使用）
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- PAPER_FILL_MODE=instant|partial|never|reject
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- LOG_LEVEL=INFO
- MONITOR_POLL_INTERVAL=60  # run_monitoring のポーリング間隔（秒）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1  # 自動 .env 読み込みを無効化

.env のパースはシンプルな実装（export 対応、クォート・エスケープの簡易処理）です。.env.example を参考に作成してください（このリポジトリの配布時に同梱されている想定）。

---

## 使い方（実行例）

1. 監視（MonitoringEngine）を単独で実行
   - 監視用スクリプト: src/kabusys/run_monitoring.py
   - デフォルトでは本番の sqlite_path を使用（KABUSYS_ENV にかかわらず監視 DB は本番パス）
   - 実行:
     - python -m kabusys.run_monitoring
   - 環境変数でポーリング間隔を変更:
     - export MONITOR_POLL_INTERVAL=30

   停止:
   - プロジェクトルートの data/stop_requested.flag を作成するとループが検知して終了します。

2. ExecutionEngine（発注エンジン）を起動
   - スクリプト: src/kabusys/run_execution.py
   - 実行:
     - python -m kabusys.run_execution
   - paper_trading モードで起動する例:
     - export KABUSYS_ENV=paper_trading
     - python -m kabusys.run_execution
   - paper_trading の場合は MockBrokerClient が使用され、データは data/paper_trading.db に保存されます（本番 DB と分離）。

   停止:
   - data/stop_requested.flag を作成すると実行エンジンに停止信号が送られます。
   - KillSwitch が条件を満たした場合は data/kill.flag が書き込まれ、実行エンジンは停止します。

3. Streamlit ダッシュボード（監視 UI）
   - ファイル: src/kabusys/monitoring/streamlit_dashboard.py
   - 起動:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視 DB を読み取りモードで開き、ダッシュボードを表示します。

4. Paper Trading 検証レポート生成
   - スクリプト: src/kabusys/tools/paper_verification_report.py
   - 実行例:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - デフォルト DB パスは data/paper_trading.db。--db オプションで上書き可能。

5. AI 機能（ニューススコア、レジーム判定）
   - ai.news_nlp.score_news(conn, target_date, api_key=None)
     - DuckDB 接続を渡し、target_date に対するニューススコアを ai_scores テーブルへ書き込む
     - api_key が None の場合は環境変数 OPENAI_API_KEY を参照
   - ai.regime_detector.score_regime(conn, target_date, api_key=None)
     - market_regime テーブルへ判定結果を書き込む

---

## 注意点 / 運用上のヒント

- 設定の自動読み込み:
  - プロジェクトルート検出に .git または pyproject.toml を使用するため、展開後にパス構成が変わりうる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化して手動で環境変数を設定してください。
- データ鮮度チェック:
  - SystemMonitor は DuckDB の prices_daily テーブルから最終日付を取得し data freshness を判定します。prices データが適切に投入されていることを確認してください。
- フェイルセーフ:
  - OpenAI 呼び出しはリトライやフォールバックを含む設計ですが、API キーが設定されていないときは明示的にエラーになる関数もあります（呼び出し側で捕捉を推奨）。
- Paper Trading と本番の DB は分離されています（settings.is_paper に基づく）。paper_trading を使う際は DB パスを確認して意図せぬ上書きを避けてください。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイルと簡単な説明です（提供コードに基づく抜粋）。

- kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数 / Settings 管理、.env 自動読み込みロジック
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite 用監視ログ永続化（init + MonitoringDB クラス）
    - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py — 注文滞留 / 約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch（flag ファイル書き込み）
    - alert_manager.py — LINE を使った通知
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — 発注オーケストレーション（OrderManager）
    - reconciler.py — 起動時の再同期 / リコンシリエーション
    - ...（BrokerFactory / Engine 等はプロジェクト全体に存在）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み算出
    - position_sizing.py — 株数算出・スケーリング・単元丸め
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value ファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリ等
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書込
    - regime_detector.py — MA200 とマクロニュースを合成して market_regime を決定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
    - __init__.py

（上記はリポジトリ内の該当ファイルを抜粋した構成です。実際の配布ではさらに execution/broker 等の追加モジュールが存在します。）

---

## 追加情報

- ロギング:
  - スクリプトは logging.basicConfig(level=logging.INFO) を使用しています。必要に応じて LOG_LEVEL 環境変数で調整できます（Settings.log_level）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() はテーブル作成と簡易マイグレーション（カラム追加）を行います。既存 DB に対して冪等に実行できます。
- テスト:
  - 各モジュールは副作用を抑えた設計（pure functions / DI）を意識しています。ユニットテストを追加しやすい構成です。

---

問題や不明点があれば、どの機能についてもっと詳しく知りたいか教えてください。実行コマンドや .env の具体例を踏まえたセットアップ手順のテンプレートも提供できます。