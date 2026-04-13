# KabuSys

日本株向け自動売買システムの一部（ライブラリ＋運用ユーティリティ群）。  
このリポジトリには発注・監視・ポートフォリオ構築・ファクター計算・AI（ニュース解析／レジーム判定）等のモジュールが含まれます。

※ 本 README は src/kabusys 以下のコードベースに基づいています。

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントから構成される日本株自動売買支援システムです。

- Execution（発注系）: ブローカーとのインタラクション、注文の状態管理、リコンシリエーション
- Monitoring（監視系）: プロセス／システム指標、注文滞留、リスク（ドローダウン・ポジション数）監視、アラート
- Portfolio（ポートフォリオ構築）: 候補選定、配分重み、ポジションサイズ決定、セクター上限など
- Research（調査系）: ファクター算出、将来リターン計算、IC 等の統計処理
- AI（ニュース NLP / レジーム判定）: OpenAI を用いたニュースセンチメント・マクロセンチメント評価
- Tools（ユーティリティ）: Paper Trading の検証レポート生成やダッシュボード起動スクリプトなど

設計方針として、DB は SQLite（監視）／DuckDB（履歴価格等の分析）を利用し、テスト可能でフェイルセーフな実装（例: API失敗時はスキップ）を心がけています。

---

## 主な機能一覧

- システム監視（CPU / メモリ / ディスク / プロセス生存判定）
- 注文滞留検出、約定異常（価格偏差）検出
- ドローダウン・ポジション上限監視と kill flag による実行停止シグナル発行
- LINE Push によるアラート（Cooldown 管理）
- ExecutionEngine（発注実行フロー）、OrderManager による二相コミット風の堅牢な発注処理
- 起動時のリコンシリエーション（OrderSent の突合、ポジション差分記録）
- ポートフォリオ構築：候補選定、等加重/スコア加重、リスクベースの株数算出、セクター制限、レジーム乗数
- Research：Momentum / Volatility / Value 等のファクター算出、将来リターン・IC・統計サマリ
- AI モジュール：ニュースを LLM でスコアリング（銘柄ごと）、マクロニュースで市場レジーム判定
- Paper Trading 用検証レポート（期間指定で統計を集約）
- Streamlit による監視ダッシュボード（read-only 接続で監視 DB を可視化）

---

## セットアップ手順（開発 / 運用向け）

前提
- Python 3.10 以上（typing の | 記法や from __future__ annotations を使用）
- SQLite / DuckDB（Python パッケージで利用）
- ネットワークが必要（OpenAI / LINE API などを使用する場合）

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （開発時はその他テスト用パッケージ等も追加）

   例（最低限）:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit

3. プロジェクトルートに .env ファイルを配置（任意）
   - config.py はプロジェクトルート（.git または pyproject.toml がある場所）を探索して `.env` / `.env.local` を自動読み込みします。
   - 自動ロードを無効化する場合: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. データディレクトリ作成
   - data/ フォルダを作成（デフォルトの DB パスや PID ファイルの保存先）
   - mkdir -p data

5. 主要な環境変数（例）
   - KABUSYS_ENV: 実行モード（development | paper_trading | live）デフォルト: development
   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須な箇所あり）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須な箇所あり）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に必要
   - SQLITE_PATH: 監視 DB path（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB path（デフォルト: data/kabusys.duckdb）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 sqlite（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE: paper_trading の約定動作（instant | partial | never | reject、デフォルト: instant）
   - PID_FILE_PATH / KILL_FLAG_PATH: PID / kill.flag の場所
   - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）

注意:
- run_monitoring（監視）は KABUSYS_ENV に関係なく「本番」の sqlite_path を使用します（run_execution は paper_trading の場合に分離された DB を使います）。

---

## 使い方（主要スクリプト・コマンド）

プロジェクトをパッケージとして扱う前提で、モジュールを -m で直接実行できます。

