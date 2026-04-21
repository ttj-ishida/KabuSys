# Changelog

すべての注目すべき変更はこのファイルに記載します。
フォーマットは Keep a Changelog に準拠します。
リリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-04-21

初回リリース。KabuSys の基本的なコア機能、CLI、ユーティリティ、ポートフォリオ構築ロジック、モニタリング / 実行ランチャー等を実装しました。

### Added
- パッケージ情報
  - パッケージ初期バージョンを追加: `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト / 実行フロー
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL`（デフォルト60秒）でポーリング間隔を上書き可能。
    - 監視プロセスは停止フラグファイル (`data/stop_requested.flag`) を監視して安全に終了。
    - Monitoring 用の DB 接続は環境にかかわらず本番用 `sqlite_path` を使用する設計。
    - SQLite / DuckDB 接続の初期化および監視 DB テーブル初期化（`init_monitoring_db`）を行う。
    - プロセス優先度を起動直後に "high" に設定。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレーディング専用 DB（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と完全に分離。
    - ブローカークライアントは `BrokerClientFactory.create(settings)` で解決（paper/live に応じて Mock/実ブローカー）。
    - エンジンはバックグラウンドスレッドで実行され、同様に `data/stop_requested.flag` で停止を検知して安全停止する。
    - 実行用 PID ファイルのパス (`data/execution.pid`) を管理。
    - 起動時に監視テーブル存在を保証するため `init_monitoring_db` を冪等に呼び出す。

- 設定管理 / ユーティリティ
  - config.py
    - 環境変数・設定取得用 `Settings` クラスを実装。
    - プロジェクトルートを `.git` または `pyproject.toml` を基準に自動検出して `.env` / `.env.local` を自動読み込み（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
    - `.env` のパースは `export KEY=val`、シングル/ダブルクォート、エスケープ、行内コメント等に対応する堅牢な実装。
    - 各種プロパティを定義（J-Quants / kabu API / DuckDB/SQLite パス / PAPER_FILL_MODE の検証 / PID/KILL フラグ設定 / リソース閾値 / KABUSYS_ENV / LOG_LEVEL 判定等）。
    - `settings = Settings()` のシングルトンインスタンスを提供。

  - config_setup.py
    - 対話式ウィザードにより `.env` を初期作成・更新する CLI を実装。
    - フレンドリーな入力プロンプト、シークレットマスク、デフォルト提示、`.env` 書き込みテンプレートを提供。

  - validate_config.py
    - 起動前に環境変数や `config/*.yaml` の不備を検出する検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML の存在・パース検査（PyYAML があれば内容検証）、本番環境向けの追加ガード（LINE 通知・KILL_FLAG_CLEAR_ON_START 等）を実装。
    - `--strict` オプションで警告を失敗として扱う機能を追加。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 全アプリ共通のロギング設定ユーティリティを実装。
    - stdout に出力する StreamHandler と 日次ローテーションで保持する TimedRotatingFileHandler（デフォルト logs/、30日保持）をルートロガーに設定。
    - 既存ハンドラのクリーンアップ、環境変数 `LOG_LEVEL` / `LOG_DIR` を尊重。
    - ファイル出力に失敗した場合はコンソール出力のみで継続。

  - utils/process_priority.py
    - cross-platform（Windows / POSIX）でプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を設定する `set_process_priority` を実装。
    - CPU affinity を制御する `set_cpu_affinity` を実装（psutil を使用、権限や未対応環境で安全に扱う）。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定: `select_candidates`（スコア降順、同点は signal_rank でタイブレーク）。
    - ウェイト計算: `calc_equal_weights`, `calc_score_weights`（スコア合計が 0 の場合は等分配にフォールバックし警告）。
  - portfolio/risk_adjustment.py
    - セクター集中制限: `apply_sector_cap`（既存保有を考慮したセクター上限判定、"unknown" セクターは無視）。
    - レジーム乗数: `calc_regime_multiplier`（"bull"/"neutral"/"bear" 対応、未知は警告・1.0 フォールバック）。
  - portfolio/position_sizing.py
    - 株数決定ロジック: `calc_position_sizes` を実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、per-stock 上限・aggregate cap のスケーリング、cost_buffer（手数料・スリッページ見積）考慮、ロット単位での端数処理（残余キャッシュで優先分配）などを実装。
  - portfolio パッケージは上記エクスポートを提供。

- 監視・検証ツール
  - monitoring との連携点として、`init_monitoring_db` を利用して監視用テーブルの存在を保証する運用を実装（冪等）。
  - tools/paper_verification_report.py
    - ペーパートレーディングの検証レポート生成スクリプトを追加。
    - デフォルト DB は `data/paper_trading.db`（`PAPER_TRADING_SQLITE_PATH` で上書き可）。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を出力。
    - P95 計算、期間フィルタ（--from / --to）、しきい値による PASS/FAIL 判定を実装。
    - デフォルト基準値:
      - 稼働率: 99.0%
      - 注文成功率: 90.0%
      - 送信率: 95.0%
      - P95 レイテンシ: 200 ms

- データ解析基盤（リサーチ）
  - research/factor_research.py（骨組み）
    - DuckDB を用いたファクター計算モジュールの骨組みを追加（モメンタム、MA200乖離、ATR、出来高/流動性、ファンダメンタル指標を想定）。
    - 設計指針: DuckDB の prices_daily / raw_financials を参照し、純粋関数で結果を返す仕様。
    - （注）ファイル末尾で実装が途中で終わるため、今後の補完・完成が想定される。

### Changed
- 初回リリースのため「変更」はありません（ベースライン追加）。

### Fixed
- 初回リリースのため「修正」はありません。

### Notes / Behavior highlights
- デフォルトのログ出力先は `logs/`、アプリ名別にファイルを生成（例: `logs/execution.log`、`logs/monitoring.log`）。
- `Settings` は環境変数の自動読み込みを行うため、プロジェクト配布後もカレントワークディレクトリに依存しない動作を意図しています。
- Monitoring と Execution の両スクリプトは起動時にプロセス優先度を "high" に設定しようと試みますが、権限不足等の場合は警告を出して継続します。
- Paper Trading と Live の DB は分離される設計（ペーパートレードは `PAPER_TRADING_SQLITE_PATH` を利用）。

---

今後の予定（想定）
- research/factor_research の完全実装（Momentum / Value / Volatility / Liquidity の各計算の完成）。
- Strategy 実装（シグナル生成・バックテスト）および ExecutionEngine の詳細なテストカバレッジ拡張。
- YAML コンフィグの明示的な読み込み/利用部分の追加とドキュメント化。