README
=====

概要
----
KabuSys は日本株向けの自動売買およびリサーチ用フレームワークです。  
このリポジトリは、実運用向けの ExecutionEngine（発注・リスク管理）・Monitoring（監視・Kill Switch）・リサーチ（ファクター計算／特徴量探索）・AI（ニュース解析／レジーム判定）等の主要コンポーネントを含みます。  
設計方針として「本番データベースとペーパートレードを分離」「ルックアヘッドバイアスを避ける」「外部 API 呼び出しは明示的・フェイルセーフに行う」ことを重視しています。

主な機能
---------
- Execution Engine
  - ブローカークライアント抽象化（実口座 / Mock）
  - 注文管理、リスク管理、オーダーの突合せ（Reconciler）
  - Paper trading モード（DB を分離）
- Monitoring
  - システム状態（CPU/メモリ/ディスク）とデータ鮮度監視
  - 取引ログ（trade_logs）/ リスクログ（risk_logs）等の永続化（SQLite）
  - Kill Switch（閾値越えで data/kill.flag を書き込み、Execution を停止）
  - アラート送出（LINE などの設定により）
- Portfolio Construction
  - 候補選定、等配分/スコア加重、ポジションサイズ計算、セクター制限、レジーム調整
- Research
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI （OpenAI 経由）
  - ニュースのセンチメントスコアリング（news_nlp / gpt-4o-mini）
  - 市場レジーム判定（regime_detector）
  - OpenAI 呼び出しはリトライ・バックオフ・レスポンス検証を行う
- ツール
  - ペーパー取引検証レポート生成（tools/paper_verification_report.py）
  - 設定ウィザード（config_setup.py）・設定検証ツール（validate_config.py）
- ロギング
  - 統一的な logging 設定（コンソール stdout + 日次ローテートファイル）

前提条件 / 必要環境
-------------------
- Python 3.10+
- 推奨パッケージ（例）
  - duckdb
  - psutil
  - openai
  - (オプション) PyYAML（config/ *.yaml 検証用）
- SQLite は標準ライブラリで利用
- ネットワーク接続（本番で kabuAPI / J-Quants / OpenAI を使う場合）

セットアップ手順
----------------
1. リポジトリをクローン / チェックアウト
2. 仮想環境を作成・有効化（例: python -m venv .venv && source .venv/bin/activate）
3. 必要パッケージをインストール
   - 例: pip install duckdb psutil openai pyyaml
   - 実運用では requirements.txt を用意して pip install -r requirements.txt を推奨
4. 環境変数設定
   - .env を作成する方法（対話式ウィザード推奨）
     - python -m kabusys.config_setup
     - ウィザードで JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等を設定してください
   - .env を作成したら（必要に応じて）検証
     - python -m kabusys.validate_config
   - 重要な環境変数（主な一覧）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB, デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading 用： instant | partial | never | reject）
     - LOG_LEVEL（例: INFO / DEBUG）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意: アラート用）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0/1）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒数、デフォルト 60）

データ・ログディレクトリ
- デフォルトで以下ファイルを生成 / 利用します（必要に応じて .env で上書き）
  - data/monitoring.db — 監視ログ（SQLite）
  - data/paper_trading.db — ペーパートレード用 SQLite（paper_trading モード）
  - data/kabusys.duckdb — DuckDB（分析データ）
  - logs/<app>.log — ログファイル（日次ローテーション、デフォルト logs/ ディレクトリ）
  - data/kill.flag — Kill Switch フラグ
  - data/stop_requested.flag — run_* スクリプトの優雅な停止制御ファイル
  - data/execution.pid — ExecutionEngine の PID（実行時）

使い方
------
基本的なエントリポイント（モジュールとして実行）:

- 環境設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い（exit(1)）

- ExecutionEngine 起動（本番 / ペーパーともに同じ起動コマンド）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、paper_trading DB に記録します
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します
  - 正常停止は data/stop_requested.flag を作成することで優雅に停止できます

