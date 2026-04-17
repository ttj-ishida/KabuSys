KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした小規模なフレームワーク群です。  
本リポジトリには以下の機能群が実装されています（バックエンドは SQLite / DuckDB を利用）。

- 注文管理・発注（ExecutionEngine による発注・リコンシリエーション）
- モニタリング（システム状態、注文滞留、リスク監視、Kill Switch）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定・セクター制約）
- リサーチ（ファクター計算・特徴量探索）
- AI を用いたニュースセンチメント / レジーム判定（OpenAI）
- 運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

主な特徴
--------
- 実運用向けの監視設計（monitoring.DB、アラート送信、kill.flag）
- Paper Trading 環境と本番環境の明確な分離（別 SQLite DB）
- DuckDB を使った時系列ファクター計算（prices_daily / raw_financials）
- OpenAI を使ったニュース NLP と市場レジーム判定（冪等性・フェイルセーフ設計）
- プロセス優先度 / CPU affinity 設定ユーティリティ（psutil ベース）

セットアップ手順
----------------
1. リポジトリをクローン（例）
   - git clone <this-repo-url>
   - ルートは pyproject.toml または .git によって自動検出されます。

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要な主なパッケージ:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

   （requirements.txt がある場合は pip install -r requirements.txt を推奨）

4. 環境変数（.env / .env.local）
   - プロジェクトルートの .env / .env.local を読み込みます（自動読み込み。無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
     - KABU_API_PASSWORD — kabuステーション API 用（必須）
     - OPENAI_API_KEY — OpenAI を使う機能で必要（news_nlp / regime_detector）
     - KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")。デフォルト: development
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE アラート送信用（任意）
     - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

5. 初期データディレクトリ
   - data ディレクトリを作る（DB ファイルが配置される）
     - mkdir -p data

使い方（主要コンポーネント）
------------------------

起動スクリプト（モジュール経由）
- 監視ループ（SystemMonitor 単体で DB に定期記録）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL によってポーリング間隔を秒で上書きできます（1 以上、デフォルト 60）。
  - 監視は KABUSYS_ENV に関係なく常に本番 sqlite_path を使用します。
  - 停止はプロジェクトルート/data/stop_requested.flag を作成すると検出して終了します。

- ExecutionEngine（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録して本番 DB と分離します。
  - 起動前に data/stop_requested.flag が存在すると起動をキャンセルします。
  - 実行中に同ファイルが作成されるとエンジン停止をトリガします。
  - 実行中は data/execution.pid に PID を書きます（設定によりパス変更可）。

ツール
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数でデフォルト変更可）
  - 指標: 稼働率、注文成功率、送信率、P95 レイテンシ等を出力し PASS/FAIL 判定を行います。

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用モードで monitoring.db を表示します（MonitoringEngine がデータを書き込む想定）。

AI / 研究機能
- ニュースセンチメント（ai.news_nlp.score_news）
  - DuckDB 接続と target_date を与えて呼び出します。OpenAI API キーが必要です。
  - 実行は AI トークン（OPENAI_API_KEY）が未設定だとエラーになります。

- レジーム判定（ai.regime_detector.score_regime）
  - DuckDB と target_date を渡して実行。OpenAI API キーが必要です。
  - prices_daily（ETF 1321）と raw_news を使って ma200 とマクロセンチメントを合成し market_regime テーブルへ書き込みます。

設定と動作上の注意
-----------------
- Settings（kabusys.config.Settings）
  - .env / .env.local / OS 環境変数を読み込みます（優先度: OS > .env.local > .env）。
  - 必須キー未設定時は ValueError を投げます。
  - KABUSYS_ENV の有効値: development, paper_trading, live
  - paper_trading 環境では発注系は mock 実装 / 別 DB を使う想定です。

- Kill / Stop フラグ
  - data/stop_requested.flag — run_monitoring / run_execution が監視する「即時停止」フラグ（存在で停止）
  - data/kill.flag — KillSwitch が書き込む停止要求（ExecutionEngine 停止のために使用）

- プロセス優先度
  - 起動スクリプトは set_process_priority("high") を呼び psutil 経由で優先度を設定します（失敗時は警告で継続）。

ディレクトリ構成（主要ファイル）
-----------------------------
以下は src/kabusys 配下の主要なファイルと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ = "0.1.0"）
  - config.py — 環境変数/設定読み込みロジック（Settings クラス）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite のテーブル作成・永続層（MonitoringDB クラス）
  - system_monitor.py — CPU/メモリ/Disk/データ鮮度/プロセス監視
  - trade_monitor.py — 注文滞留・約定異常検知
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag 書き込みロジック
  - alert_manager.py — LINE によるプッシュ通知（cooldown 管理あり）
  - monitoring_engine.py — 監視モジュールを束ねる実行ループ
  - streamlit_dashboard.py — Streamlit による簡易ダッシュボード

- src/kabusys/execution/
  - order_manager.py — 注文作成 / 重複制御 / 発注フローの外向き API
  - reconciler.py — 起動時の自動リコンシリエーション（ブローカーとの突合）
  - （その他発注関連の実装ファイルを含む想定）

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算（select_candidates / calc_equal_weights / calc_score_weights）
  - position_sizing.py — 発注株数計算（各種制約・lot 単位の丸め・aggregate cap）
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- src/kabusys/research/
  - factor_research.py — momentum/value/volatility ファクター計算（DuckDB を利用）
  - feature_exploration.py — 将来リターン計算・IC・統計サマリ等

- src/kabusys/ai/
  - news_nlp.py — ニュースを OpenAI でスコア化して ai_scores に書き込むロジック
  - regime_detector.py — 市場レジーム判定（ma200 + macro sentiment）

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成 CLI

ログ・監視・運用
----------------
- ログレベルは Settings.log_level（環境変数 LOG_LEVEL）で制御できます。
- MonitoringDB（monitoring_db.init_monitoring_db）は冪等で必要なテーブルとインデックスを作成し、既存 DB に対する簡易マイグレーション（列追加）も実施します。
- LINE アラートは channel token / user id が空の場合は送信せずログのみ出力されます。cooldown により短時間での連続通知を防止します。

よくある運用フロー（例）
-----------------------
1. DuckDB に prices_daily / raw_financials / raw_news 等のデータを投入
2. ExecutionEngine を起動（paper_trading で検証する場合は KABUSYS_ENV=paper_trading）
3. MonitoringEngine（または run_monitoring）で運用状況を定期記録
4. Streamlit ダッシュボードで状況確認
5. 日次で ai.score_news / ai.score_regime を実行して ai_scores / market_regime を更新
6. Paper Trading の結果は paper_verification_report で検証

ライセンス / 貢献
-----------------
- 本 README はリポジトリ内の実装に基づいた要約ドキュメントです。実運用に使用する際は必ずコードを読み、環境に合わせたテストを行ってください。
- 貢献歓迎。プルリクエスト・Issue はリポジトリの運用ルールに従ってください。

補足（小さなメモ）
-----------------
- モジュールは外部 API（kabuステーション、OpenAI 等）へのアクセスを伴うため、それらのキー/エンドポイントは環境変数で管理してください。
- Paper Trading モードは実取引とデータを分離することを目的としていますが、実装の詳細（MockBroker の仕様など）は該当コードを確認してください。

必要に応じて、README に加える内容（例: 具体的なコマンドの例、依存パッケージの正確なバージョン、CI / テスト手順など）を教えてください。必要に応じてサンプル .env.example の雛形も作成できます。