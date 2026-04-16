KabuSys — 自動売買システム（ドキュメント）
=================================

この README は、提供されたコードベース（src/kabusys 以下）をもとに、プロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

1. プロジェクト概要
-----------------
KabuSys は日本株向けの自動売買／研究／監視ユーティリティ群です。  
主な目的は以下：

- 戦略・ポートフォリオ構築（ファクター計算、ポジションサイズ計算、セクター制限など）
- 注文実行エンジン（ExecutionEngine）とリコンシリエーション
- 監視（System / Trade / Risk）とアラート（LINE プッシュ）
- Paper Trading 用の分離された検証基盤
- DuckDB / SQLite を用いたデータ処理と永続化
- AI（OpenAI）を用いたニュースセンチメント評価と市場レジーム判定
- Streamlit による監視ダッシュボード表示、ツール類（検証レポート生成 など）

2. 主な機能一覧
----------------
- 設定管理（環境変数 / .env 自動ロード）: kabusys.config.Settings
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV による動作モード切替（development / paper_trading / live）
  - paper_trading モードでは MockBrokerClient と専用 SQLite DB（data/paper_trading.db）を使用
  - プロセス優先度設定、PID 管理、停止フラグ監視
- 監視ループ起動スクリプト: run_monitoring.py
  - System/Trade/Risk モニタを定期実行
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き（デフォルト 60 秒）
  - 監視ログは SQLite（デフォルト data/monitoring.db）へ永続化
- 監視コンポーネント
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス存在、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視、dashboard の更新
  - KillSwitch: 条件に応じて data/kill.flag を書いて Execution を停止させる
  - AlertManager: LINE Messaging API による通知（クールダウン管理あり）
  - Streamlit ダッシュボード: 監視情報の可視化（src/kabusys/monitoring/streamlit_dashboard.py）
- Portfolio モジュール（純粋関数）
  - 候補選定・重み算出（等配分・スコア加重）
  - セクターキャップ、レジーム乗数
  - ポジションサイズ計算（単元株丸め、risk_based 等）
- Research / Factor モジュール（DuckDB ベース）
  - モメンタム、ボラティリティ、バリュー等ファクターの算出
  - 将来リターン計算、IC（スピアマン）や統計サマリー
- AI 関連
  - news_nlp.score_news: raw_news を LLM（OpenAI）でスコアリングして ai_scores に保存
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースの LLM スコアを合成して regimes を算出
  - OpenAI 呼び出しはリトライやエラーハンドリングを備える（429/5xx/タイムアウト等）
- ツール
  - tools.paper_verification_report: Paper Trading DB を解析して検証レポートを生成

3. セットアップ手順
-------------------
以下は最小限のセットアップ手順（ローカルで動かすための一般的手順）です。

必須依存（代表例）
- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード実行時）
- （プロジェクトに合わせて requirements.txt があればそれを使用）

例: 仮想環境作成と依存導入
1. 仮想環境作成
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 必要パッケージをインストール
   pip install duckdb psutil requests openai streamlit

※ 本リポジトリに requirements.txt があれば pip install -r requirements.txt を使用してください。

初期データディレクトリ
- data/ フォルダを作成（監視 DB・実行 PID・フラグ等を配置）
  mkdir -p data

環境変数（例）
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須箇所がある場合）
- KABU_API_PASSWORD: kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（任意）
- SQLITE_PATH: data/monitoring.db（監視 DB パス）
- DUCKDB_PATH: data/kabusys.duckdb
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE アラート用
- MONITOR_POLL_INTERVAL: 監視ループの秒数（整数、デフォルト 60）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

.env 自動ロード
- プロジェクトルートに .env/.env.local を置くと自動で読み込まれます（OS 環境変数を上書きしない挙動）。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. 使い方（主要スクリプト）
--------------------------

一般的な実行例（プロジェクトルートで実行）:

- ExecutionEngine（注文実行）起動
  - 通常（デフォルトは development）
    python -m kabusys.run_execution
  - Paper Trading（Mock ブローカー、専用 DB 使用）
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  特記事項:
  - プロセス優先度を High に設定します（psutil による実行権限が必要な場合がある）。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は PID が data/execution.pid（デフォルト）に書かれます。
  - ExecutionEngine は stop フラグ（data/stop_requested.flag）や kill.flag（data/kill.flag）で停止されます。

- Monitoring（監視ループ）起動
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用してログを残します（監視は環境に依存しない）。
  - 停止は data/stop_requested.flag を作成して行います（監視プロセスは flag を検知して終了）。

- Streamlit ダッシュボード（監視 UI）
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - --db で SQLite DB のパスを指定できます（デフォルト data/monitoring.db）
  - read-only モードで接続し、監視データを可視化します。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD  レポート開始日
    --to   YYYY-MM-DD  レポート終了日
    --db PATH           SQLite DB パス（PAPER_TRADING_SQLITE_PATH 環境変数の代替）

