# Changelog

すべての破壊的でない変更はここに記録します。フォーマットは「Keep a Changelog」に準拠します。  

最新リリース: 0.1.0 — 2026-04-18

## [0.1.0] - 2026-04-18

### Added
- 初期リリースを追加。プロジェクトのコア機能群を提供。
- 起動スクリプト
  - run_execution: 実行エンジン起動スクリプトを追加。プロセス優先度設定、SQLite / DuckDB 接続、ブローカークライアント生成、OrderManager / RiskManager / Reconciler の組立て、ExecutionEngine のデーモン実行・停止フラグ監視、PID ファイル対応を含む（ファイル: src/kabusys/run_execution.py）。
  - run_monitoring: SystemMonitor 用ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、停止フラグ検知、監視 DB 初期化の仕組みを含む（ファイル: src/kabusys/run_monitoring.py）。
- 設定管理
  - Settings クラス: 環境変数経由の設定読み出し、env 判定（development/paper_trading/live）、DB パス、ペーパートレード設定等を提供（ファイル: src/kabusys/config.py）。
  - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml 基準）を探索して `.env` / `.env.local` を自動読み込み。OS 環境変数の保護機構あり（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パースの強化: export 形式、クォート内エスケープ、インラインコメントの取り扱いをサポート。
- 設定ユーティリティ / CLI
  - config_setup: 対話式ウィザードで .env の初期作成・更新を支援（ファイル: src/kabusys/config_setup.py）。
  - validate_config: 起動前検証 CLI を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML があれば実施）や本番向けのガード（LINE 設定、KILL_FLAG_CLEAR_ON_START）をチェック。--strict オプションで警告を失敗扱いにできる（ファイル: src/kabusys/validate_config.py）。
- ロギング基盤
  - setup_logging ユーティリティを実装。ルートロガーへ stdout 出力の StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日分保持）を設定。ログディレクトリ作成失敗時はファイル出力をスキップしコンソールのみで継続（ファイル: src/kabusys/utils/logging_setup.py）。
  - stdout を利用することで外部スケジューラからのリダイレクト運用を容易に。
- プロセス優先度 / CPU 指定
  - set_process_priority / set_cpu_affinity を実装。Windows / POSIX の差を吸収し psutil を用いて優先度・CPU affinity を設定。権限不足や未対応環境では警告を出してスキップ（ファイル: src/kabusys/utils/process_priority.py）。
- ポートフォリオ構成（純粋関数群）
  - portfolio_builder: 候補選定（スコア降順、同点は signal_rank によるタイブレーク）、等金額・スコア加重の重み計算（score が全て 0 の場合は等金額にフォールバック）を実装（ファイル: src/kabusys/portfolio/portfolio_builder.py）。
  - risk_adjustment: セクター集中制限（apply_sector_cap：既存保有比率が上限を超えるセクターの新規候補を除外）、市場レジームに応じた投下資金乗数（calc_regime_multiplier：bull/neutral/bear とフォールバック）を実装（ファイル: src/kabusys/portfolio/risk_adjustment.py）。
  - position_sizing: allocation_method（risk_based / equal / score）に基づく株数算出、単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash を超える場合のスケーリング）ロジック、コストバッファ考慮を実装（ファイル: src/kabusys/portfolio/position_sizing.py）。
  - portfolio パッケージの公開 API を整備（ファイル: src/kabusys/portfolio/__init__.py）。
- Paper Trading 検証ツール
  - paper_verification_report: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ(P95) 等を集計して PASS/FAIL を判定するレポート生成 CLI を追加。閾値はソース内定義で調整可能（ファイル: src/kabusys/tools/paper_verification_report.py）。
- モニタリング DB 初期化ユーティリティの参照を追加（init_monitoring_db を起動スクリプトで利用）。
- パッケージメタ情報
  - __version__ = "0.1.0" を設定（ファイル: src/kabusys/__init__.py）。
- 研究用スケルトン
  - factor_research: DuckDB 接続を受けてファクター（モメンタム、ボラティリティ、バリュー等）を計算するための骨組みを追加（ファイル: src/kabusys/research/factor_research.py）。※実装は継続中（ファイル末尾が未完の状態を含む）。

### Changed
- （初期リリースにつき該当なし）

### Fixed
- （初期リリースにつき該当なし）

### Removed
- （初期リリースにつき該当なし）

### Security
- 機密値（J-Quants トークン、kabu API パスワード、LINE トークン）は .env にて管理し、config_setup の出力ではマスクするなど取り扱いに配慮。なお .env を絶対にコミットしない旨をドキュメント注記に含める。

---

注記・運用上のポイント:
- run_monitoring は KABUSYS_ENV に関わらず settings.sqlite_path（デフォルト data/monitoring.db）を利用して監視データを記録します。run_execution は paper_trading 環境時に paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離します。
- MONITOR_POLL_INTERVAL 環境変数で監視ポーリング間隔を上書き可能（1秒未満や不正値はデフォルト 60 秒にフォールバック）。
- 設定自動ロードはプロジェクトルートが検出できない場合はスキップされるため、配布後やパッケージ化環境では KABUSYS_DISABLE_AUTO_ENV_LOAD により必要に応じて制御できます。
- ログディレクトリ作成やプロセス優先度の設定は環境依存で失敗する可能性があるため、失敗時は警告を出してフォールバック動作（ファイルログ無効化・優先度未設定）します。

（将来的な更新では factor_research の完遂、戦略／実行ロジックの細部チューニング、追加の監視アラート・テストカバレッジ強化を予定しています。）