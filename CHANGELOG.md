# CHANGELOG

すべての notable な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
バージョン番号はパッケージの `kabusys.__version__` に合わせています。

---

## [Unreleased]

- なし（初回公開リリースに相当する機能群を含むため、Unreleased は空です）

---

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーション骨格を追加
  - パッケージメタ情報 (`src/kabusys/__init__.py`, バージョン 0.1.0)
- 実行エントリ・監視エントリを追加
  - run_execution: ExecutionEngine 起動スクリプト（起動時にプロセス優先度を上げ、専用スレッドで実行、停止フラグ検知で安全停止）
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔上書き可）
- 環境設定 / 検証用 CLI を追加
  - config_setup: 対話式ウィザードで `.env` を作成・更新する CLI（既存値再利用、シークレットマスク表示、保存前確認）
  - validate_config: `.env` と `config/*.yaml` の静的検証 CLI（必須環境変数チェック、パス存在チェック、YAML パースチェック、--strict オプション）
- 環境変数読み込み・設定管理
  - config: .env 自動ロード機能（OS 環境 > .env.local > .env の優先順、プロジェクトルート検出、ロード保護機構）、堅牢な .env 行パーサ実装（クォートとエスケープ、コメント扱いの改善）
  - Settings クラスにより設定値をプロパティベースで取得可能（DBパス、paper_trading 用パス、しきい値等）
- ログ・プロセス管理ユーティリティを追加
  - utils/logging_setup: stdout StreamHandler と 日次ローテーションの FileHandler をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして継続。
  - utils/process_priority: Windows / POSIX の差を吸収したプロセス優先度設定と CPU affinity 設定を提供。権限不足等の例外は警告ログで扱う。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder: シグナル選定（スコア降順、タイブレーク）、等金額/スコア重みの計算
  - portfolio/risk_adjustment: セクター集中制限の適用、レジームに応じた資金乗数計算（bull/neutral/bear）
  - portfolio/position_sizing: allocation_method（risk_based / equal / score）に基づく株数計算、lot_size 単位丸め、aggregate cap によるスケールダウンロジック、コストバッファに対応
- 監視・発注周りの DB 初期化フック
  - monitoring.monitoring_db.init_monitoring_db を呼ぶことで監視用テーブルの存在を保証（冪等）
- Paper Trading 向け機能分離
  - run_execution は KABUSYS_ENV=paper_trading の場合、Paper 専用 SQLite（data/paper_trading.db 既定）を使用し、本番 DB と完全に分離
  - BrokerClientFactory を用いて設定に応じて MockBrokerClient を利用する想定
- Paper Trading 検証レポート生成ツールを追加
  - tools/paper_verification_report: SQLite の履歴から稼働率、注文成功率、送信率、レイテンシ等を集計して PASS/FAIL を判定するレポートを標準出力に生成（P95 計算、期間フィルタ対応、閾値定義）
- research/factor_research モジュール（ファクター計算）
  - Momentum / MA / ATR 等のファクター算出を想定したインターフェースと定数群を導入（DuckDB 接続を受ける設計）

### Changed
- ロギングの標準化
  - 全起動スクリプトから `setup_logging(app_name=...)` を呼ぶことで、コンソール出力とファイル出力を統一的に扱うように変更
  - ファイルローテーションは日次・30世代保持に設定
  - StreamHandler を stdout に出力（cron 等で stdout/stderr をリダイレクトしやすくするため）
- 環境変数ロードの挙動
  - OS の環境変数を保護するために .env の上書き時に保護セットを導入（.env の自動ロードで OS 環境を上書きしない）
  - 自動ロードはプロジェクトルートが検出できない場合にスキップするように安定化
- 実行・監視プロセスの起動順序改善
  - 起動直後にプロセス優先度を先に設定（パフォーマンス優先度の確保）
  - run_execution は停止フラグ検知時に起動をスキップし、安全に終了するようになった
- 計算ロジックの保守性向上
  - position_sizing の aggregate スケーリングで残差処理（lot 単位での追加配分）を実装し、再現性を保つためソートに code を使用
  - risk_adjustment の regime マップにデフォルトフォールバックと警告出力を追加
- CLI のユーザー体験改善
  - config_setup において既存 .env の読み込みと Enter による再利用、シークレット値のマスク表示、保存前の確認を実装
  - validate_config に --strict オプションを追加し、警告を FAIL 扱いにできるようにした

### Fixed
- .env パースの堅牢化
  - クォート内のバックスラッシュエスケープ処理、クォート閉じ処理、不正行の無視等を実装し、実際の .env ファイルに含まれる複雑な値にも対応
  - export KEY=val 形式に対応
- 監視ループの堅牢化
  - MONITOR_POLL_INTERVAL の値検証を実装（0 以下や非整数は警告してデフォルトにフォールバック）。time.sleep に渡す不正値による例外を回避
  - check_once() 実行時の例外を捕捉してログ出力し、ループを継続するようにして監視の堅牢性を向上
  - run_monitoring/run_execution ともに DB コネクションを finally で閉じるようにしてリソースリークを防止
- FileHandler 作成失敗時のフォールバック
  - ログディレクトリ作成やファイルハンドラ作成に失敗した場合はコンソール出力のみで継続するよう修正（起動失敗を回避）
- process_priority/set_cpu_affinity の安全性強化
  - 対応しない OS や権限不足時に例外を上げず警告でスキップするようにして、クロスプラットフォームでの起動失敗を防止
- Paper 検証レポートの堅牢化
  - DB テーブルが存在しない／レコードがない場合に OperationalError をキャッチしてデフォルト値でレポート生成できるようにした

### Security
- `.env` に関する取り扱いの注意喚起を config_setup の生成ファイルヘッダに明記（.env を絶対に Git にコミットしない旨）

---

注意事項・今後の TODO（コード内コメントにある項目を抜粋）
- position_sizing: 銘柄ごとの lot_size を将来的にマスタ管理する設計への拡張を検討中
- risk_adjustment.apply_sector_cap: 価格欠損時（price == 0.0）にエクスポージャが過少に見積もられる可能性があるため、前日終値や取得原価のフォールバック実装を検討
- research/factor_research: ファイル末尾で実装途中の箇所が存在（モメンタム計算関数の実装続きが必要）

もし特定の変更点（例: 追加された関数や CLI の使い方、閾値や環境変数のデフォルト値一覧等）について、より詳細な履歴や説明を希望される場合は、どの項目を掘り下げるかを指示してください。