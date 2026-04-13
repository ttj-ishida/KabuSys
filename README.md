# KabuSys — README

日本株自動売買システムの一部コンポーネント群（監視・実行エンジン・リサーチ・AI補助等）。  
このリポジトリには、実行エンジンの起動スクリプト、監視機能、ポートフォリオ構築ユーティリティ、研究用ファクター計算、ニュースNLP / レジーム判定などのモジュールが含まれます。

## プロジェクト概要
- 目的: 日本株自動売買システムのコアロジック（発注管理、リコンシリエーション）、監視（プロセス/データ鮮度/注文異常/リスク）、研究用ファクター計算、AIによるニュースセンチメント評価を提供します。
- 設計方針:
  - DB（DuckDB / SQLite）を使った履歴・指標管理
  - 実行環境（本番 / ペーパー）を分離可能
  - 外部API（kabuステーション、J-Quants、OpenAI 等）との連携を想定
  - 単純関数ベースでテスト可能なコンポーネント構成

## 主な機能一覧
- 実行エンジン起動スクリプト（run_execution.py）
  - ブローカークライアント生成（paper_trading では Mock を使用）
  - OrderManager / RiskManager / Reconciler 組み立て、ExecutionEngine 実行
- 監視ループ起動スクリプト（run_monitoring.py）
  - SystemMonitor を定期ポーリングして system_status / risk_logs 等へ記録
  - MONITOR_POLL_INTERVAL でポーリング間隔上書き可（デフォルト 60秒）
- Monitoring DB（SQLite）永続化レイヤー（monitoring_db.py）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブル
  - 必要に応じたマイグレーション（カラム追加）処理を含む
- モニタ（SystemMonitor / TradeMonitor / RiskMonitor）
  - プロセス死活、データ鮮度、滞留注文、約定異常、ドローダウン、ポジション上限を検出
- KillSwitch / AlertManager
  - kill.flag による ExecutionEngine 停止シグナル、LINE Push による通知（オプション）
- Streamlit ダッシュボード（監視用）
- Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
- ポートフォリオ構築ユーティリティ（選定・重み付け・リスク調整・株数計算）
- リサーチモジュール（ファクター計算、特徴量解析、IC 計算）
- AI モジュール
  - news_nlp: raw_news を OpenAI に送り銘柄別センチメントを取得・書込
  - regime_detector: ETF（1321）MA とマクロニュースで市場レジーム判定

## 必要要件
- Python 3.10+
- 推奨パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボードを使う場合)
- SQLite（標準ライブラリに含まれます）

※ 実際の環境では requirements.txt を用意して pip でインストールしてください。

例:
pip install duckdb psutil requests openai streamlit

## 環境変数（主なもの）
- KABUSYS_ENV = development | paper_trading | live (デフォルト: development)
  - paper_trading の場合は MockBrokerClient を使用し、paper 用 DB に記録されます
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (news/regime 判定で必要)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視用デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (paper の約定挙動、instant|partial|never|reject、デフォルト: instant)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (1 にすると起動時に kill.flag を消す)
- MONITOR_POLL_INTERVAL (監視ループのポーリング間隔秒、デフォルト: 60)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (AlertManager 用)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO)

設定は .env / .env.local / OS 環境変数から読み込まれます（Settings モジュールの自動読み込み機能）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## セットアップ手順（開発環境向け、例）
1. リポジトリをクローン
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) / .venv\Scripts\activate (Windows)
3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
4. 必須環境変数を設定（.env をプロジェクトルートに置くのを推奨）
   - 例 .env:
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     KABUSYS_ENV=development
5. データディレクトリを作成
   - mkdir -p data
6. 初回は監視DBを作るか、run_* スクリプトを実行すると自動でテーブルが作成されます（init_monitoring_db を呼びます）。

## 使い方（主要スクリプト）
- 監視ループを起動
  - MONITOR_POLL_INTERVAL を環境変数で上書き可能（秒）
  - 実行:
    python -m kabusys.run_monitoring
  - 終了: Ctrl+C（KeyboardInterrupt）

- 実行エンジンを起動（トレード実行）
  - 本番/ペーパーは KABUSYS_ENV により切り替わる
  - 実行:
    python -m kabusys.run_execution

- Paper Trading 検証レポート（CLI）
  - 実行例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（デフォルトは環境変数または data/paper_trading.db）

- Streamlit 監視ダッシュボード
  - 実行:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで SQLite を開くため、MonitoringEngine を先に動かしておくことを推奨

- AI モジュール（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーが必要（api_key 引数か OPENAI_API_KEY）

## 運用上の注意 / 特記事項
- Monitoring は常に（KABUSYS_ENV に関わらず）設定された本番 sqlite_path を使用する設計です。paper_trading は run_execution 側で paper 用 SQLite を使って本番 DB と分離します。
- kill.flag によるシャットダウン
  - KillSwitch は条件（ドローダウン超過等）でデータディレクトリに kill.flag を書き込みます。ExecutionEngine は起動時にこのファイルを監視して停止する想定です（設定により起動時にクリア可能）。
- Process priority / CPU affinity
  - 起動スクリプトは最初に set_process_priority("high") を呼んでプロセス優先度を上げようとします（psutil の権限に依存）。
- DuckDB / raw データ
  - 研究・ファクター計算モジュールは DuckDB の prices_daily / raw_financials 等を参照します。データの投入は別途パイプライン（kabusys.data.pipeline）等で行う想定です。
- フェイルセーフ
  - OpenAI 呼び出しや DB の一部操作は失敗時にフォールバック（ログ出力・スキップ）するよう設計されています。

## ディレクトリ構成（抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py  — 環境変数 / .env 読み込み、Settings クラス
    - run_execution.py  — ExecutionEngine 起動スクリプト
    - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他発注関連モジュール: broker_factory 等)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - __init__.py
      - process_priority.py
    - data/ (想定: データ格納ディレクトリ)
      - *.duckdb, *.db, pid/flag ファイル 等

（実際のファイルは src/kabusys 以下を参照してください）

## サンプル .env（最小例）
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=    # 任意
LINE_USER_ID=                 # 任意

## デバッグ / 開発メモ
- 設定読み込みは config.Settings を介して行ってください。Settings は .env の自動読み込み（プロジェクトルートの .env / .env.local）を行います。
- 単体関数群（portfolio/*、research/*）は DB 参照箇所が明示されており、ユニットテストしやすく設計されています。
- DuckDB 接続は各関数に注入する形を採っています（テスト時にインメモリ DB を差し替え可）。

---

この README はコードベースの主要点を抜粋したものです。詳細は各モジュール中の docstring / コメントを参照してください。必要であれば、セットアップの手順や運用手順（systemd / supervisor 用の service ファイル、ログ運用、バックアップ方針等）を追記します。