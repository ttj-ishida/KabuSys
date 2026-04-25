# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

注意: 日付はコードベース解析時点（このCHANGELOG作成日）を用いています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-25
初回リリース — 日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加点は以下のとおりです。

### Added
- 全般
  - パッケージ初期版を追加。バージョンは `kabusys.__version__ = "0.1.0"`。
  - プロジェクトルート自動検出機能を追加 (.git または pyproject.toml を起点に探索)。これにより .env 自動読み込みが CWD に依存せず動作します。

- 設定管理
  - Settings クラスを実装。環境変数から各種設定（DB パス、API トークン、環境種別、閾値など）を取得・検証するプロパティ群を提供。
  - .env 自動ロード実装:
    - 読み込み順: OS 環境変数 > .env.local > .env
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パース機能強化:
    - export キーワード対応、シングル/ダブルクォート内のエスケープ対応、インラインコメントの扱いなどを実装。
  - PAPER_TRADING 用設定（`PAPER_TRADING_SQLITE_PATH`, `PAPER_FILL_MODE` など）をサポート。`PAPER_FILL_MODE` の有効値検証を実装。

- CLI / ユーティリティ
  - 環境設定ウィザード `kabusys.config_setup` を追加:
    - 対話式で .env の初期作成・更新を支援。必須/任意項目やデフォルトを提示し、保存前に内容確認できる。
  - 設定検証ツール `kabusys.validate_config` を追加:
    - 必須環境変数チェック、KABUSYS_ENV 検証、ログレベル検証、DB パス親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML があれば）パース検証、本番環境時の追加ガード（LINE 通知設定、Kill Switch 関連）を実施。
    - `--strict` オプションで警告も失敗扱いにできる。

- ロギング / プロセス管理
  - `kabusys.utils.logging_setup.setup_logging` を追加:
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）を組み合わせた統一的ロギング設定。
    - ログレベル/ログディレクトリ解決ルールを実装（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力を省略して stdout のみで継続。
  - `kabusys.utils.process_priority` を追加:
    - Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定するユーティリティ。
    - CPU affinity 設定機能も実装（指定が None の場合は未設定）。
    - 権限不足や非対応 OS の場合は安全にスキップしログ警告を出力。

- 実行スクリプト / エンジン
  - `run_execution.py` を追加:
    - ExecutionEngine の起動スクリプト。起動時にプロセス優先度を高く設定し、SQLite / DuckDB に接続。
    - KABUSYS_ENV=paper_trading の場合は専用（分離された）paper_trading DB を使用する挙動を想定（MockBrokerClient に対応するファクトリ経由でブローカークライアントを生成）。
    - ExecutionEngine を別スレッドで実行し、データディレクトリの停止フラグ（data/stop_requested.flag）を監視して安全に停止する仕組みを実装。
    - PID ファイル管理と monitoring テーブルの初期化を行う。
  - `run_monitoring.py` を追加:
    - SystemMonitor のポーリングループ起動スクリプト。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は実行環境にかかわらず本番の sqlite_path を使用する設計。
    - 停止フラグ検知で安全にループを抜け、DB 接続をクローズする。

- 監視 / モニタリング関連
  - monitoring DB 初期化インターフェース（init_monitoring_db）と SystemMonitor の呼び出しポイントを追加（スクリプト側で初期化を保証する形）。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - シグナル選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコアが全て 0 の場合は等分配へフォールバックして警告を出力。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限 (apply_sector_cap) とレジーム乗数 (calc_regime_multiplier) を実装。セクター不明銘柄は上限適用外。未知のレジームはフォールバック動作を採る。
  - `kabusys.portfolio.position_sizing`:
    - position sizing ロジックを実装（risk_based / equal / score の配分方式対応）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金超過時のスケーリングと端数処理）をサポート。手数料・スリッページを見込む cost_buffer も考慮。

- リサーチ / ファクター計算（骨格）
  - `kabusys.research.factor_research` を追加（モメンタム等のファクター計算を意図した実装）。DuckDB 接続を受け取り prices_daily / raw_financials を使ってファクターを計算する設計。モメンタム計算（calc_momentum）の骨格と定数群を実装（実装の一部は継続中／ファイル末尾が解析時に途中で切れています）。

- ペーパートレード検証ツール
  - `kabusys.tools.paper_verification_report` を追加:
    - paper_trading SQLite DB を読み、システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）などの指標を算出して報告する CLI スクリプト。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を設定し、PASS/FAIL 判定を出力。
    - 日付フィルタ（--from / --to）や DB パス指定 (--db) に対応。

### Changed
- なし（初期リリースのため新規追加のみ）

### Fixed
- なし（初期リリース）

### Security
- .env ファイルの自動ロードにおいて OS 側の環境変数をプロテクトする仕組みを導入（読み込み時に既存の OS 環境変数を上書きしない / 上書き許可オプションあり）。  
- .env は Git に絶対コミットしない旨を config_setup で明示。

### Notes / Migration
- 本版を使う際の注意事項:
  - 必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は .env または環境変数で設定してください。`kabusys.validate_config` で起動前検証を行うことを推奨します。
  - 本番運用（KABUSYS_ENV=live）では Kill Switch 等の設定・LINE 通知設定を必ず確認してください。
  - paper_trading 環境は本番 DB と完全に分離されるよう設計されています（paper 用 SQLite を使用）。

---

（以降のバージョン履歴はこのファイルに追加していきます）