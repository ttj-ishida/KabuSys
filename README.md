# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買・研究・監視を目的としたモジュール群です。  
本 README はコードベースから主要な機能・セットアップ手順・使い方・ディレクトリ構成を日本語でまとめたものです。

概要
- KabuSys は取引実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、調査（Research）、AI 補助（ニュースセンチメント / レジーム判定）などを含む自動売買プラットフォームのコアロジック群です。
- DuckDB を分析用のローカル DB として利用し、SQLite は監視ログやペーパートレードの記録に使用します。
- 実際の発注は kabuステーション API を利用（本番）し、ペーパートレード（KABUSYS_ENV=paper_trading）時は MockBrokerClient により本番 DB と分離された data/paper_trading.db に記録します。

主な機能一覧
- Execution
  - ExecutionEngine を起動して発注フローを実行（risk manager、order manager、reconciler 等を組み合わせて運用）
  - paper_trading モードで MockBrokerClient を使用し、本番 DB と完全分離
- Monitoring
  - システム状態（CPU / メモリ / ディスク）、Execution プロセス監視、滞留注文や約定異常チェック、リスク（ドローダウン・ポジション上限）監視
  - kill.flag による Execution の停止シグナル発行（Kill Switch）
  - 監視データは SQLite（data/monitoring.db がデフォルト）に永続化
- Portfolio
  - 候補選定、等配分 / スコア加重配分、セクター上限適用、ポジションサイズ計算（単元丸め、リスクベース等）
- Research
  - DuckDB 上の price/financials からファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（情報係数）計算、ファクター統計サマリー
- AI（OpenAI）
  - ニュース記事を LLM でセンチメント評価し ai_scores に書き込み（score_news）
  - マクロニュース + ETF ma200 を組み合わせた市場レジーム判定（score_regime）
- ユーティリティ
  - .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ログ設定、プロセス優先度 / CPU affinity 設定ユーティリティ

前提 / 必要な依存
- Python 3.9+
- 必須ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- インストール例（仮）:
  - pip install -r requirements.txt
  - requirements.txt が無い場合は上記パッケージを個別にインストール

環境変数（主要）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / 便利
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 SQLite、デフォルト: data/paper_trading.db）
  - LOG_LEVEL（デフォルト: INFO）
  - OPENAI_API_KEY（AI モジュール使用時）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番通知）
- 自動読み込み
  - プロジェクトルートの .env と .env.local は自動で読み込まれます（OS 環境変数より優先度は低い）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

セットアップ手順（推奨の初期手順）
1. リポジトリをクローンして仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate
2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
     （プロジェクトで requirements.txt があればそれを使用）
3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成
4. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合: python -m kabusys.validate_config --strict
5. ディレクトリ（data, logs）を作成（多くは起動時に自動作成されますが手動でも可）
   - mkdir -p data logs

使い方（代表的な起動・実行コマンド）
- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 動作について:
    - KABUSYS_ENV=paper_trading の場合、BrokerClientFactory が MockBrokerClient を返し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
    - 起動前に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中は data/execution.pid に PID を書き込みます（Engine 起動時）。
    - 停止は data/stop_requested.flag の作成でトリガー可能（Monitoring の KillSwitch 等から書き込む）。
- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 説明:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず production の sqlite_path を使用して監視ログを書きます（つまり監視 DB は本番 DB と共通）。
    - 監視中、data/stop_requested.flag を検知するとループを抜けて終了します。
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- AI 系の処理（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定した上で、モジュール関数を呼ぶ（例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）
  - CLI ラッパーは用意されていないためコードから呼び出す想定

ログ
- ログはデフォルトで stdout に出力され、日次ローテーションで logs/<app_name>.log に保存されます（logs ディレクトリは環境変数 LOG_DIR で上書き可能）。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御可能。

停止フラグ / Kill Switch
- Execution の停止は data/stop_requested.flag（run_execution 内で参照）または KillSwitch による data/kill.flag 書き込みで制御されます。
- KillSwitch は RiskMonitor 等のアウトプットに応じて kill.flag を作成し、Execution 側がそれを検出して安全に停止します。

注意点 / 運用上のヒント
- production（KABUSYS_ENV=live）を使う場合は LINE 通知や kill フラグ等の設定を慎重に行ってください（validate_config にも本番時の警告チェックがあります）。
- openai を使う機能は API レート制限やエラーに備え、リトライ・フェイルセーフ処理が組み込まれていますが、API キーやコスト管理は運用側で行ってください。
- process priority / CPU affinity の設定は psutil に依存し、権限不足や OS によっては設定に失敗することがあります（警告でスキップされます）。

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py                  — 環境変数 / .env 読み込み・Settings クラス
    - config_setup.py            — .env 対話式ウィザード（python -m kabusys.config_setup）
    - validate_config.py         — 設定検証 CLI（python -m kabusys.validate_config）
    - run_execution.py           — ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
    - run_monitoring.py          — Monitoring ポーリング起動スクリプト（python -m kabusys.run_monitoring）
    - utils/
      - logging_setup.py         — 共通ログ設定ユーティリティ
      - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
    - execution/                  — Execution 関連（Engine, order_manager, broker_factory 等）
    - monitoring/
      - monitoring_db.py         — SQLite 操作用ラッパー（テーブル作成・読み書き）
      - system_monitor.py        — システム状態・データ鮮度監視
      - trade_monitor.py         — 注文 / 約定監視（コード内にあり）
      - risk_monitor.py          — ドローダウン・ポジション上限監視
      - kill_switch.py           — Kill Switch（flag 書き込み）
      - monitoring_engine.py     — 複数モニタをまとめてポーリング
      - alert_manager.py         —（通知管理：LINE等、実装あり）
    - portfolio/
      - portfolio_builder.py     — 候補選定・重み計算
      - position_sizing.py       — 株数・リスク制限計算
      - risk_adjustment.py       — セクター制限・レジーム乗数
    - research/
      - factor_research.py       — ファクター計算（momentum/vol/value 等）
      - feature_exploration.py   — 将来リターン、IC、統計サマリー
    - ai/
      - news_nlp.py              — ニュースセンチメント（OpenAI 呼び出し）
      - regime_detector.py       — レジーム判定（ma200 + マクロセンチメント）
    - monitoring/monitoring_db.py
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート生成
- data/                          — デフォルトの DB / フラグファイル格納先（起動時に作成される）
- logs/                          — ログファイル出力先（設定可能）

開発者向けメモ
- .env は絶対に Git にコミットしないでください（config_setup も警告を出します）。
- DuckDB 用のスキーマはコード内（research / ai 等）で想定されています。production データの初期投入は別スクリプトで行ってください。
- テスト実行時は自動 .env ロードを無効化することができます:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

追加情報・拡張
- 各モジュール内に詳細なドキュメント（docstring）が付与されています。実装の詳細や運用ルールは該当ファイルを参照してください（PortfolioConstruction.md や StrategyModel.md 等の外部ドキュメントを参照する設計になっています）。
- 運用時は logs/ のローテーションとディスク容量、OpenAI のコスト管理、kill.flag の取り扱い（誤発動対策）に注意してください。

問題報告・コントリビューション
- バグや改善案は issue を立ててください。PR はテスト・説明を添えてお願いします。

以上。必要であれば README に含めるコマンド例や .env のサンプル、各設定値の詳細な説明（すべての環境変数や YAML 設定ファイル項目）を追記します。どの情報を詳しく載せたいか教えてください。