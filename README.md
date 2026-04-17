README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買・リサーチ用ライブラリ兼実行環境です。
主な機能は戦略に基づく銘柄選定・ポジションサイズ算出、実行エンジン（ExecutionEngine）、
監視（Monitoring）コンポーネント、リサーチ用ファクター計算、AI を使ったニュースセンチメント／
市場レジーム推定などを提供します。設計は本番環境（live）・ペーパートレード（paper_trading）・
開発（development）を想定し、設定は .env で管理します。

主な特徴
--------
- 実行エンジン（ExecutionEngine）と監視ループ（MonitoringEngine）の分離
- 本番用 DB とペーパートレード用 DB の分離（ペーパートレードは data/paper_trading.db）
- DuckDB を用いたリサーチ／ファクター計算（prices_daily / raw_financials 等）
- OpenAI を使ったニュース NLP（news_nlp）と市場レジーム判定（regime_detector）
- Kill Switch（data/kill.flag）による安全停止機構
- 簡易な設定ウィザードと設定検証 CLI
- ペーパートレード検証レポート出力ツール

必須・推奨依存ライブラリ
-----------------------
（プロジェクト内に requirements.txt がない場合、少なくとも以下をインストールしてください）
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML (config/*.yaml の検証を行う場合)
- sqlite3（標準ライブラリ）
- Python 3.10+

セットアップ手順
--------------
1. リポジトリを取得して作業環境を用意する
   - 推奨: 仮想環境を作る（venv / pyenv など）
     - python -m venv .venv
     - source .venv/bin/activate

2. 必要パッケージをインストール
   - 例:
     - pip install duckdb psutil openai pyyaml

3. 環境変数 (.env) を作成
   - 対話式ウィザードを使って .env を生成できます:
     - python -m kabusys.config_setup
   - 重要（最低限設定する項目）:
     - JQUANTS_REFRESH_TOKEN （必須）
     - KABU_API_PASSWORD （必須）
   - 必要に応じて:
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知）

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も厳格に扱う場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリ
   - デフォルトの DB / PID / フラグファイルは data/ 以下を参照します。存在しない場合は実行時に作成されます。

使い方
------

設定・検証
- 設定ウィザード（.env を生成・更新）
  - python -m kabusys.config_setup
- 設定検証（.env と config/*.yaml の存在/整合性チェック）
  - python -m kabusys.validate_config
  - --strict をつけると警告も失敗扱いにできます

実行エンジン（Execution）
- 実エンジン起動スクリプト:
  - python -m kabusys.run_execution
  - 動作に応じて KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用し、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します
- 起動前に data/stop_requested.flag が存在すると起動をスキップします
- 実行はバックグラウンドスレッドで行われ、同ディレクトリ data/execution.pid に PID を書きます
- 停止は data/stop_requested.flag を作成するか、Kill Switch による data/kill.flag が書き込まれた場合にエンジンが停止します

監視（Monitoring）
- 監視ループ起動スクリプト:
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可（秒、デフォルト 60）
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に依存しない）
  - run_monitoring は data/stop_requested.flag を検知すると終了します

Kill Switch / 停止フラグ
- KillSwitch（kabusys.monitoring.kill_switch）は監視結果に基づいて data/kill.flag を書き込みます
  - ExecutionEngine 起動時に Settings.kill_flag_clear_on_start を 1 にしていると起動時に kill.flag を自動クリアする挙動になります（本番では 0 推奨）
- 実行停止を強制したいときは手動で data/kill.flag を作成してください（または data/stop_requested.flag を作成して監視/実行プロセスを停止させる）

ペーパートレード検証レポート
- ツール:
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能（デフォルト data/paper_trading.db）
  - レポートは稼働率、注文成功率、レイテンシ等を集計して PASS/FAIL 判定を表示します

AI 関連
- ニュース NLP スコアリング:
  - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - OpenAI API キーが必要（引数で渡すか環境変数 OPENAI_API_KEY を設定）
- 市場レジーム判定:
  - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

設定（Settings）についての注意
- KABUSYS_ENV 有効値: development / paper_trading / live
- デフォルト DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- paper_trading モードでは発注ロジックがモック化され、本番 DB と分離して動作します
- .env の自動ロード:
  - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を起点に .env/.env.local を読み込みます
  - テスト時に自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

主要スクリプト一覧と実行例
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- ExecutionEngine 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ディレクトリ構成（主要ファイル）
--------------------------------
以下は src/kabusys 以下の主要モジュールを抜粋した構成です。

- kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定読み込み（Settings）
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール
  - portfolio/
    - portfolio_builder.py       — 候補選定・重み計算
    - position_sizing.py         — 株数決定・投下資金スケール
    - risk_adjustment.py         — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py         — モメンタム / ボラティリティ / バリュー計算（DuckDB）
    - feature_exploration.py     — 将来リターン / IC / 統計サマリ
    - __init__.py
  - ai/
    - news_nlp.py                — ニュースセンチメント（OpenAI 呼び出し）
    - regime_detector.py         — 市場レジーム判定（MA + マクロセンチメント）
    - __init__.py
  - monitoring/
    - monitoring_db.py           — SQLite ベースの監視 DB 層
    - system_monitor.py          — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py           — 注文滞留・約定異常監視
    - risk_monitor.py            — ドローダウン・ポジション上限監視
    - monitoring_engine.py       — 各モニタを束ねたループ
    - kill_switch.py             — kill.flag 書き込みロジック
    - alert_manager.py           — （通知管理: 実装ファイルに依存）
  - execution/
    - execution_engine.py        — ExecutionEngine（起動・注文管理）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - order_record.py
    - risk_manager.py
  - data/
    - pipeline.py (参照例: get_last_price_date)
    - stats.py (zscore_normalize 等)
  - utils/
    - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py

運用・運用時の注意
------------------
- .env は絶対に Git にコミットしないでください（config_setup.py のヘッダにも明記）
- KABUSYS_ENV=live の場合は設定ミスが致命的になるので validate_config を必ず実行して警告・エラーを確認してください
- OpenAI を使う処理は API 利用料金が発生します。キーと呼び出し頻度を管理してください
- プロセス優先度設定は psutil を使って行います。アクセス権限により設定に失敗することがあります（警告ログでスキップされます）
- Monitoring は本番監視用の DB に接続してログを残します。MONITOR_POLL_INTERVAL でポーリング頻度を調整してください

開発・テスト
------------
- モジュールは可能な限り副作用を抑えた純粋関数（ポートフォリオ関連、リサーチ）と、DB/外部 API にアクセスする部分で分離してあります。ユニットテストは純粋関数を中心に書くと簡単です
- OpenAI 呼び出しはラッパー関数（_call_openai_api）をモックしてテスト可能です
- sqlite / duckdb を使うコードはファイルパスを外から注入できるため、テスト用の一時 DB に対してテストを行えます

問い合わせ・貢献
----------------
- README の内容や実装で不明点があればリポジトリの Issue に記載してください
- コントリビューションは PR ベースで受け付けます。重大な設計変更は事前に Issue で議論してください

以上が KabuSys の概要・セットアップ・運用上のポイントです。必要であれば特定モジュールの詳細ドキュメント（たとえば ExecutionEngine の内部フロー、monitoring のアラート条件、AI モジュールのプロンプト仕様など）を追加作成しますので、どの部分を詳しくしたいか教えてください。