Keep a Changelog フォーマットに準拠して、提示されたコードベースから推測して作成した CHANGELOG.md（日本語）を下記に示します。

（注）この CHANGELOG はソースコードの内容・コメント・ TODO 等から推測して構成しています。リリース実績や日付は推測に基づくため、必要に応じて実際のリリース日やバージョンポリシーに合わせて調整してください。

----------------------------------------------------------------------
Keep a Changelog
https://keepachangelog.com/ja/1.0.0/
----------------------------------------------------------------------

すべての変更はセマンティック バージョニングに従います。
このファイルでは、変更を大まかにカテゴリ分けしています: Added, Changed, Fixed, Security, Deprecated, Removed, その他。

Unreleased
---------
- 将来的な改善メモ（コード内の TODO や設計ノートに基づく推測）
  - price が欠損（0.0）となる場合のフォールバック価格（前日終値や取得原価等）を導入予定。
  - 銘柄ごとの単元情報（lot_size）を stocks マスタに持たせ、銘柄別の lot_map をサポート予定。
  - DuckDB を用いたリサーチ・ファクター計算の完全実装（現状一部未完の関数あり）。
  - ログ周りや各種 IO のエラー時により詳細な診断情報を出力する改善。

[0.1.0] - 2026-04-18
--------------------
Added
- プロジェクト初期実装を追加（初期リリース）。
  - 実行スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（data/paper_trading.db をデフォルト）を使用し、MockBrokerClient を利用できるよう設計。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag ファイルで制御。
  - 設定関連
    - config.py: 環境変数および .env 自動読み込み機能。プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を読み込む。各種設定（DB パス、API トークン、監視閾値、環境種別 等）を提供。
    - config_setup.py: 対話式 .env 作成/更新ウィザード。シークレット項目はマスク表示。書き出しテンプレートを提供。
    - validate_config.py: 起動前に .env および config/*.yaml の存在・基本検証を行う CLI。--strict オプションで警告を FAIL 扱いにできる。PyYAML 未インストール時のフォールバックも考慮。
  - ポートフォリオ構築関連（純粋関数群）
    - portfolio/portfolio_builder.py: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
    - portfolio/position_sizing.py: 各銘柄の発注株数算出（risk_based / equal / score）。単元丸め（lot_size）、コストバッファを考慮した aggregate cap のスケーリングロジックを実装。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジームに基づく投下資金乗数（calc_regime_multiplier）。
  - リサーチ
    - research/factor_research.py: DuckDB 接続を受け取りファクター（Momentum/Value/Volatility/Liquidity）を算出するためのモジュール骨格。日数定数や P95 計算等のユーティリティを含む（実装未完の箇所あり）。
  - ツール
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツール。稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を算出し PASS/FAIL を判定。PAPER_TRADING_SQLITE_PATH で DB 指定可能。
  - ユーティリティ
    - utils/logging_setup.py: StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定する共通ユーティリティ。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - utils/process_priority.py: Windows / POSIX を吸収したプロセス優先度設定（high/normal/low）と CPU affinity 設定。権限不足や未対応 OS 時にフォールバックして安全にスキップする。
  - データ基盤
    - DuckDB を分析用 DB（デフォルト data/kabusys.duckdb）として採用。リサーチや ExecutionEngine の分析処理で使用する想定。
    - SQLite を監視・注文履歴用（デフォルト data/monitoring.db）、paper_trading 用に分離した SQLite（data/paper_trading.db）をサポート。
  - その他
    - パッケージメタ情報: kabusys.__version__ = "0.1.0" を追加。

Fixed
- 設定/入力まわりの堅牢化、フォールバック挙動の明確化
  - .env パーサ: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。無効行は無視する実装により読み込みの堅牢性を向上。
  - MONITOR_POLL_INTERVAL の不正値（0/負数/非数）を検出してデフォルト（60 秒）にフォールバックし、警告ログを出力するように実装。
  - ログ設定: ログディレクトリ作成に失敗した場合でもコンソールログ（stdout）を確実に出力するようにして起動を妨げない。
  - process_priority / set_cpu_affinity: 権限不足・未実装 API に対する例外を捕捉し警告でスキップすることで、サーバ環境や CI での起動失敗を回避。
  - ExecutionEngine 起動時の DB 初期化（監視テーブル）を冪等に行う init_monitoring_db 呼び出しを追加し、起動前のテーブル不足でのクラッシュを防止。
  - run_execution/run_monitoring における stop フラグ（data/stop_requested.flag）と PID 管理により安全な停止/起動制御を提供。

Security
- 秘密情報の扱いに配慮
  - config_setup の対話表示ではシークレット項目をマスクして表示。
  - .env ファイル生成テンプレートに「絶対に Git にコミットしないこと」と明記。
  - Settings クラスは必須環境変数が未設定の場合に明示的なエラーを投げ、誤ったデプロイを早期に検出。

Changed
- なし（初期リリース）

Deprecated
- なし

Removed
- なし

Notes / 実装上の重要ポイント（README に追記推奨）
- 環境変数の自動ロードはデフォルトで有効。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかに設定する必要がある。無効値は起動時に例外となる。
- Paper Trading と Live は DB を分離：paper_trading では paper_sqlite_path（デフォルト data/paper_trading.db）を使用するため、本番データと完全に分離可能。
- ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト ("INFO")。
- run_monitoring は MONITOR_POLL_INTERVAL（秒）でポーリング。0 以下・不正な値は 60 秒にフォールバック。
- position_sizing の aggregate スケーリングは lot_size（単元）単位での丸めや残余キャッシュを加味した再配分を行うため、出力株数は常に lot_size の倍数となる。
- risk_adjustment.apply_sector_cap は sector_map にない銘柄を "unknown" 扱いとしてセクター上限の適用対象外とする（注: price の欠損があると過少評価につながる可能性があるため TODO を残している）。

----------------------------------------------------------------------
変更履歴の編集・追記について
- 実際のリリース日やバージョン番号、詳細な修正履歴はリポジトリのコミットログ・リリースノートを参照して正確に更新してください。
- 本ファイルはコードベースからの推測に基づいて生成しているため、実際の変更履歴と差異がある可能性があります。