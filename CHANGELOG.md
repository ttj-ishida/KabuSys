# KEEP A CHANGELOG — KabuSys

すべての変更は「Keep a Changelog」形式に準拠して記載します。  
日付は本コードベース解析時点（2026-04-19）を採用しています。変更内容はソースコードから推測して記載しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ関連

## [Unreleased]
- 進行中 / 今後対応予定の事項（ソース内コメント・TODOに基づく）
  - research/factor_research.py のモメンタム計算関数の実装が途中（ファイル末尾が途切れているため完全実装が必要）。
  - portfolio/risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合のフォールバック（前日終値や取得原価の利用など）を検討する旨の TODO が存在。実装強化が必要。
  - position_sizing の将来的拡張: 銘柄別の lot_size 対応（stocks マスタを用いた拡張）。
  - 全体: 詳細な単体テストの追加（現状のコードからテストの有無は不明）。
  - ドキュメント補強: PortfolioConstruction.md / StrategyModel.md 等の参照に基づく実装だが、これらドキュメントがリポジトリ内にない場合は追加が望ましい。

---

## [0.1.0] - 2026-04-19

### Added
- 基本パッケージ情報
  - パッケージバージョンを定義: `kabusys.__version__ = "0.1.0"`。

- 設定管理
  - 環境変数/`.env` 読み込みモジュールを追加（`src/kabusys/config.py`）。
    - .env 自動読み込み（プロジェクトルートの判定は .git または pyproject.toml に基づく）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能。
    - 値の強制取得用 `_require()`、環境判定（development / paper_trading / live）および各種設定プロパティを提供。
    - `PAPER_FILL_MODE` の検証（有効値: instant|partial|never|reject）やデフォルトパス（DuckDB / SQLite / Paper Trading DB）を管理。

- 環境設定ウィザード
  - 対話式 `.env` 生成/更新ツール（`src/kabusys/config_setup.py`）。
    - 各種設定項目のプロンプト、既存 .env 読み込み、保存機能を実装。
    - `.env` 書き出しテンプレートを提供。

- 設定検証 CLI
  - `.env` と config/*.yaml を起動前に検証するツール（`src/kabusys/validate_config.py`）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスと config ファイルの存在・パース検証。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- 起動スクリプト
  - 実行エンジン起動スクリプト（`src/kabusys/run_execution.py`）。
    - `KABUSYS_ENV=paper_trading` の場合は Paper Trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用して本番DBと分離。
    - プロセス優先度を強制的に "high" に設定（`set_process_priority` を呼び出し）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine 起動（別スレッド）。
    - 停止フラグ（data/stop_requested.flag）を監視して安全に停止する仕組み。

  - 監視（Monitoring）起動スクリプト（`src/kabusys/run_monitoring.py`）。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番の sqlite_path（`data/monitoring.db`）を使用する仕様。
    - SystemMonitor を用いた単発チェック（check_once）のポーリングループ実装。停止フラグでループ終了。

- 監視 DB 初期化
  - 監視関連の DB 初期化ユーティリティ（`monitoring.monitoring_db.init_monitoring_db` を呼び出し、冪等に監視テーブルを確保）。

- ログ／プロセスユーティリティ
  - ロギング初期化ユーティリティ（`src/kabusys/utils/logging_setup.py`）。
    - StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - LOG_DIR 作成失敗時はファイルハンドラをスキップして stdout のみで継続。
    - ログレベルの解決順や既存ハンドラの安全なクリーンナップを実装。

  - プロセス優先度・CPU affinity ユーティリティ（`src/kabusys/utils/process_priority.py`）。
    - Windows / POSIX 両対応でプロセス優先度の設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - 権限不足や未対応 OS の場合は警告を出してスキップする堅牢化。

- ポートフォリオ構築モジュール
  - 銘柄選定・重み計算（`src/kabusys/portfolio/portfolio_builder.py`）
    - select_candidates: スコア降順で上位 N を選択（同点は signal_rank で tiebreak）。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重（全スコアが 0 の場合は等分配にフォールバックして警告）。

  - セクター集中制限・レジーム乗数（`src/kabusys/portfolio/risk_adjustment.py`）
    - apply_sector_cap: 既存保有のセクター別比率が閾値を超える場合、新規候補を除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた投下資金乗数（1.0 / 0.7 / 0.3）を提供。未知のレジームは 1.0 にフォールバックして警告。

  - 株数決定・リスク制限（`src/kabusys/portfolio/position_sizing.py`）
    - allocation_method に応じた発注株数計算（risk_based / equal / score）。
    - risk_based: 許容リスク率・損切り率からベース株数を算出、単元株（lot_size）丸め。
    - equal/score: 配分重みから per-position および aggregate cap を考慮して株数算出。
    - aggregate cap により現金不足時はスケーリング、残差の大きい順に単元単位で追加配分するアルゴリズムを実装。
    - cost_buffer による手数料/スリッページの保守的見積もり対応。

  - portfolio パッケージのエクスポート整備（`src/kabusys/portfolio/__init__.py`）。

- Paper Trading 検証ツール
  - `src/kabusys/tools/paper_verification_report.py` を追加。
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）からシステム安定性・注文成功率・送信率・レイテンシ等を集計してレポートを出力。
    - P95 計算、期間指定（--from/--to）、閾値による PASS/FAIL 判定（稼働率、成功率、送信率、P95 レイテンシ等）。
    - CLI オプション `--db` で DB パスを上書き可能。

- research/factor_research (骨格)
  - DuckDB 接続を受け取るファクター計算（モメンタム等）用モジュールを追加。定数や設計方針、calc_momentum の骨格を実装（ファイル末尾は未完）。

- DB 統合
  - sqlite3 と duckdb を使った運用基盤（監視用/分析用 DB）の統合を実装。

### Changed
- 既存ツールの動作方針（設計として決定）
  - 監視プロセスは KABUSYS_ENV に依存せず常に本番監視 DB（sqlite_path）を使用する方針を明記。
  - run_execution は paper_trading の場合 DB を分離（paper_sqlite_path）して安全に動作。

### Fixed
- （明示的なバグ修正履歴は不明。ソース中で入力値検証やエラーハンドリングを追加して堅牢化している箇所があるため、初期リリースとして安定性の向上を含む。）

### Deprecated
- なし（初期リリース）

### Removed
- なし

### Security
- 環境変数の必須チェック機能（J-Quants / kabu API など）を提供。`.env` の取り扱いや自動ロードは注意喚起付きで実装（.env を絶対に Git にコミットしない旨のコメントを出力する等）。

---

注記（既知の制約・注意点）
- 一部モジュールに TODO / 注意書きが存在（価格欠損フォールバック、factor_research の未完等）。本番運用前にこれらの点を確認・実装することを推奨します。
- 一部の操作（プロセス優先度設定や CPU affinity）は権限やプラットフォーム依存で失敗する可能性があり、その場合は警告ログを出してスキップする実装になっています。
- `.env` 自動読み込みはプロジェクトルートが検出できない場合はスキップされます。テストや CI で自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

もしこの CHANGELOG をベースにリリースノートや追加の詳細（例: 影響範囲、アップグレード手順、デプロイ手順）を作成したい場合は、どの情報を優先するか教えてください。