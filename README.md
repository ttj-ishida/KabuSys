# KabuSys

KabuSys は日本株向けの自動売買システムのコアライブラリです。  
このリポジトリには、発注エンジン（ExecutionEngine）、監視モジュール（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、および AI ベースのニュースセンチメント / レジーム判定などの機能群が含まれます。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- Execution
  - ExecutionEngine を起動して発注フローを実行
  - Broker クライアントの切替（実口座 / paper_trading の Mock）
  - 起動時のリコンシリエーション（未確定注文の突合せ）
  - OrderManager / OrderRepository による堅牢な注文状態管理

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態 / データ鮮度の監視
  - TradeMonitor: 注文滞留 (stale orders)、約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件に応じてフラグファイルを書き込み ExecutionEngine の停止を促す
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（read-only で監視 DB を表示）

- Portfolio
  - 候補選定・重み付け（等金額・スコア加重）
  - セクター制限・レジーム乗数適用
  - 発注株数計算（単元丸め・リスクベース配分・集約上限スケーリング）

- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算、特徴量サマリ

- AI モジュール
  - news_nlp: OpenAI を用いたニュース記事の銘柄ごとのセンチメント計算（ai_scores 書き込み）
  - regime_detector: ETF(1321) の MA とマクロニュースの LLM センチメントを合成して日次レジーム判定

- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率 / 注文成功率 / レイテンシ 等）

- 設定管理
  - .env 互換の自動読み込み（プロジェクトルートの .env / .env.local）、Settings クラスで環境変数をラップ

---

## 必要条件（推奨）

- Python 3.9+
- DuckDB Python パッケージ
- psutil
- requests
- openai (AI 機能を使う場合)
- streamlit（ダッシュボードを使う場合）

（実際の環境依存: requirements.txt がある場合はそちらを参照してください。なければ次のようにインストールします）
例:
- 仮想環境作成:
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- パッケージインストール（例）:
  - pip install duckdb psutil requests openai streamlit

---

## セットアップ手順

1. リポジトリをクローン / コピーし、カレントディレクトリをプロジェクトルートにする（pyproject.toml または .git を基準に自動で .env を探します）。
2. 仮想環境を作成して有効化する（推奨）。
3. 必要パッケージをインストールする（上記参照）。
4. 環境変数を設定する:
   - .env または OS の環境変数を使用します。自動ロードはデフォルトで有効（プロジェクトルートの .env / .env.local）。
   - 自動ロードを無効にする場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. DB の初期化:
   - 実行スクリプト（run_monitoring / run_execution）が起動時に監視 DB テーブルを冪等的に作成します。手動で準備する必要は基本的にありません。

---

## 主要な環境変数（Settings によるラップ）

- 必須（実運用で必要）
  - JQUANTS_REFRESH_TOKEN (J-Quants API トークン)
  - KABU_API_PASSWORD (kabu API 用パスワード)

- OpenAI（AI 機能を使う場合）
  - OPENAI_API_KEY

- 実行モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading の場合、MockBrokerClient を使いデータは PAPER_TRADING_SQLITE_PATH に記録されます（本番 DB と分離）

- データベース / ファイルパス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - PID_FILE_PATH（ExecutionEngine PID ファイル、デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（kill.flag、デフォルト: data/kill.flag）

- 監視関連
  - MONITOR_POLL_INTERVAL: SystemMonitor のポーリング間隔（秒。デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: Execution 起動時に既存 kill.flag を自動クリアするか ("1" で有効)
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視用閾値）

- Paper Trading 動作
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- ログ
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

---

## 使い方（起動例）

注意: パッケージをモジュールとして実行するため、PYTHONPATH に `src` を指定するかパッケージをインストールしてください。

方法 A: 開発環境で直接実行
- PYTHONPATH=src を使う例（Unix 系）
  - KABUSYS_ENV=paper_trading PYTHONPATH=src python -m kabusys.run_execution
  - PYTHONPATH=src python -m kabusys.run_monitoring

