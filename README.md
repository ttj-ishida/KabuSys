KabuSys — 日本株自動売買システム（抜粋コードベース）
=================================

このリポジトリは日本株自動売買システム「KabuSys」の主要モジュール群（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI 補助など）の実装例を含みます。ここでは配布されている主要スクリプト・設定方法・利用方法・ディレクトリ構成を日本語でまとめます。

概要
---
KabuSys は以下の責務を持つモジュール群で構成された自動売買システム設計のサンプル実装です（本リポジトリは全機能を網羅する最終製品ではなく、各コンポーネントの設計・振る舞いを示すコード群です）:

- ExecutionEngine: 注文発行・リスク管理・リコンシリエーション（再起動時の同期）を行う。
- Monitoring: システム状態、注文滞留、ドローダウン等を定期監視し、LINE 通知や停止フラグ（kill.flag）発行を行う。
- Portfolio: 候補選定、重み計算、単元丸め、セクター制限、ポジションサイジング等の純関数群。
- Research: DuckDB を用いたファクター計算・将来リターン・IC（情報係数）計算等。
- AI 補助: OpenAI（gpt-4o-mini）を使ったニュースセンチメント（ai_scores）や市場レジーム判定（market_regime）。
- Tools: Paper Trading 検証レポート生成、Streamlit ベースの監視ダッシュボード等。

主な機能一覧
---
- 実行（run_execution.py）
  - ブローカークライアント生成（実口座 / ペーパートレードを切替）
  - 注文管理（OrderManager）、リスク管理（RiskManager）
  - 再起動時のリコンシリエーション（Reconciler）
  - DuckDB / SQLite を用いた永続化

- 監視（run_monitoring.py、MonitoringEngine）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 条件に応じて data/kill.flag を作成して ExecutionEngine 停止シグナル
  - AlertManager: LINE API へのプッシュ通知（クールダウン管理）
  - Streamlit ダッシュボード（監視用）

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等金額/スコア加重、position sizing（単元丸め、リスクベース等）
  - セクター上限・レジーム乗数の適用

- リサーチ（kabusys.research）
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン、IC、統計サマリー等

- AI（kabusys.ai）
  - news_nlp: ニュース記事を集約して OpenAI に投げ、銘柄ごとにセンチメントを ai_scores に保存
  - regime_detector: ETF の MA とマクロニュースでレジーム判定

セットアップ手順
---
前提
- Python 3.9+（typing の一部機能や型注釈を利用）
- SQLite（標準ライブラリ）
- DuckDB（Python バインディング）
- ネットワークアクセス（OpenAI / LINE を使う場合）

1) 仮想環境作成（推奨）
- Unix/macOS:
  - python -m venv .venv
  - source .venv/bin/activate
- Windows:
  - python -m venv .venv
  - .venv\Scripts\activate

2) 必要パッケージのインストール（例）
- pip install duckdb psutil requests openai streamlit

（プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用してください）

3) 環境変数 / .env の準備
- プロジェクトルート（.git または pyproject.toml を基準）に .env（および任意で .env.local）を置くと自動で読み込まれます。
- 自動ロードを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な環境変数（Settings から抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須機能で使用する場合）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant|partial|never|reject、デフォルト instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- KABUSYS_ENV: 起動環境（development | paper_trading | live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

使い方（主要スクリプト）
---
1) 監視ループ起動（Monitoring）
- 環境変数 MONITOR_POLL_INTERVAL で秒を指定可能（例: 30）
- 実行:
  - python -m kabusys.run_monitoring
- 仕様:
  - 起動時にプロセス優先度を "high" に設定し、SQLite（monitoring DB）と DuckDB に接続して SystemMonitor のポーリングを行います。
  - 監視ログ・リスクイベントを data/monitoring.db に保存します。

2) 実行エンジン起動（Execution）
- paper_trading モードの例:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
  - paper_trading のときは BrokerClient の Mock 実装を使い、data/paper_trading.db に記録します（本番 DB と分離）。
- live / development でも同様に実行可能（設定に依存）。

3) Paper Trading 検証レポート
- SQLite（paper_trading）DB から検証レポートを生成します。
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

