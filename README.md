# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ＋実行スクリプト群）。  
このリポジトリには実行エンジン、監視（Monitoring）コンポーネント、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などの主要機能が含まれています。

---

## プロジェクト概要

KabuSys は以下の役割を持つコンポーネント群で構成されています。

- Execution：発注・注文管理・リスク管理・再同期待ち合わせ（Reconciler）など、実際の発注処理を行うエンジン
- Monitoring：システム稼働状態、注文滞留・約定異常、ドローダウン等を定期チェックしてログ／アラート／停止フラグを管理
- Portfolio：銘柄候補選定・配分重み計算・ポジションサイズ決定・セクター制約等の純粋関数群
- Research：ファクター計算、将来リターン計算、IC 評価などの調査用ツール
- AI：ニュースのセンチメントスコアリング（OpenAI）や市場レジーム判定
- Tools：Paper Trading 検証レポート等のユーティリティスクリプト
- CLI / スクリプト：run_execution.py / run_monitoring.py / streamlit ダッシュボード 等

設計上、DB（SQLite / DuckDB）を用いた永続化と、環境変数を使った柔軟な設定を特徴とします。

---

## 主な機能一覧

- 実行エンジン起動（run_execution.py）
  - ライブ / ペーパー（paper_trading）切替。paper_trading 時は MockBroker を使用し専用 DB に記録。
  - Reconciler による起動時復旧
  - リスク管理（ポジション上限、ドローダウン等）
- 監視エンジン起動（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリング
  - LINE によるアラート送信（AlertManager）
  - KillSwitch による停止フラグ（kill.flag）発行
  - Streamlit ダッシュボードで監視情報表示
- ポートフォリオ構築（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap 等）
- リサーチ（ファクター計算: momentum/volatility/value、forward returns、IC、統計サマリ）
- AI（news_nlp: OpenAI によるニュースセンチメント、regime_detector: マクロ + ETF MA200 を合成してレジーム判定）
- ユーティリティ：Paper Trading 検証レポート生成スクリプト

---

## セットアップ手順（ローカル開発 / 実行）

1. リポジトリをクローンしてワークディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール
   - 主要依存（本コードベースから推察）:
     - duckdb, psutil, requests, openai, streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   ※ 実際の requirements.txt がある場合はそれを利用してください。

4. 環境変数の設定
   - .env / .env.local をプロジェクトルートに置くと自動で読み込まれます（.git または pyproject.toml を起点にプロジェクトルートを探索）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（主なデフォルト値を併記）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 時の SQLite（デフォルト: data/paper_trading.db）
     - DUCKDB_PATH: 価格等の時系列データ（デフォルト: data/kabusys.duckdb）
     - OPENAI_API_KEY: OpenAI 呼び出しに必要
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須な箇所あり）
     - KABU_API_PASSWORD: kabuステーション API 用（必須な箇所あり）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（未設定時は送信スキップ）
     - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔秒（run_monitoring 用、デフォルト: 60）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
     - PID_FILE_PATH, KILL_FLAG_PATH など（デフォルトは data/ 以下）

5. DB 初期化
   - run_monitoring.py / run_execution.py は起動時に監視用テーブルを作成します（init_monitoring_db）。DuckDB 側は必要なテーブル（prices_daily, raw_news, raw_financials, news_symbols, ai_scores, market_regime 等）を事前に用意してください（解析/AI 機能を使う場合）。

---

## 使い方（主要コマンド / 実行例）

- 監視ループ起動（Monitoring）
  - デフォルトポーリング間隔 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可。
  - 実行:
    - python -m kabusys.run_monitoring
  - 停止: プロセスを Ctrl+C、またはプロジェクトルートの data/stop_requested.flag を作成すると安全終了。

- 実行エンジン起動（ExecutionEngine）
  - ペーパートレード実行:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - ライブ実行:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - 実行中にプロジェクトルートの data/stop_requested.flag が作成されると停止要求が検出され Engine を停止します。
  - ExecutionEngine は data/execution.pid（デフォルト）を書き、run_monitoring/system_monitor が PID ファイルの有無・生存確認を行います。

