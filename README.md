# KabuSys — 自動売買システム（README）

この README は、提供されたコードベース（src/kabusys 以下）についての概要・セットアップ手順・使い方・ディレクトリ構成を日本語でまとめたものです。

## プロジェクト概要
KabuSys は日本株向けの自動売買システムのコンポーネント群です。主な機能は次の通りです。

- 注文管理・発注（ExecutionEngine / OrderManager）
- リコンシリエーション（起動時の自動復旧）
- リスク管理（ドローダウン監視、ポジション上限）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）とアラート送信（LINE）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定）
- リサーチ用モジュール（ファクター計算、特徴量探索）
- AI モジュール（ニュースセンチメント評価、レジーム判定） — OpenAI を使用
- 運用検証ツール（Paper Trading レポート生成、Streamlit ダッシュボード）

設計方針としては、DuckDB と SQLite を使ったデータ処理／永続化、外部 API 呼び出しは限定的に（OpenAI やブローカー API）行い、フェイルセーフや冪等性を重視しています。

## 主な機能一覧
- Execution
  - OrderManager: 注文作成・送信・同期
  - Reconciler: 起動時の注文・ポジション突合
  - RiskManager: 発注前のリスクチェック（最大ポジション比率等）
- Monitoring
  - SystemMonitor: CPU/メモリ/Disk/データ鮮度/プロセス存否を監視
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション数監視、ダッシュボード更新
  - AlertManager: LINE プッシュ通知（クールダウン制御あり）
  - KillSwitch: 条件に応じた停止フラグ（data/kill.flag）生成
  - Streamlit ダッシュボード（監視用 UI）
- Portfolio
  - 候補選定（スコア降順）、等重・スコア重み、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算（単元株丸め、aggregate cap）
- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン、IC、統計サマリ等
- AI
  - news_nlp: ニュースを OpenAI でセンチメント化して ai_scores に書き込み
  - regime_detector: MA200 とマクロニュースの LLM センチメントを合成して市場レジーム判定
- Tools
  - paper_verification_report: Paper Trading DB から検証レポートを生成
  - streamlit_dashboard: 監視用ダッシュボード（Streamlit）

## 必要要件（推奨）
- Python 3.9+
- 必要な主なパッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- SQLite（Python 標準の sqlite3 を利用）
- インターネット接続（OpenAI、LINE API、broker API を使う場合）

（プロジェクトに requirements.txt があればそちらを優先してください）

## 環境変数と設定（要注意）
Settings クラス（kabusys.config）で環境変数から設定を読み込みます。.env / .env.local の自動ロードを行います（プロジェクトルートが .git または pyproject.toml を含む場合）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（抜粋）

- 必須系（実行内容により必須）
  - JQUANTS_REFRESH_TOKEN — J-Quants 用トークン（Settings.jquants_refresh_token）
  - KABU_API_PASSWORD — kabuステーション API パスワード
- DB / ファイルパス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
- 実行環境フラグ
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading の場合、MockBrokerClient を使用し paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます
- AI / OpenAI
  - OPENAI_API_KEY — OpenAI 呼び出しを行う場合に必須（ai モジュール使用時）
- その他
  - LOG_LEVEL（INFO 等）
  - PAPER_FILL_MODE（paper_trading の模擬約定モード、valid: instant|partial|never|reject）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60。0/負値は無効としてデフォルトにフォールバック）
  - KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag をクリアする場合は "1"

## セットアップ手順（ローカル開発向け）
1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
3. データディレクトリ作成
   - mkdir -p data
4. .env を用意（プロジェクトルートに配置）
   - .env.example があれば参照して必要な環境変数を設定
   - 例:
     - KABUSYS_ENV=development
     - OPENAI_API_KEY=sk-...
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
5. DB 初期化
   - 監視 DB は起動スクリプトが自動でテーブル作成します（init_monitoring_db を使用）
   - DuckDB（kabusys.duckdb）はリサーチ処理で使用。価格データや raw_financials をインポートして利用してください。

## 実行方法（よく使うコマンド）
- 監視ループを起動（SystemMonitor を単独でポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能
- ExecutionEngine を起動（注文実行フロー）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBroker を使い data/paper_trading.db に記録します
- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプションで期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
- AI バッチ処理（プログラム経由）
  - ニューススコアリング:
    - kabusys.ai.score_news(conn, target_date, api_key=None) — api_key を None にすると環境変数 OPENAI_API_KEY を参照
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

## 主要ファイル／モジュールの説明
（src/kabusys 以下の主要なモジュールを抜粋）

- kabusys/config.py
  - .env 自動ロード、Settings クラス（全設定の getter）
- kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL で間隔を上書き可能
- kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（起動時に Reconciler 等を組み立て）
  - KABUSYS_ENV=paper_trading の場合は paper_trading DB を使用
- kabusys/monitoring/
  - monitoring_db.py: SQLite のテーブル作成と永続化 API（MonitoringDB）
  - system_monitor.py, trade_monitor.py, risk_monitor.py: 各監視ロジック
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - alert_manager.py: LINE Push 通知
  - kill_switch.py: kill.flag の管理
  - streamlit_dashboard.py: Streamlit ベースの監視ダッシュボード
- kabusys/execution/
  - order_manager.py, reconciler.py, risk_manager など: 注文・再同期・リスク管理
- kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py: 候補選定・重み・数量計算
- kabusys/research/
  - factor_research.py, feature_exploration.py: ファクター計算・解析
- kabusys/ai/
  - news_nlp.py: ニュースを OpenAI でセンチメント評価して ai_scores に書き込み
  - regime_detector.py: MA200 とマクロニュースの LLM センチメントでレジーム判定
- kabusys/tools/paper_verification_report.py
  - Paper Trading 検証レポート生成（稼働率・注文成功率・レイテンシなど）

## ディレクトリ構成（簡易）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_monitoring.py
    - run_execution.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - alert_manager.py
      - kill_switch.py
      - streamlit_dashboard.py
    - execution/
      - reconciler.py
      - order_manager.py
      - (その他 execution 関連モジュール)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - tools/
      - paper_verification_report.py
    - utils/
      - process_priority.py
    - (その他モジュール)

## 運用上の注意 / トラブルシューティング
- .env の自動読み込みはプロジェクトルート（.git や pyproject.toml を基準）から行います。CI / テスト環境などで自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- paper_trading モードは本番 DB と完全に分離されます。Paper トレードのデータは `PAPER_TRADING_SQLITE_PATH` に保存されます。
- OpenAI を使う処理（news_nlp, regime_detector）は API キーが必須です。環境変数 `OPENAI_API_KEY` を設定するか、関数呼び出し時に api_key を渡してください。API エラーはフェイルセーフとして一定の条件で 0.0 等にフォールバックする実装になっていますが、ログを必ず確認してください。
- run_monitoring / run_execution は起動時にプロセス優先度を "high" に設定しようとします（psutil を利用）。OS 権限によっては警告が出ることがありますがノンファタルです。
- kill.flag（デフォルト path: data/kill.flag）を用いた外部停止シグナルが実装されています。運用時の手動停止や自動トリガー（ドローダウン等）に注意してください。
- SQLite や DuckDB の互換性や executemany の空リスト等の制約に配慮したコードになっています。DB のマイグレーション（ALTER TABLE）処理は init_monitoring_db 内に含まれます。

---

この README はコードベースに含まれるコメント・docstring を元に作成しています。実運用前には必ず設定ファイル（.env）と各外部 API キー、DB のパスを確認し、テスト環境で動作確認してください。必要があれば README の補足（セットアップスクリプト、systemd ユニット例、運用手順）を追記できます。