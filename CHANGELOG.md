# CHANGELOG

すべての変更は Keep a Changelog の慣例に従って記載しています。  
このファイルはコードベースの現在の状態から機能・修正点を推測して作成したものであり、実際のコミット履歴とは異なる場合があります。

フォーマット:
- Unreleased: 現在開発中の変更（必要に応じて更新）
- 各バージョン: リリース日（YYYY-MM-DD）
カテゴリ: Added, Changed, Fixed, Deprecated, Removed, Security

## [Unreleased]
- ドキュメント・リファクタリングや細かな改善が今後追加される予定。

## [0.1.0] - 2026-04-25
### Added
- 基本パッケージの初期実装を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
- 実行エントリスクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。環境変数 `KABUSYS_ENV=paper_trading` の場合は paper trading 用 DB を分離して MockBrokerClient を利用する旨の挙動を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。停止フラグファイル検知による安全停止機構を実装。
- 設定管理
  - config.py: 環境変数 / .env 自動読み込み機能を実装（プロジェクトルートの検出は .git または pyproject.toml を使用）。`.env` と `.env.local` の読み込み順序と上書きポリシー（OS環境変数保護）をサポート。多数の設定プロパティ（DB パス、PID/kill フラグ、しきい値、環境判定など）を提供。
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を実装。
  - validate_config.py: .env と config/*.yaml の起動前検証ツールを実装。`--strict` オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコアソート）と等配分・スコア加重配分の関数を追加。スコア合計が 0 の場合に等配分へフォールバックする警告ロジックを実装。
  - portfolio/position_sizing.py: 単元株（lot）丸め、リスクベース・等配分・スコア配分の株数決定ロジック、aggregate cap によるスケールダウン／再配分アルゴリズムを実装。
  - portfolio/risk_adjustment.py: セクター集中上限チェック（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジーム時のフォールバックと警告を追加。
- 監視関連
  - monitoring 初期化呼び出し（init_monitoring_db）を実行スクリプトに組み込み、監視用テーブル存在を保証（冪等）。
- 分析エンジン統合
  - DuckDB 接続を統合（duckdb_path 設定）。research/factor_research.py によるファクター計算基盤を追加（Momentum、Value、Volatility、Liquidity の計算方針を明記）。
- ユーティリティ
  - utils/logging_setup.py: ルートロガー設定ユーティリティを追加（stdout に出す StreamHandler と 日次ローテートの TimedRotatingFileHandler を設定）。既存ハンドラのクリア処理を行い二重設定を防止。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定ユーティリティを追加。アクセス権限や未実装の API 失敗時には警告でフォールバック。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを集計し PASS/FAIL 判定を出力。`--from`/`--to`/`--db` オプションを提供。
- その他
  - PID ファイル、停止フラグ、kill flag 関連のパスや挙動を統一してシステム起動／停止の安全性を向上。

### Changed
- ロギングの挙動を標準化:
  - stdout を利用する StreamHandler を採用（cron 等で stdout/stderr リダイレクトされる運用を考慮）。
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールログのみで継続するよう堅牢化。
- .env ロードの振る舞い:
  - OS 環境変数を保護する protected set を導入。`.env.local` を上書き用に読み込む仕組みを採用。

### Fixed
- 環境変数パースと値検証の堅牢化:
  - _parse_env_line() でクォート付き値・バックスラッシュエスケープ・インラインコメント処理に対応し、より安全に .env を読み込めるよう改善。
  - MONITOR_POLL_INTERVAL の不正値（0 や非数）に対して警告を出しデフォルト値へフォールバックする処理を追加。
- プロセス優先度設定の安全化:
  - psutil による例外（AccessDenied 等）をキャッチして警告を出すことで起動失敗を防止。

### Deprecated
- 特になし（初期リリースのため）。

### Removed
- 特になし（初期リリースのため）。

### Security
- 環境変数の取り扱いにおいてシークレット項目は対話型ウィザードでマスク表示される。`.env` をコミットしない旨の警告を出力。

---

注記:
- research/factor_research.py はファクター計算方針や定数を実装済みだが、ファイル末尾が途中で切れている（実装継続が想定される）。実運用前に追加の単体テスト・検証が推奨されます。
- 実装はコードの現状から推測してまとめたものです。各項目の正確な変更履歴はコミットログを参照してください。