CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、語彙は日本語で記載しています。

Unreleased
----------
（開発中の変更・今後リリース予定の項目）

Added
- 実行/監視用のエントリポイントスクリプトを追加
  - run_execution.py：ExecutionEngine を起動する CLI。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db）に記録する分離動作を実装。
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
- 設定管理・ウィザード・検証ツールを追加
  - config.py：.env の自動読み込み（.env, .env.local）、高度な .env パース（クォート・エスケープ・コメント処理）、Settings クラス（環境変数の型変換・バリデーション）を実装。
  - config_setup.py：対話式ウィザードで .env を生成・更新する CLI を実装。デフォルト値・シークレット表示・確認保存までサポート。
  - validate_config.py：起動前に .env および config/*.yaml の設定を検証する CLI。--strict オプションで警告を失敗扱いにできる。
- Paper Trading 検証ツールを追加
  - tools/paper_verification_report.py：ペーパートレード用 SQLite から稼働率、注文成功率、送信率、レイテンシ（P95 など）を集計してレポート出力するスクリプト。閾値（稼働率 99%、成立率 90% など）に基づく PASS/FAIL 判定を実装。
- ポートフォリオ構築（純粋関数群）を追加
  - portfolio/portfolio_builder.py：候補選定(select_candidates)、等金額配分(calc_equal_weights)、スコア加重(calc_score_weights) を実装。score が全て 0 の場合は警告を出して等金額にフォールバック。
  - portfolio/position_sizing.py：複数の allocation_method（risk_based / equal / score）に対応した発注株数計算ロジック、単元株（lot_size）丸め、aggregate cap によるスケールダウン（残差分の lot 単位で再配分）を実装。cost_buffer（スリッページ・手数料考慮）に対応。
  - portfolio/risk_adjustment.py：セクター集中制限 apply_sector_cap（既存保有を考慮、unknown セクターは無視）、市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear, 未知レジームは警告）を実装。
- 研究用ファクター計算モジュールを追加
  - research/factor_research.py：DuckDB を用いた momentum/volatility 等のファクター計算関数を実装（MA200、ATR20、リターン等）。P95 計算等のユーティリティ設計を含む。
- ユーティリティ
  - utils/process_priority.py：Windows/Linux/Mac の差分を吸収してプロセス優先度と CPU affinity を設定するユーティリティを追加。権限不足などは警告でスキップする堅牢性を備える。

Changed
- DB 周りの挙動整理
  - run_monitoring は監視 DB に対して常に「本番」sqlite_path を使うよう明確化（環境に依存しない監視記録）。
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と分離。
- .env の読み込み順序と保護ポリシー
  - OS 環境変数を保護しつつ .env（.env.local）を上書きする挙動を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。

Fixed
- .env パースの堅牢化
  - クォート文字内のバックスラッシュエスケープ、行内コメントの扱い、export キーワード対応などを改善し、現実的な .env の記述に対して正しく動作するように修正。
- ポートフォリオ・ポジション計算の端数処理と上限ロジックを明確化
  - 単元株（lot_size）での丸め、_max_per_stock による per-stock 上限、aggregate cap のスケーリングと残差配分を安全弁付きで実装。

Security
- 環境変数の必須項目チェックを導入（J-Quants, kabuステーション パスワード等）。validate_config による事前検出で本番誤操作のリスクを低減。

0.1.0 - 2026-04-17
------------------
初回公開リリース（ベース機能群）

Added
- パッケージの基本構成を追加
  - __init__.py にバージョン 0.1.0 を設定。
- 基本 CLI とユーティリティ群の提供
  - run_execution.py, run_monitoring.py の起動スクリプト。
  - config.py（Settings）、config_setup.py（ウィザード）、validate_config.py（検証）を提供。
  - utils/process_priority.py によりクロスプラットフォームで優先度設定をサポート。
  - DuckDB / SQLite を利用する各種コンポーネントの土台を整備（duckdb_path, sqlite_path）。
- ポートフォリオ構築とリスク調整
  - portfolio モジュール（portfolio_builder, position_sizing, risk_adjustment）を初期実装。
- 研究・レポート機能
  - research/factor_research.py（ファクター計算）、tools/paper_verification_report.py（ペーパートレード検証レポート）を実装。

Changed
- デフォルト設定
  - MONITOR_POLL_INTERVAL のデフォルトを 60 秒に設定（run_monitoring.py）。
  - 各種デフォルトパス（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）を設定ファイルで指定可能に。

Fixed
- 起動時の DB 初期化処理
  - init_monitoring_db を呼び出して監視テーブルの存在を保証する処理を run_execution/run_monitoring に追加し冪等性を確保。

Notes
- 本リリースでは ExecutionEngine や BrokerClient の詳細実装（発注ロジック、ブローカーインターフェースの具象等）は別モジュールに委譲されています。Paper Trading 用の分離された DB と MockBroker の利用により、テスト/開発環境での安全な検証が可能です。
- .env は機密情報を含むため、config_setup により生成された .env を Git にコミットしないよう注意書きを出力します。

今後の予定（例）
- ExecutionEngine および Reconciler の機能改善（再試行ロジック、詳細な注文ステータス管理など）
- モニタリングのアラート連携（LINE 通知や外部監視連携）
- DuckDB を用いたファクター計算の追加ファクター・パフォーマンス最適化
- 単体テスト・CI の整備とドキュメントの拡充

----------------------------------------
注: この CHANGELOG は提供されたコードベースの内容から推測して作成したものであり、
実際の変更履歴やリリース計画はリポジトリのコミット履歴やリリースノートに従ってください。