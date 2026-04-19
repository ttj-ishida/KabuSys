# Changelog

すべての注目すべき変更はこのファイルに記録します。
形式は「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

- リリースノートの命名規則: YYYY-MM-DD はリリース日
- 変更カテゴリ: Added, Changed, Fixed, Removed, Deprecated, Security

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading SQLite DB を使用して本番 DB と分離（デフォルト: data/paper_trading.db）。
    - ブローカークライアントの生成を BrokerClientFactory に委譲。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み合わせて ExecutionEngine を起動するワークフローを実装。
    - 停止フラグ (data/stop_requested.flag) を監視して安全にシャットダウン可能。
    - エンジンの PID を data/execution.pid に記録する仕組みを想定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用エントリポイントを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV に関わらず本番の sqlite_path を使用して監視データを保存。
    - 停止フラグ (data/stop_requested.flag) を検知してループを終了。
    - 例外発生時はログを残して次のポーリングまで待機。

- 設定・環境管理
  - config.py
    - .env ファイルと OS 環境変数からの設定読み込みを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）。
    - .env のパースは export 形式、シングル/ダブルクォート、エスケープ、インラインコメント（スペース直前の # をコメント扱い）に対応。
    - 自動ロード順序: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - Settings クラスで各環境変数の取得ラッパーを提供（例: duckdb/sqlite パス、paper_trading 用設定、監視閾値など）。
    - PAPER_FILL_MODE の検証および KABUSYS_ENV, LOG_LEVEL の検証を実装。
  - config_setup.py
    - .env を対話式に生成/更新するウィザードを実装。
    - 必須/任意項目、シークレット入力、選択肢、デフォルト値のサポート。
    - 生成した .env を上書き保存する機能を提供（保存時に確認プロンプトあり）。
  - validate_config.py
    - 起動前に設定不備を検出する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在とパース（PyYAML があれば内容検証）を実施。
    - --strict オプションで警告を FAIL 扱いにできる。

- ユーティリティ
  - utils/logging_setup.py
    - 全スクリプト共通のログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を備えたファイル出力（logs/<app_name>.log）を設定。
    - ログディレクトリ自動作成、既存ハンドラのクリーンアップ、環境変数 LOG_LEVEL / LOG_DIR による上書き対応。
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）および CPU affinity 設定のユーティリティを追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収し、psutil 経由で優先度や affinity を設定。設定失敗時は警告を出してスキップ。
    - set_process_priority() は run_* スクリプトで起動時に呼び出される設計。
  - utils/__init__.py（パッケージ化）

- ポートフォリオ構築（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコア合計が 0 の場合のフォールバックログ出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装（既存保有と当日売却予定銘柄を考慮）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear）を実装。
  - portfolio/position_sizing.py
    - 株数計算ロジックを実装（allocation_method: risk_based / equal / score）。
    - lot_size 単位丸め、1 銘柄上限、aggregate cap によるスケーリング、cost_buffer（手数料・スリッページ保守見積り）対応。
    - リスクベースの position sizing（risk_pct, stop_loss_pct）を実装。

- 研究・分析関連
  - research/factor_research.py（下地実装）
    - モメンタム・ボラティリティ等のファクター計算モジュールの下地を追加。
    - DuckDB 接続を受けて prices_daily / raw_financials テーブルを参照する設計。
    - 各種定数（MA200、ATR 期間、スキャン日数等）と calc_momentum の骨組みを含む（詳細実装継続の余地あり）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用検証レポート生成スクリプトを追加。
    - 日付フィルタ、DB パス指定（--db または PAPER_TRADING_SQLITE_PATH 環境変数）、システム稼働率・注文成功率・送信率・レイテンシ（P95）等を集計して判定（PASS/FAIL）を出力。
    - デフォルト基準値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。

- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" に設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

---

補足:
- 多くのモジュールは「DB 参照なし（純粋関数）」または「DuckDB / SQLite を使った分析・監視」の設計方針で分離されています。
- .env の自動ロードや設定検証ツールにより、ローカル開発・ペーパートレード・本番環境の運用を想定した安全ガードを備えています。
- 今後の開発予定としては、factor_research の完全実装、ExecutionEngine / SystemMonitor の詳細実装・テスト強化、Paper Trading の検証拡充が想定されます。