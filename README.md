# KabuSys

日本株自動売買システムの一部コンポーネント群（監視、実行、ポートフォリオ構築、リサーチ、AI補助など）。  
このリポジトリはライブラリと実行スクリプトを含み、ローカル環境での検証・Paper Trading・本番運用を想定しています。

## 概要
- DuckDB / SQLite ベースでマーケットデータ・ログを保持し、戦略のファクター計算・ポートフォリオ構築・発注・監視を行うモジュール群。
- OpenAI（gpt-4o-mini）を用いたニュースのセンチメント解析や市場レジーム検出機能を持つ（APIキーは必須）。
- 監視エンジンは実行プロセスの生存、データ鮮度、滞留注文、ドローダウン等を定期チェックしてアラート／停止フラグを発行する。

## 主な機能一覧
- monitoring
  - SystemMonitor: プロセス生存確認、リソース使用率、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新、リスクログ
  - AlertManager: LINE Push による通知（任意）
  - KillSwitch: kill.flag を書いて ExecutionEngine 停止をトリガー
  - Streamlit ダッシュボード（監視データ可視化）
- execution
  - ExecutionEngine 起動スクリプト（paper_trading では MockBroker を使用）
  - OrderManager / Reconciler: 発注状態同期・再起動復旧ロジック
- portfolio
  - 銘柄選定・重み計算、セクター制限、ポジションサイズ計算（純粋関数群）
- research
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）、特徴量解析、IC計算
- ai
  - news_nlp: raw_news をまとめて LLM に問い合わせ、銘柄ごとのスコアを生成して ai_scores に保存
  - regime_detector: ETF(1321) の MA とマクロニュースセンチメントを合成して market_regime を書き込み
- tools
  - paper_verification_report: Paper Trading DB から稼働率・注文成功率・レイテンシ等の検証レポートを生成

## 前提・依存
- Python >= 3.10
- ライブラリ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使う場合）
- SQLite は標準ライブラリで利用
- これらは requirements.txt がある場合はそれを使うか、手動で pip install してください。
  例:
    pip install duckdb psutil requests openai streamlit

## セットアップ手順（ローカル）
1. リポジトリをクローン／展開
2. Python 環境を準備（venv など）
3. 必要パッケージをインストール（上記参照）
4. 環境変数を設定
   - .env/.env.local に記述して自動ロードされます（デフォルト）。テスト時に自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
   - 主要な環境変数（主なもの）
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合は必須）
     - KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルトは development。
     - PAPER_FILL_MODE — Paper Trading の約定挙動（instant, partial, never, reject）。デフォルト: instant
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
     - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
   - 例 (.env)
       JQUANTS_REFRESH_TOKEN=your_token
       KABU_API_PASSWORD=your_kabu_password
       OPENAI_API_KEY=sk-...
       KABUSYS_ENV=paper_trading

5. 必要なら data ディレクトリを作成:
    mkdir -p data

注: run_monitoring / run_execution は起動時に DB 初期化（監視テーブル）を行います。

## 使い方（よく使うコマンド）
- 監視ループ起動
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）。
  - 実行:
      python -m kabusys.run_monitoring
  - 説明:
    - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に依存せず）。
    - 実行時にプロセス優先度を "high" に設定しようとします（権限不足なら警告のみ）。

- ExecutionEngine 起動（発注エンジン）
  - paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）。
  - 実行:
      python -m kabusys.run_execution
  - 起動前に data/stop_requested.flag が存在する場合は起動を行いません。
  - 起動中に data/stop_requested.flag を作成すると、安全に停止します。

- Streamlit ダッシュボード（監視可視化）
  - 実行例:
      streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 引数 --db で読み込む monitoring SQLite のパスを指定できます（デフォルト: data/monitoring.db）。
  - ダッシュボードは read-only で接続し、見やすく指標を表示します。

- Paper Trading 検証レポート
  - 実行:
      python -m kabusys.tools.paper_verification_report
      python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
      python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 出力: 稼働率、注文成功率、送信率、レイテンシ等のサマリと PASS/FAIL 判定。

- AI スコアリング / レジーム判定（ライブラリ呼び出し）
  - DuckDB 接続を用意し、ライブラリ関数を呼ぶ:
    from open code:
      from open file:
        import duckdb
        from kabusys.ai import score_news
        conn = duckdb.connect("data/kabusys.duckdb")
        score_news(conn, target_date=date(2026,4,1), api_key="sk-...")

  - 同様に regime_detector.score_regime(conn, target_date, api_key=...) を呼ぶと market_regime テーブルに書き込みます。
  - OpenAI API キーが未設定の場合は ValueError。

## 停止・制御
- 実行中プロセスの停止
  - 実行スクリプトでは data/stop_requested.flag（run_monitoring では親ディレクトリ基準で配置）を監視しています。停止させたい場合は該当ファイルを作成してください。
  - KillSwitch（監視側）が閾値を超えた場合は data/kill.flag に理由を書き込みます。ExecutionEngine はそれを検知して停止します。
  - kill.flag を手動で削除するには:
      rm data/kill.flag
  - ExecutionEngine の PID ファイル: data/execution.pid

## 主要設定（Settings クラスから）
- 使用可能な KABUSYS_ENV:
  - development, paper_trading, live
- DB 関連 default paths:
  - SQLITE_PATH -> data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH -> data/paper_trading.db
  - DUCKDB_PATH -> data/kabusys.duckdb
- Paper Trading 設定:
  - PAPER_FILL_MODE = instant | partial | never | reject
- モニタリングしきい値（環境変数で上書き可能）
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- ログ設定:
  - LOG_LEVEL (DEBUG|INFO|...)
- その他:
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START

## ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - monitoring/
    - monitoring_db.py — SQLite 永続化レイヤ（init も含む）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他発注・リポジトリ関連)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - process_priority.py

（上記は抜粋。詳細は src/kabusys 以下の実装ファイルを参照してください）

## 注意事項 / 運用上のヒント
- Python バージョンは 3.10 以上を推奨（コード内で PEP 604 の union 型などを使用）。
- .env の自動ロードはデフォルトで有効。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- run_execution は paper_trading 環境で本番 DB と分離するよう設計されています。実運用では KABUSYS_ENV=live に設定してください。
- OpenAI を利用する機能は API費用が発生します。テスト時はモック化して実行することを推奨します。
- プロセス優先度の設定は権限に依存します。権限が不足すると警告が出るだけで続行します。

## トラブルシューティング
- DB が見つからない / 読み込めない:
  - monitoring の Streamlit は読み取り専用 URI を使います。DB が存在しない場合は MonitoringEngine を起動して初期化してください。
- OpenAI 呼び出しで失敗する:
  - API キーが設定されているか、ネットワークやレート制限状況を確認してください。ライブラリ側は 5xx/429 等でリトライ実装がありますが、キー未設定は例外になります。
- プロセスが正しく停止しない:
  - stop_requested.flag / kill.flag の存在や execution.pid の中身を確認してください。PID が古くなっている場合は stale PID 検出でファイルが削除されます。

---

README はこのリポジトリの主要な使い方・構成をまとめたものです。さらに詳しい設計意図やアルゴリズム仕様（PortfolioConstruction.md、StrategyModel.md 等）が別文書として存在する想定です。必要ならそれらに基づく具体的な運用手順や設定例も追記できます。