- AI 機能（ニュースセンチメント / レジーム判定）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（prices_daily / raw_news 等テーブルが存在すること）と OpenAI API キーが必要です。
  - API エラー時はフェイルセーフ（スコアを 0 にフォールバックなど）で継続する設計です。

運用関連ファイル・フラグ
- data/stop_requested.flag : run_* スクリプトはこのファイルの存在を検知してシャットダウンします。
- data/kill.flag : KillSwitch が書き込み、ExecutionEngine に停止シグナルを送るために使用します。
- data/execution.pid : 実行エンジンの PID（存在チェックにより stale PID を検出します）

5. 重要な設計・運用メモ
------------------------
- データベース
  - 監視用 SQLite（デフォルト data/monitoring.db）に system_status / trade_logs / positions / risk_logs / dashboard テーブルを持ち、init_monitoring_db によってテーブル作成・マイグレーションを行います。
  - Paper Trading は settings.is_paper により専用 SQLite を使用して本番 DB と分離されます。
  - DuckDB は時系列価格データやファクター計算に使われます（DUCKDB_PATH）。

- 環境ごとの挙動
  - KABUSYS_ENV の有効値: development, paper_trading, live
  - paper_trading: Mock ブローカー + paper_sqlite_path を使用。発注は本番口座に影響しません。

- フェイルセーフ
  - AI 呼び出しや外部 API 呼び出しは失敗時に例外をそのまま上げない（ログを残しフォールバックする）実装が多く、運用での堅牢性に配慮されています。
  - リトライ（指数バックオフ）やデータ不足時のフォールバックが各所に実装されています。

6. ディレクトリ構成（主要ファイル）
-----------------------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数・設定管理（.env 自動ロード等）
- run_execution.py                — ExecutionEngine 起動スクリプト
- run_monitoring.py               — Monitoring 起動スクリプト

kabusys/ai/
- news_nlp.py                     — ニュース NLP スコアリング（OpenAI）
- regime_detector.py              — 市場レジーム判定（ETF MA + LLM）

kabusys/monitoring/
- monitoring_db.py                — 監視ログの永続層（SQLite）
- system_monitor.py               — CPU/メモリ/プロセス/データ鮮度監視
- trade_monitor.py                — 注文滞留・約定異常監視
- risk_monitor.py                 — DD / position limit 監視
- kill_switch.py                  — kill.flag の書き込みロジック
- alert_manager.py                — LINE Push 通知送信
- monitoring_engine.py            — 各 Monitor を束ねるエンジン
- streamlit_dashboard.py          — Streamlit 監視ダッシュボード

kabusys/execution/
- order_manager.py                — 注文作成・状態同期
- reconciler.py                   — 起動時のリコンシリエーション
- （その他: broker_factory, order_repository 等、実行ロジック関連）

kabusys/portfolio/
- portfolio_builder.py            — 候補選定・重み計算
- position_sizing.py              — 発注株数計算
- risk_adjustment.py              — セクターキャップ・レジーム乗数

kabusys/research/
- factor_research.py              — モメンタム/ボラ/バリュー等計算（DuckDB）
- feature_exploration.py          — 将来リターン・IC・統計サマリー

kabusys/tools/
- paper_verification_report.py    — Paper Trading の検証レポート生成ツール

kabusys/utils/
- process_priority.py             — プロセス優先度 / CPU affinity 設定ユーティリティ

7. よくある操作例（まとめ）
----------------------------
- 監視開始（デフォルト 60 秒間隔）
  python -m kabusys.run_monitoring

- 監視間隔を 30 秒に変更
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン（Paper Trading）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit ダッシュボード起動
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading レポート（期間指定）
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

8. 追加情報 / 開発ノート
-----------------------
- ログレベルは環境変数 LOG_LEVEL で指定できます（例: LOG_LEVEL=DEBUG）。
- process_priority の設定は psutil を利用します。権限不足等で失敗する場合はログに警告が出て設定はスキップされます。
- DuckDB のテーブル（prices_daily / raw_financials / raw_news / news_symbols / ai_scores / market_regime 等）は外部 ETL やデータ収集パイプラインにより準備する必要があります。
- 監視 DB の初期化は run_monitoring.py / run_execution.py 内で init_monitoring_db() を呼んで行われます（冪等）。

問い合わせ・貢献
----------------
コードベースの詳細・追加の実行オプションや broker 実装、データパイプラインに関する質問がある場合は、該当モジュール（kabusys/ 以下）を参照し、必要に応じて issues を立ててください。

以上。必要があれば、README に記載するサンプル .env.example を作成したり、依存関係の requirements.txt を生成するサポートを提供します。