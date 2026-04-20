KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム（KabuSys）のプロトタイプ実装です。  
モジュール群は「実行（Execution）」「監視（Monitoring）」「ポートフォリオ構築／サイズ計算」「リサーチ」「AI（ニュース NLP / レジーム判定）」「ユーティリティ／ツール」を含みます。

主な特徴
--------
- ExecutionEngine：ブローカークライアントを用いた発注エンジン（paper_trading モードでのモック実行をサポート）
- Monitoring：システム健全性・注文状態・リスク（ドローダウン／ポジション上限など）を定期監視
- Kill Switch：監視で危険シグナル検出時に停止フラグを書き込んで安全にエンジンを停止
- Portfolio モジュール：候補選定・重み計算・株数決定（単元丸め・リスク制限）
- Research（DuckDB ベース）：ファクター計算（Momentum/Volatility/Value）、Forward Return / IC 計算など
- AI モジュール：ニュースを LLM（OpenAI）でスコアリングし ai_scores に保存、マクロニュースを用いた市場レジーム判定
- ツール：Paper Trading 検証レポート作成スクリプト、対話式 .env セットアップ、設定検証 CLI
- ロギング、プロセス優先度設定、DB 初期化（SQLite / DuckDB）などのユーティリティ

セットアップ手順
----------------
前提
- Python 3.10 以上（typing の union 演算子（|）を使用）
- システムに sqlite3 は標準で同梱されています。追加で以下の外部パッケージが必要です（最小限）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の内容検証をしたい場合）
- ネットワーク接続（OpenAI や kabuAPI を使用する場合）

一般的な手順
1. リポジトリをクローンしワークディレクトリに移動
   - git clone ... && cd <repo>
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （必要に応じてその他パッケージを追加）
4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参照）
   - 自動ロード: .env / .env.local は config モジュールで自動的にロードされます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合: python -m kabusys.validate_config --strict
6. DB 初期化は起動スクリプト内で行われます（monitoring 用のテーブルは init_monitoring_db により冪等作成されます）

主要な環境変数（抜粋）
----------------------
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（paper_trading 環境で使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

使い方（主要スクリプト）
------------------------
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と完全分離）
  - 起動時に data/stop_requested.flag が存在すると起動しない
  - プロセス優先度を "high" に設定してから起動します

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）
  - 監視は production sqlite_path を使います（KABUSYS_ENV にかかわらず本番 sqlite_path を参照）
  - 停止フラグ stop_requested.flag によりループ終了

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict で警告をエラー扱い

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で変更可）

ライブラリ利用例（コードから呼び出す）
- Research（例）:
  - from kabusys.research import calc_momentum, calc_volatility
  - conn = duckdb.connect("data/kabusys.duckdb"); calc_momentum(conn, date(2026,4,1))
- AI ニューススコアリング:
  - from kabusys.ai.news_nlp import score_news
  - duckdb_conn = duckdb.connect("data/kabusys.duckdb"); score_news(duckdb_conn, target_date, api_key="...")

ファイル・ディレクトリ構成
------------------------
（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      — .env 自動ロード / Settings クラス
    - config_setup.py                — .env 対話式ウィザード
    - validate_config.py             — 起動前設定検証 CLI
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - run_monitoring.py              — Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート生成
    - execution/                      — 発注エンジン関連（BrokerClientFactory / ExecutionEngine 等）
    - monitoring/
      - monitoring_db.py             — SQLite 永続化層（監視テーブル）
      - system_monitor.py            — システム監視（CPU/メモリ/データ鮮度 / PID 監視）
      - trade_monitor.py             — 注文状態監視（滞留注文、約定異常等）
      - risk_monitor.py              — ドローダウン・ポジション上限監視
      - kill_switch.py               — kill.flag 管理
      - monitoring_engine.py         — 各 Monitor の束ね
      - alert_manager.py             — 外部通知（LINE 等）管理（注: 実装ファイル参照）
    - portfolio/
      - portfolio_builder.py         — 候補選定・重み計算
      - position_sizing.py           — 株数算出・スケーリング・単元丸め
      - risk_adjustment.py           — セクター上限・レジーム乗数
    - research/
      - factor_research.py           — Momentum / Volatility / Value 等の計算
      - feature_exploration.py       — forward returns / IC / 統計要約
    - ai/
      - news_nlp.py                  — ニュース NLU / OpenAI 呼び出し・スコア保存
      - regime_detector.py           — マクロ + ma200 を合成したレジーム判定
    - utils/
      - logging_setup.py             — 統一ログ設定（stdout + ローテートファイル）
      - process_priority.py          — プラットフォーム差分を吸収したプロセス優先度設定
    - monitoring/monitoring_db.py    — 監視用テーブル定義と MonitoringDB クラス

ログ・データ
------------
- デフォルトログディレクトリ: logs/
  - スクリプトごとに logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
- デフォルトDBパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db

運用上の注意
------------
- KABUSYS_ENV=live の場合は本番発注が行われます。必須環境変数や LINE 通知設定などを十分に確認してください。
- Kill Switch（data/kill.flag）や stop_requested.flag を用いることで、外部から安全にエンジン停止指示を出せます。
- .env は決して Git にコミットしないでください（config_setup でもその旨の注意書きあり）。
- OpenAI を利用する機能は API レート制限やコストが発生します。API キー管理と呼び出し頻度に注意してください。
- DuckDB へ大量データを格納している場合は I/O と容量管理に注意してください。

トラブルシューティング
----------------------
- .env の自動ロードを無効化したいとき:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定
- PyYAML がないと config/*.yaml のパース検証はスキップされます（validate_config.py が警告を出します）。YAML 検証を使いたい場合は PyYAML をインストールしてください。
- ログディレクトリ作成に失敗するとファイル出力は無効化され stdout のみになります（警告が出ます）。

開発者向けメモ
-------------
- 多くの関数は副作用を避ける純粋関数として実装されています（portfolio、research 系など）。
- モジュールの公開 API は各パッケージ __init__.py で制御されています（例: kabusys.research、kabusys.ai、kabusys.portfolio）。
- テストを書く際は config の自動読み込みや外部 API 呼び出しをモックしてください（news_nlp / regime_detector は API 呼び出し部分を差し替えられる設計）。

ライセンス・貢献
----------------
リポジトリのルートに LICENSE および CONTRIBUTING ドキュメントがあれば参照してください（この README には含まれていません）。

以上がこのコードベースの概要と主な使い方です。必要であれば、README に追加したい細かいコマンド例（systemd / cron / Dockerfile 用の起動例など）や環境変数の完全一覧を作成します。どの情報を詳しく載せますか？