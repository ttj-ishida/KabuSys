# KabuSys

KabuSys は日本株向けの自動売買・リサーチ・監視用ライブラリ群です。本リポジトリには以下の主要機能が含まれます:

- 注文発行・状態管理を行う ExecutionEngine（本番 / ペーパートレード対応）
- モニタリング（システム状態・注文滞留・リスク監視）とアラート送信（LINE）
- Portfolio Construction（候補選定・重み付け・ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量探索）
- AI を利用したニュースセンチメント / 市場レジーム判定（OpenAI）
- Paper Trading 検証レポート生成、Streamlit ダッシュボード

以下にプロジェクト概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成をまとめます。

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群から構成されています。

- execution: ブローカー API を介した注文管理、再同期（Reconciler）、リスク管理との連携
- monitoring: system / trade / risk の監視、ログ永続化（SQLite）、アラート（LINE）、監視ダッシュボード（Streamlit）
- portfolio: 銘柄選定・重み計算・セクター制限・ポジションサイズ計算（純粋関数）
- research: DuckDB 上の時系列データを用いたファクター計算や特徴量解析
- ai: OpenAI を使ったニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）
- tools: Paper Trading 検証レポート出力スクリプトなど
- utils / config: 環境変数読み込みやプロセス優先度設定などのユーティリティ

設計上のポイント:
- 計算ロジックは可能な限り副作用を持たない純粋関数として実装（単体テストしやすい）
- 環境変数 / .env を用いた設定管理（Settings クラス）
- Paper Trading と本番 DB の分離（KABUSYS_ENV による挙動切替）
- DuckDB を分析用データストア、SQLite を監視/発注ログ用に利用

---

## 機能一覧

主要な機能の概要：

- 実行系
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ペーパートレード環境では MockBrokerClient を利用し、data/paper_trading.db に記録
  - Reconciler による起動時の注文 / ポジション再同期

- 監視系
  - SystemMonitor: CPU / メモリ / ディスク / プロセス PID チェック、データ鮮度チェック
  - TradeMonitor: 注文滞留（stale orders）・約定レート異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視・ダッシュボード更新
  - KillSwitch: リスク条件に応じてフラグファイルを書き ExecutionEngine の停止を指示
  - AlertManager: LINE Push を使ったアラート送信（クールダウン機構あり）
  - Streamlit ダッシュボードで監視データの可視化

- ポートフォリオ構築
  - 候補選定、等重・スコア重み、リスクベース配分、単元株丸め、セクターキャップ、レジーム乗数

- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB SQL）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー

- AI（OpenAI）
  - ニュースをバッチして LLM に投げ、銘柄別センチメントを ai_scores テーブルへ書き込み
  - マクロニュース + ETF MA 乖離を組み合わせた市場レジーム判定（冪等 DB 書き込み）
  - API 呼び出しはリトライ/フォールバックを考慮（429/タイムアウト/5xx 等）

- ツール
  - Paper Trading 検証レポート出力ツール（期間指定で稼働率/成功率/レイテンシ等を出力）

---

## セットアップ手順

※ 本プロジェクトは Python 3.10+（PEP 604 の型記法や未来注釈を想定）を想定しています。適宜ご利用環境に合わせてください。

1. リポジトリをクローン
   - 例: git clone ...

2. 仮想環境作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 主要依存例（プロジェクトの requirements.txt があればそれを使用してください）:
     - duckdb
     - psutil
     - requests
     - streamlit
     - openai
   - 例:
     - pip install duckdb psutil requests streamlit openai

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（既存 OS 環境変数は保護されます）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   - 主な設定キー（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY
     - KABUSYS_ENV = development | paper_trading | live
     - PAPER_FILL_MODE = instant | partial | never | reject
     - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PID_FILE_PATH (default: data/execution.pid)
     - KILL_FLAG_PATH (default: data/kill.flag)
     - LOG_LEVEL (DEBUG/INFO/...)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔 override、秒、run_monitoring 用）

   - .env の書式は shell 形式（コメント、export KEY=val、クォート対応）に準拠しています。

5. データベース初期化
   - 監視用 SQLite は起動スクリプトが必要なテーブルを自動作成します（init_monitoring_db を実行）。
   - DuckDB は分析用テーブル（prices_daily / raw_financials / raw_news 等）を用意しておいてください（データロードは別途）。

注意:
- プロセス優先度を high に設定する処理（psutil に依存）があります。権限やプラットフォームにより設定に失敗し警告が出ますが、致命的ではありません。
- OpenAI を使う機能は OPENAI_API_KEY が必須です。キー未設定時は例外やスキップの扱いになります（関数ごとに挙動が異なります）。

---

## 使い方

以下は主要な実行例です。パッケージとしてインストールしていない場合は `python src/...` で直接実行できます。パッケージ形式でインストール済みなら `python -m kabusys.<module>` で実行できます。

1. 監視ループ起動（SystemMonitor をポーリング）
   - 実行ファイル: src/kabusys/run_monitoring.py
   - 簡単な実行:
     - python src/kabusys/run_monitoring.py
     - またはパッケージ化している場合:
       - python -m kabusys.run_monitoring
   - オプション:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
   - 動作メモ:
     - Monitoring は KABUSYS_ENV に関わらず `Settings.sqlite_path`（本番パス）を使用してログを記録します。

