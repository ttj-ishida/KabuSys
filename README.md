README.md

KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買 / 監視 / リサーチを目的とした軽量なフレームワークです。
主な設計方針は「本番と検証の分離」「ルックアヘッドバイアス回避」「外部API呼び出しのエラーハンドリング強化」です。
実行エンジン（ExecutionEngine）、監視（MonitoringEngine）、ポートフォリオ構築、ファクター計算、ニュースNLP（OpenAI）によるセンチメントなどのモジュールで構成されます。

主な機能
--------
- ExecutionEngine
  - ブローカー抽象化（実口座 / paper_trading 用 MockBroker を切替可）
  - OrderManager / OrderRepository による注文状態管理、Reconciler による再起動時の同期
  - リスク管理（RiskManager）を組み合わせた安全な発注フロー
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス生存・データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン / ポジション上限の監視とリスクログ記録
  - KillSwitch: フラグファイルによる ExecutionEngine 停止シグナル
  - AlertManager: LINE へのプッシュ通知（cooldown 管理）
  - Streamlit ダッシュボード（監視データ可視化）
- Portfolio（純粋関数群）
  - 銘柄選定、等配分・スコア加重配分、ポジションサイズ算出、セクターキャップ、レジーム乗数など
- Research
  - DuckDB を使ったファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC（Information Coefficient）計算等、研究用途のユーティリティ
- AI（OpenAI）
  - news_nlp: ニュース記事をまとめて LLM に投げ、銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector: ETF (1321) の MA とマクロニュースの LLM センチメントを合成して市場レジーム判定
- ツール
  - paper_verification_report: Paper Trading の検証レポート出力（稼働率/注文成功率/レイテンシ等）

セットアップ手順
----------------
1. 前提
   - Python 3.10 以上を推奨（コード中で型ヒントに | 演算子を使用）
   - SQLite（標準ライブラリ）、DuckDB（外部パッケージ）

2. 仮想環境（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（最低限）
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトで追加のパッケージが必要な場合は requirements.txt を用意している想定で pip install -r を使ってください）

4. 環境変数の設定
   - プロジェクトルートの .env または .env.local を読み込みます（自動ロード。ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 重要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 時の DB、デフォルト: data/paper_trading.db)
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定動作）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（監視アラート用）

   - .env の書式はシェル風（コメント行、export プレフィックス、クォートやエスケープをある程度サポート）です。

5. データディレクトリ作成（実行時に自動作成されることもありますが事前に準備しておくと良い）
   - mkdir -p data

使い方
------
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - run_monitoring は監視用 SQLite（Settings.sqlite_path）に接続し、init_monitoring_db によってテーブルを作成します
  - 監視は常に本番用 sqlite_path を使用（KABUSYS_ENV に依らず）

- ExecutionEngine 起動（発注実行）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ完全に分離して記録します
  - 起動時に pid_file を書き、監視側がプロセス生存を確認します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to   YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH を上書き）
  - 出力: 稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などのレポートと PASS/FAIL 判定

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで SQLite を開き、Overview / Positions / Orders / System タブで監視データを確認

- AI 関連
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date を与えて実行します
  - 実行には OPENAI_API_KEY が必要（引数でも渡せます）
  - LLM 呼び出しはリトライ・エラーハンドリングを備え、失敗時はフォールバック（部分的にスキップ）します

- プロセス優先度 / CPU affinity
  - run_* スクリプトは起動時に set_process_priority("high") を呼びます（psutil を使用）
  - 必要に応じて kabusys.utils.process_priority の API を利用できます

設定と挙動メモ
----------------
- Settings クラス（kabusys.config）で主要設定値は環境変数・.env から取得します。
- 自動ロード順序: OS 環境変数 > .env.local（override）> .env（未設定のみ）
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれか
- Paper Trading は本番 DB と分離（PAPER_TRADING_SQLITE_PATH を使用）
- Monitoring DB のスキーマは init_monitoring_db で作成・マイグレーションされます

ディレクトリ構成（主要ファイル）
-----------------------------
（抜粋）
- src/kabusys/
  - __init__.py            — パッケージ定義
  - config.py              — 環境変数 / Settings
  - run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py  — psutil ベースの優先度 / affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py     — SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py    — システム状態 / データ鮮度チェック
    - trade_monitor.py     — 注文滞留・約定異常検出
    - risk_monitor.py      — ドローダウン・ポジション上限監視
    - kill_switch.py       — kill.flag の書き込み / 管理
    - alert_manager.py     — LINE push 通知（クールダウン管理）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ベースのダッシュボード
  - execution/
    - order_manager.py     — OrderManager（作成 → 送信 → 同期）
    - reconciler.py        — 起動時の注文・ポジションリコンシリエーション
    - （その他: broker_factory, order_repository, order_record 等が想定される）
  - portfolio/
    - portfolio_builder.py  — 候補選定・重み計算
    - position_sizing.py    — 株数計算・単元丸め・集計キャップ
    - risk_adjustment.py    — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py    — Momentum/Volatility/Value 等のファクター計算（DuckDB）
    - feature_exploration.py— 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py           — ニュース集約 → OpenAI で銘柄別スコア化 → ai_scores へ保存
    - regime_detector.py    — MA とマクロニュースの LLM を合成して市場レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

補足 / 運用上の注意
------------------
- 本リポジトリのコードは、外部ブローカー API や OpenAI API に依存する機能を含みます。これらを使用する際は API キーや認証情報の管理を厳重に行ってください。
- Paper Trading モードは実口座と完全分離される設計ですが、設定ミスを避けるために .env の KABUSYS_ENV を確実に確認してください。
- run_execution/run_monitoring はプロセスをデーモン化しない単純起動スクリプトです。運用時は systemd / Supervisor / pm2 等でプロセスマネージメントしてください。
- データベースファイル（data/ 以下）はバックアップ・ローテーションを検討してください。特に DuckDB は大きくなる可能性があります。

貢献
----
バグ報告や改善提案は Issue を作成してください。Pull Request での貢献も歓迎します。

お問い合わせ
------------
- コード内コメントとドキュメンテーション（関数 docstring）が詳細です。実装や挙動で不明点があれば、該当モジュールの docstring をまず参照してください。

以上。README に含めたい追加項目（例: サンプル .env.example、requirements.txt の生成、CI/テスト方法など）があればお知らせください。