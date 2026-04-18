README
=====

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤のコードベースです。本リポジトリには以下の主要機能が含まれます。

- 実行エンジン（ExecutionEngine）の起動スクリプト
- システム監視（モニタリング）ループ
- 監視ログを永続化する SQLite 層
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 研究用ファクター計算・特徴量探索
- ニュース NLP / 市場レジーム判定（OpenAI を利用したスコアリング）
- 設定ウィザード・検証ツール・運用ユーティリティ
- ペーパートレード検証レポート生成ツール

特徴（抜粋）
-------------
- モジュール化された設計：monitoring / ai / portfolio / research / utils などに分割
- 環境変数 / .env による設定管理（config_setup による対話的作成 + validate_config による検証）
- 実運用を想定した監視・アラート・Kill Switch（データベース・フラグファイルを利用）
- Paper trading（完全に分離された SQLite）をサポート
- OpenAI を用いたニュースセンチメント（news_nlp）とレジーム検出（regime_detector）
- DuckDB を用いた分析処理（research パッケージ）

セットアップ
-----------

前提
- Python 3.10 以上（typing の | 演算子等を使用）
- pip が使用可能

1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（代表例）
   - pip install duckdb psutil openai
   - 解析用に PyYAML を使う場合: pip install PyYAML
   - 実際には requirements.txt があればそれを使用してください（この README には含まれていません）

3. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または .env.example を参考に手動作成
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を利用する場合:
     - OPENAI_API_KEY を設定

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告を FAIL にする厳格モード: python -m kabusys.validate_config --strict

主な環境変数（抜粋）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading の場合、Execution は MockBrokerClient を使用し data/paper_trading.db に記録
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- LOG_LEVEL, LOG_DIR
- OPENAI_API_KEY: OpenAI を使う機能で必要
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB パス（任意）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒。デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（0/1）

使い方
------

共通: ログ設定
- 全起動スクリプトは kabusys.utils.logging_setup.setup_logging を使用して統一的にログを出力します。
- ログファイル: logs/<app_name>.log（デフォルト、日次ローテーション）

1) 監視ループ（Monitoring）
- 目的: システム状態・データ鮮度・注文状況・リスク項目を定期チェックして DB に記録・アラートを出す
- 実行:
  - python -m kabusys.run_monitoring
- 挙動:
  - Settings に従い sqlite, duckdb に接続（monitoring は環境に関わらず本番 sqlite_path を使用）
  - プロセス優先度を high に設定
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 停止方法: プロジェクトルート/data/stop_requested.flag を作成するとループが終了

2) 実行エンジン（Execution）
- 目的: 発注エンジン（ExecutionEngine）を起動して取引ロジックを実行
- 実行:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading 用 DB に記録
  - プロセス優先度を high に設定
  - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了
  - 停止方法:
    - data/stop_requested.flag を作るとエンジンを安全に停止する
    - kill.flag（Settings.kill_flag_path / デフォルト data/kill.flag）を書き込むと KillSwitch によりエンジンを停止させる（監視コンポーネント経由で評価して書き込む）

3) 設定ウィザード / 検証
- 対話的 .env 生成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いして exit 1 にする

4) Paper Trading 検証レポート
- ツール: kabusys.tools.paper_verification_report
- 使い方:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）
- 出力: 稼働率 / 注文成功率 / レイテンシなどの集計と PASS/FAIL 判定

5) AI 関連
- news_nlp.score_news / ai.regime_detector.score_regime は OpenAI API を使います。OPENAI_API_KEY が必要です。
- 動作概要:
  - news_nlp: raw_news を集約して LLM に投げ、銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector: ETF 1321 の ma200 とマクロニュースの LLM 評価を組合せて market_regime を更新
- 取り扱い上の注意:
  - API 呼び出しはリトライやフォールバック（失敗時は安全にゼロ等で継続）を含みます
  - モデル: gpt-4o-mini を想定（設定はコード内定数）

運用・停止
-----------
- stop_requested.flag: 実行中ループ（monitoring / execution）はプロジェクトルート/data/stop_requested.flag の存在を定期チェックし、存在する場合は終了します。運用上のシャットダウンにはこのフラグを使います。
- kill.flag: KillSwitch（リスクトリガー）が書き込むファイル。ExecutionEngine に対する停止指示として使用されます（Settings.kill_flag_path で指定可能）。
- PID ファイル: ExecutionEngine は data/execution.pid に PID を書きます（Settings.pid_file_path）。

ディレクトリ構成（要約）
---------------------
プロジェクトルート（例）
- pyproject.toml / .git/ ...
- .env (.env.local)
- data/                      — DB / flag / pid 等のランタイムファイル
  - monitoring.db
  - paper_trading.db
  - stop_requested.flag
  - kill.flag
  - execution.pid
- logs/                      — ログファイル出力先（デフォルト）
- src/
  - kabusys/
    - __init__.py
    - config.py              — 環境変数 / Settings
    - config_setup.py        — .env 対話ウィザード
    - validate_config.py     — 起動前検証 CLI
    - run_monitoring.py      — 監視ループ起動スクリプト
    - run_execution.py       — 実行エンジン起動スクリプト
    - utils/
      - logging_setup.py     — ログ設定ユーティリティ
      - process_priority.py  — プロセス優先度・CPU affinity
    - monitoring/
      - monitoring_db.py     — SQLite テーブル定義 / 永続化 API
      - system_monitor.py    — システム状態監視
      - trade_monitor.py     — （注文監視ロジック）
      - risk_monitor.py      — ドローダウン / ポジション上限監視
      - kill_switch.py       — kill.flag の作成・評価
      - monitoring_engine.py — 監視コンポーネント束ね
      - alert_manager.py     — （通知管理）
    - execution/             — ExecutionEngine や注文管理に関連するモジュール群
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - risk_manager.py
      - reconciler.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - data/                  — データパイプライン / DuckDB 操作用（prices_daily, raw_financials 等）
    - tools/
      - paper_verification_report.py

（注）実際のファイル一覧はリポジトリの内容に依存します。上は主要コンポーネントの抜粋です。

注意事項 / 運用ヒント
--------------------
- KABUSYS_ENV により実行挙動が変わります。paper_trading は発注を模擬し本番 DB とは分離されます。live は本番挙動になりますので設定やキーの取扱に注意してください。
- .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注意書きがあります）。
- OpenAI キーや API を使う機能はコストとレイテンシが発生します。運用時はレート制限やコスト管理を行ってください。
- DuckDB / SQLite のパス（DUCKDB_PATH / SQLITE_PATH）は必要に応じて変更してください。validate_config で親ディレクトリの存在等をチェックします。
- ログ出力先のディレクトリ作成に失敗した場合はコンソール出力のみになります。必要な権限を確認してください。

開発者向け補足
--------------
- 型ヒントや純粋関数で構成されたモジュール（portfolio や research）はユニットテストが書きやすい設計です。
- OpenAI 呼び出しのラッパー関数はテストでモック化しやすい作りになっています（_call_openai_api を patch する等）。
- MonitoringDB はスキーマ変更時に簡易マイグレーションロジックを含んでいます（列追加の guard 等）。

ライセンス / バージョン
------------------------
- パッケージのバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。
- ライセンス情報・貢献ルール等はリポジトリのトップレベルに置いてください（本 README には含めていません）。

以上が本コードベースの概要・セットアップ・運用に関する README です。特定の機能（例: ExecutionEngine の詳細な起動オプション、AlertManager の設定、DuckDB のテーブル定義等）について詳しいドキュメントが必要であれば、どの項目を詳細化すべきか教えてください。