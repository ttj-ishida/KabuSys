# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

※ この CHANGELOG はリポジトリ内のコードを読み、実装内容から推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

### Added
- さまざまな起動スクリプト・CLI・ユーティリティ・アルゴリズムの初期実装を追加。
  - 起動スクリプト
    - `src/kabusys/run_monitoring.py`
      - SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 停止フラグ（data/stop_requested.flag）検知ロジック、監視用 SQLite / DuckDB 接続、プロセス優先度を高に設定する処理を実装。
      - 監視は実行環境に関わらず「本番」用の sqlite_path を使用する挙動。
    - `src/kabusys/run_execution.py`
      - ExecutionEngine 起動スクリプトを追加。`KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し、paper_trading 用 DB（data/paper_trading.db）へ記録することで本番 DB と分離。
      - 停止フラグ（data/stop_requested.flag）・PID ファイル管理、実行スレッド管理、プロセス優先度設定を実装。
  - 設定管理 / ウィザード / 検証
    - `src/kabusys/config.py`
      - .env 自動読み込み（`.env` / `.env.local`、OS 環境変数保護付き）、プロジェクトルート自動検出 (.git / pyproject.toml 基準)。
      - 各種設定プロパティ（J-Quants、kabu API、LINE、DuckDB/SQLite パス、paper_trading 用パス、監視閾値、KABUSYS_ENV/ログレベル判定 等）を提供。
      - PAPER_FILL_MODE のバリデーション、paper_trading 用 DB パス分離などを実装。
    - `src/kabusys/config_setup.py`
      - 対話式の .env 作成/更新ウィザードを実装。既存 .env 読み込み、シークレットマスク、選択肢/デフォルト提示、保存確認をサポート。
    - `src/kabusys/validate_config.py`
      - 起動前の設定検証 CLI を実装。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在・パースチェック（PyYAML 任意）や本番環境向けの追加ガードを提供。`--strict` オプションで警告を失敗扱いにできる。
  - ユーティリティ
    - `src/kabusys/utils/logging_setup.py`
      - ルートロガーの統一設定ユーティリティを実装。stdout ストリームハンドラと日次ローテートするファイルハンドラ（TimedRotatingFileHandler）を設定。LOG_DIR が作成できない場合はファイル出力をスキップして stdout のみで継続。
    - `src/kabusys/utils/process_priority.py`
      - プラットフォーム差を吸収したプロセス優先度設定ユーティリティを追加。Windows / POSIX(nice) をサポートし、CPU affinity 設定関数も提供。権限不足時は警告を出してスキップする安全設計。
  - ポートフォリオ構築（純関数群）
    - `src/kabusys/portfolio/portfolio_builder.py`
      - 候補選定 (`select_candidates`)、等重み付け (`calc_equal_weights`)、スコア重み付け (`calc_score_weights`) を実装。スコアが全て 0 の場合は等重みへフォールバック。
    - `src/kabusys/portfolio/risk_adjustment.py`
      - セクター集中制限 (`apply_sector_cap`) と市場レジームに基づく資金乗数 (`calc_regime_multiplier`) を実装。unknown セクターはセクター上限の対象外とする挙動、未知レジームはフォールバック 1.0。
    - `src/kabusys/portfolio/position_sizing.py`
      - 発注株数計算 (`calc_position_sizes`) を実装。`allocation_method` に `"risk_based"` / `"equal"` / `"score"` をサポート。単元株（lot_size）丸め、1 銘柄上限・合計投資上限（aggregate cap）、コストバッファ（手数料・スリッページ見積）によるスケーリング処理、残差を考慮した追加配分ロジックを実装。
    - `src/kabusys/portfolio/__init__.py`
      - 上記機能をパッケージ公開。
  - ツール
    - `src/kabusys/tools/paper_verification_report.py`
      - Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を出力。期間指定や DB パス指定 (--from/--to/--db) をサポート。デフォルト DB は data/paper_trading.db。
  - 研究用モジュール（作業中）
    - `src/kabusys/research/factor_research.py`（部分実装）
      - モメンタム等のファクター計算に着手（DuckDB 接続を想定、モメンタム計算などの定義あり）。ファイル末尾での未完了箇所あり（開発継続予定）。

### Changed
- パッケージメタ
  - `src/kabusys/__init__.py` にバージョン `0.1.0` と公開 API の基本を追加。

### Fixed
- N/A（初期実装のため明示的なバグ修正履歴なし）

### Known issues / Notes
- research/factor_research.py は途中で途切れる（未完了）。今後計算ロジックの完成・単体テストを追加予定。
- `apply_sector_cap` 内で価格が欠損（0.0）の場合、エクスポージャーが過少見積りされる旨の TODO コメントあり。将来的にフォールバック価格導入を検討。
- `position_sizing` は将来的に銘柄別単元（lot_size）対応への拡張予定（TODO コメントあり）。
- ログディレクトリ作成やプロセス優先度設定は権限に依存するため、失敗時はログや警告で通知して安全にフォールバックする設計。
- 監視（run_monitoring）は環境に関わらず monitoring DB として sqlite_path を使用する点は設計上の意図（監視データの一元化）なので注意。

---

## [0.1.0] - 2026-04-18

Initial public release.

- 上記「Added」に記載した全機能を初回リリースとしてまとめて公開。

[Unreleased]: #  
[0.1.0]: #