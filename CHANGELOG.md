# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

最新リリース
------------

### [0.1.0] - 2026-04-19

Added
- 初回リリース。KabuSys の基本ユーティリティ群・起動スクリプト・ポートフォリオ構築ロジック・検証ツールなどを収録。
- 実行エントリ/デーモン
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ (data/stop_requested.flag) を検知して安全に終了。
    - Monitoring は環境変数にかかわらず本番用の sqlite_path を使用する挙動を明記。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し、Paper Trading 用に `data/paper_trading.db`（環境変数で上書き可）を利用して本番 DB と完全に分離。
    - エンジンはバックグラウンドスレッドで実行され、停止フラグを検知すると engine.stop() を呼び出して安全に停止。
    - 起動・実行時に PID ファイル (`data/execution.pid` デフォルト) を扱う設計。

- 設定・環境管理
  - config.py
    - 自動的にプロジェクトルートを探索して `.env` / `.env.local` をロード（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。
    - `.env` のロード順は OS 環境変数 > .env.local > .env（.env.local は上書き、ただし OS 環境変数は保護）。
    - `.env` パースは export 形式、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントなどを考慮した実装。
    - Settings クラスを提供し、各種設定値（DB パス、API トークン、監視閾値、PAPER_FILL_MODE の妥当性チェックなど）をプロパティ経由で取得可能。
    - `PAPER_FILL_MODE` の有効値チェック（instant/partial/never/reject）とエラー報告。
    - `KABUSYS_ENV` と `LOG_LEVEL` の妥当性検査（無効値は ValueError）。

  - config_setup.py
    - 対話式ウィザードで `.env` の初期作成・更新を支援。
    - シークレットのマスク表示、既存値の再利用、choices / optional 項目に対応。
    - 書き込みフォーマットのテンプレートを提供。

  - validate_config.py
    - 起動前チェック CLI。必須環境変数・KABUSYS_ENV、DB パス、config/*.yaml の存在・パース（PyYAML があれば内容検証）・本番用ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START）などを検査。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日分保持）を設定するユーティリティ。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続するフェールセーフ。
    - LOG_LEVEL / LOG_DIR の解決順を文書化。
  - utils/process_priority.py
    - Windows / POSIX を吸収したプロセス優先度設定（high/normal/low）。
    - CPU affinity 設定関数（最初の N コアに固定）を提供。
    - アクセス権限不足などの例外をキャッチして警告ログを出しつつ安全にスキップする実装。

- ポートフォリオ構築（純粋関数: DB 非依存）
  - portfolio/portfolio_builder.py
    - シグナルから候補選定（スコア降順、タイブレークは signal_rank）。
    - 等金額配分 calc_equal_weights、スコア加重 calc_score_weights（全スコアが 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（売却予定の銘柄をエクスポージャー計算から除外可、"unknown" セクターは上限適用外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull=1.0, neutral=0.7, bear=0.3。未知のレジームは 1.0 にフォールバックして警告）。
  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく株数計算。
    - 単元（lot_size）丸め、per-position / aggregate 上限、コストバッファ（スリッページ・手数料見積）を考慮したスケールダウンロジックを実装。
    - 価格欠損時のスキップや詳細なログ出力を実装。

- 監視・レポート・データ
  - monitoring.monitoring_db.init_monitoring_db の呼び出しにより監視テーブルの存在を保証（冪等）。
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプト（SQLite を読み込み、稼働率・注文成功率・送信率・P95 レイテンシなどを計算）。
    - 基準値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定出力。
    - ファイル存在チェック、SQL 実行障害を起因とする例外をハンドリングして安全にレポートを生成。

- 研究用ファクター計算スケルトン
  - research/factor_research.py
    - DuckDB を利用したファクター計算のためのユーティリティ（Momentum / Value / Volatility / Liquidity 等を想定）の骨組み。
    - 設計方針と定数（MA、ATR、期間など）を文書化。

- パッケージ情報
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

Changed
- （初回リリースのため該当なし）

Fixed
- 実行時の堅牢性向上・フェールセーフの導入:
  - MONITOR_POLL_INTERVAL の不正値（整数変換失敗や 0 以下）を検出してデフォルトへフォールバックし、警告を出力。
  - logging_setup: ログディレクトリ作成失敗やファイルハンドラ作成失敗を捕捉して代替出力を維持。
  - process_priority: 非対応 OS や権限不足時に警告を出して処理を継続。
  - validate_config: PyYAML 未インストール時に YAML 検証をスキップして警告出力。

Security
- 環境変数の取り扱い:
  - `.env` ウィザードと自動ロードは、デフォルトで OS の環境変数を保護（.env.local/.env による不注意な上書きを防止）する設計。
  - .env ファイル生成テンプレートに "絶対に Git にコミットしないこと" を明記。

Notes / Known issues
- research/factor_research.py の一部関数が大きめの実装中またはスケルトン状態の箇所がある（将来の実装拡充を予定）。
- 一部 TODO コメントあり（例: position_sizing の銘柄ごとの lot_size を将来的にマスタ化する等）。
- monitoring は「本番 sqlite_path を使用する」旨が明記されているため、意図しない DB 上書きを避けるため運用時は環境変数・ファイルパスの設定を再確認してください。

-----------------------------------------------------------------
過去のバージョン
- なし（初回リリース）