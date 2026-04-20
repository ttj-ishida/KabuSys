CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。
タグ付け規約: なし（このリポジトリはまだ初期リリース段階）

Unreleased
----------
（現時点で未リリースの変更はありません）

0.1.0 - 2026-04-20
-----------------

Added
- 全体
  - 初期リリース。自動売買システム KabuSys の基盤モジュール群を追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動用エントリポイントを追加。プロセス優先度設定、SQLite/DuckDB 接続、Broker クライアント生成、OrderRepository/RiskManager/Reconciler の組み立て、スレッドでのセッション実行と停止フラグ監視を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL によるポーリング間隔上書き、停止フラグ検知、例外捕捉による耐障害性を実装。
- 設定・環境管理
  - config.py: .env 自動ロード（.env → .env.local、OS 環境変数保護）、環境変数パースの堅牢化（export プレフィックス、クォート処理、インラインコメント処理など）、Settings クラスによる型付プロパティ（DB パス、Paper Trading 用設定、監視閾値、環境/ログレベルの検証）を追加。
  - config_setup.py: 対話式 .env 作成ウィザードを追加（既存 .env の読み込み・編集、シークレット項目マスク、保存確認）。
  - validate_config.py: 起動前検証 CLI を追加（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス・config/*.yaml の存在チェック、--strict モード）。
- ロギング・ユーティリティ
  - utils/logging_setup.py: StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定する共通ユーティリティを追加。ログディレクトリの自動作成と失敗時のフォールバックを実装。
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加（Windows / POSIX の扱い、CPU affinity 設定関数も提供、権限不足等の際は安全にスキップ）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。スコア全てが 0 の場合等金額にフォールバックするログを出力。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、相場レジームに応じた資金乗数を返す calc_regime_multiplier を追加。未知レジームの警告フォールバック等を実装。
  - portfolio/position_sizing.py: 発注株数決定ロジックを追加（risk_based / equal / score の allocation_method、単元株丸め、1 銘柄上限・アグリゲート上限・cost_buffer を考慮したスケーリング、残差配分ロジック）。
- モニタリング／検証ツール
  - monitoring: 監視用 DB 初期化呼び出し（init_monitoring_db）を run_* スクリプトから行う実装を追加。
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを算出し PASS/FAIL 判定を出力。期間指定オプション、DB パス指定オプションをサポート。
- データ解析基盤（研究用）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加（モメンタム・MA200乖離・ATR・出来高等を想定する設計。関数インターフェースと定数を準備）。

Changed
- .env 自動読み込みの挙動
  - プロジェクトルートの検出を __file__ ベースの親探索に変更。CWD に依存せずパッケージ配布後も動作するよう改善。
  - OS 環境変数は保護され、.env.local による再上書きでも OS 環境変数が上書きされないよう保護セットを導入。
- ログ出力先
  - コンソール出力は stderr ではなく stdout を利用するように変更（Task Scheduler/cron でのリダイレクトを考慮）。
- 起動挙動（監視）
  - run_monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使用する旨を明示（監視データの単一 DB 集約を想定）。

Fixed
- .env パーサ
  - export キーワード、シングル／ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを細かく正しく処理するよう修正。無効行のスキップやキー空チェックを実装。
- process_priority の堅牢性
  - 未対応 OS や権限不足時に例外で停止しないよう例外を捕捉し警告ログでスキップする実装を追加。
- Execution 起動安全性
  - 起動時に停止フラグが既に立っている場合はエンジンを起動せず終了する安全策を追加。実行中も停止フラグ検知でエンジン.stop() を呼ぶループを実装。

Security
- 機密情報ハンドリング
  - config_setup のウィザードでシークレット項目（トークン・パスワード）について表示をマスク。.env のテンプレートはコメントで Git へのコミット禁止を明示。

Notes / Known limitations
- research/factor_research.py は設計方針・関数インターフェースを含むが、実装の詳細（SQL クエリ部分など）が一部未完の可能性あり（ファイル末尾が途中で切れている旨の痕跡あり）。
- position_sizing や risk_adjustment の挙動は現状グローバルな lot_size/パラメタを想定しており、将来的に銘柄別 lot_map 等への拡張を想定した TODO コメントが存在。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB とは分離された SQLite を用いる設計。ただし運用上の DB マイグレーション等は実装外。

参考
- バージョンはパッケージ __init__.__version__ = "0.1.0" に合わせています。