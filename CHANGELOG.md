# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

なお、このログはソースコードから推測して作成しています（コミット履歴ではありません）。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-19

### Added
- 初期リリースとして以下の主要機能を追加。
  - 実行スクリプト・監視スクリプト
    - run_execution: ExecutionEngine を起動するエントリポイント。プロセス優先度設定、SQLite / DuckDB 接続、ブローカークライアント生成、依存コンポーネント組み立て、スレッド実行・停止処理を行う（src/kabusys/run_execution.py）。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、停止フラグ検知による終了、DB 初期化を行う（src/kabusys/run_monitoring.py）。
  - 設定・環境関連
    - config.py: .env 自動読み込み（プロジェクトルート検出）、.env パースロジック、Settings クラスによる環境変数のラップ（各種パス・フラグ・閾値・環境判定をプロパティで提供）（src/kabusys/config.py）。
    - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI（src/kabusys/config_setup.py）。
    - validate_config.py: .env と config/*.yaml の事前検証用 CLI。--strict を指定すると警告も失敗扱いにできる（src/kabusys/validate_config.py）。
  - ロギング・プロセス制御ユーティリティ
    - utils/logging_setup.py: stdout 出力と日次ローテーションのファイル出力（TimedRotatingFileHandler）をルートロガーに統一して設定するユーティリティ。ログディレクトリ作成失敗時のフォールバック処理を実装（src/kabusys/utils/logging_setup.py）。
    - utils/process_priority.py: プラットフォーム差分を吸収したプロセス優先度（nice / Windows priority）および CPU affinity 設定のユーティリティ（src/kabusys/utils/process_priority.py）。
  - Portfolio（銘柄選定・配分・リスク調整）
    - portfolio_builder.py: シグナルから候補選定(select_candidates)・等配分(calc_equal_weights)・スコア加重(calc_score_weights)（src/kabusys/portfolio/portfolio_builder.py）。
    - risk_adjustment.py: セクター集中制限の適用(apply_sector_cap)・市場レジームによる乗数(calc_regime_multiplier)（src/kabusys/portfolio/risk_adjustment.py）。
    - position_sizing.py: 各銘柄の発注株数計算(calc_position_sizes)。risk_based / equal / score の割当方式、単元株丸め、aggregate cap（利用可能現金に基づくスケールダウン）、コストバッファを考慮（src/kabusys/portfolio/position_sizing.py）。
    - portfolio パッケージのエクスポートを設定（src/kabusys/portfolio/__init__.py）。
  - 研究用ファクター計算（雛形）
    - research/factor_research.py: DuckDB 接続を受けてモメンタム等のファクターを計算するモジュールの骨組み（未完の関数開始部まで含む）（src/kabusys/research/factor_research.py）。
  - Paper Trading 向けツール
    - tools/paper_verification_report.py: Paper Trading の SQLite DB（data/paper_trading.db をデフォルト）から稼働率、注文成功率、送信率、レイテンシ（P95 等）を集計し PASS/FAIL 判定するレポートジェネレータ。コマンドライン引数で期間・DB を指定可能（src/kabusys/tools/paper_verification_report.py）。

### Changed
- 設定読み込みの設計
  - .env 自動ロードの優先順位を明記し、プロジェクトルートが検出できない場合は自動ロードをスキップする仕様に（src/kabusys/config.py）。
  - OS 環境変数を保護するため .env 読み込み時に override と protected 機構を導入（既存の OS 環境変数を自動上書きしない）（src/kabusys/config.py）。
  - .env パース機能を強化し、クォートやエスケープ、インラインコメントの取り扱いに対応（src/kabusys/config.py）。
- ロギング
  - stdout（StreamHandler）を使用することで cron 等で stdout/stderr を一本化してリダイレクトしやすくした（src/kabusys/utils/logging_setup.py）。
  - ログファイル出力ディレクトリの作成に失敗した場合はファイルハンドラを無効化してコンソールのみで継続する堅牢化を実装（src/kabusys/utils/logging_setup.py）。
- 実行・監視の挙動
  - run_execution/run_monitoring 起動時にプロセス優先度を最初に high に設定するように変更（src/kabusys/run_execution.py, src/kabusys/run_monitoring.py）。
  - run_execution は KABUSYS_ENV=paper_trading の場合に専用の paper trading SQLite を使用することで本番 DB と完全分離する仕様に（src/kabusys/run_execution.py）。
  - run_monitoring は monitoring の DB 初期化において常に本番 sqlite_path を使用する（環境に依らずモニタリングは本番 DB を参照する仕様）（src/kabusys/run_monitoring.py）。
  - run_monitoring: MONITOR_POLL_INTERVAL 環境変数を追加。0 以下や不正な値はデフォルト 60 秒にフォールバックして警告を出す（src/kabusys/run_monitoring.py）。
  - 両スクリプトとも停止制御にプロジェクト内 data/stop_requested.flag の検知を採用（src/kabusys/run_execution.py, src/kabusys/run_monitoring.py）。

### Fixed / Robustness
- process_priority の実装はプラットフォーム差を吸収し、権限不足や未サポート環境では警告を出して処理をスキップするようにした（src/kabusys/utils/process_priority.py）。
- position_sizing のスケールダウンロジックは lot_size 単位での再配分を実装し、残余キャッシュを考慮して端数処理を行うよう改善（src/kabusys/portfolio/position_sizing.py）。
- risk_adjustment.apply_sector_cap は「unknown」セクターに対しては上限適用を除外する挙動を明示（src/kabusys/portfolio/risk_adjustment.py）。
- config.setup の .env 書き込みフォーマットを整備し、コメント付きのテンプレートを出力するようにした（src/kabusys/config_setup.py）。
- validate_config は PyYAML 未インストール時に YAML 検証をスキップし警告を出す処理を追加。また config/*.yaml の存在チェックとパース検証を実装（src/kabusys/validate_config.py）。
- paper_verification_report の集計ではデータ欠落時に sqlite3.OperationalError を捕捉して安全に N/A 等を返すようにした（src/kabusys/tools/paper_verification_report.py）。

### Internal / Documentation
- パッケージメタ情報にバージョンを付与（__version__ = "0.1.0"）（src/kabusys/__init__.py）。
- 各モジュールに docstring と詳細な実装注釈（TODO や設計方針）を追加し、将来の拡張や注意点を明示。
- 各種閾値や定数（例: Paper レポートの合格基準、ポジション計算パラメータ、ログローテーション日数など）をソース内で定義し、容易に調整可能にした。

### Removed
- （なし）

---

開発・運用に関する注意:
- .env ファイルは絶対にリポジトリにコミットしないこと（config_setup.py の出力ヘッダにも明記）。
- 本番環境では KABUSYS_ENV を "live" に設定することで追加の安全確認や警告が行われる（validate_config.py, config.py）。
- process_priority / cpu_affinity の設定は OS と実行権限に依存するため、特権がない環境では設定がスキップされる可能性があります。