1. 監視ループ起動（Monitoring）
   - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（正の整数）。
   - 実行:
     - python -m kabusys.run_monitoring
   - 補足:
     - 起動時にプロセス優先度を "high" に変更しようとします（権限不足などで失敗することがあります）。
     - 監視 DB は settings.sqlite_path（デフォルト data/monitoring.db）に接続します。

2. 発注エンジン起動（Execution）
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録されます（本番 DB と分離）。
   - 実行:
     - python -m kabusys.run_execution
   - 補足:
     - 起動時にプロセス優先度を "high" に設定します。
     - 実際のブローカー接続情報や API トークンは環境変数で設定してください。

3. Paper Trading 検証レポート
   - usage:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - オプション: --db パスで DB を指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

4. Streamlit ダッシュボード（監視）
   - 実行:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - read-only 接続で DB を開くため、MonitoringEngine が作成する monitoring.db を指定してください。

5. AI 機能（ニューススコア／レジーム判定）
   - OpenAI API キーが必要（OPENAI_API_KEY）。関数はプログラムから呼び出す形で利用します（kabusys.ai.score_news / score_regime）。
   - 大量の API 呼び出しはレート制限やコストに注意。

6. kill.flag の取り扱い
   - KillSwitch は data/kill.flag を作成して ExecutionEngine に停止シグナルを送ります。
   - 起動時に Kill flag をクリアする設定（KILL_FLAG_CLEAR_ON_START=1）があります（Settings.kill_flag_clear_on_start）。

---

## 環境変数（抜粋とデフォルト）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）デフォルト: INFO
- SQLITE_PATH: data/monitoring.db
- DUCKDB_PATH: data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: "1" で起動時に kill.flag を削除
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒（デフォルト 60）
- OPENAI_API_KEY: OpenAI API キー（AI 機能に必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に必要

（config.py 内の Settings クラス参照で他の設定・検証ロジックを確認できます）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主なファイル・ディレクトリ構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 読み込み / Settings
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite を使った監視ログ永続化
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py       — 注文滞留／約定異常監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の管理
    - alert_manager.py       — LINE 通知
    - monitoring_engine.py   — 複数 Monitor の統合ポーリング
    - streamlit_dashboard.py — Streamlit 監視ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py          — 起動時リコンシリエーション
    - (その他: broker_factory, execution_engine, order_repository 等はコード内参照)
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
    - news_nlp.py            — ニュースを LLM でスコアリング
    - regime_detector.py     — マクロ＋ETF MA200 によるレジーム判定
  - utils/
    - __init__.py
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - data/ (実行時に作成・利用される想定)
    - kabusys.duckdb (デフォルト)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)

---

## 運用上の注意点 / 実装上のポイント

- run_monitoring は Settings.env に関わらず monitoring DB（sqlite_path）を使います。監視は本番 DB に対して行う設計です。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使って本番データと分離します。
- .env のパースは細かいルール（export プレフィックス対応・クォート内のエスケープ対応・インラインコメント処理等）を実装しています。config.py を参照してください。
- MONITOR_POLL_INTERVAL に 0 以下や非整数を与えると警告してデフォルト値（60 秒）にフォールバックします。
- OpenAI 呼び出しはリトライ（指数バックオフ）を実装していますが、API コストやレート制限に注意してください。API の失敗は通常フェイルセーフ（代替値で継続）になっています。
- process priority / cpu affinity の設定はプラットフォーム依存です。権限不足や非対応 OS の場合は警告が出てスキップされます。
- Streamlit ダッシュボードは監視 DB に read-only で接続するため、MonitoringEngine を先に起動してログを生成してください。

---

## よくある操作例

- 監視（バックグラウンドで常時稼働させる）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring &

- 発注エンジン（Paper Trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポート（期間指定）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

必要であれば、README に以下を追加できます：
- 具体的な requirements.txt（推奨パッケージとバージョン）
- サンプル .env.example
- 実行時の systemd / supervisord 用 unit / service 定義例
- 詳細な API ドキュメント（各モジュールの public API）
ご希望があれば追記します。