方法 B: 開発インストール
- pip install -e .
- python -m kabusys.run_execution
- python -m kabusys.run_monitoring

実行スクリプトの説明:
- run_execution.py
  - ExecutionEngine を起動します。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用し MockBrokerClient を使います。
  - 起動直後にプロセス優先度を "high" に設定します（set_process_priority）。
- run_monitoring.py
  - SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL により間隔を上書き可）。
  - 監視は常に monitoring 用 sqlite_path（Settings.sqlite_path）を使用します。

ツール:
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB パス指定: --db PATH（デフォルト：data/paper_trading.db）

監視ダッシュボード（Streamlit）
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を read-only モードで開き、ポジション / オーダー / システム状態 / リスクログ 等を表示します。

ログレベル変更例:
- LOG_LEVEL=DEBUG python -m kabusys.run_monitoring

プロセス制御:
- ExecutionEngine の停止は KillSwitch により data/kill.flag を書き込むことで行われます（kill.flag を監視して処理を安全に停止する実装）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み取り・Settings クラス、.env 自動読み込みロジック
  - run_execution.py
    - ExecutionEngine 起動スクリプト（本番 / paper_trading の切替）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - order_manager.py, reconciler.py, ...（発注ロジック、ブローカー抽象）
  - monitoring/
    - monitoring_db.py（SQLite スキーマ + 永続化 API）
    - system_monitor.py, trade_monitor.py, risk_monitor.py
    - monitoring_engine.py（複数モニタを束ねてポーリング）
    - alert_manager.py（LINE への push）
    - kill_switch.py（フラグファイルによる停止）
    - streamlit_dashboard.py（監視ダッシュボード）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - research/
    - factor_research.py, feature_exploration.py
  - ai/
    - news_nlp.py（ニュースセンチメント）
    - regime_detector.py（市場レジーム判定）
  - tools/
    - paper_verification_report.py（Paper Trading の検証レポート）

その他:
- data/ (想定)
  - kabusys.duckdb
  - monitoring.db
  - paper_trading.db
  - kill.flag
  - execution.pid

---

## 実装上の注意点 / 補足

- DB 初期化
  - monitoring 用スキーマ（system_status, trade_logs, positions, risk_logs, dashboard）は init_monitoring_db() によって冪等的に作成されます。run_monitoring / run_execution は起動時にこの初期化を行います。

- Paper Trading
  - KABUSYS_ENV=paper_trading を指定すると paper_trading 用 sqlite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離して動作します。
  - PAPER_FILL_MODE によって MockBroker の約定挙動を変えられます（instant / partial / never / reject）。

- OpenAI API
  - news_nlp.py / regime_detector.py は OpenAI（gpt-4o-mini）を呼び出します。API キーが必要です（OPENAI_API_KEY）。
  - API 呼び出しはリトライ・バックオフ・レスポンス検証が実装されていますが、API 利用には費用がかかります。

- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml を検出）から .env/.env.local を自動読み込みします。
  - テスト等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- プロセス優先度 / CPU affinity
  - 起動時に set_process_priority("high") を呼び出します。権限が不足する場合や未対応 OS のときは警告ログを出してスキップします。

- Streamlit ダッシュボードは DB を read-only で開きます。監視実行中に同時読み書きしても安全に参照できるよう URI に ?mode=ro を付けて接続しています。

---

## 開発 / テストのヒント

- 単体関数群（portfolio / research 等）は副作用がなく純粋関数として設計されている部分が多く、ユニットテストが書きやすいです。
- AI 部分やネットワーク I/O は外部呼び出しをモックしやすいよう内部呼び出しをラップしています（テスト時に patch 可能）。
- Settings の自動 .env 読み込みは便利ですが、テストで環境を制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って明示的に環境をセットしてください。

---

README は以上です。必要があれば以下を追記できます:
- 依存関係の requirements.txt（推奨パッケージとバージョン）
- 実行例のより詳しいコマンド（systemd / Docker / supervisor 用のサンプル）
- DB スキーマの詳細ドキュメント（列の説明）