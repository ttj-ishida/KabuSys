# Changelog

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。  
このファイルは、与えられたコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

## [0.1.0] - 2026-04-18

### Added
- 全体
  - 初期バージョンのパッケージを追加。パッケージバージョンは `kabusys.__version__ = "0.1.0"`。
  - DuckDB と SQLite を併用するデータ基盤を採用（設定でパス指定可能）。

- 起動スクリプト
  - `run_execution.py`
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper 専用の SQLite（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（paper/live に応じた実装を想定）。
    - エンジンはデーモンスレッドで実行され、プロセス間の停止フラグ（`data/stop_requested.flag`）で安全に停止可能。
    - 起動時にプロセス優先度を `high` に設定する処理を追加。

  - `run_monitoring.py`
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト: 60秒）。無効値はデフォルトにフォールバックして警告。
    - 監視は環境に関わらず本番用の `sqlite_path` を使用する設計。

- 設定・ユーティリティ
  - `config.py`
    - 環境変数を集約する `Settings` クラスを追加。多数のプロパティ（DBパス、API トークン、閾値、環境種別など）を提供。
    - 自動 `.env` ロード機能を追加（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - `.env` の読み込みは `.env` → `.env.local` の順で行い、OS 環境変数を保護する仕組みを備える。
    - `PAPER_FILL_MODE` 等の入力検証（有効な値チェック）を実装。

  - `config_setup.py`
    - 対話式ウィザードで `.env` を初期作成 / 更新する CLI を追加。
    - 必須・任意項目、シークレットのマスク表示、入力補助、保存確認などのユーザーフローを実装。

  - `validate_config.py`
    - 起動前に `.env` や `config/*.yaml` の問題を検出する検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV・LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML が存在する場合）等を行う。
    - `--strict` オプションで警告を失敗扱いにできる。

  - `utils/logging_setup.py`
    - 統一的なログ初期化ユーティリティを追加。
    - stdout 出力用 StreamHandler と日次ローテーション（TimedRotatingFileHandler、30日保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続するフォールバック実装。

  - `utils/process_priority.py`
    - クロスプラットフォームでプロセス優先度を設定するユーティリティを追加（Windows/Posix を吸収）。
    - CPU affinity を設定する `set_cpu_affinity` を用意（利用可能なコア数を検出して固定）。
    - 権限不足等で設定できない場合は警告を出して安全にスキップ。

- Execution コンポーネント（高レベル）
  - `execution` パッケージ周りの起動時組み立てを実装（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の起動シーケンスを run_execution.py から呼ぶ）。
  - RiskManager のデフォルト設定を `RiskConfig` で定義し、初期ポートフォリオ値にブローカーの利用可能現金を使用。

- Portfolio 構築ロジック（純関数群）
  - `portfolio/portfolio_builder.py`
    - シグナルの選別（スコア降順、タイブレークは signal_rank）を行う `select_candidates`。
    - 等配分 `calc_equal_weights`、スコア加重 `calc_score_weights` を追加（スコア合計が0 の場合は等配分へフォールバックして警告）。
  - `portfolio/risk_adjustment.py`
    - セクター集中制限を行う `apply_sector_cap` を追加。既存保有のセクター別エクスポージャーを計算し、上限を超えるセクターの新規候補を除外する。
    - 市場レジームに応じた投下資金乗数を返す `calc_regime_multiplier` を追加（`bull`/`neutral`/`bear` をマップし、未知値は警告の上 1.0 フォールバック）。
  - `portfolio/position_sizing.py`
    - 発注株数を決定する `calc_position_sizes` を実装。`risk_based` / `equal` / `score` の配分方式に対応。
    - 単元株（lot_size）の丸め、1銘柄上限（max_position_pct）、投下資金の aggregate cap、コストバッファ（cost_buffer）を考慮したスケーリング処理を実装。
    - スケールダウン時は残差に基づき lot 単位で再配分するロジックを備える。
  - `portfolio/__init__.py` で関数群をエクスポート。

- Tools
  - `tools/paper_verification_report.py`
    - ペーパートレードの検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出して判定（PASS/FAIL）を出力。
    - P95 計算、日付フィルタ、DB パス解決ロジック（オプション引数/環境変数/デフォルト）を実装。
    - 各種閾値（稼働率99%、成立率90%、送信率95%、P95レイテンシ200ms）を定義。

- Monitoring
  - 監視用 DB 初期化関数参照 `monitoring.monitoring_db.init_monitoring_db` を起動ルーチンから呼び出して監視テーブルの存在を保証。

- Research
  - `research/factor_research.py` を追加（ファクター計算モジュールの骨格、Momentum/Value/Volatility/Liquidity を想定）。DuckDB 接続を受ける設計。

### Changed
- N/A（初期リリースのため過去からの変更は無し。設計上の注意点・既定値をドキュメント内コメントで明示）

### Fixed
- N/A（初期リリース）

### Removed
- N/A

### Known issues / Notes
- `research/factor_research.py` の実装は途中で終わっている箇所があり（ファイル末尾で `calc_momentum` の実装が未完）、完全なファクター計算ロジックは未実装。
- `portfolio/risk_adjustment.apply_sector_cap` 内で価格が欠損（0.0）だった場合にエクスポージャーが過少見積もられる旨の TODO コメントが残っており、フォールバック価格（前日終値や取得原価など）を用いる拡張が検討中。
- プロセス優先度や CPU affinity の設定は権限やプラットフォームに依存するため、失敗時は警告を出してスキップする挙動。運用環境では権限に注意が必要。
- `.env` パーサはシングル/ダブルクォート内のエスケープ処理やインラインコメント処理を実装しているが、非常に特殊なケースのパース結果は要確認。
- ログディレクトリ作成やファイルハンドラ生成が失敗した場合は標準出力のみで継続する設計。監視やログローテーションを期待する場合は `LOG_DIR` のパーミッション等を確認すること。

---

今後のリリース候補（例）
- factor_research の完全実装（Momentum/Value/Volatility/Liquidity の算出と正規化）
- Execution / Broker のテストダブル化と MockBroker の明示的実装
- monitoring_db の実装詳細と SystemMonitor のドキュメント追記
- 単体テスト・CI の追加や README / 運用ドキュメントの拡充

（この CHANGELOG はコードベースから推測して作成したもので、実際のコミット履歴ではありません。必要であれば各ファイルごとの詳細差分や起動手順を追記します。）