# KabuSys

KabuSys は日本株の自動売買／リサーチ／監視を目的とした軽量なコードベースです。  
このリポジトリは取引実行エンジン、監視（モニタリング）機能、ポートフォリオ構築、ファクター計算、ニュースNLP（OpenAI を使ったセンチメント評価）などの主要コンポーネントで構成されています。

以下はコードベースの概要、機能、セットアップ手順、使い方、主要ディレクトリ構成の説明です。

プロジェクト概要
- 目的: 日本株向けの自動売買システムのコンポーネント（ExecutionEngine、Monitoring、Research、AI ニューススコアリング、ポートフォリオ構築等）を提供する。
- 設計方針:
  - DB は SQLite（監視用 / 紙トレ用）と DuckDB（時系列・ファクタ計算用）を併用。
  - Paper Trading（検証）モードは実運用 DB と分離（data/paper_trading.db）。
  - 環境変数/.env による設定管理（自動 .env ロード機構あり）。
  - OpenAI を用いるモジュールは API キーを環境変数または引数で受け取る（フェイルセーフ実装）。

主な機能一覧
- 実行関連
  - run_execution.py: ExecutionEngine の起動スクリプト。KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用して paper_trading 用 DB に記録。
  - order_manager、reconciler による状態管理・再同期間合（クラッシュ復旧のためのリコンシリエーション）。
- 監視（Monitoring）
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト（デフォルト 60 秒）。
  - SystemMonitor: CPU/メモリ/ディスク/プロセス生存チェック、データ鮮度チェック（DuckDB の最終価格日）。
  - TradeMonitor: 注文滞留（stale orders）、約定異常価格の検出。
  - RiskMonitor: ドローダウン / ポジション数上限の監視とダッシュボード更新。
  - KillSwitch: kill.flag による ExecutionEngine 停止シグナル管理。
  - AlertManager: LINE Messaging API 経由のアラート（クールダウン管理）。
  - monitoring DB 用ユーティリティ（init_monitoring_db, MonitoringDB）。
  - Streamlit ダッシュボード（監視データの可視化）。
- 研究・ファクター系
  - research/factor_research.py: Momentum / Volatility / Value 等のファクター計算（DuckDB 経由で prices_daily/raw_financials を参照）。
  - research/feature_exploration.py: 将来リターン計算、IC（Information Coefficient）等の統計ツール。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定・等分/スコア重みの計算。
  - portfolio/position_sizing.py: 株数決定・リスク制限・単元株丸め（lot_size）。
  - portfolio/risk_adjustment.py: セクターキャップ、レジーム乗数。
- AI（OpenAI）
  - ai/news_nlp.py: ニュース記事の銘柄別センチメント（OpenAI）を ai_scores テーブルへ書き込む。
  - ai/regime_detector.py: ma200 とマクロニュースセンチメントを合成して日次の市場レジーム判定（market_regime への書き込み）。
- ツール
  - tools/paper_verification_report.py: Paper Trading DB（data/paper_trading.db 等）から検証レポートを生成。稼働率、注文成功率、レイテンシなどを算出。

セットアップ手順（開発環境）
1. リポジトリをクローンして作業ディレクトリをルートにする。
2. Python 3.9+（対応するバージョン）を用意する。
3. 依存パッケージをインストール（requirements.txt がある場合はそれを使ってください）。無ければ主要な依存を手動で入れる例:
   - pip install duckdb psutil requests openai streamlit
4. 環境変数の設定
   - プロジェクトルートに .env を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数（例）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須用途がある場合）
     - KABU_API_PASSWORD: kabu API のパスワード（注文系で必須）
     - OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必要）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知を有効にする場合
     - SQLITE_PATH: 監視 DB のパス（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: paper trading 用 sqlite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で使用）
     - PID_FILE_PATH / KILL_FLAG_PATH 等（デフォルトは data 以下）
5. data ディレクトリを準備（自動で作られる場合もあるが手動で作成しておくと安全）
   - mkdir -p data

使い方（実行例）
- 監視ループ起動（SystemMonitor のポーリング）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可（秒、デフォルト 60）
  - 実行:
    - python -m kabusys.run_monitoring
  - 監視は monitoring.db（デフォルト data/monitoring.db）にログを記録します。

