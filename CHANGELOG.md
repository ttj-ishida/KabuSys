CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-04-18
--------------------

Added
- 初回リリース: KabuSys 基本機能群を追加。
  - コア CLI / 起動スクリプト
    - run_execution: 実行エンジン起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は paper_sqlite_path（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント生成を組み込み。
      - ExecutionEngine をスレッドで起動し、 data/stop_requested.flag を検知して安全に停止可能。
      - 起動時にプロセス優先度を "high" に設定（set_process_priority）。
      - PID ファイルを書き込むための設定（data/execution.pid）をサポート。
    - run_monitoring: システム監視ポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境に関わらず監視用 sqlite_path（デフォルト: data/monitoring.db）を使用。
      - 停止フラグ（data/stop_requested.flag）検知でループ終了。
      - 起動時にプロセス優先度を "high" に設定。
  - 設定管理
    - config.py:
      - .env 自動ロード機能を追加（プロジェクトルート検出: .git または pyproject.toml を基準）。
      - .env / .env.local の読み込み順序と保護（OS 環境変数は上書きされない）を実装。
      - Settings クラスを導入し、J-Quants / kabu API / DB パス /監視・システム設定等のプロパティを提供。
      - PAPER_FILL_MODE に対するバリデーション（有効値: instant, partial, never, reject）。
      - KABUSYS_ENV のバリデーション（development, paper_trading, live）と便宜的プロパティ（is_live/is_paper/is_dev）。
  - 環境設定支援ツール
    - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。
      - 秘匿入力（トークンやパスワード）や選択肢をサポート。
      - 保存前の確認表示、.env のテンプレート的書式での書き出しを行う。
  - 設定検証ツール
    - validate_config.py: .env および config/*.yaml の起動前検証 CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスの親ディレクトリチェック、YAML のパースチェック（PyYAML が存在する場合）。
      - --strict オプションで警告を失敗扱いにできる。
  - ロギング・ユーティリティ
    - utils/logging_setup.py:
      - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を一括設定するユーティリティを追加。
      - ログレベル・ログディレクトリは引数 / 環境変数 / デフォルトの順で解決。
      - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力にフォールバック。
  - プロセス優先度ユーティリティ
    - utils/process_priority.py:
      - Windows / POSIX の違いを吸収してプロセス優先度（high/normal/low）を設定する関数を追加。
      - CPU affinity を最初 N コアに固定する set_cpu_affinity を提供。
      - 権限不足や未対応 OS の場合は安全に警告を出してスキップする実装。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py:
      - 銘柄候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
      - スコア合計が 0 の場合は等金額配分にフォールバックして警告を出す。
    - portfolio/risk_adjustment.py:
      - セクター集中制限を適用する apply_sector_cap を実装（売却予定銘柄の除外、"unknown" セクターは除外対象としない挙動）。
      - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull=1.0 / neutral=0.7 / bear=0.3、未知は警告で 1.0 にフォールバック）。
    - portfolio/position_sizing.py:
      - 各配分方式（risk_based, equal, score）に基づく発注株数計算を実装。
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超える場合のスケールダウン）や cost_buffer を考慮したスケーリングロジックを備える。
      - price 欠損時のスキップやロギングを実施。
  - Paper Trading 検証ツール
    - tools/paper_verification_report.py:
      - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から集計して検証レポートを生成するツールを追加。
      - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）などを算出し、閾値比較（PASS/FAIL）を行う。
      - 日付フィルタ、コマンドライン引数（--from/--to/--db）をサポート。
  - リサーチ（ファクター計算）のスケルトン
    - research/factor_research.py:
      - モメンタム等のファクター計算モジュールの雛形を追加（DuckDB 接続を受け取り prices_daily/raw_financials を参照して計算する設計）。
      - 主要定数（窓長等）と calc_momentum の開始部分を実装（注: 実装途中の箇所あり）。

Changed
- パッケージ情報
  - src/kabusys/__init__.py にて __version__ を "0.1.0" に設定（初期バージョン）。

Fixed
- N/A（初回リリースのため既知のバグ修正履歴なし）。

Deprecated
- N/A

Removed
- N/A

Security
- N/A

Notes / 実装上の重要な挙動
- .env 自動ロード
  - デフォルトでプロジェクトルートの .env を自動で読み込みます。.env.local は .env より優先して上書きされます。
  - OS 環境変数は保護され、.env の値で上書きされません。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は KABUSYS_ENV に関わらず monitoring 用 DB（Settings.sqlite_path）を使う設計です。監視データは本番用 DB に保存される点に注意してください。
- run_execution は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と分離します。ペーパートレードのデータは data/paper_trading.db に記録されます（変更可能）。
- ログはデフォルトで logs/ ディレクトリに日次ローテートで保存されます。ディレクトリ作成に失敗した場合はコンソールログのみになります。
- process_priority の設定は権限や OS に依存します。設定に失敗しても警告を出して継続します。
- portfolio/position_sizing の aggregate cap スケールダウンは lot_size（単元）単位で再配分を行うため、端数処理により厳密な利用可能現金全額を使い切れない場合があります（意図的な安全設計）。

Known issues / TODO
- research/factor_research.py の calc_momentum 実装はファイル末尾が未完了（実装途中）。リサーチ機能の完成が次フェーズの課題です。
- position_sizing で price が欠損（0.0）の場合のフォールバック価格（前日終値や取得原価など）を使う拡張は TODO としてコメントに残しています。
- 一部のファイルで外部モジュール（psutil, duckdb, PyYAML 等）への依存があります。CI / デプロイ環境で依存パッケージの整備が必要です。

References
- 各 CLI の使い方はソース内 docstring とヘルプ（python -m module あるいは --help）を参照してください。