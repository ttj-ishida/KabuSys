# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

※ このリポジトリの初期リリースを記録しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

### Added
- 初回リリース: KabuSys — 日本株自動売買システム（__version__ = 0.1.0）。
- 実行ランナー
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトの data/stop_requested.flag ファイルで制御。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計。
    - プロセス優先度を起動時に設定（utils.process_priority を使用）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト data/paper_trading.db）に記録して本番 DB と分離。
    - ブローカー・OrderRepository・OrderManager・RiskManager・Reconciler を組み立て、Engine をスレッドで実行。停止フラグ検知で安全に停止。
    - 起動時にプロセス優先度設定を実行。
- 設定管理
  - config.py
    - .env 自動読み込み機能を追加（プロジェクトルートが特定できる場合）。
    - `.env` / `.env.local` の読み込み順と保護（OS 環境変数は上書き防止）を実装。
    - .env 行パーサーは `export KEY=val`、クォート（シングル/ダブル）とバックスラッシュエスケープ、コメント処理に対応。
    - Settings クラスを導入し、各種設定値（DBパス、KABU API、LINE トークン、監視閾値、PAPER_FILL_MODE 等）をプロパティ経由で提供。入力値の基本バリデーションを実装。
- 設定ユーティリティ / CLI
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。シークレット項目はマスクして表示。
  - validate_config.py
    - 起動前チェック CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、DB パスや config/*.yaml の存在（および PyYAML があればパース検証）を行う。
    - `--strict` オプションで警告を失敗扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選定（タイブレークに signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェックで新規候補を除外するロジック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull/neutral/bear のマッピングと未知レジームのフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り、残差を用いたロット追加配分ロジックを実装。
- 研究用ファクター計算
  - research/factor_research.py
    - DuckDB を用いたモメンタム・ボラティリティ・流動性ファクター計算（mom_1m/3m/6m、MA200乖離、ATR20、20日平均売買代金 等）。
    - 欠損データやウィンドウ不足時の None ハンドリングを行う。
- ユーティリティ
  - utils/process_priority.py
    - Windows / POSIX（Linux/Mac 等）に対応したプロセス優先度設定（高/通常/低）と CPU affinity 設定ユーティリティを追加。権限不足等を安全にフォールバック（警告ログ）する。
- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite を解析して検証レポートを生成する CLI を追加（稼働率、注文成功率・送信率、リスク却下数、レイテンシ指標。P95 の計算等）。
    - デフォルト DB パスは環境変数 `PAPER_TRADING_SQLITE_PATH` または data/paper_trading.db。
- データベース / 初期化
  - 監視用 DB 初期化関数（monitoring_db.init_monitoring_db）をランナーで呼び出して監視テーブルの存在を保証（冪等）。
- パッケージ構成
  - pakage の __init__.py にてエクスポートとバージョンを設定。

### Changed
- （なし、初回リリース）

### Fixed
- （なし、初回リリース）

### Removed
- （なし、初回リリース）

### Security
- .env ファイルは絶対に Git にコミットしないことを明記するヘッダを config_setup の出力に含める。

---

## Notes / Known limitations
- apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャーが過少見積りされ得る旨を TODO コメントで記載。将来的にフォールバック価格の導入を想定。
- position_sizing:
  - 銘柄別の lot_size をサポートしていない（将来的な拡張 TODO）。
  - aggregation スケーリングの再現性を確保するためソート順や安定性に配慮しているが、端数処理の扱いに注意が必要。
- process_priority / set_cpu_affinity:
  - 一部プラットフォームや権限によっては設定に失敗し、警告を出してスキップする仕様。
- 設定自動読み込み:
  - プロジェクトルート（.git または pyproject.toml）を探索できない場合は自動ロードをスキップする。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
- calc_score_weights / calc_regime_multiplier:
  - スコア合計が 0 の場合や未知レジーム時にフォールバック動作を行い、警告ログを出す。
- run_monitoring:
  - 監視は意図的に本番 sqlite_path を使用する設計（環境に依存しない監視データの一元化）。
- tools/paper_verification_report:
  - 対象のテーブルが存在しない場合は N/A 表示やデフォルト値を返す。Pyスクリプトは SQLite スキーマの存在を前提としている。

---

参考: 各モジュール内のドキュメント文字列とコードコメントに基づいて変更点を記載しています。実際の動作詳細や追加のパラメータ調整はソースコード内の docstring / TODO コメントを参照してください。