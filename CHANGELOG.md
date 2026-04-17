# Changelog

すべての非互換性のある変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

なお以下の内容はコードベースから推測して記載しています（実装コメント・定数名・CLI ヘルプ等を参照）。

## [Unreleased]

## [0.1.0] - 2026-04-17

### Added
- 全体
  - 初期リリースを公開。パッケージメタ情報として `__version__ = "0.1.0"` を設定。
- 設定・環境読み込み
  - 環境変数/`.env` 管理モジュールを追加（kabusys.config）。
    - プロジェクトルートを `.git` または `pyproject.toml` から検出して `.env` / `.env.local` を自動読み込み（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
    - 必須環境変数取得ヘルパー `_require()` を提供。
    - 各種設定プロパティを提供（J-Quants トークン、kabu API、DuckDB/SQLite パス、Paper Trading 関連、監視しきい値、ログレベル、環境判定など）。
    - `PAPER_FILL_MODE`（paper trading のモック約定モード）を導入（`instant`, `partial`, `never`, `reject` を受け入れ、無効値は例外）。
- CLI ツール
  - 設定ウィザード CLI（kabusys.config_setup）を追加。
    - 対話式で `.env` を作成/更新するウィザード。シークレット入力のマスク表示やデフォルト値サポートあり。
    - `--env-file` オプションで保存先を指定可能。
  - 設定検証 CLI（kabusys.validate_config）を追加。
    - `.env` と `config/*.yaml` の存在・基本整合性チェックを実行。`--strict` モードで警告も失敗扱いに。
    - 必須環境変数の未設定やプレースホルダ検出、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML がない場合はスキップ）等を実施。
  - Paper Trading 検証レポートツール（kabusys.tools.paper_verification_report）を追加。
    - Paper Trading 用 SQLite（デフォルト `data/paper_trading.db`）から稼働率・注文成功率・送信率・レイテンシ等を集計し、PASS/FAIL 判定を出力。
    - CLI にて期間フィルタ `--from` / `--to`、および DB パス `--db` を指定可能。
    - デフォルトの合格基準（稼働率99%、注文成功率90%、送信率95%、P95レイテンシ <=200ms）を定義。
- 実行・監視プロセス起動スクリプト
  - Execution エンジン起動スクリプト（kabusys.run_execution）を追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を利用し、Paper Trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH` またはデフォルト `data/paper_trading.db`）に完全に分離して記録。
    - プロセス優先度を起動時に設定（`set_process_priority("high")`）。
    - 停止フラグファイル（`data/stop_requested.flag`）検出による安全停止、PID ファイル出力をサポート。
    - RiskManager / Reconciler / OrderManager 等の組み立てロジックを含む実行エンジン起動フローを実装。
  - SystemMonitor ポーリング起動スクリプト（kabusys.run_monitoring）を追加。
    - デフォルトポーリング間隔は 60 秒。`MONITOR_POLL_INTERVAL` 環境変数で上書き可能（不正値はデフォルトにフォールバック）。
    - 監視（monitoring）は環境に関係なく本番用の `sqlite_path` を使用して状態を記録。
    - 停止フラグ検出でループを抜ける実装、予期せぬエラーはログに例外として残し次回まで待機。
- データベース / 分析
  - DuckDB を分析バックエンドとして統合（`Settings.duckdb_path` を経由して接続）。
  - 監視テーブル初期化ユーティリティ `init_monitoring_db` を導入（冪等に監視テーブルを準備）。
- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み計算（kabusys.portfolio.portfolio_builder）
    - `select_candidates()`：スコア降順＋タイブレークで上位 N を選択。
    - `calc_equal_weights()`：等金額配分。
    - `calc_score_weights()`：スコア比率で配分。全スコアが 0 の場合は等配分にフォールバックして警告。
  - セクター制限・レジーム乗数（kabusys.portfolio.risk_adjustment）
    - `apply_sector_cap()`：既存保有のセクター比率が上限を超える場合に新規候補を除外（unknown セクターは除外対象外）。
    - `calc_regime_multiplier()`：市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未定義はフォールバック 1.0）。
  - 株数決定・リスク制限・単元丸め（kabusys.portfolio.position_sizing）
    - `calc_position_sizes()`：`risk_based` / `equal` / `score` の配分方式に対応。ロット（lot_size）単位で丸め、max position / aggregate cap / cost_buffer を考慮してスケールダウン実施。スケール時は端数を大きい順に lot 単位で再配分するアルゴリズムを実装。
- 研究モジュール（DuckDB ベース）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム、ボラティリティ等のファクター群を DuckDB クエリで計算する関数を実装（例: `calc_momentum`, `calc_volatility`）。
    - 各関数は prices_daily / raw_financials テーブルのみを参照し、(date, code) キーの dict を返す設計。
- ユーティリティ
  - プロセス優先度 / CPU affinity ユーティリティ（kabusys.utils.process_priority）を追加。
    - `set_process_priority(level)` で Windows / POSIX の差分を吸収して優先度を設定（失敗時は警告ログ）。
    - `set_cpu_affinity(cpu_count)` により最初の N コアにプロセスをピン留め可能（未対応 OS や権限不足時は警告でスキップ）。

### Changed
- （初回公開のため、後方互換性を壊すような変更履歴はなし。実装設計上の注意点をドキュメントに反映）
  - 設定検証の出力形式やメッセージは日本語で分かりやすく表示するよう整備。
  - `.env` 読み込みルールを明確化（OS 環境 > .env.local > .env、既存 OS 環境の保護）。

### Fixed
- 実行 / 監視周りの堅牢性向上
  - ポーリングループ中の例外をキャッチしてログに残し、ループが停止しないようにした（監視プロセス）。
  - ExecutionEngine 起動時に停止フラグが既に立っている場合は起動を中止する安全措置を追加。

### Documentation
- 各モジュールに docstring と CLI ヘルプを追加。使い方や設計上の注意（例: レジーム乗数の挙動、price 欠損時の注意点、.env を絶対に Git にコミットしない旨）を明文化。

### Notes / Known limitations
- 一部の関数は外部データ（prices_daily や raw_financials）の品質に依存します。例えば price 欠損時は exposure の過少評価につながる可能性があり、将来的にフォールバック価格の導入を検討しています（該当箇所に TODO コメントあり）。
- `calc_regime_multiplier()` は未定義レジームで 1.0 にフォールバックし、警告を出す設計です。
- `process_priority` と `set_cpu_affinity` は権限や OS に依存するため、実行環境により動作しない場合は警告でスキップされます。
- Paper Trading の約定挙動は `PAPER_FILL_MODE` に依存します。テスト時は適切に設定してください。

---

（以降のリリースでは「Unreleased」セクションに変更を追加の上、バージョンを切って日付を入れてください）