CHANGELOG
=========

すべての注目すべき変更点を記録します。本ファイルは "Keep a Changelog" のフォーマットに準拠しています。

バージョンポリシー:
- SemVer を想定したバージョニング（本リリースはパッケージ内 __version__ に合わせて 0.1.0）。

[Unreleased]
------------

（現在の配布は 0.1.0 のため、未リリースの変更はここに追記してください。）

[0.1.0] - 2026-04-18
-------------------

Added
- プロジェクト初期リリース: KabuSys 基本機能群を追加。
  - 基本パッケージ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を定義。
- 環境設定・管理
  - Settings クラス（src/kabusys/config.py）
    - .env 自動読み込み機能（プロジェクトルートは .git または pyproject.toml で探索）。
    - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 多数の環境変数プロパティを提供（J-Quants / kabu API / DB パス / ログ / 監視閾値など）。
    - 値の検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
  - .env パーサー強化（export 形式、クォート文字列、バックスラッシュエスケープ、インラインコメント対応）。
  - .env 書き込み・対話ウィザード CLI（src/kabusys/config_setup.py）
    - 初期 .env 作成や既存 .env の更新を対話式に実行可能。
    - シークレット項目はマスク表示、保存前に確認可能。
- 設定検証 CLI（src/kabusys/validate_config.py）
  - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベルチェック、DB パス親ディレクトリ確認。
  - config/*.yaml の存在確認と（PyYAML がある場合は）パース検証。
  - 本番用の追加ガード（LINE トークンや Kill Switch の設定チェック）。
  - --strict オプションで警告を FAIL 扱いにできる。
- 実行スクリプト
  - 監視プロセス起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する挙動を明示。
    - stop フラグファイル（data/stop_requested.flag）検知で安全にループ終了。
    - 監視用 DB 初期化（init_monitoring_db）と DuckDB 接続。
    - プロセス優先度を最初に "high" にセット。
    - check_once() 実行時の例外はキャッチしてログに出力、次ポーリングで継続。
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）を使用し本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading 用は Mock 想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - エンジンは別スレッドで実行、stop フラグを検知したら engine.stop() で停止。
    - PID ファイル管理、プロセス優先度を "high" に設定。
- ログ関連ユーティリティ（src/kabusys/utils/logging_setup.py）
  - ルートロガーを統一的に設定する setup_logging を提供。
  - StreamHandler を stdout に出力（stderr ではなく stdout を使用）。
  - TimedRotatingFileHandler による日次ログローテーション（デフォルト logs/<app_name>.log、30 日保持）。ログディレクトリの作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - ログレベル・ログディレクトリの解決順を明確化（引数 > 環境変数 > デフォルト）。
- プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
  - set_process_priority(level) で Windows / POSIX を吸収した優先度設定を実装。アクセス拒否等は警告ログでスキップ。
  - set_cpu_affinity(cpu_count) でプロセスを最初の N コアに固定（失敗時は警告）。
- ポートフォリオ構築モジュール（src/kabusys/portfolio/*）
  - portfolio_builder.py
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化による加重配分、全スコアが 0 の場合は等分にフォールバックし警告。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中の既存保有比率が閾値を超えると同セクターの新規候補を除外。
    - calc_regime_multiplier: レジーム (bull/neutral/bear) に応じた資金乗数を返却（未知の値は 1.0 でフォールバック）。
  - position_sizing.py
    - calc_position_sizes: risk_based / equal / score の配分方式に対応。lot_size による丸め、max position/aggregate cap の適用、cost_buffer を加味したスケーリングロジックを実装。
  - これら関数は純粋関数としてメモリ内計算のみを行い、副作用なし。
- Paper Trading 検証レポートツール（src/kabusys/tools/paper_verification_report.py）
  - SQLite（paper_trading DB）からシステム稼働率・注文成功率・送信率・レイテンシ等を集計し、PASS/FAIL 判定を出力する CLI を提供。
  - P95 計算、閾値（稼働率 99%, 成立率 90%, 送信率 95%, P95 レイテンシ 200 ms）を設定。
  - --from/--to/--db オプションで期間/DB を指定可能。テーブルがない場合は安全に N/A を出力。
- 研究用ファクター計算モジュール（src/kabusys/research/factor_research.py）
  - モメンタム、ボラティリティ、バリュー等ファクターの計算方針と一部実装（DuckDB の prices_daily / raw_financials を参照）を追加。
  - 設計上の注意点（営業日ベースの窓、欠損ハンドリング、戻り型など）を明記。
- DB 初期化呼び出し（init_monitoring_db）を起動スクリプトで冪等に実行することで監視テーブルの存在を保証。
- 各種接続（sqlite3 / duckdb）のクローズを finally ブロックで確実に行うよう実装。

Changed
- ロギングのデフォルト挙動を明確化: stdout をメインの StreamHandler に使用し、ログファイル作成失敗時はコンソールのみで継続するフォールバックを追加。
- .env 読み込み優先順位を明確化: OS 環境変数 > .env.local > .env（既存 OS 環境変数を保護）。
- run_monitoring の挙動: 環境（KABUSYS_ENV）に依存せず監視は production sqlite_path を使用する仕様を明示（監視データは環境に依存しないため）。
- run_execution の DB 選択: paper_trading 環境では paper_sqlite_path を使用して本番 DB から完全分離。
- process_priority の挙動: OS 固有 API 呼び出し失敗時は警告ログでスキップする堅牢性を向上。
- ポートフォリオ算出ロジックの丸め・スケーリングロジックについて、lot_size と cost_buffer を導入して実運用を意識した振る舞いに。

Fixed
- .env の読み込みにおいて、OS 環境変数を上書きしないよう保護機能を実装（テスト / CI 等での既存値保護）。
- ログハンドラの多重追加を防止するため、setup_logging で既存ハンドラを flush/close してから削除するよう変更。
- 起動スクリプトでの接続漏れを防止するため、sqlite3 / duckdb 接続は finally で必ず close するように修正。

Deprecated
- （なし）

Removed
- （なし）

Security
- （なし）

Notes / Known limitations
- research/factor_research.py はファクター計算の実装が続く形で一部未完の箇所が存在します（将来的な拡張予定）。
- 一部機能は外部モジュール（psutil, duckdb, PyYAML 等）に依存します。これらが存在しない場合は該当機能をスキップするフォールバックが入っていますが、完全な動作を得るためには依存パッケージのインストールを推奨します。
- 実際の live 運用では KABUSYS_ENV=live の設定や LINE 通知設定等を慎重に確認してください（validate_config の警告参照）。

作者・メンテナ
- KabuSys 開発チーム

--- 
（今後の変更は本ファイル [Unreleased] セクションに追記し、リリース時にバージョンと日付を付けて移動してください。）