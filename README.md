KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買／リサーチ基盤（KabuSys）の一部実装です。
本 README はコードベースの主要コンポーネント、導入手順、実行方法、ディレクトリ構成を日本語でまとめたものです。

要点
- Python 3.10+ を想定（型ヒントに | 形式を使用）
- 永続化: SQLite（監視用等）および DuckDB（バッチ集計／リサーチ用）
- 外部 API: kabuステーション、J-Quants、OpenAI（AI機能は任意）
- 設定は .env（および .env.local）で管理。対話式ウィザードと検証ツールあり

プロジェクト概要
----------------
KabuSys は以下のような責務を持つモジュール群から構成されています。

- 実行エンジン（ExecutionEngine 起動スクリプト）: 発注・オーダー管理・リスク管理を行う（run_execution.py）。
- 監視（Monitoring）: システム稼働・注文状況・リスクをポーリングしてログ／アラートを出す（run_monitoring.py と各 Monitor）。
- ポートフォリオ構築: 候補選定、重み付け、ポジションサイズ計算（kabusys.portfolio）。
- リサーチ: ファクター計算、特徴量探索、将来リターン等（kabusys.research）。
- AI ユーティリティ: ニュース NLP（OpenAI）でセンチメントを算出、レジーム判定（kabusys.ai）。
- ツール: ペーパートレード検証レポート生成スクリプト等（kabusys.tools）。
- 設定管理ユーティリティ: .env の生成ウィザード（config_setup）と検証ツール（validate_config）。

主な機能一覧
----------------
- 起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine を起動（KABUSYS_ENV による挙動切替あり）
  - python -m kabusys.run_monitoring : SystemMonitor のポーリングループ起動
