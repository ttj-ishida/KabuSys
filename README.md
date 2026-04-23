KabuSys — 日本株自動売買システム
===============================

概要
----
KabuSys は日本株向けの自動売買・研究基盤の小規模な実装群です。本コードベースは以下の主要責務を持ちます。

- 発注実行エンジン（ExecutionEngine） — ブローカークライアントを通じた注文管理・リスク管理・照合
- 監視（Monitoring） — システム状態・注文ログ・リスク（ドローダウン、ポジション上限）を定期監視しアラートや Kill Switch を管理
- ポートフォリオ構築（選定・重み付け・ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量探索）
- AI 支援（ニュースの NLP スコアリング、レジーム判定）
- 運用ツール（ペーパートレード検証レポート等）
- 設定管理用 CLI（.env ウィザード、構成検証）

主な特徴（機能一覧）
-----------------
- 環境設定管理（.env 自動読み込み、対話式ウィザード）
- 起動スクリプト:
  - run_execution: ExecutionEngine を起動（paper_trading モード時は MockBroker を使用し DB を分離）
  - run_monitoring: SystemMonitor をポーリング
- 監視基盤:
  - system_status / trade_logs / positions / risk_logs / dashboard を持つ SQLite ベースの監視 DB（init_monitoring_db）
  - RiskMonitor（ドローダウン・ポジション上限監視）、KillSwitch、MonitoringEngine
- ポートフォリオ構築用純関数群:
  - 候補選定（select_candidates）、等重・スコア重み（calc_equal_weights / calc_score_weights）
  - セクター上限チェック（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）
  - 発注株数計算（calc_position_sizes） — リスクベース・等分配・スコア配分対応、単元（lot）丸め、aggregate cap 調整
- リサーチ:
  - ファクター計算（momenta, volatility, value 等）
  - 将来リターン・IC（Information Coefficient）・統計サマリー
- AI モジュール:
  - news_nlp.score_news: OpenAI を使ったニュースセンチメント集約（銘柄単位）→ ai_scores へ書き込み
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースの LLM センチメントを合成して市場レジーム判定
- 運用ツール:
  - tools.paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポートを出力
- ログ設定共通化（utils.logging_setup）・プロセス優先度設定（utils.process_priority）

前提 / 必要パッケージ
------------------
最低限の想定:
- Python 3.10+
- 必要な外部ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時は任意）
- SQLite は標準ライブラリで利用

（プロジェクトの requirements.txt がある場合はそれを使用してください。）

セットアップ手順
--------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. 初期設定（.env の作成）
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - これにより .env が作成されます（.env は絶対に Git にコミットしないでください）。

5. 設定検証
   - python -m kabusys.validate_config
   - 必須環境変数や config/*.yaml の簡易チェックを行います。
   - --strict を付けると警告も失敗扱いになります。

6. データディレクトリを作成（任意）
   - デフォルトの DB / ログパスは data/ と logs/。存在しない場合は自動作成されますが事前に作ると権限問題を回避できます。
   - mkdir -p data logs

基本的な使い方
-------------

環境変数（主要）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading: MockBroker を使用し data/paper_trading.db に記録（本番 DB と分離）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- PAPER_FILL_MODE: ペーパートレードにおける約定挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

起動系
- ExecutionEngine を起動（通常）
  - python -m kabusys.run_execution
  - KABUSYS_ENV によって paper_trading モードで MockBroker を使用します。
  - 停止判定は data/stop_requested.flag または data/kill.flag を使用します。

- SystemMonitor（監視）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒指定可能（デフォルト 60s）。
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用してログを取ります。

ツール
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD (--to YYYY-MM-DD)
    - --db PATH （PAPER_TRADING_SQLITE_PATH に優先）
  - 出力: 稼働率、注文成功率、レイテンシ等の指標と PASS/FAIL 判定

プログラム API（コードから呼び出す例）
- AI スコアリング:
  - from kabusys.ai import score_news
  - score_news(conn=duckdb_conn, target_date=date.today(), api_key="...")

- リサーチ関数:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - calc_momentum(duckdb_conn, target_date)

- ポートフォリオ構築:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes

監視・Kill Switch の振る舞い
- RiskMonitor がダッシュボードを参照してドローダウンやポジション上限を検出すると risk_logs に記録し、KillSwitch が条件を満たせば data/kill.flag を書き込むことで ExecutionEngine に対して停止シグナルを送ります。
- Kill flag は Settings.kill_flag_path（デフォルト data/kill.flag）で管理されます。Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を指定していると自動的にクリアされますが、本番では避けることを推奨。

ログ
- 共通のログ設定ユーティリティ（kabusys.utils.logging_setup）を全起動スクリプトで使用しています。
- デフォルトログディレクトリ: logs/
- ログはコンソール（stdout）と日次ローテートされたファイルに出力されます（30 日保持）。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py             — Settings / 自動 .env ロード
- config_setup.py       — .env 対話ウィザード
- validate_config.py    — 設定検証 CLI
- run_execution.py      — ExecutionEngine 起動スクリプト
- run_monitoring.py     — SystemMonitor 起動スクリプト

サブパッケージ（主要）
- ai/
  - news_nlp.py         — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py  — レジーム判定（MA + マクロ NLP）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- monitoring/
  - monitoring_db.py     — SQLite スキーマ / 永続層
  - system_monitor.py    — システム・データ鮮度監視
  - trade_monitor.py     — （注文ログ監視等）
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - logging_setup.py
  - process_priority.py
- tools/
  - paper_verification_report.py

（ファイル一覧はリポジトリの現状に基づきます。将来的に増減する場合があります）

運用上の注意
------------
- .env（秘密情報）は絶対に Git 管理しないでください。config_setup.py は .env の作成・更新に利用してください。
- KABUSYS_ENV=live の場合は本番扱いになります。LINE 通知等の設定が正しいか必ず validate_config で確認してください。
- Kill Switch の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番環境では危険です。開発用に限定してください。
- AI モジュールを使う場合は OPENAI_API_KEY を設定し、API 利用制限に注意してください。API の失敗はフェイルセーフ（スコア 0.0 にフォールバック等）で扱う設計ですが、運用上の影響を確認してください。

開発・拡張
----------
- 研究用関数群は DuckDB 接続を受け取り prices_daily / raw_financials 等のテーブルを参照します。DuckDB にデータをロードしてローカルで検証できます。
- ポートフォリオ・ポジションサイズ計算などは純関数設計なのでユニットテストが容易です。
- OpenAI 呼び出しはテスト時に差し替え可能な小さなラッパー関数として設計されています（unittest.mock.patch で差し替え推奨）。

ライセンス・貢献
----------------
- この README にはライセンス情報は含まれていません。実装を共有する際は LICENSE ファイルを追加してください。
- バグ修正・機能追加は Pull Request を通じて行ってください。大きな設計変更は事前に Issue で相談してください。

補足（よく使うコマンド例）
-----------------------
- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。README の内容は実装ファイルに基づく要約です。必要に応じてセットアップ手順や依存関係をプロジェクト実態に合わせて更新してください。