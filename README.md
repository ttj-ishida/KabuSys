KabuSys — 日本株自動売買システム
================================

このリポジトリは、J‑Quants / kabu ステーション 等を利用した日本株自動売買システムのコードベースです。
README は開発者向けにプロジェクト概要、主な機能、セットアップ手順、利用方法、ディレクトリ構成を日本語でまとめたものです。

プロジェクト概要
---------------
KabuSys は以下の要素で構成される自動売買プラットフォームです。

- 戦略の研究・ファクター計算（DuckDB を用いた時系列処理）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- ExecutionEngine（ブローカークライアント経由で発注。paper_trading モードは MockBroker）
- 監視（System / Trade / Risk モニタ、Kill Switch）
- AI 補助（ニュース NLP によるセンチメント、レジーム判定：OpenAI 利用）
- 運用支援ツール（設定ウィザード、設定検証、Paper Trading 検証レポート）

主な特徴（機能一覧）
-------------------
- 設定管理
  - .env 自動ロード（プロジェクトルートの .env / .env.local、環境変数優先）
  - 設定ウィザード (python -m kabusys.config_setup)
  - 設定検証 CLI (python -m kabusys.validate_config)
- 実行 / 監視プロセス
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV による paper_trading/live 切替）
  - run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
  - Kill Switch: 条件を満たすと data/kill.flag を書き ExecutionEngine を停止
- モニタリング永続化
  - SQLite ベースの monitoring DB（system_status / trade_logs / positions / risk_logs / dashboard）
  - MonitoringDB クラスで読み書き
- ポートフォリオ構築
  - 候補選定（スコア降順）
  - 重み付け（等分・スコア加重）
  - ポジションサイジング（risk_based / equal / score、単元株丸め、aggregate cap）
  - セクターキャップ適用、レジーム乗数
- 研究モジュール
  - ファクター計算（momentum, volatility, value 等）
  - 将来リターン計算、IC（情報係数）や統計サマリ
- AI モジュール（OpenAI）
  - news_nlp: ニュースを集約して LLM に投げ、銘柄別センチメントを ai_scores に格納
  - regime_detector: ETF とマクロニュースを用いて market_regime を判定
- 運用ツール
  - tools/paper_verification_report: Paper Trading の検証レポート生成（SQLite 参照）

必須環境変数（主なもの）
-----------------------
最低限設定が必要な環境変数（validate_config でもチェックされます）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
その他（任意 / デフォルトあり）:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時に必要）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs/）

セットアップ手順
---------------
1. リポジトリを取得
   - git clone … (あるいは配布ソースを展開)

2. Python 環境（推奨: venv）を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 主要依存（コード参照）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定ファイル検証時に任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   注意: リポジトリに requirements.txt がない場合は上のパッケージを必要に応じて追加してください。

4. .env を作成
   - 推奨: python -m kabusys.config_setup で対話的に作成
   - もしくは .env.example を参考に手動作成
   - 自動ロードを無効化したい場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになる

6. データディレクトリの確認
   - デフォルトのデータパス（data/, logs/）が自動作成されますが、必要に応じて手動で作ってください。

基本的な使い方（起動 / 停止 / ツール）
-------------------------------------

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 用 DB に記録（本番 DB と分離）
    - 起動前に data/stop_requested.flag が存在すると起動しない
    - 実行中は data/execution.pid に PID を書く（設定により変更可）

- Monitoring を起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト 60 秒）
  - 監視は環境に関わらず本番 sqlite_path を使って監視ログを保存します
  - 停止方法: プロジェクトルート data/stop_requested.flag を作成すると監視ループは終了します

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告があると終了コード 1 を返します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to   YYYY-MM-DD
    - --db PATH （デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- AI（ニュース NLP / レジーム判定）
  - これらは関数 API（kabusys.ai）として提供されています。利用には OPENAI_API_KEY が必要です。
  - 例（Python から呼ぶ）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="…")

停止と Kill Switch
------------------
- 停止フラグ:
  - data/stop_requested.flag — run_execution/run_monitoring が監視している簡易停止フラグ（存在するとプロセスは停止）