2. ExecutionEngine 起動（注文実行）
   - 実行ファイル: src/kabusys/run_execution.py
   - 実行:
     - python src/kabusys/run_execution.py
     - あるいは: python -m kabusys.run_execution
   - 動作メモ:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、Paper 用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用して本番 DB と分離します。
     - 起動時に Reconciler による同期処理が行われます。
     - PID ファイル（Settings.pid_file_path）に PID を書きます。KillSwitch は KILL_FLAG_PATH のファイル存在で停止を検知します。

3. Streamlit ダッシュボード
   - ファイル: src/kabusys/monitoring/streamlit_dashboard.py
   - 起動例:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 説明:
     - 監視用 SQLite を読み取り専用で開き、Overview / Positions / Orders / System タブを表示します。

4. Paper Trading 検証レポート
   - スクリプト: src/kabusys/tools/paper_verification_report.py
   - 実行例:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - --db で DB パスを上書き可能（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）
   - 出力:
     - 稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数などを標準出力に整形して出力します。

5. AI 関連（プログラム API）
   - ニュースセンチメント:
     - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
     - 必要: DuckDB 接続（raw_news / news_symbols / ai_scores テーブル）と OpenAI API key（api_key 引数または環境変数 OPENAI_API_KEY）
   - 市場レジーム判定:
     - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
     - DuckDB の prices_daily / raw_news / market_regime テーブルを使用し、計算結果は market_regime に冪等で書き込まれます

6. 設定確認 / .env 自動読み込み
   - Settings クラス（kabusys.config.Settings）が環境変数をラップしています。
   - .env の読み込み順序: OS 環境変数 > .env.local > .env（自動ロードはデフォルト有効）
   - 自動ロードを無効にする:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 主要ファイル / ディレクトリ構成

以下はコードベースの主要ファイルと簡単な説明です（抜粋）。

- src/kabusys/
  - __init__.py: パッケージ定義（__version__ 等）
  - config.py: 環境変数と .env 読み込み、Settings クラス
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ（psutil）
  - monitoring/
    - __init__.py
    - monitoring_db.py: SQLite による監視ログ永続化層（テーブル作成・マイグレーション含む）
    - system_monitor.py: CPU/メモリ/ディスク/データ鮮度 / PID チェック
    - trade_monitor.py: 注文滞留・約定異常監視
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - kill_switch.py: kill.flag を書き ExecutionEngine 停止シグナルを送る
    - alert_manager.py: LINE Push 通知（クールダウンあり）
    - monitoring_engine.py: 各 Monitor を束ねる（run / run_once）
    - streamlit_dashboard.py: Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py: Order state machine の外向き API
    - reconciler.py: 起動時の注文・ポジション再同期
    - order_repository.py, order_record.py, broker_*: （発注処理、ブローカーラッパー等、実装ファイル）
  - portfolio/
    - portfolio_builder.py: 候補選定・重み計算
    - position_sizing.py: 株数決定・集計キャップ処理
    - risk_adjustment.py: セクターキャップ・レジーム乗数
    - __init__.py: エクスポート
  - research/
    - factor_research.py: Momentum / Volatility / Value の計算（DuckDB）
    - feature_exploration.py: 将来リターン・IC・統計サマリー
    - __init__.py
  - ai/
    - news_nlp.py: ニュースを LLM に投げて銘柄別センチメントを生成
    - regime_detector.py: ETF MA + マクロニュースでレジーム判定
    - __init__.py
  - tools/
    - __init__.py
    - paper_verification_report.py: Paper Trading 検証レポート出力ツール

---

## 運用上の留意点

- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離されています。誤って本番 DB を操作しないように env を確認してください。
- run_monitoring は監視ログ用 SQLite を常に本番パスで開きます（環境にかかわらず）。
- process priority / CPU affinity 設定はプラットフォーム依存です。権限不足で設定に失敗しても警告が出るのみで致命的ではありません。
- KillSwitch はファイルベース（KILL_FLAG_PATH）です。ExecutionEngine 側は起動時に kill.flag をクリアするオプション（Settings.kill_flag_clear_on_start）を持っています。
- OpenAI の呼び出しは API レートリミット・障害を考慮してリトライ／フォールバック実装がありますが、API キー管理は運用側で行ってください。

---

## よく使うコマンド例まとめ

- 監視を起動（60 秒間隔）:
  - MONITOR_POLL_INTERVAL=60 python src/kabusys/run_monitoring.py

- 実行エンジンを起動（paper_trading モードの例）:
  - export KABUSYS_ENV=paper_trading
  - python src/kabusys/run_execution.py

- Streamlit ダッシュボード起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading の検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

何か特定の箇所（例: 環境変数のテンプレート、duckdb データロード手順、API クライアントの実装例、CI 用設定）について詳細な README 追加を希望される場合は教えてください。必要に応じて .env.example の雛形や起動スクリプトの systemd ユニット例なども作成できます。