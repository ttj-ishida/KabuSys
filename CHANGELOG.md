# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
タグ付きリリースがない場合はバージョン番号と日付を仮定しています。コードベースの内容から推測してまとめたため、実際のコミット履歴と差異がある可能性があります。

## [Unreleased]
- ドキュメント化されていない細かな改善やリファクタの可能性あり（コードベースから明示的な未リリース差分は検出できません）。

## [0.1.0] - 2026-04-22
初回公開リリース（コードベースから推測）。

### Added
- 全体
  - パッケージ基盤を追加。パッケージのバージョンは __version__ = "0.1.0" に設定。
  - 共通設定管理モジュール `kabusys.config` を追加。.env 自動読み込み（.env → .env.local の順、OS 環境変数を保護）や必須環境変数チェック機能を提供。
  - 対話式設定ウィザード CLI `kabusys.config_setup` を追加し、.env の初期作成・更新を支援（シークレット入力のマスク、選択肢・デフォルトのサポート、保存確認）。
  - 設定検証 CLI `kabusys.validate_config` を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML インストール時）、
    本番環境用の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START）などをチェック。`--strict` オプションで警告を FAIL 扱いにできる。
  - ログ設定ユーティリティ `kabusys.utils.logging_setup` を追加。stdout 出力の StreamHandler と 日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
    ログディレクトリ自動作成、既存ハンドラのクリーンアップ、環境変数/引数によるログレベル・出力先指定をサポート。
  - プロセス優先度・CPU affinity ユーティリティ `kabusys.utils.process_priority` を追加。Windows / POSIX(Linux/Mac/FreeBSD) を吸収し `set_process_priority` / `set_cpu_affinity` を提供。
    psutil ベースでアクセス拒否や未実装を穏やかに扱う実装。
- 実行・監視
  - 実行エントリ `kabusys.run_execution` を追加。起動時にプロセス優先度を高に設定し、環境に応じて本番 DB と paper_trading 用 DB を分離して接続。
    BrokerClientFactory からブローカークライアントを作成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで起動、停止フラグ検知で安全停止する仕組みを提供。
    Paper Trading (`KABUSYS_ENV=paper_trading`) 時は専用 DB（data/paper_trading.db）に記録して本番と分離する設計。
  - 監視エントリ `kabusys.run_monitoring` を追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    起動時にプロセス優先度を高に設定し、監視用 DB テーブルの初期化を行い SystemMonitor を定期実行。停止フラグファイルでループを終了する仕組みを実装。
- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - シグナルから候補選定 select_candidates（スコア降順、タイブレークに signal_rank）を実装。
    - 等配分 calc_equal_weights、スコア加重 calc_score_weights（全スコアが 0 の場合は等配分にフォールバック）を実装。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限 apply_sector_cap を実装。既存保有を加味して上限超過セクターの新規候補を除外（"unknown" セクターは無視）。
    - 市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear とフォールバック）を実装。
  - `kabusys.portfolio.position_sizing`
    - position sizing ロジックを実装。allocation_method として "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、cost_buffer（手数料・スリッページを考慮）等を実装。
    - スケーリング後に残余キャッシュを fractional 残差の大きい順に lot 単位で再配分するロジックを搭載。
- モニタリング / DB
  - `kabusys.monitoring.monitoring_db`（参照あり）を初期化する仕組みを各エントリから呼び出し、監視テーブルの存在を保証（冪等）。
  - DuckDB 接続を使用するコードパス（分析用ファイル: data/kabusys.duckdb）をサポート。
- ツール
  - `kabusys.tools.paper_verification_report` を追加。Paper Trading の SQLite (data/paper_trading.db) を解析して以下を算出・出力：
    - システム稼働率（uptime）、ポーリング数、エラー数
    - 注文統計（Created / Filled / Sent）から注文成功率・送信率
    - リスク却下数（risk_logs）
    - レイテンシ（avg / max / P95）※P95 は独自実装
    - 閾値（稼働率、成功率、送信率、P95）に基づく PASS/FAIL 判定。
  - CLI オプションで期間指定（--from / --to）や DB パス上書きをサポート。
- 研究（未完/着手）
  - `kabusys.research.factor_research` を追加。DuckDB の prices_daily / raw_financials を参照してモメンタム・バリュー・ボラティリティ等のファクターを計算する方針を実装開始（モメンタム計算関数の雛形が存在）。

### Changed
- .env のパースと自動ロード仕様を整備
  - `_parse_env_line` がクォート値やバックスラッシュエスケープ、"export KEY=val" 形式、インラインコメントの扱い等に対応。
  - _load_env_file にて override/ protected（OS 環境変数保護）オプションを実装し、安全に .env/.env.local をマージする設計。
- ログ出力
  - logging_setup: コンソールは stdout を利用するようにした（stderr ではない）。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
- プロセス優先度
  - Windows と POSIX の差分を吸収する実装。例外時は警告ログでスキップする挙動。

### Fixed
- 実行と監視の起動スクリプトで DB 接続を finally ブロックで確実に閉じるようにしてリソースリークを防止。
- Monitoring モジュール: MONITOR_POLL_INTERVAL に不正な値が設定された場合にデフォルトへフォールバックして time.sleep の ValueError を回避するロジックを追加。

### Notes / Known limitations
- factor_research モジュールは実装途中（ソース末尾が断片的に存在）。完全なファクター計算は未完成の可能性がある。
- position_sizing や apply_sector_cap は価格欠損時の挙動に注記（price が欠損するとエクスポージャーが過少評価される等）。将来的に価格フォールバックの改善が必要。
- `init_monitoring_db`、`SystemMonitor`、`ExecutionEngine`、`BrokerClientFactory` 等の詳細実装は本差分に含まれるファイルからは参照のみ（実体は他ファイルに存在）であるため、実動作の細部はそれら実装に依存する。
- ローカル環境や本番環境での動作には環境変数（特に JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）が必要。`kabusys.validate_config` と `kabusys.config_setup` を活用して導入を推奨。

--- 

（この CHANGELOG はリポジトリ内のソースコードの内容を元に推測して作成しています。実際のコミットログやリリースポリシーに合わせて調整してください。）