- Kill Switch:
  - 監視側が条件（ドローダウン・ポジション上限等）を満たすと data/kill.flag を書き、ExecutionEngine に停止指示を出します。
  - 設定により Kill Flag の自動クリアを許可している場合（KILL_FLAG_CLEAR_ON_START=1）には注意してください（本番では 0 を推奨）。

ログ
---
- setup_logging 関数でログを統一管理します
  - コンソール (stdout) と日次ローテーションファイル（logs/<app_name>.log）を出力
  - デフォルトログディレクトリ: logs/
  - LOG_DIR 環境変数で変更可
  - LOG_LEVEL 環境変数でレベルを指定

データベース（デフォルトパス）
----------------------------
- DuckDB: data/kabusys.duckdb （環境変数 DUCKDB_PATH で変更可）
- 監視 SQLite: data/monitoring.db （環境変数 SQLITE_PATH で変更可）
- Paper Trading SQLite: data/paper_trading.db （環境変数 PAPER_TRADING_SQLITE_PATH で変更可）

主なモジュール（ディレクトリ構成）
--------------------------------
以下は主要ファイル・パッケージの抜粋的な構成（src/kabusys 以下）です。実際のリポジトリではさらにファイルが含まれます。

- kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定読み込みロジック
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py           — ニュース NLP（OpenAI）
    - regime_detector.py    — 市場レジーム判定（OpenAI + ETF）
  - portfolio/
    - portfolio_builder.py  — 候補選定・重み計算
    - position_sizing.py    — 発注株数計算・集約制限
    - risk_adjustment.py    — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py    — ファクター計算 (momentum/volatility/value)
    - feature_exploration.py— 将来リターン / IC / 統計
  - monitoring/
    - monitoring_db.py      — SQLite 永続層（テーブル作成 / マイグレーション / CRUD）
    - system_monitor.py     — システム状態監視
    - trade_monitor.py      — （注文監視）※実装参照
    - risk_monitor.py       — ドローダウン・ポジション監視
    - kill_switch.py        — kill.flag 操作用ユーティリティ
    - monitoring_engine.py  — 各 Monitor を束ねるエンジン
    - alert_manager.py      — （通知送信）※実装参照
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity ユーティリティ
  - data/                   — 実行時に使用されるディレクトリ（pid/flag/db/logs 等）

開発上の注意点 / ベストプラクティス
----------------------------------
- .env は決して Git にコミットしないでください（config_setup でもヘッダに注意喚起あり）。
- KABUSYS_ENV を live にすると本番設定になるため、LINE 通知や Kill Switch 設定などを十分に確認してください。
- Paper Trading は本番 DB と分離（PAPER_TRADING_SQLITE_PATH）する設計です。テスト時は paper_trading モードを利用してください。
- AI 機能を使う場合は OPENAI_API_KEY を設定し、API のレート制限やコストに注意してください。
- DuckDB による分析処理は大量データを扱う場合に I/O やメモリの負荷が高くなることがあります。適切に環境設定を行ってください。
- ログディレクトリ作成やファイル書き込みに失敗した場合、システムはコンソール出力のみで継続するよう実装されていますが、運用時は logs ディレクトリが正しく書き込み可能であることを確認してください。

トラブルシューティング
----------------------
- 設定検証でエラーが出る:
  - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を確認
  - .env を正しく配置しているか、プロジェクトルートが認識されているか確認
- ExecutionEngine / Monitoring が開始しない:
  - data/stop_requested.flag が存在すると起動を拒否します。不要なら削除してください。
  - pid/flag のパーミッションやファイル所有権を確認
- OpenAI 呼び出しエラー:
  - OPENAI_API_KEY が設定されているか、API 利用制限・ネットワークを確認

ライセンス・バージョン
----------------------
- パッケージの __version__ は 0.1.0（src/kabusys/__init__.py）。
- ライセンス情報はリポジトリの LICENSE ファイルを確認してください（本 README 上に含まれていない場合は追加してください）。

最後に
-------
この README はコードベースの主要点をまとめたものです。より詳細な仕様やドキュメント（PortfolioConstruction.md、StrategyModel.md 等）がプロジェクトに含まれている場合はそちらも合わせて参照してください。質問や追加したい項目があれば教えてください。