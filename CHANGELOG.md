# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。日付はリリース日を示します。

最新: Unreleased

## [Unreleased]

- ドキュメント注記・TODO:
  - position_sizing.calc_position_sizes の価格欠損時のフォールバック（前日終値や取得原価など）を将来的に追加する旨の TODO。
  - factor_research モジュールの実装続き（ファイル末尾が途中で切れていることの示唆）。

---

## [0.1.0] - 2026-04-19

初回リリース。以下の主要機能を含みます。

### Added
- 全体
  - パッケージ初期バージョンを導入（kabusys v0.1.0）。
  - モジュール構成を整備: data/、strategy/、execution/、monitoring/ 等を想定したパッケージ構造。

- 起動スクリプト / 実行管理
  - run_execution.py：ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite(DB) を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成、OrderRepository、OrderManager、RiskManager、Reconciler を組み立て ExecutionEngine を実行。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による起動/停止制御。
    - スレッドで engine.run_session を実行し、停止時は engine.stop を呼び出して安全に停止。
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ検知でループ終了。check_once() の例外はログ出力して継続。

- 設定・環境
  - config.py：環境変数 / 設定管理モジュールを追加。
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
    - 複数の設定プロパティを提供（J-Quants、kabu API、LINE、DuckDB/SQLite パス、paper trading 設定、監視閾値、ログ設定等）。
    - PAPER_FILL_MODE のバリデーション、KABUSYS_ENV / LOG_LEVEL の検証関数を実装。
  - config_setup.py：対話式 .env ウィザードを追加。
    - .env の読み込み・既存値の再利用、シークレットマスク表示、.env の書き出しテンプレート。
    - 起動後に validate_config の実行を推奨するメッセージ出力。
  - validate_config.py：設定検証 CLI を追加。
    - 必須/任意環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリチェック。
    - config/*.yaml の存在確認と PyYAML が存在する場合はパース検証。
    - KABUSYS_ENV=live の際の追加注意（LINE 通知設定や kill flag の自動クリア設定の警告）。
    - --strict オプションで警告をエラー扱いにする機能。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py：一貫したログ設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と 日次ローテートの TimedRotatingFileHandler をルートロガーに設定。
    - ログレベル・ログディレクトリ解決の優先順位と、ディレクトリ作成失敗時のフォールバック（コンソールのみ）を実装。
  - utils/process_priority.py：プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX の差分吸収。psutil を使用して優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアにピン留めする関数を追加。
    - 権限エラー等は警告を出して安全にスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py：
    - select_candidates：BUY シグナルのスコア順選定（タイブレークに signal_rank）。
    - calc_equal_weights：等金額配分。
    - calc_score_weights：スコア比率配分（スコア合計が 0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py：
    - apply_sector_cap：セクター集中上限をチェックして候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier：市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは警告して 1.0 でフォールバック。
  - portfolio/position_sizing.py：
    - calc_position_sizes：weight / candidates / risk ベース等の複数方式に対応した株数決定ロジック。
    - 単元（lot_size）丸め、per-position/aggregate キャップ、cost_buffer を考慮したスケールダウンロジックを実装。

- データ分析 / リサーチ
  - research/factor_research.py（部分実装）：DuckDB 接続を受けてモメンタム等のファクターを計算する設計を追加。
    - モメンタム（1M/3M/6M）、MA200 乖離、ATR、出来高ベースの流動性等を想定。
    - 関数 calc_momentum の開始実装（ファイル末尾が途中で切れている）。

- Paper Trading 向けツール
  - tools/paper_verification_report.py：ペーパートレード検証レポート生成スクリプトを追加。
    - SQLite （デフォルト data/paper_trading.db）からシステム安定性、注文成功率、送信率、リスク却下数、API レイテンシ（平均・最大・P95）を集計してレポート化。
    - デフォルト基準値（稼働率 99%、注文成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づき PASS/FAIL を判定。
    - --from / --to / --db オプションをサポート。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Implementation details
- 停止制御:
  - 複数のスクリプトでプロジェクトルート下の data/stop_requested.flag を監視して安全に終了する仕組みを採用。
- DB の扱い:
  - 監視機能は環境にかかわらず本番 sqlite_path を使用し、run_execution は paper_trading 環境で DB を分離することでテストと本番の混同を避ける設計。
- ログ:
  - ログは stdout とファイルの両方へ出力。ログディレクトリ作成失敗時はファイル出力を安全にスキップして stdout のみで継続。
- 標準ライブラリ外依存:
  - psutil（プロセス設定）および（任意）PyYAML（config 検証）を利用するが、PyYAML がない場合は YAML 検証をスキップして警告を出す。

---

開発・運用上の注意点や TODO はソース内コメントに記載済みです（例: 価格欠損時のフォールバック、factor_research の未完部分など）。必要であればリリースノートをより詳細に分割して作成します。