- 実行エンジン起動（ExecutionEngine）
  - KABUSYS_ENV によって挙動が変わる:
    - KABUSYS_ENV=paper_trading: MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録。「本番 DB と完全分離」
    - live: 実ブローカー接続（Kabu API など）を使用
  - 実行:
    - python -m kabusys.run_execution
  - 起動時に stop flag (data/stop_requested.flag) が存在する場合は起動しません。
  - 実行中に stop flag を作成すると安全に停止処理を行います。

- Streamlit ダッシュボード（監視可視化）
  - 起動方法:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで SQLite を開くため、監視エンジンが稼働中でも安全に閲覧できます。

- Paper Trading 検証レポート生成
  - 使い方:
    - python -m kabusys.tools.paper_verification_report
    - オプション:
      - --from YYYY-MM-DD
      - --to YYYY-MM-DD
      - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）
  - 出力: 稼働率、注文成功率、送信率、P95 レイテンシ等。基準値に基づいて PASS/FAIL 判定を行います。

- AI 関連
  - ai.news_nlp.score_news と ai.regime_detector.score_regime は OpenAI API を使用します。OPENAI_API_KEY を設定するか、関数引数で api_key を渡してください。
  - API 呼び出しはリトライ・フォールバック実装を含み、失敗が全体を止めないようになっています（ただし API キー未設定だとエラーになります）。

設定 / 環境変数（主なもの）
- KABUSYS_ENV: development | paper_trading | live
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒（デフォルト 60）
- SQLITE_PATH: 監視 DB（data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 DB（data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（data/kabusys.duckdb）
- PID_FILE_PATH, KILL_FLAG_PATH: 実行制御に使用
- PAPER_FILL_MODE: paper_trading の約定挙動（instant / partial / never / reject）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで必須）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 用トークン/パスワード
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE 通知）用

注意事項 / 運用メモ
- run_monitoring は監視用 DB として常に本番 sqlite_path を参照します（KABUSYS_ENV に依らず本番設定を使う実装になっています）。paper_trading と混ざらないよう注意してください。
- run_execution は paper_trading モード時に paper DB を使用して本番 DB と分離します。
- set_process_priority("high") を起動直後に呼出しています。OS により権限エラー（AccessDenied）になる場合がありますが、その場合はログで警告が出て処理は継続します。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して行います。自動ロードを禁止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Stop / Kill 制御:
  - data/stop_requested.flag: run_monitoring/run_execution はこのファイルの存在でループを抜ける（停止）ようになっています。
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります（kill.flag の書込みは冪等）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env のロードと Settings クラス
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）による ai_scores 書込み
    - regime_detector.py — レジーム判定（ma200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py — monitoring DB スキーマと MonitoringDB クラス
    - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種モニタ
    - kill_switch.py — kill.flag 操作
    - alert_manager.py — LINE 送信
    - monitoring_engine.py — 各 Monitor を束ねる実行エンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - reconciler.py, order_manager.py, ...（注文管理・再同期間合）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - research/
    - factor_research.py, feature_exploration.py
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py

開発向けヒント
- DuckDB と DuckDB 接続を使ったファクタ計算やリサーチ系は、prices_daily / raw_financials / raw_news 等のテーブルが必要です。クリーンなテストを行う場合はテスト用の DuckDB を用意してください。
- monitoring DB は init_monitoring_db() でスキーマを冪等に作成します。初回起動時に自動でテーブル作成されます。
- ai モジュールのテストは _call_openai_api をモックして実施すると簡単です（コード中でもパッチを想定している箇所があります）。
- 単体関数群（portfolio, research）は DB 非依存（純粋関数）が多く、単体テストしやすい設計です。

ライセンス / バージョン
- パッケージバージョン: __version__ = "0.1.0"
- ライセンス表記はリポジトリ内の LICENSE を参照してください（存在する場合）。

以上が README の概略です。必要であれば、README にサンプル .env.example、requirements.txt の推奨内容、主要コマンドのワンライナー（systemd サービス例や supervisor 設定など）を追記します。どの情報を追加しますか？