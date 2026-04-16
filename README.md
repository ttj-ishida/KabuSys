KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買／研究プラットフォームのコードベースです。本リポジトリは複数の責務を持つコンポーネント群で構成されています: 実際の発注を行う ExecutionEngine、システム／注文を監視する Monitoring、ファクター計算や研究用ユーティリティ、AI（ニュース NLP / レジーム判定）モジュール、ポートフォリオ構築ロジックなど。  
本 README はコードベースに含まれる主要な機能・セットアップ・使い方・ディレクトリ構成を簡潔にまとめたものです。

主な機能
--------
- 実行（Execution）
  - ExecutionEngine による注文作成・管理、OrderManager、Reconciler（起動時の自動復旧）
  - paper_trading モードでは MockBrokerClient を使用、実運用 DB と分離
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス PID、データ鮮度のチェック
  - TradeMonitor: 滞留注文（stale order）、約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、kill flag 発行
  - AlertManager: LINE への一方向プッシュ通知
  - MonitoringEngine: 上記を統合したポーリングループ
  - Streamlit ダッシュボード（監視データ可視化）
- 研究（Research）
  - ファクター計算（momentum / volatility / value 等）
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ
- ポートフォリオ構築（Portfolio）
  - 候補選定、重み付け、セクター制限、ポジションサイズ計算（lot サイズ丸め等）
- AI（OpenAI）
  - news_nlp: ニュース記事のセンチメントスコア取得（OpenAI API）
  - regime_detector: マクロセンチメントと ETF MA を合成して市場レジーム判定
- 運用補助ツール
  - paper_verification_report: Paper Trading 用検証レポート生成スクリプト

セットアップ
------------
前提:
- Python 3.10 以上（型アノテーション等を利用）
- OS に依存する機能（プロセス優先度設定など）は psutil が必要

例: 仮想環境作成と依存パッケージのインストール
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必須ライブラリをインストール（例）
   - pip install duckdb psutil requests openai streamlit

   （実際の project requirements が存在する場合は requirements.txt / pyproject.toml を参照してください）

環境変数（主なもの）
- KABUSYS_ENV: 起動環境 ("development" | "paper_trading" | "live")。既定は development。
  - paper_trading の場合、ExecutionEngine は MockBrokerClient を使い data/paper_trading.db を使用（本番 DB と分離）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須で使う機能あり）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須で使う機能あり）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（AI モジュール利用時）
- PAPER_FILL_MODE: paper_trading の約定挙動 ("instant" | "partial" | "never" | "reject")（デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: Paper DB パス（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視 DB（monitoring.db）パス（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB のパス（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）。1 未満や不正値は無視されデフォルトにフォールバック。
- LOG_LEVEL: ログレベル ("DEBUG"..."CRITICAL")

.env の自動読み込み:
- プロジェクトルートに .env / .env.local がある場合、自動的に読み込まれます（OS 環境変数を優先）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ファイル・DB の既定位置
- data/monitoring.db         — SQLite（監視ログ）
- data/paper_trading.db      — SQLite（paper_trading 用、KABUSYS_ENV=paper_trading の場合に使用）
- data/kabusys.duckdb        — DuckDB（履歴データ / prices_daily 等）
- data/execution.pid         — ExecutionEngine の PID ファイル
- data/stop_requested.flag   — 手動停止要求フラグ（起動スクリプトがこれを検出して安全停止）
- data/kill.flag             — KillSwitch が書く実行停止フラグ（ExecutionEngine に停止命令）

使い方（実行例）
----------------

1) 監視ループを起動（Monitoring）
- コマンド:
  - python -m kabusys.run_monitoring
- 説明:
  - SystemMonitor を中心としたポーリングループを開始します。MONITOR_POLL_INTERVAL 環境変数で間隔を秒単位に調整できます（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path（SQLITE_PATH）を使用して monitoring テーブル群を初期化します。
  - 起動時にプロセス優先度を "high" に設定しようとします（権限不足時は警告でスキップ）。

2) 実行エンジンを起動（Execution）
- コマンド:
  - python -m kabusys.run_execution
- 説明:
  - ExecutionEngine を起動してトレードセッションを実行します。
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db を使って本番 DB と完全分離します。
  - 起動前に data/stop_requested.flag が存在する場合は起動せず終了します。起動後は同フラグを監視して停止要求を受け付けます。

3) Streamlit 監視ダッシュボード
- コマンド:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - Monitoring の SQLite DB を read-only で開き、Overview / Positions / Orders / System タブを表示します。

4) Paper Trading 検証レポート
- コマンド:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
- 説明:
  - Paper Trading の SQLite に記録されたログから稼働率、注文成功率、レイテンシ等を集計して標準出力へレポートを出力します。

