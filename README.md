KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を行うための小規模なフレームワークです。本プロジェクトは以下の要素で構成されています。

- 発注実行エンジン（ExecutionEngine）と Order 管理
- Paper Trading（モックブローカー）対応（本番 DB と分離）
- 監視（System / Trade / Risk）と kill flag による安全停止
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- リサーチ（ファクター計算・特徴量探索）
- AI を用いたニュース NLP（OpenAI）と市場レジーム検出
- モニタリング用 Streamlit ダッシュボード
- 検証レポート生成ツール（Paper Trading 向け）

主な特徴（機能一覧）
-----------------
- 実行
  - ExecutionEngine を起動して発注／リスク管理／再突合（reconciliation）を実行
  - KABUSYS_ENV により "development" / "paper_trading" / "live" を切替可能
  - paper_trading モードでは MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）

- 監視
  - SystemMonitor: CPU/メモリ/ディスク/プロセス生存・データ鮮度監視
  - TradeMonitor: 注文滞留や約定時の価格異常検出
  - RiskMonitor: ドローダウンやポジション数上限の監視とログ記録
  - KillSwitch: しきい値超過時に data/kill.flag を出力して ExecutionEngine を停止
  - AlertManager: LINE Messaging API へプッシュ通知（クールダウン管理）

- ポートフォリオ構築
  - 候補選定（スコア降順）
  - 等金額またはスコア加重の重み付け
  - リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ決定（単元株丸め、aggregate cap、コストバッファ）

- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（OpenAI）
  - ニュースを LLM（gpt-4o-mini）でセンチメント評価して ai_scores テーブルへ格納
  - マクロニュースと ETF MA200 乖離を組み合わせて市場レジーム判定（bull/neutral/bear）

- ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定可）
  - Streamlit ダッシュボードで監視情報の可視化

セットアップ手順
----------------

前提
- Python 3.10 以上（コード中での型 | Union 構文を使用）
- SQLite（組み込み）
- DuckDB（pip パッケージ）
- ネットワークアクセス（OpenAI API / LINE API を使う場合）

依存パッケージ（代表例）
- duckdb
- psutil
- requests
- openai
- streamlit

インストール例
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

（プロジェクトに requirements.txt があればそれを使ってください）

環境変数
- 自動で .env / .env.local をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 重要な環境変数:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須の機能を使う場合）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
  - OPENAI_API_KEY — OpenAI を使う場合に必要
  - KABUSYS_ENV — 起動環境 (development | paper_trading | live) (デフォルト: development)
  - PAPER_FILL_MODE — paper_trading の約定モード（instant|partial|never|reject）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — kill flag（デフォルト: data/kill.flag）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒。run_monitoring のみ。デフォルト 60）

初期化
- 監視用 DB スキーマは run_monitoring/run_execution 内で自動的に作成（init_monitoring_db）されます。手動で作成する必要は通常ありません。
- data ディレクトリを作る: mkdir -p data

使い方（起動・実行例）
---------------------

1) ExecutionEngine を起動（本番 or paper_trading）
- 本番風起動（development での接続設定に応じて挙動は変わります）
  - KABUSYS_ENV=live KABU_API_PASSWORD=... python -m kabusys.run_execution

- Paper Trading（DB を分離、MockBroker 使用）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 必要に応じて PAPER_FILL_MODE=instant|partial|never|reject を設定

2) 監視プロセスを起動
- MONITOR_POLL_INTERVAL を指定してポーリング間隔を変更可能（秒、デフォルト 60）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

3) Paper Trading 検証レポート（コマンドライン）
- python -m kabusys.tools.paper_verification_report
- 期間指定例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB を手動指定:
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

4) Streamlit ダッシュボード（監視用）
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ブラウザでダッシュボードの GUI を閲覧、簡易的に監視状態とログを確認できます。

5) AI コンポーネントの呼び出し（スクリプト内 API）
- ニュース NLP（指定日付のスコアを ai_scores テーブルへ保存）
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key="...")

- レジーム判定（market_regime テーブルへ書き込み）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key="...")

実運用上のポイント
- Monitoring は常に（KABUSYS_ENV にかかわらず）本番の sqlite_path を使ってログを残す設計になっています（run_monitoring 内の注意）。
- ExecutionEngine は paper_trading 時に paper_sqlite_path を使うため、本番 DB と完全に分離されています。
- kill.flag による安全停止: KillSwitch が trigger した場合、data/kill.flag が書込まれ、ExecutionEngine は起動時や定期チェックでこれを確認して停止することを想定しています。
- プロセス優先度: 起動時に set_process_priority("high") を呼び出しますが、権限がないと失敗してスキップされます（警告ログ）。

ディレクトリ構成（主要ファイル）
-------------------------------

src/kabusys/
- __init__.py
- config.py                    — 環境変数読み込み / Settings
- run_execution.py             — ExecutionEngine 起動スクリプト
- run_monitoring.py            — SystemMonitor 単体起動スクリプト
- tools/
  - __init__.py
  - paper_verification_report.py — Paper Trading 検証レポート CLI
- monitoring/
  - __init__.py
  - monitoring_db.py            — SQLite スキーマと永続化層
  - system_monitor.py           — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py            — 注文滞留・約定異常検出
  - risk_monitor.py             — ドローダウン・ポジション数監視
  - kill_switch.py              — kill.flag 書込ロジック
  - alert_manager.py            — LINE 通知
  - monitoring_engine.py        — 各 Monitor を束ねたループ
  - streamlit_dashboard.py      — Streamlit ダッシュボード
- execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - execution_engine.py
  - broker_factory.py
  - broker_api.py               — ブローカー API 抽象
  - order_record.py             — Order の状態遷移ロジック
  - ...（実際のブローカー実装や order_record の追加定義がある想定）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- ai/
  - news_nlp.py                 — ニュースセンチメント (OpenAI)
  - regime_detector.py          — マクロ + MA200 でレジーム判定
  - __init__.py
- data/
  - pipeline.py                 — DuckDB prices の最終日取得など（参照用）
  - stats.py                    — zscore_normalize 等（リサーチ補助）
- utils/
  - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ
  - __init__.py

データ・ファイル（デフォルトパス）
- data/kabusys.duckdb        (DuckDB)
- data/monitoring.db         (監視ログ: SQLite)
- data/paper_trading.db      (paper_trading 用 SQLite)
- data/execution.pid         (ExecutionEngine の PID ファイル)
- data/kill.flag             (KillSwitch が書き込む停止フラグ)

開発・デバッグのヒント
- .env/.env.local に環境変数を置くと自動読み込みされます（プロジェクトルート検出に .git または pyproject.toml を使用）。
- Settings クラスにより各種設定値がラップされているため、テスト時は環境変数を差し替えて挙動を確認できます。
- Streamlit ダッシュボードは監視 DB を読み取り専用で開くため、MonitoringEngine を先に起動してデータを生成しておくと便利です。
- OpenAI 関連は API 呼び出しに冪等性やフォールバック（失敗時は 0.0 やスキップ）処理が組み込まれていますが、API キーとレート制限に注意してください。

ライセンス・貢献
----------------
- 本 README はコードベースに基づく概要と操作説明です。ライセンス情報やコントリビュート手順はリポジトリのトップレベルに別途用意してください。

質問・補足
--------
使い方や特定モジュールの動作について詳しい説明が必要であれば、どの機能（例: ExecutionEngine の設定、AI スコアリングの内部、ポジション決定ロジックなど）を深掘りしたいか教えてください。追加でサンプル .env.example の雛形も作成できます。