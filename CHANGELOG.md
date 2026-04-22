# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-22
最初の公開スナップショット。自動売買システム KabuSys のコアユーティリティ群、起動スクリプト、ポートフォリオ構築ロジック、検証ツール等を実装しました。

### Added
- 基本バージョン情報を追加
  - `kabusys.__version__ = "0.1.0"` を設定。

- 環境設定・管理
  - .env 自動読み込み機構を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - .env パース機能を実装（コメント行、export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープに対応）。
  - 環境変数保護機能（OS 環境変数を上書きしない）および上書きオプションを実装。
  - Settings クラスを追加し、アプリ用設定（DB パス、API トークン、監視閾値、環境種別 等）をプロパティとして提供。
  - PAPER_FILL_MODE の検証（有効値: "instant", "partial", "never", "reject"）を実装。
  - 環境種別（KABUSYS_ENV）の検証（development / paper_trading / live）を実装。

- 設定関連 CLI
  - 環境設定ウィザード `kabusys.config_setup` を追加。
    - 対話式で .env を生成/更新。機密項目はマスク表示。
  - 設定検証 CLI `kabusys.validate_config` を追加。
    - 必須環境変数やログレベル、DB パス、config/*.yaml の存在・パース（PyYAML があれば）をチェック。
    - --strict オプションで警告をエラー扱いにできる。

- 起動スクリプト
  - 実行エンジン起動スクリプト `run_execution.py` を追加。
    - プロセス優先度を高く設定してから起動。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading SQLite を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理に対応。
  - 監視ループ起動スクリプト `run_monitoring.py` を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。
    - SystemMonitor の単発チェックをポーリング実行、例外はログに捕捉してループを継続。

- ロギング・プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` を追加。
    - stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - プロセス優先度と CPU affinity 設定ユーティリティ `kabusys.utils.process_priority` を追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を考慮した nice/priority 設定。
    - set_process_priority("high" | "normal" | "low") と set_cpu_affinity(N) を提供。失敗時は警告を出してスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - 候補選定・重み算出 (`kabusys.portfolio.portfolio_builder`)
    - select_candidates: スコア降順 + signal_rank の tiebreak。
    - calc_equal_weights, calc_score_weights: 等配分およびスコア加重（スコア合計 0.0 は等配分にフォールバック）。
  - セクター集中制限・レジーム乗数 (`kabusys.portfolio.risk_adjustment`)
    - apply_sector_cap: セクター別既存エクスポージャーが閾値を超える場合に候補を除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数（未知は警告して 1.0 フォールバック）。
  - 株数計算・丸めロジック (`kabusys.portfolio.position_sizing`)
    - calc_position_sizes: risk_based / equal / score の割当方式、単元株（lot_size）丸め、per-position 上限・aggregate cap、cost_buffer を考慮したスケーリングと残差補正ロジック実装。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - ペーパートレード用 SQLite (デフォルト: data/paper_trading.db) から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数）を集計し人間向けレポートを出力。
    - CLI から期間（--from / --to）や DB パスを指定可能。
    - デフォルトの合格基準 (稼働率 >=99%、成立率 >=90%、送信率 >=95%、P95 latency <=200ms) を設定。

- リサーチ（ファクター計算）基盤
  - DuckDB を使うファクター計算モジュール `kabusys.research.factor_research` の基礎実装を追加（モメンタム等の定数・設計方針を含む）。（処理途中で続きがあることがコードから読み取れます）

### Changed
- DB 接続の挙動
  - 監視 (run_monitoring) は環境に関係なく Settings.sqlite_path（本番用パス想定）を使用する設計に固定。
  - 実行エンジン (run_execution) は paper_trading 環境では paper_sqlite_path を優先して使用し、本番 DB と分離するように実装。

- ログ設定の挙動
  - 既存ハンドラがある場合は一度 flush/close してからルートロガーのハンドラをクリアし再設定することで二重出力を防止。

### Fixed
- .env パーサの堅牢化
  - クォートされた値に対するバックスラッシュエスケープ処理を実装し、クォート内のインラインコメントを無視するよう改善。
  - クォート無し値に対しては、'#' の直前がスペース/タブのときのみコメントとして扱うようにして誤削除を回避。

- 起動時の安全措置
  - ExecutionEngine 起動前に停止フラグの存在をチェックして、既に停止フラグが立っている場合は起動を中止するように修正。
  - ポーリングループ、エンジン実行ループともに例外をキャッチしてログに残しつつ継続する実装にして、単回の例外でプロセスが落ちないように改善。

### Security
- 秘密情報取り扱い改善
  - config_setup の表示で機密項目（J-Quants トークンや kabu API パスワード）をマスクして表示するようにし、対話出力での露出を低減。

### Notes / Known limitations
- research.factor_research モジュールは設計方針・定数を備えていますが、ファンクション本体（データ抽出の SQL 等）が途中で終わっている箇所があり、計算ロジックの完成は今後のリリースで予定されています。
- position_sizing における価格欠損（price が 0.0 の場合）の取り扱いは暫定（TODO コメントあり）。将来的にフォールバック価格や株式ごとの単元情報の導入を検討。
- ログディレクトリ作成やプロセス優先度設定は権限に依存するため、権限不足時は警告を出してスキップする動作にしています。

---

（この CHANGELOG は現行のソースコードから推測して作成したものです。実際のコミット履歴とは差分がある可能性があります。）