# CHANGELOG

すべての notable な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）に合わせています。

## [Unreleased]

## [0.1.0] - 2026-04-22
初期リリース — 基本的な自動売買フレームワークを実装。

### Added
- コアパッケージの骨組みを追加
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
- 実行・監視ランナー
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory を利用してブローカークライアントを生成（paper_trading では Mock を想定）。
    - エンジンは別スレッドで run_session を実行し、停止フラグ（data/stop_requested.flag）により安全停止可能。
    - 実行用 PID ファイル管理（data/execution.pid）に対応。
  - SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視 DB は環境にかかわらず本番 sqlite_path を使用。
    - stop フラグ検出や例外保護によるロバストなループ設計。
- 設定管理
  - Settings クラス実装（src/kabusys/config.py）
    - .env 自動ロード機能（プロジェクトルート検出: .git / pyproject.toml を基準）。
    - .env のパースは引用符・エスケープ・export 形式・インラインコメントを考慮。
    - 各種環境変数プロパティ（DB パス、API トークン、paper_trading 用設定、監視閾値等）を提供。
    - 環境（development / paper_trading / live）とログレベルの検証。
  - 環境設定ウィザード CLI を追加（src/kabusys/config_setup.py）
    - 対話形式で .env の初期作成・更新を支援。
    - デフォルト値、選択肢、シークレット項目対応、保存確認を実装。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）
    - 必須環境変数チェック、KABUSYS_ENV 検証、ログレベル、DB パスの親ディレクトリ確認、config/*.yaml の存在とパースチェック（PyYAML がある場合）。
    - 本番環境（live）に対する追加ガード（LINE 設定、KILL_FLAG_CLEAR_ON_START の注意喚起）。
- ロギング / プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差分を吸収して優先度設定（high/normal/low）を提供。
    - CPU affinity 固定機能（最初の N コアにピン留め）。
    - 権限不足や未対応 OS 時の安全フォールバック（警告ログ）。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順・タイブレーク条件を実装。
    - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合はフォールバック）。
  - セクター上限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有に基づくセクター集中除外ロジック。
    - calc_regime_multiplier: market_regime に応じた投入資金乗数（bull/neutral/bear）と未知レジームのフォールバック。
  - 株数決定・資金制約処理（src/kabusys/portfolio/position_sizing.py）
    - allocation_method: "risk_based" / "equal" / "score" に対応。
    - 単元株（lot_size）丸め、最大ポジション比率、利用可能現金に応じた aggregate キャップとスケーリングロジック。
    - cost_buffer（手数料・スリッページ見積り）対応。
  - ポートフォリオ公開インターフェース（src/kabusys/portfolio/__init__.py）。
- Paper Trading 検証ツール
  - paper_verification_report スクリプトを追加（src/kabusys/tools/paper_verification_report.py）
    - SQLite（paper_trading DB）から稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）を集計。
    - しきい値による PASS/FAIL 判定を実装（稼働率、成功率、送信率、P95 レイテンシ等）。
    - コマンドラインで期間フィルタおよび DB パス指定可能。
- リサーチ / ファクター計算基盤（部分実装）
  - factor_research モジュール追加（src/kabusys/research/factor_research.py）
    - Momentum / Value / Volatility / Liquidity の計算方針を定義。
    - DuckDB を使った prices_daily / raw_financials ベースの計算を想定。
    - モメンタム計算（calc_momentum）を実装開始（営業日窓・MA200 等の計算方針を記述）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）
  - ただし多くの箇所で入力値検証・フォールバック処理（不正な MONITOR_POLL_INTERVAL、PAPER_FILL_MODE の検証、ログディレクトリ作成失敗時のフォールバック等）を実装し、運用上の堅牢性を高めています。

### Security
- なし（初回リリース）
  - 環境変数の取り扱いでシークレット項目を明示、.env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

---

注:
- この CHANGELOG はソースコードから推測できる機能・設計意図に基づいて作成しました。実際の変更履歴やコミットログがある場合は、それに基づいて正確に更新してください。