# KabuSys

日本株自動売買システムのコアライブラリ群および運用用ユーティリティ群です。本リポジトリは戦略の研究／ファクター計算、ポートフォリオ構築、発注実行（ExecutionEngine）、監視（Monitoring）や運用支援ツール（レポート・ダッシュボード）を含みます。

---

## プロジェクト概要

- DuckDB を使った時系列価格 / 財務データの集計・ファクター計算（research）
- ポートフォリオ構築（候補選定、重み付け、リスク調整、株数決定）
- Execution 層（ブローカラッパー／OrderManager／Reconciler／RiskManager 等）による発注制御
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor / AlertManager / KillSwitch）
- Paper Trading 用検証・レポート生成および Streamlit ダッシュボード
- OpenAI を使ったニュース NLP によるセンチメント評価・レジーム判定（AI モジュール）

設計上の特徴：
- 多くの処理は純粋関数（副作用なし）で記述され、テストしやすい構成になっています。
- 環境（KABUSYS_ENV）に応じて Paper Trading（本番 DB と完全分離）を選択可能。
- .env 自動ロード機能によりローカル環境変数を簡単に管理できます。

---

## 主な機能一覧

- research
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 上で SQL＋Python）
  - 将来リターン計算・IC（Information Coefficient）算出・統計サマリー
- portfolio
  - 候補選定（score / rank によるソート）
  - 等重・スコア加重の重み計算
  - セクター集中制限、レジーム乗数適用
  - 株数決定（risk-based / equal / score）および単元株丸め、投下資金スケーリング
- execution
  - Broker 抽象（Factory）経由の発注実行、OrderManager による状態遷移管理
  - Reconciler による起動時の自動復旧（ブローカーとの突合）
  - リスク管理（利用率、ドローダウン、回路遮断等）
- monitoring
  - SystemMonitor（CPU/メモリ/ディスク/プロセス状態/データ鮮度）
  - TradeMonitor（滞留注文・約定異常検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - AlertManager（LINE への通知）、KillSwitch（フラグファイルによる ExecutionEngine 停止）
  - MonitoringEngine：各 Monitor を束ねたポーリングループ
  - Streamlit ダッシュボード（監視データの可視化）
- ai
  - news_nlp: OpenAI を使ったニュースセンチメントスコアリング（ai_scores へ書き込み）
  - regime_detector: マクロ＋ETF MA 乖離から市場レジーム判定

- tools
  - paper_verification_report: Paper Trading データから検証レポートを生成

---

## セットアップ手順（開発環境）

以下はローカルで開発／運用するための最小セットアップ例です。

1. リポジトリをクローン
   - git clone <リポジトリURL>
   - cd <repo>

2. Python 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - requirements.txt がない場合、主要な依存を手動で入れてください。例:
     - pip install duckdb psutil requests openai streamlit
   - 実際の運用ではパッケージバージョンを固定した requirements.txt を作成してください。

4. パッケージを開発インストール（推奨）
   - 上位に setup.cfg/pyproject.toml がある構成であれば:
     - pip install -e .
   - ない場合は PYTHONPATH を使して実行できます（例: PYTHONPATH=src python -m kabusys.run_monitoring）

5. 環境変数
   - .env (プロジェクトルート) または .env.local に環境変数を置きます。
   - 自動ロードはデフォルトで有効（プロジェクトルートに .git または pyproject.toml がある場合）。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主に使われる環境変数（一例）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、ブローカーは MockBrokerClient を使用し data/paper_trading.db に記録されます
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必要な場合）
- KABU_API_PASSWORD: kabuステーション API パスワード（必要な場合）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE）を使う場合
- SQLITE_PATH（監視 DB, デフォルト data/monitoring.db）
- DUCKDB_PATH（DuckDB ファイル, デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH（paper_trading 時の監視 DB, デフォルト data/paper_trading.db）
- PID_FILE_PATH, KILL_FLAG_PATH 等（デフォルトは data/ 配下）

---

## 使い方

環境の準備が整ったら以下を参考に各機能を起動します。パッケージがインストールされていない場合は PYTHONPATH=src を付けて実行してください。

例: パッケージをインストールせずに実行する場合
- PYTHONPATH=src python -m kabusys.run_monitoring

（パッケージを pip install -e . している場合は）
- python -m kabusys.run_monitoring
- python -m kabusys.run_execution

