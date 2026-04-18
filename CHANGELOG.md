# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  

履歴はコードベースの構成・実装内容から推測して作成しています。

## [Unreleased]

予定/既知の改善点・注意点
- research/factor_research.py が途中まで実装されているため、ファクター計算モジュールの完成（残りの処理とテスト追加）が必要。
- position_sizing の将来的な拡張点:
  - 銘柄ごとの lot_size（単元株）のマスタ導入（現状は全銘柄共通 lot_size=100 の想定）。
  - 価格欠損時のフォールバック（前日終値や取得原価）を導入する TODO。
- 自動テスト・CI の追加（現状コードからはテストの痕跡が少ないため推奨）。

---

## [0.1.0] - 2026-04-18

初回公開リリース（推定）。以下の主要機能とユーティリティを実装。

### Added
- 基本パッケージ情報
  - パッケージのバージョン定義を追加（kabusys.__version__ = "0.1.0"）。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを実装。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て実行。
    - エンジンは別スレッドで起動、stop フラグ検知で安全終了。PID ファイル管理。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）検知でループ終了。
    - 監視データベース初期化（init_monitoring_db）、DuckDB 接続の確立。
- 設定管理
  - config.py: 環境変数・設定管理クラス（Settings）を追加。
    - .env 自動ロード（プロジェクトルート検出: .git または pyproject.toml）。
    - 複数の設定プロパティ（DB パス、PID パス、閾値、環境判定メソッド等）を提供。
    - PAPER_FILL_MODE 等の値検証を実装。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを実装（secret 入力や既存値の再利用に対応）。
  - validate_config.py: .env と config/*.yaml の起動前検証 CLI を実装（--strict オプションあり）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、YAML パースチェック（PyYAML がない場合はスキップ警告）、本番環境向けガード（LINE 設定未登録や Kill Switch 設定等）を実施。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソートと上位選出。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分ロジック（スコア全て 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェックと候補フィルタリング（"unknown" セクターは除外対象にならない設計）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知値は 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 複数の配分方式（risk_based/equal/score）に対応した株数決定ロジック。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap によるスケールダウン、端数再配分ロジックを実装。
    - cost_buffer による保守的コスト見積りをサポート。
  - package-level export（kabusys.portfolio.__all__）を追加。
- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング初期化ユーティリティを追加。
    - StreamHandler を stdout に出力、TimedRotatingFileHandler で日次ローテーション（30 日分保持）。
    - LOG_DIR 作成失敗時はファイル出力をスキップしてコンソールのみで継続するフェイルバック。
    - 既存ハンドラの重複防止（クリアして再設定）。
  - utils/process_priority.py: プロセス優先度と CPU affinity のユーティリティを追加。
    - Windows/Linux/macOS 等を吸収して high/normal/low を設定。権限不足は警告でスキップ。
    - set_cpu_affinity により最初 N コアに固定可能（未指定時は全コア）。
- 監視・モニタリング基盤
  - monitoring 側の DB 初期化（init_monitoring_db を run スクリプトで呼び出し）。
  - SystemMonitor を用いた単発チェック呼び出し（monitor.check_once()）。
- 分析 / レポートツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。
    - システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出・表示。
    - Pass/Fail の閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - --from / --to / --db オプションに対応。PAPER_TRADING_SQLITE_PATH 環境変数をサポート。
- research
  - research/factor_research.py: ファクター計算モジュールの骨子を追加（Momentum, Value, Volatility, Liquidity を想定、DuckDB 接続を受ける設計）。一部未完。

### Changed
- ログ出力ポリシー
  - logging_setup にて stdout を標準出力に使用する方針を明示（cron 等で stdout/stderr を一本化する運用を想定）。
- DB 接続方針
  - run_monitoring は環境に関わらず本番 sqlite_path を使用する設計（監視 DB は常に本番用であるという運用判断）。
  - run_execution は paper_trading 環境で専用の paper_sqlite_path を使用して DB を完全分離。

### Fixed
- 環境変数パースの堅牢化（config._parse_env_line）
  - export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメント処理、コメントの扱いの微妙な差を考慮してパースを実装。
- validate_config: PyYAML 未インストール時に YAML 検証をスキップする旨の警告を追加。

### Known issues / Notes
- research/factor_research.py は未完のため、ファクター計算部分の実装とテストが必要（本 CHANGELOG 作成時点で途中で切れている）。
- position_sizing の価格欠損（price が 0.0 など）時の取り扱いはコメントで TODO（価格フォールバック未実装）。
- 設定の自動ロードはプロジェクトルート検出に依存するため、配布後の動作を保証するために pyproject.toml 等を含める必要あり。
- process_priority / set_cpu_affinity は権限やプラットフォームの制約で失敗することがあり、その場合はログ警告でスキップする設計。

---

今後の予定
- factor_research の完成および DuckDB 上での検証クエリ最適化。
- 銘柄別の lot_size 対応、価格フォールバック実装。
- さらなるユニットテスト追加と CI パイプライン整備。

（この CHANGELOG はコードから推測して作成しています。実際のリリースノートとは差異がある場合があります。）