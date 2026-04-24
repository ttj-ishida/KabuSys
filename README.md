README
=====

概要
---
KabuSys は日本株自動売買システムのライブラリ兼ランタイムツール群です。  
主な目的は以下の通りです。

- 日次のファクター計算・リサーチ（DuckDB を用いた分析）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- ExecutionEngine による発注（本番 / ペーパートレードモード対応）
- 監視（System / Trade / Risk の定期チェックと Kill Switch）
- AI を使ったニュース NLP（OpenAI を用いたセンチメント評価）
- ペーパートレードの検証レポート生成、設定ウィザードや設定検証ツール

主な特徴
--------
- 環境変数 / .env による設定管理（config_setup による対話式生成）
- DuckDB（分析用）と SQLite（監視 / 発注ログ）の併用
- 本番とペーパートレードの DB・ブローカ分離
- ログは stdout と日次ローテートファイル出力（logs/）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント / レジーム判定
- 監視コンポーネントは kill.flag により ExecutionEngine を安全に停止可能

セットアップ手順
----------------

1. リポジトリを取得
   - git clone ... またはパッケージ配布から展開

2. Python 環境の準備
   - 推奨: 仮想環境を作成してアクティベート
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 代表的な依存:
     - duckdb
     - psutil
     - openai
     - PyYAML （validate_config の YAML 検証に利用）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ 実際の requirements.txt がある場合はそれを使ってください。

4. ディレクトリ作成（初回）
   - data/ と logs/ を事前に作っておくと安全です（スクリプトでも自動作成あり）。
     - mkdir -p data logs

5. .env の作成
   - python -m kabusys.config_setup を実行すると対話式で .env を生成できます（プロジェクトルートに .env を置く）。
   - 重要: .env は機密情報を含むため Git にコミットしないでください。

6. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

主要な環境変数（代表）
---------------------
- JQUANTS_REFRESH_TOKEN : J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
- KABUSYS_ENV           : 実行環境（development | paper_trading | live）デフォルト: development
- LOG_LEVEL             : ログレベル（DEBUG/INFO/...）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH           : 監視 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY        : OpenAI API キー（ニュース NLP / レジーム判定で使用）
- PAPER_FILL_MODE       : ペーパートレード時の約定挙動（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL : 監視ループのポーリング間隔（秒、デフォルト 60）

使い方
------

設定ウィザード / 検証
- 対話式 .env 作成:
  - python -m kabusys.config_setup
- 設定を検証:
  - python -m kabusys.validate_config
  - 例: python -m kabusys.validate_config --strict

ExecutionEngine（発注）起動
- 実行コマンド:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）
  - 起動時に data/stop_requested.flag が存在すると起動しません
  - 実行中に stop flag を置くとエンジンを停止します
  - PID ファイル: data/execution.pid（設定で変更可能）

Monitoring（監視）起動
- 実行コマンド:
  - python -m kabusys.run_monitoring
- 挙動:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き（秒、デフォルト 60）
  - 監視は設定された sqlite_path（monitoring.db）を使用（KABUSYS_ENV に依存しない）
  - data/stop_requested.flag を検知すると終了
  - 監視は SystemMonitor / TradeMonitor / RiskMonitor を呼び出し、必要に応じて Kill Switch（data/kill.flag）を書きます

Paper Trading 検証レポート
- コマンド:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可）
- 出力: 標準出力にレポート（稼働率、成功率、レイテンシなど）を表示

AI 関連
- ニュースセンチメント（ai.news_nlp.score_news）:
  - DuckDB 接続と target_date, OpenAI API キーを渡して実行
  - 例（スクリプトから）:
    - from openai import OpenAI ではなく、score_news を呼び出す形で利用
  - 注意: OPENAI_API_KEY が必要
- 市場レジーム判定（ai.regime_detector.score_regime）:
  - DuckDB 接続と target_date, OpenAI API キーを渡して実行

ライブラリとしての利用例
- portfolio モジュール:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
- research モジュール:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

ログ
---
- デフォルトで stdout に出力され、logs/<app_name>.log に日次ローテートで出力されます（logs/ ディレクトリ）。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御可能。

ディレクトリ構成（主要ファイル）
-------------------------------
プロジェクトルート（省略）/src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定管理
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring ループ起動スクリプト

サブパッケージ（主要）
- ai/
  - news_nlp.py            — ニュース NLP（OpenAI）スコアリング
  - regime_detector.py     — 市場レジーム判定
- monitoring/
  - monitoring_db.py       — SQLite 永続化層
  - system_monitor.py      — システム・データ鮮度監視
  - trade_monitor.py       — 発注・約定の監視（コード上には参照あり）
  - risk_monitor.py        — ドローダウン／ポジション上限監視
  - kill_switch.py         — kill.flag の読み書き
  - monitoring_engine.py   — 各 Monitor を束ねるエンジン
  - alert_manager.py       — アラート送信（LINE 等、実装場所に依存）
- execution/
  - broker_factory.py      — ブローカークライアント生成（Mock / 実ブローカー）
  - execution_engine.py    — ExecutionEngine 本体
  - order_manager.py       — 注文管理
  - order_repository.py    — DB 永続化
  - reconciler.py          — 注文整合処理
  - risk_manager.py        — 実行時リスク管理
- portfolio/
  - portfolio_builder.py   — 候補選定 / 重み計算
  - position_sizing.py     — 株数計算 / 制限適用
  - risk_adjustment.py     — セクターキャップ / レジーム乗数
- research/
  - factor_research.py     — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン / IC / 統計
- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity 設定
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

運用上の注意
------------
- .env および API キーなどの機密情報は厳重に管理してください（.env を Git にコミットしない）。
- KABUSYS_ENV=live の場合は本番運用になります。validate_config で警告が出る項目を必ず確認してください。
- Monitoring は監視用 DB（SQLITE_PATH）を参照して Kill Switch を作動させる可能性があるため、本番 DB のパス・設定に注意してください。
- OpenAI 呼び出しは API コストとレート制限に注意して運用してください。リトライロジックは実装されていますが、無制御の大量リクエストは避けてください。
- プロセス優先度の設定や CPU affinity は OS・実行権限に依存します。set_process_priority/set_cpu_affinity は失敗した場合に警告を出してスキップします。

貢献・開発
----------
- 新しい設定項目は config_setup.py と config.py、validate_config.py の三箇所を更新してください。
- DB スキーマ変更は monitoring_db.init_monitoring_db にマイグレーションを追加してください（既存 DB への互換性を考慮）。
- テストはモジュール単位で行い、外部 API 呼び出しはモック化してください（特に OpenAI 呼び出しは patch 可能に実装済み）。

ライセンス・その他
------------------
- 本ドキュメントはコードベースに基づく簡易 README です。実運用向けには更なる docs の整備、Unit テスト、CI、セキュリティレビューを推奨します。