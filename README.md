KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした軽量なシステム群です。  
主な機能は取引エンジン（ExecutionEngine）、監視（Monitoring）、ファクター計算／リサーチ、ポートフォリオ構築、AI（ニュースセンチメント・レジーム判定）などです。  
設計方針としては、環境変数/.env による設定管理、DuckDB / SQLite を用いたデータ格納、外部 API 呼び出し（kabuステーション / J-Quants / OpenAI 等）は明示的に制御されフェイルセーフを重視しています。

主な特徴
--------
- ExecutionEngine（run_execution.py）
  - 本番 / ペーパートレードを環境で切替可能（KABUSYS_ENV）
  - Broker クライアントの抽象化（実ブローカー or モック）
  - リスク管理（RiskManager）・注文管理（OrderManager）・再整合（Reconciler）を組み合わせた実行
- Monitoring（run_monitoring.py / monitoring モジュール群）
  - CPU / メモリ / ディスク・プロセス存在チェック、データ鮮度チェック
  - リスク（ドローダウン / ポジション上限）監視、Kill Switch（kill.flag）発動
  - 監視ログは SQLite（data/monitoring.db）に永続化
- Portfolio モジュール
  - 候補選定、重み付け（等金額／スコア加重）、ポジションサイズ決定、セクターキャップ・レジーム乗数
  - 単体での純粋関数群（DBアクセスなし）でテスト容易
- Research（DuckDB ベース）
  - Momentum / Volatility / Value 等ファクター計算
  - 将来リターン・IC 計算・統計サマリー
- AI モジュール（OpenAI）
  - ニュースのセンチメントスコアリング（news_nlp）
  - マクロ + 指数（1321）ベースの市場レジーム判定（regime_detector）
  - OpenAI 呼び出しはリトライ・バッファ等を実装
- ツール
  - 環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
- ユーティリティ
  - 統一的ログ設定（logs 日次ローテーション）
  - プロセス優先度 / CPU affinity 設定

前提・依存
-----------
- Python 3.10+
- 主な外部ライブラリ（必要に応じてインストール）
  - duckdb
  - psutil
  - openai (AI 機能使用時)
  - PyYAML（config YAML 検証を行う場合）
- 環境変数 / .env による設定（自動ロード機能あり）
  - プロジェクトルートに .env / .env.local があると自動ロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

重要な環境変数（主なもの）
--------------------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 選択 / デフォルト
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID：アラート通知（任意）
  - OPENAI_API_KEY：AI 機能で使用
  - MONITOR_POLL_INTERVAL：監視ポーリング間隔（秒、default: 60）
  - KILL_FLAG_CLEAR_ON_START：起動時に kill.flag を自動クリアする（0/1、production では 0 推奨）

セットアップ手順
--------------
1. リポジトリをクローン / ダウンロード
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージのインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
4. 環境変数設定
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - あるいは .env ファイルを手動で用意（.env.example を参考に）
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱います
6. データディレクトリ作成（必要なら）
   - logs/ や data/ は自動作成されますが、権限等に注意してください

使い方（主要コマンド）
--------------------
- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
  - 停止は data/stop_requested.flag を作成することで行えます（存在検知で安全停止）
  - PID ファイル: data/execution.pid（Settings.pid_file_path で上書き可能）
- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は常に Settings.sqlite_path（本番 monitoring DB）を使用します（env に関わらず）
  - 停止は data/stop_requested.flag を作成
- 環境設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB パスを指定可
- AI / レジーム判定 / ニューススコア
  - OpenAI API キー（OPENAI_API_KEY）が必要
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をプログラムから呼び出して使用

停止・Kill スイッチの運用
------------------------
- 強制停止指示（Kill Switch）
  - kabusys.monitoring.kill_switch が条件を満たすと data/kill.flag を書き込みます。ExecutionEngine はこのフラグを検出して停止できます。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると自動でクリアされます（本番では 0 を推奨）。
- 手動停止
  - data/stop_requested.flag を作成すると run_execution.py / run_monitoring.py が検知して安全に終了します。

ログ
---
- setup_logging により標準出力（stdout）とファイル出力（logs/<app_name>.log、日次ローテーション）が設定されます。
- デフォルトログディレクトリ: logs/
- LOG_LEVEL 環境変数で制御（例: LOG_LEVEL=DEBUG）

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env ロードと Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - (trade_monitor.py 等の監視関連)
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/                — Execution 実装（BrokerFactory, Engine, OrderManager 等）
  - data/                     — （実行時生成）data/*.db, pid/flag ファイルなど
- config/                     — system_config.yaml 等の YAML（テンプレート/生成スクリプトで使用）
- logs/                       — ログ出力先（デフォルト）

開発上の注意
-------------
- DuckDB / SQLite のパスは Settings で制御。paper_trading 環境は本番 DB から分離する設計（paper_trading 用 DB を利用）。
- AI 機能は API 呼び出しを行うためコスト・レート制限に注意。OpenAI キーが未設定の場合は明示的に例外を投げる箇所があるため安全に扱ってください。
- .env は機密情報を含むため絶対に Git へコミットしないでください（config_setup.py にも注意書きあり）。
- Python の型アノテーション / 新しい構文（|）を使用しているため Python 3.10+ を推奨します。

よくある操作例
--------------
- 開発用に最小構成で起動（開発モード・ローカルモック等を想定）
  1. python -m kabusys.config_setup
  2. python -m kabusys.validate_config
  3. KABUSYS_ENV=development python -m kabusys.run_monitoring
  4. KABUSYS_ENV=development python -m kabusys.run_execution
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サポート / 拡張ポイント
-----------------------
- Broker クライアントや Mock 実装の追加・差し替え
- ポートフォリオ構築アルゴリズム（スコアリング/最適化）
- モニタリング条件・アラート種別のカスタマイズ
- AI モデル / プロンプトの改良（news_nlp / regime_detector）

ライセンス・バージョン
---------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状: 0.1.0）。

問い合わせ・変更提案
--------------------
リポジトリ内の該当ファイル（config.py / run_*.py / monitoring / ai / portfolio / research 等）を参照し、不明点があればソースからの確認を推奨します。README に不足があれば追記しますので、必要な項目（例: 実行例のログ抜粋、詳細な環境変数一覧、CI/テスト手順）を教えてください。