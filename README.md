README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のコアライブラリ群です。本リポジトリは以下の主要機能群を含みます。

- Execution: 発注エンジン（本番 / ペーパートレード切替対応）
- Monitoring: システム稼働・注文状態・リスクの監視と Kill Switch
- Research: ファクター計算・特徴量解析
- Portfolio: 候補選定・配分・ポジションサイズ計算・リスク調整
- AI: ニュース NLP（OpenAI）を使ったセンチメント評価とレジーム判定
- Tools: Paper Trading の検証レポート生成などユーティリティ

特徴
----
- 本番／ペーパートレードを環境変数で切り替え可能（KABUSYS_ENV）
- SQLite（監視／ペーパートレード DB）と DuckDB（分析用）を併用
- Monitoring は常に本番用 sqlite_path を参照して監視ログを永続化
- ペーパートレード時は mock ブローカで完全に分離された DB（data/paper_trading.db）を使用
- OpenAI（gpt-4o-mini）を用いたニュースのセンチメント評価と市場レジーム判定（フェイルセーフ実装）
- ロギングは stdout + 日次ローテートファイル（logs/*.log）

前提・依存
-----------
主な外部依存（少なくとも以下のパッケージが必要です）:
- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config ファイル検証で使用）
（requirements.txt がある場合はそれを使用してください）

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動します。
   - 例: git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化し、依存をインストールします。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install -r requirements.txt  （requirements.txt がない場合は duckdb, psutil, openai, PyYAML 等を個別に入れてください）

3. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     → .env を生成または更新します（J-Quants トークンや kabu API パスワードなどを入力）
   - 自動ロードについて:
     - パッケージは起動時にプロジェクトルートの .env を自動で読み込みます（.env.local の上書きも可）。
     - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 問題があれば表示されるエラー／警告を確認し修正してください。
   - --strict を付けると警告も失敗扱いで exit(1) になります。

主要な環境変数（主なもの）
--------------------------
以下は重要な環境変数とデフォルト値（存在しない場合）。

必須（起動前に .env に設定してください）
- JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API パスワード

主要な任意 / 設定可能項目
- KABUSYS_ENV           : 実行モード（development | paper_trading | live） デフォルト: development
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL             : ログレベル（DEBUG/INFO/...） デフォルト: INFO
- OPENAI_API_KEY        : OpenAI API キー（AI モジュール使用時）
- PAPER_FILL_MODE       : ペーパートレードの約定挙動（instant/partial/never/reject） デフォルト: instant
- KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動クリアするか（0/1）デフォルト: 0
- MONITOR_POLL_INTERVAL : run_monitoring のポーリング間隔（秒） デフォルト: 60

使い方（コマンド）
-----------------

設定ウィザード
- python -m kabusys.config_setup
  - .env を対話式に作成／更新します。

設定検証
- python -m kabusys.validate_config
  - .env と config/*.yaml の基本チェックを行います。

ExecutionEngine（発注エンジン）起動
- python -m kabusys.run_execution
  - KABUSYS_ENV に応じて本番/ペーパーの DB とブローカクライアントを選択します。
  - ペーパートレード時は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - エンジンは data/execution.pid に PID を書きます。停止は stop flag の作成で行います。

Monitoring（監視ループ）起動
- python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視ログは settings.sqlite_path（デフォルト data/monitoring.db）へ記録されます（Monitoring は常に本番 sqlite_path を使用）。
  - 停止はプロジェクトルート/data/stop_requested.flag を作成することで行います。

Paper Trading 検証レポート生成（ツール）
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH 環境変数、または --db で DB ファイルを指定できます。
  - 稼働率、注文成功率、レイテンシ等を集計して PASS/FAIL 判定を出力します。

AI 関連（プログラム API）
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡してニュースセンチメントを ai_scores テーブルへ書き込みます。
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ保存します。
（これらは CLI ではなく Python API として利用する想定です。OPENAI_API_KEY を環境変数で渡すことも可能です。）

停止・Kill Switch
- kill.flag（Settings.kill_flag_path）: Kill Switch による ExecutionEngine 停止指令ファイル
  - Monitoring 側の KillSwitch が条件（ドローダウン、ポジション上限等）を満たすと data/kill.flag を書き込みます。
  - ExecutionEngine は起動時に kill.flag を検出すると起動を止め、稼働中に kill.flag が検知されると停止します。
- data/stop_requested.flag: 外部から run_*.py を終了させるためのフラグ（両スクリプトで参照）

ログ
---
- logs/<app_name>.log に日次ローテートで出力されます（デフォルト logs/ ディレクトリ）。
- コンソール出力は stdout に流れます。ログ設定は kabusys.utils.logging_setup.setup_logging で統一管理されています。

ディレクトリ構成（抜粋）
---------------------
以下は主要なファイル / ディレクトリ（src/kabusys 以下）の概要です。

- run_monitoring.py        : SystemMonitor をポーリングする起動スクリプト
- run_execution.py         : ExecutionEngine（発注エンジン）起動スクリプト
- config.py                : 環境変数 / 設定読み込みロジック（.env 自動読み込み・Settings クラス）
- config_setup.py          : .env 対話式ウィザード
- validate_config.py       : 起動前の設定検証 CLI

- monitoring/
  - monitoring_db.py       : SQLite 監視 DB レイヤ（テーブル初期化・読み書き）
  - system_monitor.py      : システム状態 / データ鮮度監視
  - trade_monitor.py       : （注文監視ロジック群）
  - risk_monitor.py        : ドローダウン・ポジション上限監視
  - kill_switch.py         : kill.flag 書込ロジック
  - monitoring_engine.py   : 各 Monitor を束ねるエンジン
  - alert_manager.py       : （外部通知管理 — LINE 等）

- execution/
  - execution_engine.py    : 発注セッション実行ロジック
  - order_manager.py       : 注文管理
  - order_repository.py    : 注文 DB レイヤ
  - broker_factory.py      : ブローカクライアント生成（本番 / mock 切替）
  - risk_manager.py        : 実行時リスク管理

- portfolio/
  - portfolio_builder.py   : 候補選定・重み計算
  - position_sizing.py     : 株数（ロット）計算、投下資金スケールロジック
  - risk_adjustment.py     : セクター上限、レジーム乗数

- research/
  - factor_research.py     : モメンタム / ボラティリティ / バリュー計算（DuckDB 使用）
  - feature_exploration.py : 将来リターン、IC、統計サマリー

- ai/
  - news_nlp.py            : ニュースセンチメント取得（OpenAI）
  - regime_detector.py     : マクロ + ETF MA を使ったレジーム判定

- tools/
  - paper_verification_report.py : ペーパートレード評価レポート

- utils/
  - logging_setup.py       : ログの統一設定
  - process_priority.py    : プロセス優先度・CPU affinity 設定ユーティリティ

注意事項 / 運用上のポイント
---------------------------
- 本番稼働時は KABUSYS_ENV=live とし、環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）を安全に管理してください。
- .env ファイルは絶対に Git にコミットしないでください（config_setup が注意書きを出力します）。
- Monitoring は監視 DB（monitoring.db）へ常に書き込みます。データ消失を避けるため DB のバックアップやディスク容量監視を推奨します。
- OpenAI を使う機能は API レート制限・コスト面を考慮して運用してください。失敗時はフェイルセーフで継続する実装になっていますが、API キーの漏洩に注意してください。
- プロセス優先度設定（set_process_priority）は OS により制限される場合があります（権限不足時は警告でスキップ）。

開発・テスト
-------------
- モジュールは Python の import として単体テストしやすい設計（副作用を最小化）になっています。例えば research の関数は DuckDB 接続を受け取る純粋関数群です。
- run_* スクリプトは if __name__ == "__main__": ブロックを持つため、モジュールとしてのインポートやユニットテストが容易です。
- AI 呼び出し部分は API 呼び出し関数をラップしており、ユニットテスト時はモック差替え可能（例: unittest.mock.patch）。

ライセンス・バージョン
---------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリルートの LICENSE を参照してください（存在する場合）。

補足（トラブルシューティング）
------------------------------
- ログディレクトリ作成失敗時はファイル出力が無効化され、コンソールのみ出力されます。権限やパスを確認してください。
- DB のマイグレーション（カラム追加）は init_monitoring_db が上書きなしで実行します。既存 DB に対する変更はバックアップしてから行ってください。

以上が本コードベースの概要と使い方です。必要であれば、特定モジュール（例: execution_engine や ai/news_nlp）の内部 API ドキュメントや起動時のログサンプル、.env のサンプルテンプレートを追加できます。どの情報を詳述しましょうか？