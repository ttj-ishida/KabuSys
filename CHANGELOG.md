# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。重要な機能追加・振る舞い・CLI をコードベースから推測してまとめています。

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ初期リリース:
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。
- 設定・環境変数管理:
  - Settings クラスを提供し、アプリケーション全体の設定値を環境変数から取得する機能を追加。
  - 自動 .env ロード機能:
    - プロジェクトルート (.git または pyproject.toml を基準) を探索して自動的に `.env` / `.env.local` を読み込む（環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
    - `.env.local` は OS 環境変数を保護しつつ `.env` より優先して読み込む挙動を実装。
  - .env パーサを実装（クォート、エスケープ、`export KEY=...` 形式、インラインコメント処理に対応）。
- 設定ウィザード CLI:
  - `kabusys.config_setup` に対話式ウィザードを追加。`.env` の初期作成・更新を支援。
  - デフォルト値表示、シークレットマスク、選択肢バリデーション、保存確認などを実装。
- 設定検証 CLI:
  - `kabusys.validate_config` を追加。必須環境変数、KABUSYS_ENV、DB パス、config/*.yaml の存在とパース (PyYAML があれば) をチェック。
  - `--strict` オプションを提供（警告を FAIL 扱いにできる）。
  - 本番環境用の追加ガード（LINE 通知設定の確認や KILL_FLAG_CLEAR_ON_START の警告）を実装。
- 実行系/監視実行スクリプト:
  - `run_execution.py` を追加:
    - ExecutionEngine の起動ロジックを提供。プロセス優先度を最初に「high」に設定。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離する設計。
    - Broker クライアント生成は `BrokerClientFactory` 経由（paper_trading では MockBrokerClient を使う想定）。
    - 停止フラグ（data/stop_requested.flag）を検知して安全に停止する仕組みを実装。
  - `run_monitoring.py` を追加:
    - SystemMonitor のポーリングループ起動スクリプトを提供。プロセス優先度を「high」に設定して起動。
    - 環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）でポーリング間隔を上書き可能。無効値はデフォルトにフォールバックして警告を出す。
    - 監視用の SQLite DB は監視用途に本番 sqlite_path を使用する挙動（環境にかかわらず本番 sqlite_path を使う旨を注記）。
    - 停止フラグを監視してループを終了する実装。
- 監視 DB 初期化ヘルパ:
  - 監視テーブルの存在を保証する init_monitoring_db 呼び出しを run_execution/run_monitoring に統合（冪等に初期化可能）。
- Portfolio モジュール（銘柄選定・配分・ポジション決定・リスク調整）:
  - 銘柄選定: select_candidates（スコア降順、タイブレークに signal_rank を使用）。
  - 重み計算: calc_equal_weights（等金額）、calc_score_weights（スコア正規化、全スコア 0 の場合はフォールバックで等金額にする）。
  - セクター集中制限: apply_sector_cap（既存保有のセクターエクスポージャが閾値を超える場合、新規候補を除外、"unknown" セクターは制限対象外）。
  - レジーム乗数: calc_regime_multiplier（"bull"/"neutral"/"bear" に基づく投下資金乗数、未知はフォールバックで 1.0）。
  - ポジションサイズ計算: calc_position_sizes
    - allocation_method に応じた株数算出（"risk_based", "equal", "score" をサポート）。
    - lot_size（単元株）丸め、per-stock 上限・aggregate cap の算出とスケーリング、cost_buffer による保守的見積りを実装。
    - 価格欠損時のスキップ、ログ出力による説明性を備える。
- リサーチ / ファクター計算:
  - factor_research モジュールを追加。DuckDB 接続を受け、prices_daily / raw_financials を参照してファクター（モメンタム、200 日 MA 乖離、ATR、流動性など）を計算する関数を実装（calc_momentum, calc_volatility 等）。
  - P95 などの集計ロジックをサポート。
- ユーティリティ:
  - process_priority: set_process_priority と set_cpu_affinity を実装。Windows/Linux/macOS 向けに psutil を使って優先度と CPU affinity を設定し、権限不足や未対応 OS の場合は警告を出して安全にフォールバックする。
- ツール:
  - tools.paper_verification_report: ペーパートレード DB を解析してレポートを生成する CLI を追加。稼働率・注文成功率・送信率・レイテンシ（P95）等の指標を算出し PASS/FAIL 判定を行う。DB パスは引数または環境変数で指定可能。

### Changed
- .env 読み込み順序と保護ロジックの仕様化:
  - OS 環境変数を保護キー集合として扱い、`.env.local` の上書きでも OS 環境変数は上書きされないように実装。
- 設定検証の挙動:
  - config/*.yaml の存在チェックは PyYAML の有無により柔軟にスキップするようにし、パーサがあれば中身のパースも行う。
- DB パス関連の表示/警告:
  - validate_config にて DB ファイルの親ディレクトリが存在しない場合に警告を出す（起動時に自動作成される旨コメント）。
- run_monitoring のポーリング間隔の扱い:
  - 環境変数 `MONITOR_POLL_INTERVAL` の不正入力時（非整数・0 以下など）はログで警告し、デフォルト 60 秒にフォールバックする設計。

### Fixed / Robustness improvements
- .env ファイルパーサの堅牢化:
  - クォート中のバックスラッシュエスケープ、`export ` プレフィックス、コメント扱いの細かなルールを実装し、実運用での .env 設定ミスに寛容に。
- プラットフォーム互換性:
  - process_priority/set_cpu_affinity は未対応プラットフォームや権限不足時に安全に警告を出してスキップすることで、起動失敗を防止。
- CLI 停止制御:
  - run_execution/run_monitoring ともに project-level の stop flag（data/stop_requested.flag）を監視し、外部から安全に停止できる仕組みを提供。
- Paper トレード分離:
  - paper_trading 環境では専用 SQLite DB を使うことで本番データと完全に分離されるように配慮。

### Security
- .env の取り扱い注意喚起を config_setup のヘッダーに明示（.env を絶対に Git にコミットしない、など）。

### Known limitations / Notes
- price が欠損（0.0）の場合、apply_sector_cap および calc_position_sizes のエクスポージャ/算出結果が過小評価される旨の TODO コメントが残っています。将来的な価格フォールバック（前日終値や取得原価）対応が検討されています。
- 一部モジュール（BrokerClient 等）はファクトリ/抽象化によって差し替えられる設計になっており、実際のブローカークライアント実装は別モジュールに依存します（paper_trading 用 Mock の存在を想定）。
- DuckDB / PyYAML / psutil 等の外部依存は実行環境にインストールされていることが前提です。足りない場合は一部機能をスキップまたは警告でフォールバックします。

---

今後のリリースでは、テストカバレッジの拡充、価格フォールバックの実装、銘柄別 lot_size 対応、より詳細なモニタリングアラートの追加などが見込まれます。