- Monitoring 起動（監視ループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを記録します
  - data/stop_requested.flag を置くと監視ループは終了します

- Paper trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで PAPER_TRADING_SQLITE_PATH を指定可能（優先）

- AI 機能（例）
  - kabusys.ai.score_news (news_nlp.score_news) — DuckDB 接続と target_date を渡して実行
  - kabusys.ai.regime_detector.score_regime — 同様に DuckDB 接続と target_date を渡して実行
  - 注意: OPENAI_API_KEY を環境変数か引数で指定してください

停止 / Kill Switch
- Execution を外部から停止する方法:
  - kill.flag: 監視コンポーネント（KillSwitch）が閾値を満たすと data/kill.flag を作成します。Execution 起動時に Settings.kill_flag_clear_on_start により自動クリア可（本番では 0 推奨）。
  - stop_requested.flag: 手動でプロセスを優雅に終了させたい場合は data/stop_requested.flag を作成してください（run_execution/run_monitoring が検出して終了します）。

注意点 / 運用上のヒント
- .env を絶対に Git にコミットしないでください（機密情報を含みます）。
- 本番環境（KABUSYS_ENV=live）では LINE 通知設定や kill flag の挙動を十分に確認してください。validate_config は本番向けガードチェックを行います。
- OpenAI 呼び出しはネットワーク/課金を伴うため、本番ではレートやエラーハンドリングのポリシーを確認してください。
- DuckDB / SQLite のパスは .env で明示的に指定して、運用環境での配置をコントロールしてください。

主要ディレクトリ構成
-------------------
（src/kabusys 以下の主要ファイル・ディレクトリを抜粋）

- src/kabusys/
  - __init__.py                    — パッケージ定義
  - config.py                      — 環境変数・設定管理 (.env 自動ロード含む)
  - config_setup.py                — 対話式 .env ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — Monitoring 起動スクリプト

  - execution/                     — 実際の発注ロジック群（broker_factory, execution_engine, order_manager, risk_manager 等）
  - monitoring/
    - monitoring_db.py             — SQLite 永続化層（テーブル定義 / CRUD）
    - system_monitor.py            — システム状態・データ鮮度監視
    - trade_monitor.py             — 取引ログ整合性監視（滞留注文・約定異常等）
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - kill_switch.py               — Kill Switch 制御
    - monitoring_engine.py         — 各モニターを束ねるループ
    - alert_manager.py             — 通知管理（LINE 等）
  - portfolio/
    - portfolio_builder.py         — 候補選定・重み計算
    - position_sizing.py           — 株数決定・スケールダウン等
    - risk_adjustment.py           — セクター上限・レジーム乗数
  - research/
    - factor_research.py           — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py       — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py                  — ニュースの OpenAI ベースセンチメント解析（ai_scores 書き込み）
    - regime_detector.py           — マクロ＋MA200 を使ったレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の合格判定・レポート生成
  - utils/
    - logging_setup.py             — ログ設定ユーティリティ（stdout + 日次ファイル）
    - process_priority.py          — プロセス優先度 / CPU affinity 設定ユーティリティ

開発者向けメモ
---------------
- DuckDB を使ったリサーチ関数は副作用を持たない純粋関数群として設計されています（テストしやすい）。
- OpenAI 呼び出しは各モジュールでラップされ、テスト時は _call_openai_api をモックすることを想定しています。
- monitoring_db.init_monitoring_db は冪等でマイグレーション（カラム追加）も含んでいるため、起動時に呼んで問題ありません。

ライセンス・その他
------------------
- 本プロジェクトの利用・配布ルールはリポジトリの LICENSE を参照してください（存在しない場合は適宜追加してください）。
- セキュリティ上の機密情報（API トークン等）は .env や環境変数で管理し、公開リポジトリには絶対に含めないでください。

お問い合わせ / 参考
------------------
- 実装や運用に関する質問はリポジトリの Issue へお願いします。