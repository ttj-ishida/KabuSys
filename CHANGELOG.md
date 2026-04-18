CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に従って記載しています。  
日付はリポジトリ内のコードから推測した最初のリリースを想定しています。

フォーマットの説明:  
- Added: 新機能、追加されたモジュールや CLI。  
- Changed: 既存挙動の仕様・内部実装の改善。  
- Fixed: バグ修正（コード内コメント等から推測して記載）。  
- Removed / Deprecated / Security: 該当なしの場合は記載を省略しています。  

[Unreleased]
------------

（現時点のコードは初期リリース相当と判断されます。将来の未リリース変更はここに記載してください。）

[0.1.0] - 2026-04-18
--------------------

Added
- 基本コンポーネントの初期実装を追加
  - 実行エンジン起動スクリプト: run_execution.py
    - ExecutionEngine を起動する CLI エントリポイントを提供。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用し、Mock ブローカを利用する設計（BrokerClientFactory 経由）。
    - デーモン風に ExecutionEngine を別スレッドで実行し、data/stop_requested.flag により安全停止可能。
    - PID 書き込みファイル（data/execution.pid）の扱いをサポート。
  - 監視プロセス起動スクリプト: run_monitoring.py
    - SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用の sqlite_path を使用する（環境に依存しない運用を想定）。
    - data/stop_requested.flag によりループを停止可能。
  - 設定管理モジュール: config.py
    - .env 自動読み込み機能（プロジェクトルートを .git / pyproject.toml で検出）。
    - .env/.env.local の読み込み順序と OS 環境変数の保護（上書き禁止）を実装。
    - 各種プロパティ（J-Quants / kabu API / DB パス /監視閾値 /実行環境フラグ等）を提供。
    - PAPER_FILL_MODE のバリデーションや PAPER_TRADING_SQLITE_PATH のサポートなどを実装。
  - 設定検証 CLI: validate_config.py
    - .env と config/*.yaml の存在・基本整合性を確認する CLI（--strict オプションで警告も失敗扱いに）。
    - 必須環境変数チェック・パスの親ディレクトリ存在チェック・YAML パースチェック（PyYAML 利用、未インストール時はスキップ）・本番時の追加ガード等。
  - 設定ウィザード CLI: config_setup.py
    - 対話形式で .env の初期作成・更新を支援するウィザード。
    - 秘匿値は表示をマスクし、保存時に .env を生成（.env の Git コミット禁止を明記）。
  - ロギングユーティリティ: utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（毎日ローテーション、30日保持）を設定する共通セットアップ。
    - ログレベル / ログディレクトリの解決ロジック（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続。
  - プロセス優先度ユーティリティ: utils/process_priority.py
    - Windows / POSIX (Linux/Mac/FreeBSD) の差分を吸収してプロセス優先度（nice / Windows priority class）を設定。
    - CPU affinity を限定する set_cpu_affinity を提供。
  - ポートフォリオ構築ライブラリ (純粋関数群)
    - portfolio/portfolio_builder.py: 候補選定と等金額・スコア加重の重み計算。
    - portfolio/risk_adjustment.py: セクター上限適用、レジーム乗数計算（bull/neutral/bear）。
    - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）、aggregate cap によるスケールダウン、単元株（lot_size）丸め。
    - portfolio/__init__.py でエクスポート。
  - 研究用ファクター計算基盤: research/factor_research.py
    - Momentum / Value / Volatility / Liquidity を計画した設計。DuckDB 接続を受け取り prices_daily / raw_financials を参照する方針で実装開始（モジュールは部分実装）。
  - Paper Trading 検証レポート: tools/paper_verification_report.py
    - ペーパートレードの検証レポートを SQLite DB（デフォルト data/paper_trading.db）から生成する CLI。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計・基準値判定（閾値はソース内定数で定義）。
    - --from / --to / --db オプションをサポート。
  - パッケージメタデータ: __init__.py に __version__ = "0.1.0" を設定。

Changed
- ログ出力ポリシー
  - StreamHandler を stdout に固定（stderr ではない）: cron や Task Scheduler などからのリダイレクトを一元化するため。
- .env 読み込み方針
  - プロジェクトルートの自動検出（.git / pyproject.toml を起点）により CWD に依存しないロードを実現。
  - .env のパースロジックを強化: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントルールなどをサポート。
- DB の分離ポリシー
  - 実行エンジンは paper_trading 環境であれば paper_sqlite_path を使用し、本番 DB と完全に分離して動作するように実装。
  - 監視プロセスは環境に関わらず production sqlite_path を使用する（監視データは一元管理）。

Fixed
- 環境変数パースの堅牢化
  - .env 中のシークレットや引用符・エスケープを正しく扱うように改善（testable なパーサ実装）。
- 起動時のログ二重登録防止
  - setup_logging() が既存ハンドラを flush/close のうえクリアしてからハンドラを再設定するようにして、複数回呼び出しても重複出力が発生しないよう修正。
- process priority / cpu affinity の例外処理
  - アクセス権限不足や未サポート環境での落ちを防ぐため警告ログにフォールバック。

Notes / Known limitations / TODOs
- research/factor_research.py は部分実装（ソースファイル末尾に未完の記述あり）。ファクター計算の完全実装は今後の作業。
- position_sizing.calc_position_sizes / risk_adjustment.apply_sector_cap 内にある TODO:
  - 価格欠損 (price == 0.0) 時のフォールバック価格（前日終値や取得原価）に関する改善点が残っている。
  - 将来的には銘柄ごとの lot_size をマスタ化して対応する予定（現状は全銘柄共通の lot_size を想定）。
- run_monitoring と run_execution は stop flag / pid file のファイルベース制御を採用しているため、運用環境でのファイルパーミッション・タイミングに注意が必要。
- ログディレクトリ作成やファイルハンドラ作成に失敗した場合、詳細は stderr/ログに出力されるが、ファイル出力が無効化される点に留意。

開発者向けメモ
- 設定ロードはデフォルトで自動実行されるが、テストなどで自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- validate_config.py を CI に組み込むことで、デプロイ前に必須環境変数やコンフィグファイルの有無を検出できます（--strict で警告も FAIL 扱いにできます）。
- paper_trading 用 DB のパスは環境変数 PAPER_TRADING_SQLITE_PATH でオーバーライド可能。tools/paper_verification_report も同様。

以上。必要であれば各変更点をファイル毎により詳細に分解したエントリに展開します。