4) Streamlit ダッシュボード（監視）
- 実行:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ブラウザで監視ダッシュボードを表示します（read-only で DB を開きます）。

注意点 / トラブルシューティング
- .env の自動ロード:
  - config._find_project_root() によりプロジェクトルートを自動判定し .env / .env.local を読み込みます。CWD に依存しない設計です。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は冪等で、足りないカラムを自動追加する簡易マイグレーションを含みます（例: trade_logs.latency_ms, dashboard.peak_value）。
- PID / kill.flag:
  - ExecutionEngine は pid ファイルを書き、SystemMonitor はその存在や stale PID をチェックします。ファイル書き込み権限に注意してください。
- OpenAI / LINE:
  - AI 機能や通知には API キーが必要です。キー未設定時は該当機能を呼ばないか、機能側で明示的にエラーを投げます。
- psutil によるプロセス優先度設定や CPU affinity は OS に依存します。権限不足で警告が出る場合がありますが動作自体は継続します。

ディレクトリ構成（抜粋）
---
src/
  kabusys/
    __init__.py                        -- パッケージ情報
    config.py                          -- 環境変数/設定ロード（.env 読込含む）
    run_monitoring.py                  -- SystemMonitor ポーリングループ起動スクリプト
    run_execution.py                   -- ExecutionEngine 起動スクリプト
    tools/
      __init__.py
      paper_verification_report.py     -- Paper Trading 検証レポート生成
    ai/
      __init__.py
      news_nlp.py                      -- ニュース NLP スコアリング（OpenAI）
      regime_detector.py               -- 市場レジーム判定（MA + マクロニュース）
    monitoring/
      __init__.py
      monitoring_db.py                 -- SQLite 永続化レイヤ（system_status, trade_logs ...）
      system_monitor.py                -- CPU/メモリ/ディスク/データ鮮度監視
      trade_monitor.py                 -- 注文滞留・約定異常監視
      risk_monitor.py                  -- ドローダウン・ポジション上限監視
      kill_switch.py                   -- kill.flag 書込み/評価
      alert_manager.py                 -- LINE Push 通知
      monitoring_engine.py             -- 各 Monitor を束ねる
      streamlit_dashboard.py           -- Streamlit 監視ダッシュボード
    execution/
      order_manager.py                 -- 注文状態遷移・送信ラッパ
      reconciler.py                    -- 起動時リコンシリエーション（同期）
      (その他: broker_factory, order_repository, risk_manager など)
    portfolio/
      portfolio_builder.py             -- 候補選定 / 重み計算
      position_sizing.py               -- 株数決定 / 単元丸め / aggregate cap
      risk_adjustment.py               -- セクターキャップ / レジーム乗数
      __init__.py
    research/
      factor_research.py               -- Momentum/Volatility/Value ファクター
      feature_exploration.py           -- 将来リターン / IC / 統計サマリ
      __init__.py
    utils/
      __init__.py
      process_priority.py              -- プロセス優先度/CPU affinity ユーティリティ
    data/ (想定)
      (DuckDB / SQLite のデータファイルや各種マスタ/テーブルはここを想定)

開発・拡張のガイドライン（簡潔）
---
- 設定は config.Settings 経由で取得してください。直接 os.environ を使わないこと。
- DB スキーマ変更は monitoring_db.init_monitoring_db に追加可能な簡易マイグレーションを書いて冪等性を保つこと。
- AI 呼び出し部分は外部 API の不安定性に備え、リトライ・フォールバック（0.0 など）を行っています。テスト時は _call_openai_api をモックする設計です。
- Streamlit は監視向けの読み取り専用ビューを提供します。DB を読み出す際は読み取り専用モードで接続すると安全です。

ライセンス・注意
---
- 本 README は提供されたコードから推測される仕様をまとめたものです。実運用前に必ずコードレビュー・セキュリティ・料金（API 利用料等）・法令順守を確認してください。

必要なら、セットアップ手順の詳細化（requirements.txt 作成、systemd ユニットの例、.env.example のテンプレートなど）や、各モジュール（ExecutionEngine や Broker API）の起動フロー詳細を加えた README の拡張版を作成します。必要な内容を教えてください。