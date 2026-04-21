# KabuSys

日本株向けの自動売買/リサーチ用ライブラリ兼実行フレームワークです。本リポジトリは以下の機能群を含み、プロダクション運用を想定した設計になっています。

- 注文実行エンジン（ExecutionEngine）と監視プロセス（Monitoring）
- ポートフォリオ構築・ポジションサイジングの純粋関数群
- DuckDB を用いたファクター計算 / リサーチ
- OpenAI を使ったニュース NLP（センチメント付与）と市場レジーム判定
- 監視ログ（SQLite）への永続化、キルスイッチ（flag ファイル）による制御
- 環境設定ウィザード・設定検証ツール・ペーパートレード検証レポート出力

以下はこのコードベースを使い始めるための README (日本語) です。

プロジェクト概要
----------------
KabuSys は日本株を対象にした自動売買システムの構成要素群を提供します。主要な目的は以下です。

- 市場データ / 財務データを DuckDB で集計・計算してファクターを生成する（research）
- ポートフォリオ構築・ポジションサイズ計算（portfolio）
- 注文管理・発注フロー（execution, broker_factory 等 — 本リポジトリの一部は参照実装）
- 実行プロセスやシステム状態を監視し、アラート・Kill Switch を有効化する（monitoring）
- OpenAI を使ったニュースのセンチメント評価・レジーム判定（ai）
- ペーパートレード用の検証レポート生成ツール（tools）

機能一覧
--------
主な機能（抜粋）:

- 実行エンジン起動スクリプト
  - run_execution.py: KABUSYS_ENV に応じて paper_trading（MockBroker）/live を切替。専用 DB を使用する。
- 監視プロセス起動スクリプト
  - run_monitoring.py: SystemMonitor をポーリングし監視/アラート/kill 判定を実施。MONITOR_POLL_INTERVAL でポーリング間隔を変更可能。
