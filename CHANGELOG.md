CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。
このファイルはプロジェクトのリリース履歴を要約したものです。

フォーマット:
- 参照: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現時点の未リリースの変更はありません）

[0.1.0] - 2026-04-18
-------------------

Added
- 初回リリース。基本的な自動売買システム「KabuSys」のコアユーティリティ・CLI・ポートフォリオ構築・監視・実行エンジン起動スクリプト等を追加。
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
- 設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。プロジェクトルートは .git または pyproject.toml を基準に探索。
    - .env/.env.local の読み込み順序（OS環境変数 > .env.local > .env）と、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - 環境変数パースの堅牢化（export 形式、クォート内エスケープ、インラインコメント処理など）。
    - 各種設定プロパティ（DBパス、PID/kill フラグ、閾値、環境判定メソッド等）を提供。
- 環境設定ウィザード CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。よく使う設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス等）をサポート。
    - 既存値の読み込み、シークレットマスク表示、確認プロンプト、ファイル書き込みを実装。
- 設定検証 CLI
  - src/kabusys/validate_config.py
    - .env と config/*.yaml の基本的検証を行う CLI を追加（必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ確認、YAML のパースチェックなど）。
    - --strict オプションで警告をエラー扱いとするモードを提供。
- ロギングユーティリティ
  - src/kabusys/utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）をルートロガーに統一的に設定するユーティリティを追加。
    - LOG_LEVEL / LOG_DIR / 引数による設定上書き、既存ハンドラのクリア、ログディレクトリ自動作成（失敗時にコンソールのみ）などを実装。
- プロセス優先度・CPU affinity ユーティリティ
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収してプロセス優先度（high/normal/low）を設定する関数を追加。CPU affinity を最初の N コアに固定する関数も提供。
    - 権限不足や未対応 OS の場合は警告ログを出して安全にフォールバック。
- 実行系起動スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を high に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite を使用（settings.paper_sqlite_path）して本番 DB と分離する挙動を実装。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の起動（デーモンスレッド）と停止フラグ（data/stop_requested.flag）による安全停止処理を実装。
    - 起動時に監視テーブルが存在することを保証する処理（init_monitoring_db の呼び出し）を含む。
- 監視系起動スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用する点を明示。
    - 停止フラグ（data/stop_requested.flag）検出でループを終了、KeyboardInterrupt 対応、例外時はログ出力して次ポーリングへ継続。
- 監視 DB 初期化ユーティリティ（インポート箇所存在）
  - src/kabusys/monitoring/monitoring_db.py（呼び出し箇所から DB 初期化処理を行うユーティリティを提供することを想定）。
- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の SQLite DB（デフォルト: data/paper_trading.db）からレポートを生成するスクリプトを追加。
    - システム稼働率、注文成功率（fill/send）、リスク却下数、API レイテンシ（avg/max/P95）を集計し、閾値に基づいて PASS/FAIL を判定する機能を提供。
    - CLI で期間指定（--from/--to）・DB 指定（--db）が可能。
    - デフォルト閾値: 稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms（ソース中定数で定義）。
- ポートフォリオ構築ライブラリ（純関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナル選定（select_candidates: score 降順、signal_rank をタイブレーク）および等金額/スコア加重（calc_equal_weights / calc_score_weights）を実装。スコアが全て 0 の場合は等金額にフォールバックして警告。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター別時価を計算して上限超過セクターの新規候補を除外する挙動を提供。unknown セクターは上限適用対象外。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を提供（bull:1.0, neutral:0.7, bear:0.3、未知は 1.0 でフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - ポジションサイズ計算を実装（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap によるスケールダウン、コストバッファ考慮、残余キャッシュによる端数配分ロジック等を含む。
  - src/kabusys/portfolio/__init__.py にて上記関数群をエクスポート。
- リサーチ（ファクター計算）モジュール（初期実装）
  - src/kabusys/research/factor_research.py
    - Momentum/Value/Volatility/Liquidity 系ファクターを計算する設計と一部実装を追加。DuckDB 接続を受け取り prices_daily / raw_financials を参照する方針（未完の関数あり）。
    - モメンタム関連定数（1M/3M/6M、MA200、ATR など）を定義。
- ユーティリティ等
  - src/kabusys/utils/__init__.py、tools/__init__.py を追加してパッケージ化。
  - 各モジュールでのログ出力・例外ハンドリングの実装を強化。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 注意事項
- デフォルトの DB/ファイルパス（data/ 以下）や .env の取り扱いにより、プロジェクトルートのファイル構成が前提になります。プロジェクトルート検出に失敗した場合は自動 .env ロードをスキップします。
- 実行スクリプト（run_execution / run_monitoring）は起動前に必ず validate_config を実行し、必要な環境変数や設定ファイルが整っていることを確認することを推奨します。
- paper_trading モードは本番 DB と完全に分離して動作する設計です。PAPER_TRADING_SQLITE_PATH を適切に設定してください。
- 一部モジュール（factor_research の詳細ロジック等）は実装途中の箇所があります。実運用前に追加のレビュー・テストを行ってください。