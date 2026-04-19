# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

なお、本CHANGELOGはリポジトリ内のソースコードから機能・振る舞いを推測して作成した推定の変更履歴です。実際のコミット履歴とは異なる場合があります。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-19

初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装・追加しました。

### Added
- 実行エントリ・監視ランナー
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - 起動時にプロセス優先度を「high」に設定。
    - KABUSYS_ENV が `paper_trading` の場合、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - ブローカークライアントのファクトリ（BrokerClientFactory）を利用し、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立ててデーモンスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）検知による安全な停止処理と PID ファイルサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書き（デフォルト 60 秒）。
    - 監視は実行環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検知でループを終了、例外はキャッチしてログを残して次ポーリングへ継続。

- 設定関連
  - config.py: 環境変数/`.env` 自動読み込み機構・Settings クラスを実装。
    - プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
    - 複雑な `.env` のパースに対応（export プレフィックス、クォート内のエスケープ、インラインコメント処理など）。
    - 各種設定プロパティ（DB パス、KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を提供し、妥当性チェックを実施。
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加。
    - サンプル項目群（J-Quants token、kabu API パスワード、DB パス、ログ設定、Kill Switch 設定等）を定義。
    - 既存 .env 読み込み、シークレット値のマスク表示、保存確認、ファイル書き込みを実装。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および PyYAML によるパース検証を実装。
    - `--strict` オプションで警告をエラー扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率に応じた重み付け（全銘柄スコアが 0 の場合は等金額にフォールバックして WARNING）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限を適用して新規候補をフィルタ（"unknown" セクターは上限適用除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（"bull"、"neutral"、"bear" を想定、未知レジームは 1.0 にフォールバックして WARN）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数を計算（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元（lot_size）で丸め、1銘柄上限・aggregate cap（利用可能現金）でスケールダウン、cost_buffer を考慮した保守的見積り、残余キャッシュでの端数分配アルゴリズムを実装。
    - 価格欠損時のスキップ、各種パラメータ（risk_pct, stop_loss_pct, max_position_pct, max_utilization 等）を受け入れ。

- ロギング/プロセスユーティリティ
  - utils/logging_setup.py
    - setup_logging 関数を実装: StreamHandler（stdout）と TimedRotatingFileHandler（デフォルト logs/、日次ローテーション、30 日保持）をルートロガーへ設定。
    - 既存ハンドラのクリーンアップ、ログディレクトリの作成失敗時はファイル出力をスキップして stdout のみで継続。
    - LOG_LEVEL / LOG_DIR 解決順の明確化。
  - utils/process_priority.py
    - set_process_priority: Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定。権限不足等は WARN でスキップ。
    - set_cpu_affinity: 指定コア数へ CPU affinity を設定（未対応 OS や権限不足は WARN でスキップ）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計し、閾値（稼働率 99%、fill 90% 等）で PASS/FAIL を判定。
    - P95 計算、期間フィルタ（--from/--to）、DB パスのオーバーライド（--db / 環境変数）に対応。

- 研究/ファクター計算（骨格）
  - research/factor_research.py
    - モメンタム、移動平均乖離、ATR、流動性などのファクター計算ロジックを設計・一部実装（duckdb 接続を受け prices_daily/raw_financials を使用する方針）。
    - 定数・設計方針（窓幅・スキャン範囲・出力フォーマット）を定義。実装の続きを想定（ファイル末尾で切れているが設計意図は明示）。

- パッケージ情報
  - kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。

### Changed
- なし（初回リリースのため新規追加が中心）

### Fixed
- なし（初回リリースのためバグ修正履歴なし）

### Known issues / Notes / TODO
- apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる旨の TODO コメントあり。将来的に前日終値や取得原価によるフォールバックを検討する必要あり。
- position_sizing: 将来的に銘柄別の単元（lot_size）を stocks マスタで管理する拡張を想定している旨の TODO コメントあり。
- research/factor_research.py はファイル末尾で途中終了しており、実装が継続中であることを示唆する。完全実装とユニットテストの追加が必要。
- `.env` パーサは多くのケースに対応しているが、極端なエッジケースの追加検証が望ましい（特に引用符内の複雑なエスケープやコメント解釈）。
- 本番環境（KABUSYS_ENV=live）では Kill Switch や LINE 通知設定などのガードがあるが、運用ルールの周知と追加テストを推奨。

### Security
- なし

----

参考: この CHANGELOG はリポジトリのソースコード（起動スクリプト、設定処理、ポートフォリオ構築ロジック、ユーティリティ、ツール）をもとに推測して作成しています。実際のリリースノートやコミット履歴が存在する場合はそちらを優先してください。