- 環境設定サポート
  - config_setup.py: 対話形式で .env を生成・更新するウィザード
  - validate_config.py: .env と config/*.yaml の簡易検証（--strict オプションあり）
- ログ設定ユーティリティ
  - utils/logging_setup.py: stdout と日次ローテートファイル出力を統一的に設定
- プロセス優先度設定ユーティリティ
  - utils/process_priority.py: Windows/Linux 双方に対応した優先度設定・CPU affinity
- ポートフォリオ構築
  - portfolio: 候補選定、等比率/スコア比率配分、ポジション数計算（単元調整・aggregate cap）
- リサーチ
  - research: モメンタム/ボラティリティ/バリュー系ファクター計算、将来リターン・IC 計算等（DuckDB 接続を受ける）
- AI（OpenAI）
  - ai/news_nlp.py: ニュース記事を LLM に投げて銘柄別センチメント（ai_score）を ai_scores テーブルへ書込
  - ai/regime_detector.py: ETF (1321) の MA とマクロニュースセンチメントを合成して market_regime を算出・書込
- 監視・リスク
  - monitoring: system/trade/risk の各モニタ、MonitoringDB（SQLite）による永続化、KillSwitch、MonitoringEngine
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB を解析して Pass/Fail 判定付きレポートを標準出力へ出力

セットアップ手順
-------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 基本的に次をインストールしてください（requirements.txt があればそちらを利用）
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証時に YAML ファイル検査を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. データディレクトリ作成
   - data/ と logs/ を作成します（logging_setup が自動作成することもありますが事前に作ると確実）
     - mkdir -p data logs

5. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動で作る場合は .env.example を参考に必要な環境変数を設定してください。
   - 主要な環境変数（Settings クラス参照）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR)
     - OPENAI_API_KEY (AI 機能を使う場合)
     - PAPER_FILL_MODE (paper_trading の約定挙動): instant|partial|never|reject

6. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit 1）扱いになります

使い方
------
主要なエントリポイントと例:

- 実行エンジン（Execution）
  - python -m kabusys.run_execution
  - 起動時に process priority を "high" に設定し、KABUSYS_ENV に応じて paper_trading 用 DB を使います。
  - 実行中に data/stop_requested.flag が作られると安全に停止します。
  - PID ファイル: data/execution.pid（設定で変更可）

- 監視プロセス（Monitoring）
  - python -m kabusys.run_monitoring
  - SystemMonitor をポーリングして monitoring DB にログを蓄積し、KillSwitch 評価や各種アラートを実行します。
  - ポーリング間隔は環境変数で変更可能:
    - MONITOR_POLL_INTERVAL（秒。デフォルト 60）
  - 監視は常に本番 sqlite_path を使用する設計（KABUSYS_ENV に依存しない）

- .env の作成・更新（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD  --to YYYY-MM-DD
    - --db PATH  (PAPER_TRADING_SQLITE_PATH 環境変数の代替)

- AI / リサーチ関数（ライブラリとして呼び出す）
  - ニュースセンチメント付与:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key=...)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=...)

ログ / ファイル
- ログ: logs/<app_name>.log（デフォルト daily rotation で 30 日保持）。setup_logging() を各起動スクリプトで呼んでいます。
- 監視 DB (SQLite): data/monitoring.db（デフォルト）
- DuckDB: data/kabusys.duckdb（デフォルト）
- ペーパートレード DB: data/paper_trading.db（paper_trading 用、設定で上書き可能）
- Kill / Stop flags:
  - data/kill.flag : ExecutionEngine に停止命令を送る Kill Switch（KillSwitch クラスで生成）
  - data/stop_requested.flag : run_monitoring / run_execution の外部停止トリガー（あるとループを終了）

注意点 / 運用ヒント
- KABUSYS_ENV を live にすると実際に発注が行われるため本番設定は慎重に。
- run_execution は起動時に kill flag を検知すると起動を中止します（安全設計）。
- ai/news_nlp と ai/regime_detector は OpenAI API に依存します。API キーとレート制御を適切に設定してください。
- DuckDB / SQLite のファイルパスは環境変数で上書きできます。バックアップや永続化に注意してください。
- psutil を使ってプロセス優先度や CPU affinity を変更します。権限や OS により設定できない場合があります（警告ログが出ます）。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                  — 環境変数/設定ラッパー（Settings）
    - config_setup.py            — .env 対話式ウィザード
    - validate_config.py         — 設定検証 CLI
    - run_execution.py           — ExecutionEngine 起動スクリプト
    - run_monitoring.py          — Monitoring 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - __init__.py
      - logging_setup.py         — ログ設定ユーティリティ
      - process_priority.py      — 優先度 / CPU affinity ユーティリティ
    - portfolio/
      - __init__.py
      - portfolio_builder.py     — 候補選定・重み計算
      - risk_adjustment.py       — セクターキャップ・レジーム乗数
      - position_sizing.py       — 株数決定・aggregate cap
    - research/
      - __init__.py
      - factor_research.py       — momentum/value/volatility ファクター計算
      - feature_exploration.py   — forward returns, IC, summary
    - ai/
      - __init__.py
      - news_nlp.py              — ニュース NLP（OpenAI）
      - regime_detector.py       — 市場レジーム判定（OpenAI + ETF）
    - monitoring/
      - monitoring_db.py         — SQLite テーブル定義・MonitoringDB
      - system_monitor.py        — システム状態・データ鮮度監視
      - trade_monitor.py         — （trade モニタ; 実装参照）
      - risk_monitor.py          — ドローダウン/ポジション上限監視
      - kill_switch.py           — kill.flag 制御
      - monitoring_engine.py     — 各 Monitor を束ねるエンジン
    - portfolio/                 — ポートフォリオ関連（上記）
    - research/                  — リサーチ関連（上記）
    - ...（execution, data, strategy 等のパッケージが想定される）

ライセンス / 貢献
-----------------
（ここにライセンス情報やコントリビュート手順を追加してください。リポジトリに LICENSE ファイルがあればその内容に従ってください。）

最後に
-------
この README はコードベースに基づく導入ガイドです。実戦運用を行う場合は設定ファイル（config/*.yaml）や .env の内容、Kill Switch / ログ保管・監視体制を十分に検討してください。質問や追加のドキュメントが必要であれば教えてください。