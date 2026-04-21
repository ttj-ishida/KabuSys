# CHANGELOG

すべての変更は Keep a Changelog の構成に準拠しています。主要なリリース履歴と、コードベースから推測される追加・変更点・修正点を日本語でまとめています。

フォーマット:
- 重要度順にカテゴリ化（Added / Changed / Fixed / Security / その他）
- 各項目は該当するソースファイルや振る舞いを明示

## [Unreleased]
- なし

## [0.1.0] - 2026-04-21
初回リリース。日本株自動売買フレームワーク「KabuSys」の基礎機能群を実装。

### Added
- コア CLI / 起動スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV に応じて paper_trading 用 DB を分離し、BrokerClientFactory により本番/モックブローカーを選択してエンジンをデーモンスレッドで実行（src/kabusys/run_execution.py）。
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能、停止は data/stop_requested.flag による（src/kabusys/run_monitoring.py）。
  - validate_config: .env や config/*.yaml の存在・基本妥当性を検査する CLI。--strict により警告を失敗扱いにできる（src/kabusys/validate_config.py）。
  - config_setup: 対話式ウィザードで .env を作成・更新するツール（src/kabusys/config_setup.py）。
  - tools.paper_verification_report: Paper Trading 用 SQLite のログを解析して稼働率・注文成功率・レイテンシ等の検証レポートを生成するツール（src/kabusys/tools/paper_verification_report.py）。

- 設定管理
  - Settings クラス: 環境変数をラップしたプロパティ群を提供（J-Quants / kabu API / DB パス / 監視閾値 / 環境判定など）（src/kabusys/config.py）。
  - 自動 .env ロード: プロジェクトルート（.git または pyproject.toml）を基に .env/.env.local を自動読み込み（既存 OS 環境を保護する挙動あり）（src/kabusys/config.py）。
  - .env パーサ: export 形式・クォート・エスケープ・インラインコメント等に対応する堅牢なパーサを実装（src/kabusys/config.py）。

- ポートフォリオ構築ロジック（純粋関数）
  - portfolio_builder: 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）（src/kabusys/portfolio/portfolio_builder.py）。
  - risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）（src/kabusys/portfolio/risk_adjustment.py）。
  - position_sizing: 発注株数計算（allocation_method: risk_based/equal/score）、単元株切り捨て、aggregate cap によるスケーリング、cost_buffer を考慮した安全見積り（src/kabusys/portfolio/position_sizing.py）。

- ユーティリティ
  - logging_setup: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（ログ日次ローテーション）を統一的に設定。既存ハンドラの二重設定防止とログディレクトリ作成のフォールバックを実装（src/kabusys/utils/logging_setup.py）。
  - process_priority: Windows/Linux/macOS でのプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）設定を抽象化し、CPU affinity 設定も提供（src/kabusys/utils/process_priority.py）。

- 監視・実行周りの耐障害性実装
  - monitoring 側で監視 DB の初期化を行う init_monitoring_db 呼び出しを統一（run_execution/run_monitoring）。
  - run_monitoring は監視 DB に本番 sqlite_path を常に使用する設計（環境により誤ってテスト DB に書き込まないようにするための仕様）。

- レポート / 解析
  - paper_verification_report: P95 計算、期間フィルタ、各種閾値による PASS/FAIL 判定を実装。DB 存在チェックやテーブル未存在時のフォールバック処理あり（src/kabusys/tools/paper_verification_report.py）。

### Changed
- ロギング関連
  - コンソール出力を stderr ではなく stdout に統一（cron 等で stdout/stderr を一本化してリダイレクトする運用を想定）（src/kabusys/utils/logging_setup.py）。
  - setup_logging は既存ハンドラを flush/close してから削除し、二重登録を防止するように変更（src/kabusys/utils/logging_setup.py）。

- .env 自動読み込み順序
  - OS 環境変数 > .env.local > .env の優先度で読み込み。既存 OS 環境を保護するため protected set を利用して上書きを回避（src/kabusys/config.py）。

- 起動時の振る舞い
  - run_execution / run_monitoring 起動時にプロセス優先度を "high" に設定する処理を追加（src/kabusys/run_execution.py, src/kabusys/run_monitoring.py）。
  - run_execution は paper_trading 環境時に専用の SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離（src/kabusys/run_execution.py）。

### Fixed / Robustness
- .env パーシング強化
  - クォート内でのバックスラッシュエスケープ、閉じクォート検出、そしてクォートなし時のインラインコメント扱いを正しく処理するように改善（src/kabusys/config.py）。
- MONITOR_POLL_INTERVAL の妥当性チェック
  - run_monitoring のポーリング間隔を環境変数から取得する際、整数変換と 1 未満の値の検出を行い、不正値はログで警告してデフォルト（60 秒）にフォールバックする（src/kabusys/run_monitoring.py）。
- ログ出力先ディレクトリ作成失敗時の挙動
  - ログディレクトリ作成に失敗してもプロセスは継続し、ファイルハンドラ作成をスキップしてコンソール出力のみで動作するようにした（src/kabusys/utils/logging_setup.py）。
- process_priority の安全化
  - アクセス権限の不足や未サポート OS に対して警告を出し、安全にスキップする実装（src/kabusys/utils/process_priority.py）。
- position_sizing の合計配分スケーリング
  - aggregate cap を超過した場合の縮小アルゴリズムを実装。縮小後に残余キャッシュで lot_size 単位の再配分を行う際、残差順・コード安定キーで追加配分を決定し再現性を担保（src/kabusys/portfolio/position_sizing.py）。

### Security
- config_setup に .env ヘッダを書き込み、.env を絶対に Git にコミットしない旨の注意を明記（src/kabusys/config_setup.py）。
- Settings._require で必須環境変数が未設定の場合に明示的なエラーを投げることで起動ミスを早期検出（src/kabusys/config.py）。

### Documentation / Other
- 各モジュールに詳細な docstring と使い方コメントを追加（例: portfolio 説明、research 設計方針、logging/process_priority の使い方など）。
- research/factor_research.py にファクター計算の設計方針と定数、calc_momentum のインターフェースを追加（実装は途中まで。データは DuckDB の prices_daily / raw_financials を想定）（src/kabusys/research/factor_research.py）。
- パッケージバージョンを __version__ = "0.1.0" に設定（src/kabusys/__init__.py）。

### Notes / Known limitations
- factor_research.calc_momentum はファイル末尾で途中（start_da... のような切断痕跡）になっており、計算ロジックが未完了の可能性がある。実装を補完する必要あり（src/kabusys/research/factor_research.py）。
- 一部の TODO（価格欠損時のフォールバック価格、将来的な銘柄別 lot_size マスタ）はコメントとして残されている。運用上の注意点として扱うこと。
- Monitoring は設計上「監視 DB に常に本番 sqlite_path を使用」するため、テスト時には DB パスの扱いに注意が必要（意図的に分離された paper_trading DB は Execution 用のみ）。

---

（比較リンク等の外部参照は未設定）
