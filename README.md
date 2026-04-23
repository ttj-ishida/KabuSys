KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買・研究・監視フレームワークです。  
主な目的は以下のとおりです。

- シグナル生成 → ポートフォリオ構築 → 注文発行（ExecutionEngine）
- 実行状況・システム状態の常時監視（Monitoring）
- DuckDB を用いたファクター計算・リサーチ機能
- ニュースの LLM（OpenAI）によるセンチメント判定や市場レジーム推定
- Paper Trading（模擬発注）を本番 DB から分離して検証可能
- 簡易 CLI（環境セットアップ、設定検証、レポート生成）

特徴
----
- 柔軟な実行環境: KABUSYS_ENV による `development` / `paper_trading` / `live` 切替
- Paper Trading は本番 DB と分離（デフォルト data/paper_trading.db）
- DuckDB を使った高速なファクター計算・集計
- OpenAI を用いたニュース NLP（score_news）およびレジーム検出（regime_detector）
- 監視系: system_monitor / trade_monitor / risk_monitor / kill_switch / alert_manager（ログ & kill.flag による制御）
- ログは stdout と日次ローテートファイル（logs/*.log）に出力

必要要件
-------
- Python 3.10+
- SQLite（標準ライブラリ）
- 推奨 Python パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - pyyaml（設定検証で YAML の中身チェックを行いたい場合）
- optional: その他 execution 側で使う HTTP クライアント等（環境により変動）

セットアップ手順
---------------
1. リポジトリをクローンして仮想環境を用意
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （requirements.txt / pyproject があればそれに従ってください）

3. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - 必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - 実行環境: KABUSYS_ENV を適切に設定（development / paper_trading / live）
   - ウィザード終了後、python -m kabusys.validate_config で検証
     - --strict を付けると警告も失敗扱いになります

4. データディレクトリの準備
   - デフォルト DB / ログパスは data/, logs/
   - 必要に応じて .env で DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を上書き

5. OpenAI を使う機能を利用する場合
   - 環境変数 OPENAI_API_KEY を設定（または関連する関数へ明示的に渡す）

使い方
------

共通
- ログ設定は kabusys.utils.logging_setup.setup_logging を使って統一されています。ログファイルは既定で logs/<app_name>.log。

設定検証・ウィザード
- 対話式 .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

ExecutionEngine（発注エンジン）
- 実行:
  - python -m kabusys.run_execution
- 動作:
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、Paper Trading 用 DB（デフォルト data/paper_trading.db）に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動しません。
  - 停止は data/stop_requested.flag / kill.flag による外部制御で可能。

Monitoring（監視プロセス）
- 実行:
  - python -m kabusys.run_monitoring
- 動作:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）
  - 監視は本番の sqlite_path（デフォルト data/monitoring.db）を使用（環境にかかわらず本番 DB を参照する設計）
  - system_monitor / trade_monitor / risk_monitor を組み合わせ、必要に応じて kill.flag を書き込んで Execution を停止させます。

Paper Trading レポート
- Paper Trading の検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB path 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

AI（ニュース NLP / レジーム判定）
- ニューススコアリング（ai.news_nlp.score_news）:
  - DuckDB 接続と target_date を渡して利用
  - OpenAI API キーは環境変数 OPENAI_API_KEY または関数引数で指定
- レジーム判定（ai.regime_detector.score_regime）:
  - DuckDB 接続と target_date を渡して利用
  - 同様に OpenAI API キーが必要

Kill Switch / フラグ
- 実行系の安全停止は data/kill.flag（KillSwitch）や data/stop_requested.flag により実現
- kill.flag を手動でクリアする場合:
  - rm data/kill.flag などで削除
- Settings により起動時に kill_flag を自動クリアする挙動を制御できます（KILL_FLAG_CLEAR_ON_START）

主要環境変数（主なもの）
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）

ディレクトリ構成（主要ファイル）
--------------------------------
以下はソースツリー（src/kabusys）内の主要ファイル / ディレクトリ構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理（自動 .env ロード等）
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 起動前設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - utils/
    - __init__.py
    - logging_setup.py            — ログ設定ユーティリティ
    - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py            — 監視用 SQLite の永続化層
    - system_monitor.py           — システム & データ鮮度監視
    - trade_monitor.py            —（取引状態監視: 未掲示のコードだが存在）
    - risk_monitor.py             — ドローダウン・ポジション上限監視
    - kill_switch.py              — kill.flag の制御
    - monitoring_engine.py        — 各 monitor をまとめるエンジン
    - alert_manager.py            —（アラート送信機構: 未掲示のコードだが想定）
  - execution/
    - broker_factory.py           — ブローカークライアント生成
    - execution_engine.py         — ExecutionEngine 実装（発注ループ）
    - order_*                     — 注文管理 / リポジトリ / 再整合ロジック等
    - risk_manager.py             — 発注時のリスク管理
  - portfolio/
    - portfolio_builder.py        — 候補選定・重み計算
    - position_sizing.py          — 発注株数決定・キャップ処理
    - risk_adjustment.py          — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py          — Momentum / Value / Volatility 等の計算（DuckDB）
    - feature_exploration.py      — 将来リターン計算・IC 等
  - ai/
    - news_nlp.py                 — ニュース NLP（OpenAI）による銘柄スコアリング
    - regime_detector.py          — マクロ + ETF MA によるレジーム判定

開発のヒント / 注意点
--------------------
- Python バージョン: 3.10 以上（型アノテーションの | を利用）
- .env は機密情報を含むため Git にコミットしないでください
- 本番（KABUSYS_ENV=live）では kill_flag_clear_on_start は 0 を推奨
- OpenAI を利用する機能は API コスト・レイテンシに注意して運用してください
- DuckDB / SQLite のファイルパスは .env で指定可能。運用時はバックアップ戦略を検討してください

お問い合わせ / 追加
------------------
この README はコードベースの主要機能と利用方法の概要です。  
追加で必要なドキュメント（API 詳細、ExecutionEngine の設定項目、Alert の送信先設定など）を希望される場合は、どのトピックを詳細化したいか指示してください。