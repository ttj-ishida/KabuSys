# Changelog

すべての notable な変更は Keep a Changelog のガイドラインに従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- なし

## [0.1.0] - 2026-04-23
初期リリース — 基本的な自動売買フレームワークと運用用ユーティリティを実装しました。

### 追加 (Added)
- 実行エントリ / 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。プロセス優先度設定、高優先度での起動、停止フラグ/PID 管理、paper_trading モード時の専用 SQLite DB 分離をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔の上書き、停止フラグ検出、例外ハンドリングを実装。

- 設定管理とウィザード / 検証ツール
  - config.py: 環境変数読み込み・設定取得モジュールを追加。プロジェクトルート自動検出、.env / .env.local 自動読み込み（OS 環境変数を保護）を実装。多くの設定プロパティ（DB パス、paper_trading 設定、監視閾値、ログレベル等）を提供。
    - .env のパースで export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントを考慮。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。デフォルト値・選択肢・シークレット入力をサポートし、.env ファイル生成を行う。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ検査、config/*.yaml の存在・パース検証（PyYAML が利用可能な場合）。--strict モードで警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ (純粋関数群)
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコアソートと上位抽出（タイブレーク処理あり）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装。全スコアが 0 の場合のフォールバックロジックを含む。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（既存ポジションを基にセクター別エクスポージャー計算）と候補除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を返す。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて発注株数を算出。lot_size による丸め、最大ポジション上限、aggregate キャップ（available_cash）によるスケールダウン、cost_buffer を考慮した保守的見積り、端数処理（残余キャッシュを用いた lot 単位の追加配分）を実装。

- 実行系コンポーネント（エンジン周りの組立て）
  - run_execution.py 内での OrderRepository / OrderManager / RiskManager / Reconciler 組み立てと ExecutionEngine 起動フローを実装（broker_factory にて環境に応じたブローカークライアントを生成）。

- 監視・レポート
  - monitoring 関連初期化（init_monitoring_db 呼び出し）と、Monitoring が常に本番 sqlite_path を参照する仕様を実装（run_monitoring.py）。
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。稼働率、注文成功率・送信率、リスク却下数、レイテンシ指標（平均/最大/P95）を算出し、閾値に基づく PASS/FAIL を判定する。P95 計算・日付フィルタ・DB パス引数/環境変数対応を実装。

- リサーチ（ファクター計算）
  - research/factor_research.py: DuckDB 接続を利用したモメンタム/ボラティリティ/バリュー等のファクター計算枠組みを実装（関数群・定数・スキャン窓長等を定義）。

- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。ログディレクトリ作成失敗時にファイル出力を無効化する安全策を実装。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定と CPU affinity 設定を追加（psutil 利用）。Windows / POSIX の差分を吸収し、権限不足時には警告を出してスキップする。

- パッケージ情報
  - __init__.py: パッケージバージョン __version__ = "0.1.0" を追加。

### 変更 (Changed)
- なし（初回リリースのため該当なし）

### 修正 (Fixed)
- 設定パースの堅牢化
  - .env 読み込み時に export プレフィックスやクォート・エスケープ・インラインコメントを正しく扱うよう改善。OS 環境変数は protected として .env.local の override から保護。
- DB 分離の安全策
  - paper_trading 環境で run_execution が専用の paper_sqlite_path を使用するようにし、本番データと完全分離する実装を適用。
- ログ設定の失敗耐性
  - ログディレクトリ作成やファイルハンドラ作成に失敗した場合でもコンソール出力（stdout）にフォールバックするように実装。

### 既知の注意点 / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price が 0.0（欠損）の場合にエクスポージャーが過小見積りされる可能性があるため、将来的には前日終値や取得原価などのフォールバック価格を検討するコメントを残しています。
- position_sizing の lot_size は現状グローバル固定（例:100）。将来的には銘柄別 lot_map を受け取る設計への拡張を想定しています（TODO コメントあり）。
- research/factor_research.py の一部実装は継続作業中（ファイル末尾が未完の可能性あり）。
- run_monitoring は Monitoring が常に本番 sqlite_path を使用する設計（意図的）であり、環境に応じた動作分離が必要な場合は注意してください。

### セキュリティ (Security)
- 現状特筆すべきセキュリティ修正はありません。環境変数に API トークンやパスワードを保持する設計のため、.env ファイルを絶対にリポジトリに含めない運用を README 等で周知してください（config_setup.py で同旨の注意書きを付加）。

---

この CHANGELOG はソースコードから推測して作成しています。実際のコミット履歴やリリース方針に合わせて適宜修正してください。