5) AI モジュール（プログラム内から呼び出し）
- news_nlp（銘柄ごとのニュースセンチメントを DuckDB の raw_news から取得して ai_scores に書き込む）
  - 例（Python）:
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 4, 1), api_key="YOUR_OPENAI_KEY")
- regime_detector（市場レジーム判定）
  - 例（Python）:
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, date(2026, 4, 1), api_key="YOUR_OPENAI_KEY")

停止・強制停止制御
-----------------
- 停止リクエスト（スクリプト側監視）
  - data/stop_requested.flag を作成すると run_execution.py / run_monitoring.py は次のポーリングで検出して安全に停止します。
- KillSwitch（リスク閾値により ExecutionEngine を停止させる）
  - RiskMonitor が閾値を超えると KillSwitch が data/kill.flag に理由を書き込みます。ExecutionEngine は起動時に kill.flag をクリアする動作を設定できます（Settings.kill_flag_clear_on_start）。

注意事項 / 運用上のポイント
-------------------------
- paper_trading モードは本番 DB と完全に分離するよう設計されています。必ず KABUSYS_ENV を適切に設定して運用してください。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CI / テストで自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI を使う機能は API キー（OPENAI_API_KEY）を要求します。API の失敗時はフェイルセーフ（スコア=0 など）で継続する実装が多いですが、運用ポリシーに応じてレート制御や再試行設定を行ってください。
- process priority / cpu affinity の設定はプラットフォーム依存であり、権限不足時にはスキップされます（ログに警告）。

主なディレクトリ構成
-------------------
（src/kabusys 以下の主要ファイル／ディレクトリと簡単な説明）

- src/kabusys/
  - __init__.py                — パッケージの基本情報（バージョン等）
  - config.py                  — Settings クラス: 環境変数の読み取りと検証、.env 自動読み込み
  - run_monitoring.py          — SystemMonitor ポーリングループの起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
- src/kabusys/monitoring/
  - monitoring_db.py           — SQLite を使った監視ログ永続化（init / CRUD）
  - system_monitor.py          — CPU/メモリ/ディスク/プロセス/データ鮮度チェック
  - trade_monitor.py           — 注文滞留 / 約定異常検出
  - risk_monitor.py            — ドローダウン・ポジション上限監視
  - kill_switch.py             — kill.flag 書き込みユーティリティ
  - alert_manager.py           — LINE プッシュ通知用
  - monitoring_engine.py       — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py     — Streamlit ダッシュボード
- src/kabusys/execution/
  - order_manager.py           — 発注・状態管理ロジック
  - reconciler.py              — 起動時リコンシリエーション（注文・ポジション同期）
  - ...（broker_factory, execution_engine, order_repository 等が存在）
- src/kabusys/portfolio/
  - portfolio_builder.py       — 候補選定 / 等重配分 / スコア重み付け
  - position_sizing.py         — 株数算出・上限・単元丸め・スケール調整
  - risk_adjustment.py         — セクターキャップ・レジーム乗数
- src/kabusys/research/
  - factor_research.py         — Momentum / Volatility / Value ファクター計算
  - feature_exploration.py     — 将来リターン / IC / 統計サマリ等
- src/kabusys/ai/
  - news_nlp.py                — ニュースによる銘柄センチメント計算（OpenAI 経由）
  - regime_detector.py         — マクロ + ETF MA によるレジーム判定（OpenAI 経由）
- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート出力スクリプト
- src/kabusys/utils/
  - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ

補足: Settings に定義されている代表的プロパティ
- env / is_live / is_paper / is_dev
- duckdb_path / sqlite_path / paper_sqlite_path / pid_file_path / kill_flag_path
- PAPER_FILL_MODE の検証ロジックあり（instant|partial|never|reject）

トラブルシューティング
-----------------------
- .env を編集しても反映されない場合:
  - プロジェクトルートが正しく検出されているか (.git または pyproject.toml があるか) 確認。
  - 自動読み込みを無効にしている (KABUSYS_DISABLE_AUTO_ENV_LOAD=1) 場合は手動で環境変数を設定するか明示的に読み込んでください。
- OpenAI 関連で JSON 解析エラーが発生する場合:
  - API レスポンスが期待された JSON を返しているか、API キーやモデルに問題がないかを確認してください。news_nlp は JSON mode を利用して厳密な JSON を期待する設計です。

ライセンス・開発ポリシー
------------------------
（この README にはライセンス情報は含まれていません。実際のプロジェクトでは LICENSE ファイルを参照してください。）

終わりに
-------
この README はコードベースの主要箇所の使い方と設計上のポイントをまとめたものです。実装の詳細や設計ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）はリポジトリ内の参照ドキュメントを確認してください。追加で README に載せたい運用手順やデプロイ手順などがあれば指示ください。