- Streamlit ダッシュボード（監視）
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB が存在し読み取り可能であることが必要（監視を先に起動してデータを書き込んでおく）。

- Paper Trading 検証レポート
  - 使い方（ヘッダーに記載）:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスはオプション --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能（デフォルト: data/paper_trading.db）。

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要。
  - モジュール関数を直接呼び出す形:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - DuckDB に必要なテーブル（raw_news, news_symbols, ai_scores, prices_daily 等）が揃っていること。

- Kill Switch / Stop
  - KillSwitch はリスク条件（ドローダウン、ポジション上限）満たすと data/kill.flag を書き、ExecutionEngine 側で停止判定に用います。
  - kill.flag のデフォルトパスは Settings.kill_flag_path（デフォルト data/kill.flag）。
  - kill.flag を消去する機能も提供（KillSwitch.clear）。

---

## 設定（Settings）についての補足

- 設定は環境変数経由で取得され、Settings クラス（kabusys.config）からアクセスできます。よく使う設定とデフォルト:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - DUCKDB_PATH: data/kabusys.duckdb
  - PAPER_FILL_MODE: instant (valid: instant|partial|never|reject)
  - LOG_LEVEL: INFO（DEBUG 等に変更可能）
  - PID_FILE_PATH / KILL_FLAG_PATH: default は data/ 以下

- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml を探索）を基に .env / .env.local を自動で読み込みます。
  - OS 環境変数が優先され、.env.local は .env を上書きします。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

---

## ディレクトリ構成（主要ファイル）

下記は src/kabusys 以下の主要ファイル／ディレクトリ（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - run_monitoring.py             — Monitoring ポーリング起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite 監視ログ永続化層
    - monitoring_engine.py         — 各 Monitor を束ねる Engine
    - system_monitor.py            — CPU/Mem/Disk / データ鮮度 / プロセス監視
    - trade_monitor.py             — 注文滞留 / 約定異常監視
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - kill_switch.py               — kill.flag 書き込みユーティリティ
    - alert_manager.py             — LINE 通知
    - streamlit_dashboard.py       — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py          — (主要実行ロジック; 一部は別ファイルに分割)
    - broker_factory.py
    - broker_api.py
    - order_record.py
    - order_repository.py
    - order_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/                           — 実行時データファイル（data/*.db, pid/flag 等）を想定
  - utils/
    - __init__.py
    - process_priority.py           — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記は抜粋です。詳細は各ファイルの docstring / コメントを参照してください。）

---

## 運用上の注意点 / 補足

- DB とデータ整合性
  - Monitoring のテーブルは init_monitoring_db() により自動作成／マイグレーションされます（SQLite）。
  - DuckDB の prices_daily / raw_financials / raw_news 等は外部導入が必要です（リサーチ／AI 機能で利用）。
- ペーパートレード環境
  - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を利用し、本番 DB と分離された PAPER_TRADING_SQLITE_PATH に記録されます。
- OpenAI 利用
  - AI 機能は OPENAI_API_KEY を要求します。API のレート制限やエラーに対してはリトライやフォールバックが実装されていますが、コストに注意してください。
- 停止フラグ / PID
  - run_execution/run_monitoring は data/stop_requested.flag の存在を見て安全に停止します。また実行エンジンは data/execution.pid を書きます。
- プロセス優先度設定
  - 起動時に set_process_priority("high") を呼び出し、psutil を使って優先度を設定します。権限不足などで設定できない場合は警告を出してスキップします。

---

README は上記の概要と実行手順を押さえていれば基本的に運用を開始できます。  
さらに詳細な動作（ExecutionEngine の内部フロー、DB スキーマ、外部 API の挙動、ユニットテスト等）は各モジュールの docstring と実装を参照してください。もし README に追加してほしい実例（.env.example のテンプレート、docker-compose 例、CI 設定等）があれば教えてください。