- 環境設定
  - python -m kabusys.config_setup : 対話式 .env 作成／更新ウィザード
  - python -m kabusys.validate_config : 環境変数・config/*.yaml の検証（--strict オプションで警告も失敗扱い）
- モニタリング
  - system_monitor / trade_monitor / risk_monitor / monitoring_engine（ポーリング・アラート・Kill Switch）
  - SQLite に監視ログを永続化 (data/monitoring.db デフォルト)
- ポートフォリオ構築
  - 候補選定、等重配分・スコア加重、リスク制約（セクターキャップ、レジーム補正）、株数決定（単元丸め）
- リサーチ
  - momentum / volatility / value ファクター計算（DuckDB 上の prices_daily, raw_financials テーブル）
  - forward returns、IC（Information Coefficient）、統計サマリ
- AI（任意）
  - ニュースをまとめて OpenAI に投げ、銘柄毎のスコアを ai_scores テーブルに保存（kabusys.ai.news_nlp）
  - ETF とマクロ記事を組合せた市場レジーム判定（kabusys.ai.regime_detector）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

セットアップ手順
----------------
前提
- Python 3.10+
- SQLite（OS 標準で利用可）
- DuckDB（Python モジュールで利用）
- ネットワーク接続（kabuステーション/API/OpenAI を使う場合）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール（最小セット）
   - pip install duckdb psutil
   - AI 機能を使う場合: pip install openai
   - YAML 検証を使う場合: pip install pyyaml
   （requirements.txt がないため、必要に応じて上記パッケージを追加してください）

4. .env の作成
   - 対話式ウィザードを利用（推奨）:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考に .env を用意する
   - 主に必須の環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH, SQLITE_PATH（任意、デフォルトは data/kabusys.duckdb / data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード時の DB 分離）
     - LOG_LEVEL, LOG_DIR（ログ設定）

5. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります

使い方（起動／ユーティリティ）
----------------
- ExecutionEngine 起動（発注実行）
  - 通常（環境に応じて .env を設定）
  - python -m kabusys.run_execution
  - 動作: Settings.env に応じて paper_trading であれば MockBrokerClient を使用し、DB を分離します（PAPER_TRADING_SQLITE_PATH を使用）。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は Settings.sqlite_path（本番 sqlite）を参照してログを書きます（monitoring は常に本番 sqlite_path を使用する設計）

- 停止・Kill Switch
  - ExecutionEngine/Monitoring はフラグファイルでの停止に対応
    - data/stop_requested.flag : 各 run_*.py が参照する停止フラグ
    - data/kill.flag : KillSwitch が書き込む ExecutionEngine 停止フラグ
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで PAPER_TRADING_SQLITE_PATH をオーバーライド可能

- AI 機能（ニュース・レジーム）
  - OpenAI API キーが必要（OPENAI_API_KEY または関数引数）
  - モジュール関数を呼び出して利用:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

ログと監査
----------------
- ログは kabusys.utils.logging_setup.setup_logging により統一管理されます
  - デフォルト: logs/<app_name>.log（日時ローテート、30日保持）
  - 環境変数 LOG_DIR で出力先を変更可能
  - ログレベルは環境変数 LOG_LEVEL または引数で設定

注意点 / 実運用での考慮事項
----------------
- KABUSYS_ENV=live 設定時は本番 API へ実際に発注が行われるため、設定・トークン・Kill Switch の扱いを十分確認してください。
- Paper Trading は本番 DB と分離するよう設計（settings.paper_sqlite_path を使用）
- OpenAI 呼び出しはレート制限や時間超過を考慮したリトライ実装を行っていますが、APIキーと料金体系には注意してください。
- monitoring_db モジュール内で軽微なスキーママイグレーションを行うため、DB ファイルのバックアップを取ってください。

ディレクトリ構成（抜粋）
----------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / Settings 管理（.env 自動読み込み）
- config_setup.py                — .env 対話式ウィザード
- validate_config.py             — 起動前設定検証 CLI
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor ポーリング起動スクリプト

kabusys/utils/
- logging_setup.py               — ログ設定ユーティリティ
- process_priority.py            — プロセス優先度 / CPU affinity 設定ユーティリティ

kabusys/monitoring/
- monitoring_db.py               — SQLite 監視ログ永続化層
- system_monitor.py              — システム状態・データ鮮度監視
- trade_monitor.py               — 発注ログ監視（滞留・異常約定検出 等）
- risk_monitor.py                — ドローダウン・ポジション上限監視
- kill_switch.py                 — kill.flag 管理
- monitoring_engine.py           — 各 Monitor を束ねるエンジン
- alert_manager.py               — （アラート送信の抽象化：LINE 等を想定）

kabusys/execution/   (実装ファイルは本 README のコードブロックには含まれていませんが、発注系の主要クラスを含む想定)
- broker_factory.py
- execution_engine.py
- order_manager.py
- order_repository.py
- reconciler.py
- risk_manager.py

kabusys/portfolio/
- portfolio_builder.py           — 候補選定、等配分・スコア配分
- position_sizing.py             — 株数計算、aggregate cap、単元丸め
- risk_adjustment.py             — セクターキャップ、レジーム乗数

kabusys/research/
- factor_research.py             — momentum/volatility/value 等のファクター計算
- feature_exploration.py         — forward returns / IC / 統計サマリ

kabusys/ai/
- news_nlp.py                    — ニュース NLP スコアリング（OpenAI 経由）
- regime_detector.py             — マクロ + MA200 によるレジーム判定

kabusys/tools/
- paper_verification_report.py   — Paper Trading 検証レポート生成スクリプト

data/
- *.db                           — デフォルトで data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db 等を使用
- kill.flag / stop_requested.flag / execution.pid などのフラグ / pid ファイル

よく使うコマンド例
----------------
- .env を初期作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution

- Monitoring 起動（デフォルト 60 秒間隔）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

ライセンス・貢献
----------------
- 本 README はコードベース（サンプル）に基づいた説明です。リポジトリのライセンスは別途確認してください。
- 貢献やバグ報告は Issue / Pull Request をお願いします。

補足（実装上の注記）
----------------
- Settings は自動でプロジェクトルートの .env/.env.local をロードします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- monitoring_db.init_monitoring_db は必要なテーブルを冪等的に作成し、軽微なマイグレーション（カラム追加）を行います。
- process_priority.set_process_priority は Windows / POSIX を吸収して優先度設定を試みますが、権限不足時は警告を出してスキップします。
- AI 呼び出し部分は外部キー（OPENAI_API_KEY）およびネットワーク状況に依存します。ロギング・リトライの実装がありますが、費用とレート制限には注意してください。

何か追加で README に盛り込みたい項目（例：サンプル .env、より詳しい実行フロー図、依存パッケージの pinned list など）があれば教えてください。必要に応じて追記します。