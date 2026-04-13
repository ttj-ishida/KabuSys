# KabuSys

日本株自動売買システムのモジュール群（ライブラリ / ツール / 実行スクリプト群）

この README はリポジトリ内の主要コンポーネント（監視、実行、ポートフォリオ構築、リサーチ、AIニュース処理 等）についての概要、セットアップ手順、使い方、およびディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関わる以下の機能を提供するモジュール化されたシステムです。

- 注文管理・実行（ExecutionEngine、OrderManager、BrokerClientFactory 等）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor、MonitoringEngine）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、セクター制限 等）
- リサーチ / ファクター計算（モメンタム、ボラティリティ、バリュー）
- AI を使ったニュースセンチメント評価（OpenAI API を利用）
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）
- 永続化は主に SQLite（監視用 / Paper Trading 用）と DuckDB（時系列・リサーチ用）

設計方針の一部：
- 本番 DB と Paper Trading DB は分離
- ルックアヘッドバイアス防止：日付参照時に datetime.today()/date.today() を直接参照しない実装方針
- フェイルセーフ：外部 API 失敗時はフェイルフォールバックして継続する設計

---

## 主な機能一覧

- 監視
  - SystemMonitor: CPU/メモリ/Disk、プロセス生存、株価データ鮮度を監視しログを保存
  - TradeMonitor: 滞留注文・約定異常価格を検出してリスクログへ記録
  - RiskMonitor: ドローダウンやポジション上限をチェックし、kill.flag を生成する仕組みを提供
  - AlertManager: LINE Push による一方向通知（クールダウン管理あり）
  - Streamlit ダッシュボードで監視情報を可視化

- 実行（Execution）
  - ExecutionEngine / OrderManager / Reconciler による発注・状態管理・復旧処理
  - Paper Trading モード（MockBrokerClient・専用 SQLite）によるリスク検証

- ポートフォリオ構築
  - 候補選定（score / rank）
  - 等比率・スコア加重の重み計算
  - リスク調整（セクター上限、レジーム乗数）
  - 株数決定（リスクベース / 比率ベース）、単元株丸め、aggregate cap

- リサーチ
  - ファクター計算: モメンタム / ボラティリティ / バリュー 等（DuckDB 利用）
  - 特徴量解析: 将来リターン計算、IC（Spearman）や統計サマリー

- AI（OpenAI）
  - news_nlp.score_news: ニュース記事をまとめて LLM でセンチメント評価し DuckDB に書き込み
  - regime_detector.score_regime: ETF (1321) の MA とマクロ記事センチメントを合成して市場レジーム判定

- ツール
  - paper_verification_report: Paper Trading の検証レポートを生成（成功率 / レイテンシ / 稼働率 等）

---

## セットアップ手順

前提
- Python 3.9+（コードは typing 等の構文を使用）
- SQLite（標準で付属）
- DuckDB（Python パッケージ）
- 実行環境により追加パッケージ（psutil, requests, streamlit, openai 等）

推奨手順（例）:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   requirements.txt があれば:
   - pip install -r requirements.txt

   手動例（最低限）:
   - pip install duckdb psutil requests streamlit openai

3. .env の用意
   - リポジトリルートに .env または .env.local を配置して環境変数を設定できます。
   - 自動ロードはデフォルトで有効（プロジェクトルートは .git または pyproject.toml を基準に検出）。
   - テストで自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データディレクトリ作成
   - mkdir -p data

5. （任意）Paper Trading 用 DB 初期化は実行スクリプトが必要に応じて実行します。

---

## 主な環境変数（抜粋）とデフォルト

- KABUSYS_ENV: 起動環境（development / paper_trading / live） — デフォルト: development
- SQLITE_PATH: 監視 DB path — デフォルト: data/monitoring.db
- DUCKDB_PATH: DuckDB path — デフォルト: data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite — デフォルト: data/paper_trading.db
- PAPER_FILL_MODE: paper_trading の MockBroker の fill 動作 — 有効値: instant|partial|never|reject（デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine PID ファイル path — デフォルト: data/execution.pid
- KILL_FLAG_PATH: kill flag path — デフォルト: data/kill.flag
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒） — デフォルト: 60
- OPENAI_API_KEY: OpenAI API キー（AI 関連機能で必須）
- JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD: 外部 API 用必須設定（使用する機能に応じて）

Settings モジュールは自動的に .env / .env.local を読み込みます（OS 環境変数優先）。詳細は src/kabusys/config.py を参照してください。

---

## 使い方（主要スクリプト）

プロジェクトをパッケージとして扱う場合は `python -m kabusys.<module>` の形で実行できます。

1. 監視ループを起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒）
   - 監視は Settings.env にかかわらず監視用の sqlite_path（本番設定）を使用します

