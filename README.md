README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤（小規模プロダクション向け）を想定した Python パッケージです。本リポジトリ内には以下の主要機能を持つコンポーネントが含まれます。

- 実行エンジン（ExecutionEngine）: 発注・リスク管理・注文管理の起動スクリプト
- 監視（Monitoring）: システム状態・注文データ・リスク監視のポーリングループ
- ポートフォリオ構築ユーティリティ: 候補選定、重み計算、ポジションサイズ算出
- リサーチ / ファクター計算: DuckDB 上の時系列データを使ったファクター計算、IC 計測など
- AI モジュール: ニュースを LLM（OpenAI）でスコアリングする処理、レジーム判定
- ユーティリティ: ログ設定、プロセス優先度、設定ウィザード、設定検証ツール
- 運用ツール: ペーパートレード検証レポート生成スクリプト 等

特徴
----
- モジュール化された純粋関数群（ポートフォリオ関連、リサーチ）によりテストしやすい
- 起動スクリプトから共通の logging 設定・プロセス優先度設定を利用
- Paper Trading（KABUSYS_ENV=paper_trading）では本番 DB と分離して専用 SQLite を利用
- OpenAI を用いたニュース NLP・マクロセンチメントで市場レジーム判定を行う機能を搭載
- 監視データは SQLite（monitoring DB）に永続化し、kill.flag による実行停止等の運用機能あり

必要条件（概略）
----------------
（環境はプロジェクトに合わせて調整してください）
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- （任意）PyYAML（config/*.yaml の検証を enable にしたい場合）

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリに移動
   - この README がパッケージルート（pyproject.toml / .git がある場所）を前提とします。

2. 仮想環境作成・依存パッケージをインストール
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -r requirements.txt
   - requirements.txt がない場合は少なくとも duckdb, psutil, openai（必要な場合）をインストールしてください。

3. 環境変数設定
   - .env をプロジェクトルートに置くか環境変数を直接設定します。
   - 対話式ウィザードで .env を作る:
     - python -m kabusys.config_setup
   - 生成後、設定検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります

主な環境変数（よく使うもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB (monitoring)（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

使い方（実行例）
----------------

1) 監視ループを起動
- 監視プロセスは監視用 SQLite に書き込みを行い、data/stop_requested.flag により停止できます。
- 起動:
  - python -m kabusys.run_monitoring
- オプション:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（例: export MONITOR_POLL_INTERVAL=120）。
- 補足:
  - 監視は Settings にかかわらず本番 sqlite_path を使用する実装になっています（運用上の注意）。

2) 実行エンジンを起動（注文発行等）
- KABUSYS_ENV によって実行挙動が変わります（paper_trading では MockBrokerClient を使い paper DB を使用）。
- 起動:
  - python -m kabusys.run_execution
- 補足:
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 実行中に stop flag を置くことで安全に停止できます。
  - 実行時は data/execution.pid に PID ファイルを書きます。

3) .env 作成・更新ウィザード
- python -m kabusys.config_setup

4) 設定検証
- python -m kabusys.validate_config
- --strict を付けると警告も失敗扱い（exit 1）

5) Paper Trading 検証レポート（運用・レポート用）
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - --db オプションで PAPER_TRADING_SQLITE_PATH を上書き可能

6) AI 関連（ライブラリ関数として利用）
- ニュース NLP スコア付与:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- これらは DuckDB 接続（DuckDBPyConnection）を受け取り、データベースのテーブルを参照／更新します。API キーは引数または環境変数 OPENAI_API_KEY を使用。

運用に関する注意点
----------------
- Paper Trading と本番 DB は分離されています。KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite が使用されます（PAPER_TRADING_SQLITE_PATH）。
- kill.flag / stop_requested.flag:
  - KillSwitch（kill.flag）: リスク事象発生時に ExecutionEngine を停止するために書き込まれます（Settings.kill_flag_path で指定可能）。
  - stop_requested.flag: run_monitoring/run_execution がプロジェクト内 data ディレクトリ下の stop_requested.flag を監視し、存在時は処理を終えます。
- ログ:
  - デフォルトで stdout に出力され、logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリは LOG_DIR 環境変数またはデフォルト "logs/"。
- OpenAI（LLM）を利用する機能は API 利用料が発生します。API キーは厳重に管理してください。

ディレクトリ構成（主要ファイル）
-----------------------------
（src/kabusys 以下。抜粋）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数・Settings 管理（.env 自動ロード機能あり）
  - config_setup.py           — .env の対話式ウィザード
  - validate_config.py        — 起動前の設定検証 CLI
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト（paper_trading 分離）
  - monitoring/
    - monitoring_db.py        — SQLite ベースの監視 DB 永続化層
    - system_monitor.py       — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py        — （注文系監視）※ファイルの一部（省略）
    - risk_monitor.py         — ドローダウン・ポジション数監視
    - kill_switch.py          — kill.flag 書き込みロジック
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — （アラート送信管理）※ファイル参照
  - execution/                 — ExecutionEngine 関連（broker_factory, order_manager など）
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 発注株数算出ロジック
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — momentum/value/volatility 等のファクター計算
    - feature_exploration.py  — 将来リターン計算、IC、統計サマリ
  - ai/
    - news_nlp.py             — ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py      — ETF MA とマクロセンチメントによるレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成ツール
  - utils/
    - logging_setup.py        — 共通ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ

補足（設計メモ）
----------------
- 多くの関数は DuckDB / SQLite 接続を呼び出し側から受け取る設計で、外部依存を最小化してテストしやすくしています。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- AI（OpenAI）関連の API 呼び出しはリトライやレスポンス検証を行い、部分失敗時にも既存データを毀損しないよう配慮されています。

よくある操作まとめ
------------------
- .env を作る: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 監視起動: python -m kabusys.run_monitoring
- 実行エンジン起動: python -m kabusys.run_execution
- Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

ライセンス / コントリビュート
----------------------------
本 README 内ではライセンスや貢献フローについては指定していません。必要に応じてプロジェクトルートに LICENSE と CONTRIBUTING.md を追加してください。

問い合わせ
----------
不明点や追加ドキュメントの要求があれば教えてください。README に追記・改善します。