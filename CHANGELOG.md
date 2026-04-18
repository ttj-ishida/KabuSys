# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはリポジトリ内の最近の機能追加・改善をコードベースから推測してまとめたものです。

全般ルール:
- 日付は本リリースが反映されたと推定される日付を使用しています。
- ファイル/機能名はコード内の実装に基づき記載しています。

## [0.1.0] - 2026-04-18

### 追加
- 初期公開リリース: KabuSys — 日本株自動売買システムの基本コンポーネント群を追加。
- 設定・環境関連
  - 環境変数/設定読み込みモジュール `kabusys.config` を追加。
    - プロジェクトルート自動検出（.git / pyproject.toml）で .env を自動ロード。
    - .env パース処理を実装（export 前置、クォート処理、インラインコメントの扱い等に対応）。
    - Settings クラスを実装し、J-Quants / kabu API / DB パス /各種閾値 /環境種別（development/paper_trading/live）などをプロパティ経由で取得可能に。
    - paper_trading 向けの設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等）を追加。
  - 設定ウィザード CLI `kabusys.config_setup` を追加。
    - 対話式で .env を作成・更新するウィザードを提供。
  - 設定検証 CLI `kabusys.validate_config` を追加。
    - 必須環境変数や YAML 設定ファイル存在チェック、本番環境向けのガードなどを実施。`--strict` オプションで警告を失敗扱いに可能。

- 実行 / 監視エントリポイント
  - `kabusys/run_execution.py`
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、DB 接続、ブローカークライアント生成、Order/ Risk / Reconciler の組み立て、デーモンスレッドでの実行・停止フラグ監視を実装。
    - KABUSYS_ENV が `paper_trading` の場合は paper 用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - 起動時に停止フラグ（data/stop_requested.flag）存在確認し、既に立っている場合は起動を止める。
  - `kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。プロセス優先度設定、SQLite / DuckDB 接続、ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 監視停止用フラグの検出によりループを終了。

- ロギング / プロセス制御ユーティリティ
  - `kabusys/utils/logging_setup.py`
    - 統一的なロギング初期化関数 `setup_logging()` を提供。stdout への StreamHandler と日次ローテーションする TimedRotatingFileHandler（デフォルト logs/<app>.log）を設定。既存ハンドラをクリアして二重設定を防止。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - `kabusys/utils/process_priority.py`
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定 `set_process_priority(level)` を実装（"high"/"normal"/"low"）。
    - CPU affinity を設定する `set_cpu_affinity(cpu_count)` を実装。
    - psutil を利用、権限不足等の場合は警告ログを出して安全にフォールバック。

- ポートフォリオ構築関連（純粋関数モジュール）
  - `kabusys/portfolio/portfolio_builder.py`
    - 候補選定 `select_candidates()`、等重み `calc_equal_weights()`、スコア加重 `calc_score_weights()` を追加。スコアが全てゼロの際のフォールバック動作を実装。
  - `kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限 `apply_sector_cap()` と市場レジームに応じた乗数 `calc_regime_multiplier()` を追加。未知レジームや unknown セクターのフォールバック挙動を明記。
  - `kabusys/portfolio/position_sizing.py`
    - ポジションサイズ計算 `calc_position_sizes()` を追加。allocation_method（"risk_based" / "equal" / "score"）対応、単元株（lot_size）丸め、1銘柄上限・総投下上限（aggregate cap）に基づくスケーリング、手数料・スリッページ見積りのための cost_buffer を考慮した設計。

- モニタリング / 実行 DB 初期化
  - `kabusys.monitoring.monitoring_db.init_monitoring_db` を利用して監視用テーブルの存在を保証（冪等に初期化）。

- ツール
  - `kabusys/tools/paper_verification_report.py`
    - Paper Trading 用の検証レポート生成器を追加。稼働率、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL を判定。日付フィルタや DB パス指定に対応。P95 計算ユーティリティ含む。
  - `kabusys/research/factor_research.py`
    - ファクター計算モジュールの骨格を追加（モメンタムなどを計算する関数を実装する設計）。（注：ファイル末尾で実装途中の箇所あり）

### 変更
- .env 自動ロードの挙動
  - OS 環境変数が優先され、.env.local は .env を上書きするが OS 環境変数は保護される（protected 機構）。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` によって自動ロードを無効化可能。
- ログ出力
  - ログのコンソール出力を stderr ではなく stdout にし、タスクスケジューラなどからのリダイレクト運用を考慮。
- 監視挙動
  - `run_monitoring` は KABUSYS_ENV に関わらず本番 sqlite_path を使用する旨を明記（監視データは環境依存にしない方針）。
- Execution エンジン
  - paper_trading の場合に専用 DB を使用して本番 DB と完全分離する動作を追加。
- 設定検証
  - `validate_config` にて config/*.yaml の存在確認および（PyYAML があれば）パース検証を行い、ファイル欠落やパースエラーを警告/エラーで報告するように。

### 修正
- .env パーサの堅牢化
  - export プレフィックスの対応、クォート文字内のバックスラッシュエスケープ処理、インラインコメントの扱いなどを改善して実務での .env 設定に耐えるようにした。
- process_priority の障害耐性を向上
  - 対応 OS でない場合や権限不足時に例外を投げず警告ログでスキップするように修正。
- ログハンドラの二重追加防止
  - setup_logging() は既存ハンドラを flush/close してから削除し、二重出力を防止するようにした。

### 注意事項 / 既知の制限
- research/factor_research.py の一部関数は実装途中（ファイル末端での実装継続が想定される）。完全なファクター計算は今後の実装で完成予定。
- position_sizing の注記にある通り、price が欠損（0.0）の場合にエクスポージャーが過少見積もられる可能性があり、将来的に前日終値などのフォールバックが推奨されている。
- .env ファイルは機密情報を含むため Git にコミットしないこと（config_setup においてもヘッダで注意喚起）。

### セキュリティ
- .env ファイルを誤ってコミットしないよう README / config_setup の生成ヘッダで明示（.env は絶対に Git にコミットしない旨）している。

---

今後の予定（コードベースから推測）
- research モジュールの完成（Momentum / Value / Volatility / Liquidity 等のファクター算出）
- ExecutionEngine / SystemMonitor の詳細実装・堅牢化（エラーハンドリング、リトライ、より詳細なメトリクス収集）
- テスト補強と CI での静的解析導入

（以上）