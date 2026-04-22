# CHANGELOG

すべての変更は Keep a Changelog のガイドラインに従って記述しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（現時点のディレクトリ状態では未リリースの差分はありません）

## [0.1.0] - 2026-04-22
初回リリース。主要機能、ユーティリティ、CLI、アルゴリズム実装の初期バージョンを追加。

### Added
- 実行エントリ／デーモン
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル data/stop_requested.flag を監視して安全にループを終了。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用する旨を明記。
    - duckdb と sqlite3 の接続初期化を行い、init_monitoring_db を呼び出す。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient（BrokerClientFactory 経由）を使用し、paper_trading 用 DB（data/paper_trading.db）に記録して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）と pid ファイル（data/execution.pid）による起動/停止制御を実装。
    - ExecutionEngine を別スレッドで起動し、安全に停止する制御ループを実装。

- 環境設定・検証
  - config.py: 環境変数読み込み・管理用 Settings クラスを追加。
    - .env 自動ロード機能（プロジェクトルート(.git または pyproject.toml)が見つかる場合）。
    - 複雑な .env パースを実装（export プレフィックス、クォートとエスケープ、インラインコメント処理など）。
    - 多数の設定プロパティを提供（J-Quants・kabu API・DB パス・監視閾値・env/log レベル判定 等）。
    - PAPER_FILL_MODE のバリデーション、paper_sqlite_path、KILL_FLAG_CLEAR_ON_START 等をサポート。
  - config_setup.py: 対話式 .env ウィザードを追加。
    - 初期 .env 作成・既存 .env の更新を対話形式で支援。
    - 秘匿項目はマスク表示、保存前に内容確認を実施。
  - validate_config.py: 起動前チェック用 CLI を追加。
    - 必須環境変数の有無、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ存在チェック、config/*.yaml の存在と (PyYAML があれば) パース検証を実行。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: シグナルのソートと上位 N 抜粋。
    - calc_equal_weights, calc_score_weights: 等金額・スコア加重配分を実装。全スコアが 0 の場合は等金額にフォールバック。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限ロジック（既存保有を踏まえ新規候補をフィルタ）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を実装（未知レジームは 1.0 へフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数決定、単元株丸め、per-position および aggregate cap の調整、cost_buffer を考慮したスケーリングロジックを実装。

- ユーティリティ
  - utils/logging_setup.py:
    - 統一的なロギング設定関数 setup_logging を追加。
    - stdout への StreamHandler と、日次ローテーション（TimedRotatingFileHandler）でのファイル出力（logs/<app_name>.log）を提供。
    - ログディレクトリ作成失敗時にはファイル出力をスキップしてコンソール出力のみで継続するフェールセーフ。
  - utils/process_priority.py:
    - set_process_priority: Windows/Linux(Mac/FreeBSD など) を吸収してプロセス優先度を設定するユーティリティを追加。
    - set_cpu_affinity: プロセスの CPU affinity を最初の N コアにピン留めする機能を追加（権限不足や未対応環境では警告ログ）。
    - 設定失敗時は例外を投げず警告でスキップする安全設計。

- ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite データベースから検証レポートを生成する CLI を追加。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを計算し PASS/FAIL を判定する閾値を定義（例: uptime >= 99%、fill_rate >= 90%、P95 <= 200 ms）。
    - 日付範囲フィルタ、P95 計算、各種データ欠損時の graceful handling を実装。

- リサーチ（骨格）
  - research/factor_research.py:
    - ファクター計算モジュールの基礎（モメンタム/MA/ATR/出来高などの設計）を追加。DuckDB 接続を受け prices_daily / raw_financials を参照する方針で実装を開始（calc_momentum の実装開始が見られるがファイル末尾は途中まで）。

- パッケージメタデータ
  - __init__.py にバージョン __version__ = "0.1.0" を設定。

### Changed
- （初回リリースのため変更履歴はなし）

### Fixed
- .env パーサの堅牢性向上:
  - export プレフィックス対応、クォート内エスケープ、インラインコメントの取り扱い、空行・コメント行のスキップ等に対応して既存の .env 処理で誤動作しにくくした。
- ログ出力の堅牢化:
  - ログディレクトリが作成できない環境でもコンソールログが機能するようフォールバック処理を追加。
- プロセス優先度設定の互換性考慮:
  - Windows と POSIX 系で定数や nice 値の存在差を吸収し、呼び出し元がプラットフォームを意識しないようにした。権限不足等で失敗しても警告ログに留める。

### Security
- 特にセキュリティ修正はありませんが、シークレット項目の扱い（config_setup のマスク表示、.env の Git へのコミット禁止の注記）を明示しています。

### Notes / Known limitations
- research/factor_research.py は初期実装（calc_momentum 等）を含みますが、ファイル末尾は未完であり追加実装・テストが必要です。
- run_monitoring は「監視は環境にかかわらず本番 sqlite_path を使用する」と明示しています。意図的な設計だが、開発用途では設定に注意してください。
- set_process_priority / set_cpu_affinity は OS 権限によって動作しない（AccessDenied）場合があります。この場合は警告を出して続行します。
- PAPER_FILL_MODE の値は厳格に検証され、不正値では ValueError が発生します。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に探索します。配布後や特殊なディレクトリ構成では自動ロードがスキップされる場合があります（その場合は環境変数を直接設定してください）。

---

開発/運用での次の TODO（推奨）
- factor_research の完全実装と単体テストの追加。
- ExecutionEngine / SystemMonitor 周辺の統合テスト（paper_trading と live の挙動確認）。
- 単体テスト・CI を整備して env パーサや position_sizing 等の数学的ロジックの回帰を防止。
- 単元株数（lot_size）を銘柄別に管理するためのマスタ管理（stocks マスタ導入）の検討。

---- 
（この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴がある場合は差分に基づいて調整してください。）