1) 監視ループ（MonitoringEngine を単独で起動したい場合）
- python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）をオーバーライド可能（デフォルト 60 秒）
  - 監視は Settings に依らず本番 sqlite_path を使用する仕様

2) 実行エンジン（ExecutionEngine）
- KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します
- python -m kabusys.run_execution

3) Streamlit ダッシュボード（監視データの可視化）
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - デフォルトは data/monitoring.db（読み取り専用 URI を使用して開く）

4) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

5) AI 関連（ニューススコアリング／レジーム判定）
- news_nlp.score_news(conn, target_date, api_key=...) をプログラムから呼ぶ／OpenAI API キー必要
- regime_detector.score_regime(conn, target_date, api_key=...) で市場レジーム判定と DB 書き込み

注意点:
- 実行中の ExecutionEngine を外部から停止させるには KillSwitch が利用する data/kill.flag を作成します（KillSwitch は kill.flag を書き込む役割を持ちます）。Monitoring 側は条件に応じて kill.flag を書き込みます。
- PID ファイル (Settings.pid_file_path) により ExecutionEngine の生存監視を行います。SystemMonitor は stale PID を検出して削除およびログ記録します。

---

## 主要設定（Settings の概要）

設定は環境変数から読み込みます。主要プロパティ：
- env (KABUSYS_ENV): development | paper_trading | live
- sqlite_path / duckdb_path / paper_sqlite_path
- paper_fill_mode: instant | partial | never | reject
- pid_file_path / kill_flag_path
- cpu_threshold_pct / memory_threshold_pct / disk_threshold_pct
- LOG_LEVEL

.env の読み込み仕様:
- プロジェクトルート（.git または pyproject.toml）を自動検出して .env → .env.local の順に読み込みます
- OS 環境変数は保護され、.env.local で上書きする場合でも既存の OS 環境変数は保護されます
- 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成

（抜粋）src/kabusys 以下の主要ファイル・モジュール：

- kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理（.env 自動ロード含む）
  - run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト（paper_trading モード対応）
  - utils/
    - process_priority.py         — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py            — SQLite ベースの監視 DB（スキーマ初期化・読み書き）
    - system_monitor.py           — システム状態・データ鮮度監視
    - trade_monitor.py            — 注文滞留 / 約定異常監視
    - risk_monitor.py             — ドローダウン・ポジション上限監視
    - monitoring_engine.py        — 各 Monitor を束ねるポーリングロジック
    - alert_manager.py            — LINE Push 通知
    - kill_switch.py              — kill.flag 管理
    - streamlit_dashboard.py      — Streamlit ベースのダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py
    - order_record.py
    - broker_factory.py
    - execution_engine.py
    - risk_manager.py
    - ... (発注系の実装)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/
    - pipeline.py (prices/io などを提供する想定)
    - stats.py (zscore_normalize 等)
  - tools/
    - paper_verification_report.py
    - __init__.py

データ／DB（デフォルトパス）
- DuckDB: data/kabusys.duckdb
- 監視 SQLite: data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db
- PID / kill flag: data/execution.pid, data/kill.flag

---

## 運用上の注意 / よくある質問

- Paper Trading と本番 DB は完全分離されています。KABUSYS_ENV=paper_trading を指定すると paper 用 SQLite に記録されます。
- MONITOR_POLL_INTERVAL を 0 や負値にすると無効扱いとなり、デフォルト間隔（60 秒）が使用されます。
- OpenAI API 呼び出し（ai.news_nlp / regime_detector）は API エラーや 5xx 系に対して再試行ロジックを組んでいますが、API キーが未設定だと例外を投げます。CI やテストではモック化してください。
- streamlit ダッシュボードは監視 DB を読み取り専用で開きます（URI with ?mode=ro）。監視プロセスと同時に安全に閲覧できます。

---

## 貢献 / 開発メモ

- 各モジュールは副作用をできるだけ抑え、単体テストが書きやすい設計になっています。ユニットテストでは psutil / requests / OpenAI 呼び出し等をモックすることが推奨されます。
- DB スキーマの初期化・マイグレーションコードは monitoring_db.init_monitoring_db に集約されています。スキーマ変更時は既存データの互換性を考慮したマイグレーションを実装してください。

---

README に載せるべき追加情報や、運用向けの具体的な systemd/サービス定義、あるいは requirements.txt の内容を追記したい場合はお知らせください。必要に応じてサンプル .env.example も作成します。