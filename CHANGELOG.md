# CHANGELOG

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

注意: この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴・差分と若干異なる可能性があります。

## [0.1.0] - 2026-04-22

Added
- 初回公開リリース相当の機能群を追加。
- 実行・監視エントリポイント
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient（BrokerClientFactory により切替）を使用し、ペーパートレード用の専用 SQLite（デフォルト: data/paper_trading.db）へ記録する。実行中の PID 管理、停止フラグ (data/stop_requested.flag) による安全な停止、バックグラウンドスレッドでのセッション実行とタイムアウト付き join を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。監視は環境に関わらず本番用 sqlite_path を使用。起動時にプロセス優先度を上げる処理を実行。
- 設定管理と初期化ツール
  - config.py: 環境変数の読み込み・検証を提供。プロジェクトルート自動検出（.git または pyproject.toml 基準）、.env/.env.local の自動ロード（OS 環境変数を保護）を実装。各種設定プロパティ（パス、閾値、運用モード、PAPER_FILL_MODE の妥当性チェック等）を提供。
  - config_setup.py: 対話式ウィザードで .env ファイルを初期作成・更新する CLI を追加。シークレットはマスク表示、ユーザ確認後にファイルを生成。
  - validate_config.py: 起動前チェック用 CLI を追加。必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在チェック、--strict オプションで警告を FAIL 扱いにできる機能を提供。
- ログ・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）を組み合わせ、ログディレクトリの自動作成や作成失敗時のフォールバック（コンソールのみ）を実装。LOG_LEVEL / LOG_DIR による設定をサポート。
  - utils/process_priority.py: Windows / POSIX を吸収したプロセス優先度設定ユーティリティを追加。nice 値や Windows の優先度クラスを適切に設定し、失敗時は警告でスキップ。CPU affinity 設定機能も提供。
- ポートフォリオ構築ライブラリ（純関数群、DB非依存）
  - portfolio/portfolio_builder.py: シグナル選別（スコア降順、同点タイブレーク）、等配分・スコア加重配分（スコア合計が0の場合は等配分へフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中上限チェック（既存ポジション評価を考慮し、当日売却予定銘柄を除外）と市場レジームに基づく投下資金乗数（bull/neutral/bear）を実装。未知のレジーム値は警告の上でフォールバック。
  - portfolio/position_sizing.py: 単元株丸め、リスクベースおよび重みベースの株数算出、1銘柄上限・合計利用可能現金（aggregate cap）でのスケールダウン、cost_buffer を用いた保守的見積もり、残余配分ロジックなどを実装。
- リサーチ / ファクター計算（基礎）
  - research/factor_research.py: DuckDB 接続を受け取り prices_daily / raw_financials を参照するファクター計算モジュールの骨組みを追加（モメンタム・移動平均などの定義と設計方針を含む）。（ファイル末尾で計算関数が未完の箇所あり。）
- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成 CLI を追加。稼働率・注文成功率・送信率・レイテンシ（P95）等の指標を SQLite から集計し、閾値に基づき PASS/FAIL を判定。日付フィルタ、DB パス指定オプションをサポート。
- モニタリング DB 初期化と SystemMonitor 呼び出し補助（監視テーブルの自動作成）
  - 各起動スクリプトで init_monitoring_db を呼び、監視テーブルの存在を保証（冪等）。
- パッケージ情報
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / Known issues
- config._parse_env_line は複雑なクォート・エスケープとインラインコメントの扱いに対応していますが、極端に特殊な .env フォーマットでの互換性については注意が必要です。
- portfolio/risk_adjustment.apply_sector_cap は価格欠損（price_map が 0.0 等）の場合にエクスポージャーが過少見積りされる可能性がある点を TODO コメントで指摘しており、将来的にフォールバック価格の導入が想定されています。
- research/factor_research.py の実装は途中で切れている節があり、完全なファクター出力は今後の実装が必要です。
- ロギングでファイル出力が失敗した場合は自動的にコンソール出力へフォールバックします（運用環境ではログディレクトリ権限を確認することを推奨します）。

---

今後のリリース案（例）
- 0.2.0: factor_research の完成、Strategy/Execution の統合テスト、パフォーマンス改善、モニタリング指標の拡張
- 0.1.x: バグ修正、小さな改善（.env パーサ堅牢性向上、PID/フラグ管理の強化 等）

もし特定のファイル単位での変更点や、リリースノートの表現を別の形式（英語・より詳細な箇条書きなど）で希望される場合はお知らせください。