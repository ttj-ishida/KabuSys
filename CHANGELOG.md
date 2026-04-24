# Changelog

すべての注目すべき変更を記録します。規約: Keep a Changelog に準拠しています。

最新の変更は最上部に記載しています。

## [Unreleased]

- ドキュメント整備・リファクタ候補
  - DuckDB を用いる分析/計算部分（kabusys.research など）やログ周りの拡張を予定。

---

## [0.1.0] - 2026-04-24

初回リリース。以下はソースコードから推測される主な機能・改善点の概要。

### Added（追加）

- 実行エントリスクリプト
  - ExecutionEngine 起動用スクリプト（src/kabusys/run_execution.py）
    - Paper Trading モード時は MockBrokerClient を使用して本番 DB と分離（data/paper_trading.db）。
    - Engine を別スレッドで実行し、stop フラグによる安全停止をサポート。
    - 実行中の PID を data/execution.pid に保存する想定（pid_file の扱い）。
  - SystemMonitor 起動用スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。
    - 監視ループはプロセス優先度設定・DB 初期化・DuckDB 接続・停止フラグ検知等を行う。

- 設定管理・ウィザード・検証
  - Settings クラスによる環境変数ラッパ（src/kabusys/config.py）
    - .env / .env.local の自動読み込み（プロジェクトルート検出ロジック付き）。
    - 各種プロパティ（DB パス、ログレベル、env 判定、paper_fill_mode のバリデーション等）。
  - 対話式 .env 作成ウィザード（src/kabusys/config_setup.py）
    - 必須/任意項目、デフォルト値、シークレット入力の扱い、.env ファイル書き出し機能。
  - 設定検証 CLI（src/kabusys/validate_config.py）
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在とパース検証、production 向けのガードチェック（LINE 通知等）。

- ロギング・プロセス管理ユーティリティ
  - ロギング初期化ユーティリティ（src/kabusys/utils/logging_setup.py）
    - stdout への StreamHandler と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。
    - LOG_DIR/LOG_LEVEL 優先順に対応し、ディレクトリ作成失敗時はファイル出力をスキップ。
  - プロセス優先度 / CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差分吸収。high/normal/low の優先度設定と最初 N コアへの固定機能（best-effort、権限不足時は警告ログ）。

- ポートフォリオ構築関連（純粋関数群）
  - 候補選定・配分（src/kabusys/portfolio/portfolio_builder.py）
    - スコア降順ソート、等配分・スコア加重配分（スコア合計が 0 の場合のフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - 既存ポジションを考慮したセクター上限チェック、レジームに応じた投下資金乗数（bull/neutral/bear）。
  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の配分方式、単元株丸め、aggregate cap によるスケールダウン（コストバッファ考慮）。
  - 上記をまとめてエクスポートするモジュール（src/kabusys/portfolio/__init__.py）。

- Paper Trading 検証レポート
  - paper_verification_report CLI（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading の SQLite DB を解析して稼働率、注文成功率、送信率、レイテンシ（P95 など）を算出し PASS/FAIL 判定を出力。
    - 日付フィルタ、DB パスの CLI 引数対応、閾値はコード内定義（稼働率 99%、P95 200ms 等）。

- 研究系 / ファクター計算の骨組み
  - ファクター計算モジュールの一部（src/kabusys/research/factor_research.py）を含む（モメンタム等の計算意図と定数が定義されている）。

### Changed（変更）

- .env 読み込みの振る舞い（src/kabusys/config.py）
  - 自動読み込み順を OS 環境変数 > .env.local > .env として、.env.local は既存 OS 環境変数を保護しつつ上書き可能。
  - プロジェクトルートの検出は .git または pyproject.toml を起点に上位ディレクトリを探索する方式に変更（配布後も CWD に依存しない）。

- ログ出力の標準化（src/kabusys/utils/logging_setup.py）
  - コンソール出力は stdout を採用（cron 等で stdout/stderr を統合する運用を考慮）。

- Execution / Monitoring の DB 取り扱い
  - monitoring（SystemMonitor）は KABUSYS_ENV に関係なく監視用 sqlite_path を利用（運用上の意図を明示）。
  - execution は paper_trading 時に PAPER_TRADING_SQLITE_PATH を使用し、本番 DB と完全分離するよう変更。

### Fixed（修正 / 安全性向上）

- 環境変数パーサの堅牢化（src/kabusys/config.py）
  - .env 行パースで export プレフィックス、クォート文字列（引用内のバックスラッシュエスケープ処理）、インラインコメントの扱い等に対応。
  - 不正な行や空行・コメント行をスキップするように改善。

- MONITOR_POLL_INTERVAL のバリデーション（src/kabusys/run_monitoring.py）
  - 0 以下や非整数を検出してデフォルト（60 秒）へフォールバックし、警告ログを出力するようにした（time.sleep への不正値渡しを回避）。

- 各種ベストエフォート処理
  - ログディレクトリ作成失敗、ファイルハンドラ生成失敗、プロセス優先度設定失敗、CPU affinity 設定失敗等については例外を握りつぶして警告を出し、アプリケーションの起動を阻害しないように実装（運用上の堅牢性向上）。

### Documentation（ドキュメント）

- 各モジュールにドキュメンストリングを追加
  - モジュール用途、引数説明、返り値、設計方針、注意事項（例: position_sizing の lot_size 将来的拡張等）が詳細に記載されている。

### Internal / その他

- モジュール構成と命名
  - package の __all__、バージョン定義（__version__ = "0.1.0"）を含む基本的なパッケージメタ情報を追加（src/kabusys/__init__.py）。
- config/*.yaml の検証ロジック（validate_config）で PyYAML が未インストールの場合は警告を出してパース検証をスキップする柔軟性を確保。

---

注:
- 上記はソースコードから推測してまとめた変更点／機能一覧です。実際のコミット履歴やリリースノートと一致しない可能性があります。必要であれば、特定ファイルや機能について、より詳細な CHANGELOG 項目に落とし込むことも可能です。