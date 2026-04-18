CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。  
日付はこのリリースでのコードベースの状態から推測して付与しています。

0.1.0 - 2026-04-18
-----------------

Added
- 初回公開リリースとして以下の主要コンポーネントを追加。
  - 実行/監視エントリポイント
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV が paper_trading の場合は専用の paper_trading DB を使用し MockBroker を利用して本番 DB と完全分離する挙動をサポート。停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）の取り扱いを実装。
    - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する点を明示。
  - 設定関連ユーティリティ
    - config.py: 環境変数読み込みと Settings クラスを提供。プロジェクトルート自動検出（.git / pyproject.toml 基準）、.env/.env.local 自動ロード（オーバーライドと保護キー対応）、多くの設定プロパティ（DB パス、KABUSYS_ENV 判定、paper_trading 用パス、閾値設定など）を実装。PAPER_FILL_MODE の検証も含む。
    - config_setup.py: 対話式ウィザードで .env を生成/更新する CLI を追加。シークレットマスク、選択肢サポート、既存 .env の読み込み・Enter による再利用をサポート。
    - validate_config.py: 起動前検証 CLI を追加。必須環境変数や config/*.yaml の存在・パースチェック、DB パス／ログレベル／本番ガード（LINE 設定・KILL フラグ設定）等を検証。--strict オプションで警告を FAIL 扱いにできる。
  - ロギング・プロセスユーティリティ
    - utils/logging_setup.py: ルートロガーの統一セットアップ関数を追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせ、ログディレクトリ作成失敗時はファイル出力をスキップして継続する堅牢性を確保。
    - utils/process_priority.py: Windows/Linux/macOS の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。CPU affinity 設定関数も提供。権限エラー等はワーニングでスキップする設計。
  - ポートフォリオ構築関連（純粋関数）
    - portfolio/portfolio_builder.py: シグナルの候補選定（スコア降順、signal_rank によるタイブレーク）と重み計算（等金額 / スコア加重）を実装。全スコアが 0 の場合は等金額にフォールバックして警告を出力。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。unknown セクターは上限適用外とするなどの仕様を明記。
    - portfolio/position_sizing.py: position sizing ロジックを実装。allocation_method に "risk_based" と "equal"/"score" をサポート。単元（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash 超過時のスケーリング）や cost_buffer を考慮した保守的見積り、端数配分ロジック（fractional remainder に基づき lot 単位での追加配分）を実装。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。期間フィルタ、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等を集計し、閾値に基づいて PASS/FAIL を判定。DB 欠損テーブルに対する頑健性（OperationalError を捕捉して N/A/0 を返す）を備える。P95 計算関数を実装。
  - リサーチ
    - research/factor_research.py: ファクター計算モジュールを追加（Momentum/Value/Volatility/Liquidity を想定）。DuckDB 接続を受けて prices_daily / raw_financials を参照する仕様。ただし momentum 計算関数の実装が途中まで（ファイル末尾で切れている）であり、引き続き実装・整備が必要。

Changed
- パッケージメタ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

Fixed
- なし（初回リリースのため該当なし）。

Known issues / Work in progress
- research/factor_research.calc_momentum の実装が途中で終端している（WIP）。ファクター計算の完全実装・テストは今後のタスク。
- position_sizing の price の欠損時の挙動について TODO コメントあり（価格欠損があるとエクスポージャーが過少見積りになりうる）。将来的にフォールバック価格の導入を検討。
- 一部の外部依存（psutil, duckdb, PyYAML）が必須またはオプションで必要。validate_config では PyYAML 未インストール時に YAML チェックをスキップするが、完全な検証のためには依存を満たすことを推奨。

Notes
- 設定や運用上の安全策に配慮した設計を多数取り入れています（.env の保護、KILL フラグ／PID 管理、本番ガード、ログの冗長化）。
- paper_trading は本番データと分離されるよう明確に実装されているため、ペーパートレード実行時の安全性が確保されています。
- ロギングは stdout に出す設計になっており、Task Scheduler や cron 等での運用を考慮しています。

References
- この CHANGELOG はコードベースの内容から推測して作成しています。細かな挙動や仕様に関しては個々のモジュール（各 .py ファイル）のドキュメント／コメントを参照してください。