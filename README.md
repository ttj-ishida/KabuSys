KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システム骨格です。信号生成・ポートフォリオ構築・発注管理・監視・レポーティング・AI（ニュースのセンチメント解析／レジーム判定）などの主要機能をモジュール化して提供します。  
このリポジトリはライブラリ群と起動用スクリプト（ExecutionEngine / Monitoring）および補助ツール群を含みます。

主な特徴（機能一覧）
------------------
- 環境設定管理
  - .env の対話式ウィザード（config_setup）
  - 起動前の設定検証ツール（validate_config）
  - 自動 .env 読み込み（プロジェクトルート検出）
- 実行エンジン
  - run_execution: ExecutionEngine を起動。KABUSYS_ENV に応じてペーパートレード（独立 DB）をサポート
  - ブローカークライアント切替（本番 / Mock）
  - 注文管理、リスク管理、再整合（reconciler）などのサブシステム
- 監視（Monitoring）
  - run_monitoring: SystemMonitor を定期実行し system_status 等を監視・記録
  - MonitoringEngine: System / Trade / Risk 各モニタの統合ループ、Kill Switch 評価、アラート発行
  - 監視ログ（SQLite）と分析用 DuckDB への出力
- ポートフォリオ構築（純粋関数）
  - 候補選定、等額／スコア加重配分、ポジションサイズ計算、セクター制約、レジーム乗数など
- リサーチ（DuckDB を利用）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC 計算・特徴量サマリ
- AI（OpenAI API）
  - ニュースのセンチメント解析（news_nlp）
  - マーケットレジーム判定（regime_detector）
  - （OpenAI API キー必要 / 失敗時はフォールバックする処理あり）
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools.paper_verification_report）
- ユーティリティ
  - ログ設定（console + 日次ローテーション）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

セットアップ手順
----------------
前提
- Python 3.10+（型注釈で Union shorthand を使用）
- 推奨パッケージ（少なくとも以下をインストールしてください）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（設定ファイル検証時に推奨）
- 仮想環境の使用を推奨します。

例（venv + pip）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存関係インストール（任意の requirements.txt がない場合は最低限）
   - pip install duckdb psutil openai PyYAML

3. 初期設定（.env 作成）
   - python -m kabusys.config_setup
     - 対話式に環境変数を入力して .env を生成します。
   - 生成した .env を編集して必要なトークンやパスを正しく設定してください。

必須環境変数（主要）
- JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD      : kabuステーション API パスワード（必須）
- KABUSYS_ENV            : 実行環境 (development | paper_trading | live)（デフォルト: development）
- OPENAI_API_KEY         : OpenAI を使う場合に必要（AI 機能）

その他よく使う環境変数（代表）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            : 監視 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : ペーパートレード専用 SQLite（paper_trading 実行時に使用）
- LOG_LEVEL / LOG_DIR
- KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
- PAPER_FILL_MODE        : ペーパートレードの約定挙動（instant|partial|never|reject）

自動 .env 読み込みを無効化する場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードをスキップできます（テスト用）。

設定検証
- python -m kabusys.validate_config
- 可能であれば --strict を付けて警告も失敗扱いにできます。

使い方（起動・運用）
--------------------

1) ExecutionEngine 起動
- 本番・ペーパートレードを切り替えて起動します（.env の KABUSYS_ENV を設定）。
- コマンド:
  - python -m kabusys.run_execution
- ペーパートレード時:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録します（本番 DB と分離）。

2) Monitoring 起動
- 監視ループを立ち上げ system_status 等を定期記録します。
- コマンド:
  - python -m kabusys.run_monitoring
- ポーリング間隔の上書き:
  - 環境変数 MONITOR_POLL_INTERVAL=30 などで秒数を指定（デフォルト 60 秒）。
- 監視は常に本番 sqlite_path を参照します（監視 DB は KABUSYS_ENV に依らず本番パスを使用）。

停止（Kill Switch / Stop フラグ）
- Monitoring の KillSwitch がトリガーされた場合、data/kill.flag が書き込まれます。ExecutionEngine は起動時・ランタイムでこのフラグを検出して安全停止します。
- 手動停止シグナル（run_execution/run_monitoring 停止用）:
  - プロジェクトルートの data/stop_requested.flag を作成すると、run_* スクリプトは検出して終了します。
- PID ファイル:
  - data/execution.pid 等の PID ファイルを使用します（Settings.pid_file_path）。

3) Paper Trading 検証レポート
- tools.paper_verification_report を使ってペーパートレード結果のサマリ・PASS/FAIL 判定を出力できます。
- 例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

4) AI 機能
- news_nlp.score_news(conn, target_date, api_key=None)
  - OpenAI API キー（引数 or OPENAI_API_KEY 環境変数）が必要。
- regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF（1321）の MA とマクロニュースを元にレジーム判定を行い DuckDB に書き込みます。
- 注意: OpenAI 呼び出しはネットワーク/API エラーに対してリトライやフォールバックが組み込まれていますが、API キーの設定と呼び出し回数には注意してください。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py                      — パッケージ定義
  - config.py                        — 環境変数 / Settings 管理（自動 .env 読み込み）
  - config_setup.py                  — .env 対話式ウィザード
  - validate_config.py               — 起動前設定検証 CLI
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - run_monitoring.py                — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py   — ペーパートレード検証レポート
  - portfolio/
    - portfolio_builder.py           — 候補選定・重み計算
    - position_sizing.py             — 注文株数計算・集計上限
    - risk_adjustment.py             — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py             — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py         — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py                    — ニュース NLP（OpenAI）による銘柄スコアリング
    - regime_detector.py             — 市場レジーム判定（MA + マクロニュース）
  - monitoring/
    - monitoring_db.py               — SQLite 永続化層（テーブル作成・CRUD）
    - system_monitor.py              — システム状態・データ鮮度監視
    - trade_monitor.py               — 発注関連監視（滞留注文など）※（実装ファイルあり）
    - risk_monitor.py                — ドローダウン / ポジション上限監視
    - kill_switch.py                 — Kill Switch 制御（data/kill.flag）
    - monitoring_engine.py           — 各 Monitor を束ねるループ
  - utils/
    - logging_setup.py               — 統一ログ設定（stdout + 日次ローテーション）
    - process_priority.py            — プロセス優先度 / CPU affinity 設定

運用時の注意点・ベストプラクティス
---------------------------------
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup と README にも明記）。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨（自動クリアは危険）。
- Monitoring は本番 DB を参照して監視を行います。ペーパートレード DB は paper_trading 専用に分離されています。
- ログは logs/<app_name>.log に日次ローテーションで保存されます。LOG_DIR で変更可能。
- OpenAI を使う機能は API コストとレスポンスの不確実性を伴うため、使用ポリシーとレート制限に注意してください。

開発／テスト
-------------
- 自動 .env ロードを無効にする:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してテスト用に環境変数を制御できます。
- モジュールは純粋関数になっている箇所が多く（portfolio, research 等）、ユニットテストが容易です。
- AI 呼び出し部分は内部関数 (_call_openai_api 等) をモックしてテスト可能になるよう設計されています。

ライセンス・貢献
----------------
この README に含まれていないライセンス表記や貢献ルールがある場合はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください。

付録：よく使うコマンド早見
------------------------
- .env ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README は以上です。追加で「インストール用 requirements.txt の例」や「実行時のログサンプル」「DB スキーマの詳しい説明」を希望される場合は、その旨を教えてください。