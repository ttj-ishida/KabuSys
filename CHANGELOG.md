# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
各項目はコードベース（src/ 以下）の現状から推測して記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-23
初回リリース（推定）。日本株自動売買システム KabuSys の基本的な実行スクリプト、設定管理、ポートフォリオ構築、リスク調整、ポジションサイズ計算、ロギング・プロセスユーティリティ、検証・ウィザードツール等を含む。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離し、MockBrokerClient を利用する設計をサポート。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による起動／停止制御。
    - 起動時にプロセス優先度を "high" に設定。
    - ExecutionEngine を別スレッドで動かし、外部停止フラグ検知で安全停止を試みる。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用する（設計上の注意）。
    - 停止フラグ（data/stop_requested.flag）でループを終了。check_once() 実行中の例外はログ出力して次回ポーリングへフォールバック。

- 設定・環境管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を探索）。
    - .env / .env.local を OS 環境変数と競合しない形で読み込む（.env.local は上書き）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 複雑な .env のパース対応（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、行末コメントの扱い等）。
    - Settings クラスでアプリケーション設定をプロパティとして提供（DB パス、API トークン、Paper Trading 設定、閾値、ログ設定等）。値検証（有効な KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を実施。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成／更新を支援。
    - シークレット項目のマスク表示、選択肢・デフォルトの提示、確認・保存機能を提供。
  - validate_config.py
    - .env および config/*.yaml の検証用 CLI。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パス（親ディレクトリ存在チェック）、YAML パースチェック（PyYAML がある場合）などを実施。
    - --strict オプションで警告も FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates(): BUY シグナルをスコア降順（同点は signal_rank の昇順でタイブレーク）で選択。
    - calc_equal_weights(), calc_score_weights(): 等金額配分・スコア加重配分。スコア合計が 0 の場合は等配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - apply_sector_cap(): 既存ポジションのセクター比率が上限を超える場合、新規候補をブロック（unknown セクターは除外しない）。
    - calc_regime_multiplier(): market regime（bull/neutral/bear）に応じた投下資金乗数を返す。未知のレジームは 1.0 にフォールバックして警告を出す。
  - portfolio/position_sizing.py
    - calc_position_sizes(): allocation_method("risk_based" | "equal" | "score") に基づき発注株数を算出。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、ポートフォリオ全体の利用上限（max_utilization）を考慮。
    - risk_based 方式では stop_loss_pct に基づくリスク額から株数算出。
    - aggregate cap（合計投資額が利用可能現金を超える場合）でスケーリングし、残差は lot_size 単位で大きい順に配分するロジックを実装。
    - cost_buffer（手数料・スリッページ見積）を考慮した保守的なコスト見積り。
    - 価格欠損時は該当銘柄をスキップしてロギングする挙動。

- 解析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプト（SQLite DB を読み取り、稼働率・注文成功率・送信率・レイテンシ等を集計）。
    - P95（95百分位）計算ロジック、複数テーブル（system_status, trade_logs, risk_logs）からの指標抽出。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）による PASS/FAIL 判定。
    - --from/--to/--db オプションで期間・DB を指定可能。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - ログレベル解決順やログディレクトリ解決順を明確化。ファイル出力用ディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - psutil を用いたプロセス優先度設定ユーティリティ（Windows / POSIX の差分を吸収）。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。権限不足等で失敗した場合は警告を出してスキップ。

- research/factor_research.py（部分実装を含む）
  - DuckDB 接続を受けるファクター計算モジュール（モメンタム、MA200 乖離、ATR、出来高指標等）を準備。設計方針や定数が記載されている（関数実装は途中で切れているファイルあり）。

### Changed
- なし（初回リリース想定のため、既存からの変更履歴は無し）。

### Fixed
- .env パースの堅牢化（引用符内のエスケープ、行内コメントの扱い、export プレフィックス対応）により現実的な .env フォーマットに対応。
- ログディレクトリ作成失敗時に明示的警告を出し、ファイルハンドラをスキップしてアプリがクラッシュしないよう改善。

### Deprecated
- なし

### Removed
- なし

### Security
- API トークン等のシークレットは .env に保存する前提（config_setup でシークレット項目をマスク表示）。ただし .env は絶対にリポジトリにコミットしないよう注意喚起あり。

### Known issues / TODO（ソース内コメントより推測）
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャーが過少見積りされてブロックが外れる可能性があるため、将来的に前日終値や取得原価等のフォールバック価格を導入することを検討すべき。
- portfolio/position_sizing:
  - 現在は全銘柄共通の lot_size（デフォルト 100）を使用。将来的に銘柄別 lot_map を導入する拡張予定（コメントで TODO）。
- research/factor_research.py:
  - ファイル末尾で実装が途中で切れている（calc_momentum の実装が途中）。ファクター計算機能は追加実装が必要。
- 実行時の権限や環境（psutil による優先度設定、ファイルシステム権限等）により一部機能（プロセス優先度設定、CPU affinity、ログファイル作成）が失敗する可能性がある。これらは現在ログ出力で「スキップ」処理しており、運用時の検証が推奨される。
- monitoring は常に本番 sqlite_path を参照する設計のため、意図せぬ環境で監視データを書き換えないよう運用上の注意が必要。

---

リリース内容の記述はソースコードから推測したものであり、実際のリリースノートとは差異がある可能性があります。不明点があれば該当ファイルを指定して詳細を追加します。