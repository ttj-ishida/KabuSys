KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買プラットフォームのコアライブラリ群です。  
注文の生成・送信・リコンシリエーション（復旧）、ポートフォリオ構築ロジック、ファクター計算、監視（モニタリング）、
ニュースセンチメントを使った AI 評価など、アルゴリズム売買運用に必要な主要コンポーネントを含みます。

主な特徴
--------
- ExecutionEngine（発注エンジン）:
  - ブローカークライアント抽象化（実環境/ペーパー取引を切替可能）
  - OrderManager / OrderRepository による注文ライフサイクル管理
  - 起動時の Reconciler による自動復旧（OrderSent の突合、ポジション差分検出）
  - RiskManager による各種リスク制御（レート制限、最大ポジション比率など）
- Monitoring（監視）:
  - SystemMonitor: CPU/メモリ/ディスクや Execution プロセス存在チェック、データ鮮度検査
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード永続化
  - KillSwitch: 異常時にデータ/フラグで Execution 停止をトリガ
  - AlertManager: LINE Push で一方向通知
  - Streamlit ダッシュボードで可視化
- Portfolio（ポートフォリオ構築）:
  - 候補選定（スコア順位、等配分/スコア配分）、ポジションサイズ計算（risk_based / equal / score）
  - セクター上限適用、レジーム乗数計算
- Research（調査用モジュール）:
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI（ニュース NLP / レジーム判定）:
  - OpenAI を使ったニュースの銘柄別センチメント算出（ai_scores への書き込み）
  - マクロニュースと ETF MA200 を合成した市場レジーム判定と永続化
  - API 呼び出しはリトライ/フォールバック実装でフェイルセーフ設計
- 開発/運用支援ツール:
  - paper_trading モード（本番 DB と分離）
  - paper_verification_report：ペーパートレード結果の検証レポート生成
- 設定管理:
  - .env / .env.local 自動読み込み（OS 環境変数を優先）
  - Settings クラス経由で環境変数を集中管理

システム要件
-------------
- Python >= 3.10（| 型ヒント等の構文を使用）
- SQLite（標準ライブラリで使用）
- 主要依存パッケージ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード用)
- （オプション）LINE 通知や OpenAI を利用する場合は各種 API キーを設定

セットアップ手順
----------------
1. リポジトリをクローンしてワークディレクトリへ移動。
2. 仮想環境を作成・有効化（推奨）。
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール（例）:
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトで requirements.txt を用意している場合は pip install -r requirements.txt）
4. data ディレクトリ作成:
   - mkdir -p data
5. 環境変数を用意:
   - .env / .env.local をプロジェクトルートに置くと自動読み込みされます（OS 環境変数が優先）。
   - 主な環境変数（例）:
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant|partial|never|reject
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - LOG_LEVEL=INFO
     - MONITOR_POLL_INTERVAL=60  （監視ループの秒間隔を上書き）
6. DB 初期化
   - 多くの起動スクリプト（run_execution / run_monitoring）は内部で init_monitoring_db を呼び DB スキーマを作成します。手動での初期化は不要です。

使い方
------
- 実行エンジン（本番 / ペーパートレード）
  - 本番（環境変数で切替）:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパー取引（MockBroker を使用し専用 DB に記録）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - run_execution は起動時に process priority を high に設定し、依存コンポーネントを組み立ててセッション実行します。

- 監視ループ（SystemMonitor の単独起動）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。

- Streamlit ダッシュボード
  - 起動例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開きダッシュボード表示を行います（MonitoringEngine が DB を更新していることが前提）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）

- AI / リサーチ機能（ライブラリ利用例）
  - ニューススコアリング（外部スクリプトから呼び出す場合）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # 書き込みは DuckDB 上の ai_scores テーブル
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- 監視・アラート
  - AlertManager は LINE のトークンが未設定だと送信スキップ（ログ出力のみ）。クールダウン機能あり。
  - KillSwitch は RiskMonitor 等からのフラグで data/kill.flag を作成し Execution の停止を促します（Execution 側で kill.flag を検出して終了する設計）。

設定（Settings）
----------------
- Settings クラスは環境変数を参照して各種パスや閾値を提供します。
- 自動 .env ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を読み込みます。
  - OS 環境変数が優先され、.env.local は .env を上書きします。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効にできます。
- KABUSYS_ENV の有効値:
  - development, paper_trading, live

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュールと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義・バージョン
  - config.py — 環境変数 / Settings の実装（.env 読み込み含む）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト

- src/kabusys/execution/
  - order_manager.py — 発注の高レベル API（作成→送信→同期）
  - reconciler.py — 起動時の注文/ポジション突合
  - （※ broker 関連・order_repository 等の実装が別ファイルに存在）

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite スキーマ初期化／永続化 API
  - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py — 滞留注文・約定異常検出
  - risk_monitor.py — ドローダウンやポジション上限監視
  - kill_switch.py — フラグファイルでの停止トリガ
  - alert_manager.py — LINE Push 通知機能
  - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py — Streamlit ベースのダッシュボード

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・丸め・投下資金スケール
  - risk_adjustment.py — セクター制限・レジーム乗数

- src/kabusys/research/
  - factor_research.py — Momentum / Volatility / Value 等ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン、IC、統計サマリ

- src/kabusys/ai/
  - news_nlp.py — ニュースの銘柄別センチメント算出（OpenAI 経由）
  - regime_detector.py — マクロニュース + ETF MA200 によるレジーム判定

- src/kabusys/tools/
  - paper_verification_report.py — ペーパートレード結果の集計・判定レポート生成

- src/kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

補足 / 運用上の注意
-------------------
- データ鮮度チェック / レジーム判定 / ニューススコアはすべてタイムバイアス対策（target_date を明示）を意識した実装になっています。日時処理において datetime.today()/date.today() を直接参照しない設計を採用している箇所があります。
- OpenAI / LINE 等の外部サービスはネットワーク障害・レート制限を想定してリトライやフォールバック設定が実装されていますが、API キーの管理・利用は運用上の責任として適切に行ってください。
- run_monitoring は監視用 DB（monitoring.db）を常に本番 sqlite_path に書き込みます（KABUSYS_ENV に依らず本番 DB を使う仕様）。ペーパー取引のログは paper_trading 専用 DB に分離されます。

ライセンス・貢献
----------------
（ライセンス情報・貢献方法があればここに追記してください）

お問い合わせ
------------
実装や運用に関する質問があれば実装者またはリポジトリの管理者にお問い合わせください。

以上。