2. ExecutionEngine を起動（発注エンジン）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading DB（PAPER_TRADING_SQLITE_PATH）へ記録して本番 DB と分離
   - 起動時にプロセス優先度を "high" に設定する処理が行われます（psutil による試行）

3. Streamlit 監視ダッシュボード
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 読み取り専用で SQLite DB を開いてダッシュボードを表示

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - オプション例:
     - --from 2026-04-01 --to 2026-04-11
     - --db path/to/paper_trading.db
   - デフォルトは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db

5. AI 関連
   - ニューススコアリング:
     - 呼び出し関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
     - 環境変数 OPENAI_API_KEY が必要（または api_key 引数で指定）
   - レジーム判定:
     - 呼び出し関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
     - 同様に API キーが必要
   - これらは DuckDB コネクションを渡して実行します（メイン実行スクリプトから呼ばれる想定）

---

## 重要な挙動・運用上の注意

- Paper Trading モードでは SQLite DB を分離して記録します（settings.is_paper が True の場合）。
- run_monitoring は Settings に従って本番 sqlite_path を使用（環境に依存しない設計）。
- kill.flag: RiskMonitor や KillSwitch により一定条件を満たすと指定パスにフラグファイルを書き、ExecutionEngine 停止シグナルとして使います。Execution 起動時にフラグのクリーンアップ設定が可能（Settings.kill_flag_clear_on_start）。
- Process priority / CPU affinity の設定は psutil を用いて行います。権限不足や未対応 OS の場合は設定に失敗しても警告が出力され処理は続行されます。
- OpenAI 利用部は外部 API 呼び出しに依存します。API 失敗時はフェイルセーフ（スコア 0.0 にフォールバック、または処理スキップ）で動作するよう設計されています。

---

## ディレクトリ構成（主要ファイル・モジュール）

（パスは src/kabusys 以下を起点に表記）

- __init__.py
  - パッケージメタ情報（__version__ 等）

- config.py
  - Settings クラス：.env 読み込み、環境変数管理、デフォルト値とバリデーション

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト

- run_execution.py
  - ExecutionEngine 起動スクリプト（Paper Trading の分離動作を含む）

- monitoring/
  - monitoring_db.py: SQLite ベースの監視ログ永続化層（スキーマ作成・マイグレーション含む）
  - system_monitor.py: CPU/メモリ/Disk/プロセス/データ鮮度監視
  - trade_monitor.py: 注文滞留・約定価格異常検出
  - risk_monitor.py: ドローダウン・ポジション上限監視（ダッシュボード更新・リスクログ出力）
  - kill_switch.py: kill.flag の作成・管理ロジック
  - alert_manager.py: LINE Push 通知ユーティリティ
  - monitoring_engine.py: 各モニタを束ねるエンジン
  - streamlit_dashboard.py: Streamlit を用いた監視ダッシュボード

- execution/
  - order_manager.py: Order State Machine の外向け API（作成・送信・同期ロジック）
  - reconciler.py: 起動時の注文・ポジションのリコンシリエーション（自動復旧）
  - その他（broker_factory, execution_engine, order_repository 等） — 発注・ブローカー関連実装（リポジトリ全体参照）

- portfolio/
  - portfolio_builder.py: 候補選定・スコアソート
  - risk_adjustment.py: セクター上限・レジーム乗数
  - position_sizing.py: 発注株数計算（リスクベース / 比率ベース）

- research/
  - factor_research.py: momentum/volatility/value ファクター計算（DuckDB 経由）
  - feature_exploration.py: 将来リターン・IC・統計サマリー、ランク関数など

- ai/
  - news_nlp.py: raw_news を LLM で処理して ai_scores に書き込むワークフロー
  - regime_detector.py: ETF MA とマクロニュースを使ったレジーム判定

- tools/
  - paper_verification_report.py: Paper Trading の検証レポート生成スクリプト

- utils/
  - process_priority.py: プラットフォーム差分を吸収するプロセス優先度 / CPU affinity のユーティリティ

---

## 例: よく使うコマンドまとめ

- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行（Paper Trading モード）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

---

## トラブルシューティング / 補足

- .env 自動読み込みはプロジェクトルート検出（.git または pyproject.toml）に依存します。配布後の環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動で env を管理してください。
- OpenAI 関連は API レート制限やネットワーク障害を考慮したリトライロジックを組み込んでいますが、API キーの漏洩防止に注意してください。
- MonitoringDB のスキーマは init_monitoring_db() で冪等に作成され、マイグレーション（カラム追加）も起動時に一部自動対応します。
- 実行環境（特に psutil の機能）により process priority / cpu affinity の効果が異なります。権限不足や未対応 OS では警告を出してスキップされます。

---

この README はコードベースの主要部分に基づいて作成しました。細部の API（ExecutionEngine の設定項目やブローカー実装、OrderRepository のスキーマ等）はソースコードの該当モジュールを参照してください。質問や補足情報が必要であれば教えてください。