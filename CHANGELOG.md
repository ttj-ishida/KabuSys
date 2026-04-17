# CHANGELOG

このプロジェクトは Keep a Changelog の形式に従ってドキュメント化しています。  
主な変更はリリース単位で記載しています。コードベースから推測して記載したため、実際のコミット履歴とは差分がある可能性があります。

## [Unreleased]
（現状、開発中の変更はここに記載します）

## [0.1.0] - Initial release
初回リリース。基本的な自動売買フレームワークのコア機能と運用ツールを含みます。

### Added
- パッケージ初期版を追加
  - バージョン: `kabusys.__version__ = "0.1.0"`

- 設定・環境管理
  - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で探索）。
  - .env ファイルのパーサを実装（コメント、export プレフィックス、クォートとエスケープに対応）。
  - Settings クラスを追加し、環境変数をプロパティ経由で取得するAPIを提供。
  - 環境変数のバリデーション（有効な KABUSYS_ENV / LOG_LEVEL のチェック）、各種デフォルトパス（DuckDB/SQLite等）を提供。
  - PAPER_FILL_MODE の厳密チェック（"instant" / "partial" / "never" / "reject" のみ許容）。

- 設定支援 CLI
  - config_setup.py: 対話式ウィザードで .env を作成・更新するツールを追加（秘匿入力、選択肢、デフォルトの表示、確認プロンプト）。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。必須環境変数チェック、パス存在チェック、YAML のパース（PyYAML が無ければ警告）や本番環境向けの追加ガードを実装。`--strict` オプションで警告を失敗扱いにできる。

- 実行・監視ランナー
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - 実行前にプロセス優先度を "high" に設定。
    - Paper Trading モード時は paper 用 SQLite を使用して本番 DB と完全に分離（PAPER_TRADING_SQLITE_PATH を使用可能）。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと起動（スレッド実行・停止フラグ監視）。
    - デフォルトの RiskConfig 値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、初期ポートフォリオ値はブローカーから取得。

  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - 監視は環境に関わらず本番用 sqlite_path を使用して監視テーブルを初期化（init_monitoring_db）。
    - 停止フラグファイル（data/stop_requested.flag）を検知してループを終了。
    - check_once() 実行時の例外をキャッチしてログに記録後、次ポーリングまで待機。

- 監視 DB 初期化
  - monitoring_db 初期化関数を実装し、監視テーブルの存在を保証（冪等）。

- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（Fill率）、送信率、P95 レイテンシ、リスク却下数などを集計・評価。
    - 閾値（稼働率 >=99%、Fill >=90%、Send >=95%、P95 <=200ms）に基づく PASS/FAIL 判定を実装。
    - 日付フィルタ（--from / --to）と DB 指定（--db / PAPER_TRADING_SQLITE_PATH）に対応。

- ポートフォリオ構成ライブラリ（純粋関数群）
  - portfolio.portfolio_builder: 候補選定 (select_candidates)、等分配・スコア配分 (calc_equal_weights, calc_score_weights) を追加。
    - calc_score_weights は全スコアが 0 の場合に等分配へフォールバック（警告ログ）。
  - portfolio.risk_adjustment: セクター集中制限 (apply_sector_cap) と市況レジームに応じた乗数 (calc_regime_multiplier) を追加。
    - apply_sector_cap は sell_codes を受け、当日売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier は 'bull'/'neutral'/'bear' に対応、未知のレジームは 1.0 でフォールバック（警告）。
  - portfolio.position_sizing: 発注株数算出ロジックを実装（risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap によるスケールダウン（残差処理で lot 単位の再配分）を含む。
    - cost_buffer を用いた保守的見積りに対応。
    - 価格欠損時のスキップと debug ログ出力。

- リサーチ（ファクター計算）
  - research.factor_research: DuckDB を用いたファクター計算ユーティリティを追加（モメンタム、ボラティリティ/流動性等）。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を計算。
    - calc_volatility: ATR20、相対ATR、20日平均売買代金、出来高比率を計算（部分実装、ウィンドウ長に基づく集計）。
    - DuckDB の prices_daily テーブルを参照し、スキャン範囲のバッファを確保。

- プロセス制御ユーティリティ
  - utils.process_priority: プラットフォーム差分を吸収したプロセス優先度設定と CPU affinity 設定を追加。
    - Windows / POSIX (Linux, Darwin, FreeBSD) に対応する nice/HIGH_PRIORITY_CLASS マッピング。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足や未対応 OS では警告を出してスキップ。

- パッケージ構成
  - __all__ を介した公開 API を portfolio モジュールで整備。
  - tools パッケージ追加（paper_verification_report を含む）。

### Changed
- N/A（初回リリースのため過去変更なし）

### Fixed
- N/A（初回リリースのため過去修正なし）

### Known caveats / Notes
- apply_sector_cap 内の価格欠損（price が 0.0 の場合）に関する注記: 現在は 0.0 を使うと過少見積りになりうるため、将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO コメントあり。
- validate_config は PyYAML 未インストール時に YAML 内容検証をスキップして警告を出す仕様。
- process_priority / set_cpu_affinity は権限不足や環境により実行できないことがあり、その際は警告でスキップされる。
- MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）は警告してデフォルト 60 秒にフォールバックする。
- Paper Trading は本番 DB と完全分離（デフォルト path: data/paper_trading.db）される設計。ただし運用時のパス設定ミスに注意。

### Security
- .env の取り扱いに関する注記: config_setup により生成される .env ファイルは「絶対に Git にコミットしないこと」との注記を明示。

---

今後のリリース案（推測）
- テストカバレッジの強化（特に portfolio / position_sizing の端数処理や scaling ロジック）
- apply_sector_cap の価格フォールバック実装
- research.factor_research の追加ファクター実装完了（Value 指標など）とテスト
- ExecutionEngine / Broker 周りの詳細実装とエンド・ツー・エンドテスト
- CI での自動設定検証・コード品質チェック導入

（※この CHANGELOG は提供されたソースコードから推測して作成しています。正確な変更履歴は実際のコミットログをご参照ください。）