CHANGELOG
=========
すべての注目すべき変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-19
-----------------

Added
- 初回リリース: KabuSys 基本コンポーネントを多数追加。
- CLI / 起動スクリプト
  - run_monitoring.py: SystemMonitor をポーリングで実行するループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト内 data/stop_requested.flag によるフラグ検知で行う。
    - Monitoring は環境 (KABUSYS_ENV) にかかわらず Settings.sqlite_path（本番用）を使用。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading では専用の paper_trading DB を使用し MockBrokerClient を使うことで本番 DB と分離。
    - 停止フラグ / PID ファイル管理、スレッド管理を実装。
- 環境設定・検証ツール
  - config_setup.py: 対話式 .env ウィザードを追加（.env の初期作成・更新を支援）。
    - 秘匿値はマスク表示、保存前に確認プロンプトを表示。
    - .env ファイルに注記（Git にコミットしないよう注意喚起）を付加して保存。
  - validate_config.py: 起動前の設定検証 CLI を追加（必須環境変数・パス・YAML の有無・本番向けガード等をチェック）。
    - --strict モードをサポート（警告を FAIL として扱う）。
- 設定管理
  - config.py: Settings クラスによる環境変数/設定の集中管理を追加。
    - .env 自動ロード機能: プロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を読み込む。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパース改善: export プレフィックス対応、クォート付き値のエスケープ処理、インラインコメント処理などに対応。
    - 多数のプロパティを提供（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / DB パス / PAPER_FILL_MODE / PID/kill flag 関連 / CPU/MEM/DISK 閾値 / 環境判定プロパティ等）。
    - 環境値のバリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の有効値チェック）。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的ログ設定ユーティリティを追加。
    - stdout に StreamHandler を出力（cron 等でのリダイレクトを考慮）、日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を追加。ログディレクトリ作成に失敗した場合はファイル出力をスキップして継続。
    - ログレベル・ログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX 差分を吸収（psutil を利用）。set_process_priority("high"|"normal"|"low")、set_cpu_affinity を提供。設定に失敗した場合は警告を出してスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選択する関数。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分の計算。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中の上限チェックと候補除外ロジック。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数。
  - portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数を計算する総合関数（risk_based / equal / score をサポート）。lot_size 単位で丸め、aggregate cap によるスケールダウンを実装。手数料やスリッページを考慮する cost_buffer をサポート。
  - portfolio/__init__.py で上記 API をエクスポート。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading DB から各種指標（稼働率・注文成功率・送信率・レイテンシ等）を集計してレポート出力するスクリプトを追加。
    - P95 計算、閾値による PASS/FAIL 判定（デフォルト基準値をソース内に定義）。
    - --from / --to / --db オプションをサポート。
- 研究用モジュール（未完の部分を含む）
  - research/factor_research.py: ファクター計算モジュールの骨格を追加。
    - Momentum / MA / ATR / Liquidity 等の設計方針と定数、calc_momentum の実装開始（prices_daily を使った計算を想定）。（一部実装が途中で切れているため今後拡張予定）
- パッケージメタ情報
  - __init__.py に __version__ = "0.1.0" を設定。

Changed
- （初回リリースのため該当なし）

Fixed
- .env 読み込みに関する堅牢性向上（ファイルが開けない場合に警告を出してスキップ、コメントやクォート処理の改善）。
- logging_setup: 既存ハンドラの二重設定を避けるため既存ハンドラをフラッシュ/クローズしてから再設定する処理を追加。

Security
- config_setup が .env に関する注意書きを出力し、.env を Git にコミットしないよう明示。
- Settings._require() により必須環境変数未設定時は早期にエラーを出す実装を追加。

Notes / Implementation details
- run_execution は paper_trading 環境時に paper_sqlite_path を使用することで本番データと完全分離する設計。risk manager の初期化時に初期ポートフォリオ値として broker.get_available_cash() を参照する点に注意。
- run_monitoring は monitoring 用 DB 初期化（init_monitoring_db）を行い、duckdb を分析用に併用している。Monitoring が本番用 sqlite_path を参照する仕様は意図的（環境ごとの DB 分離は Execution 側で行う）。
- logging_setup は stdout を使う設計（stderr ではない）で、cron / Task Scheduler での扱いを考慮している。
- process_priority の実行は権限が必要になる場合があり、失敗時は警告ログでスキップするため起動は継続される。
- 一部モジュール（monitoring_db、SystemMonitor、ExecutionEngine 等）はこの差分に含まれる他ファイルで利用される前提で実装されている（本 CHANGELOG は提供されたファイル群から推測して作成）。

Developer notes / TODO
- research/factor_research.py の calc_momentum 等の関数が途中で切れているため、ファクター計算の完成・テストが必要。
- position_sizing の price 欠損時のフォールバック（前日終値や取得原価の採用）について注釈が残っている。将来的に stocks マスタで lot_size を持たせる等の拡張を検討。
- apply_sector_cap の "unknown" セクターの扱いは現状で上限適用対象外とする仕様。要運用確認。

----- 

注: 本 CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のリリースノートに併記する際はリポジトリのコミット履歴や担当者の確認を推奨します。