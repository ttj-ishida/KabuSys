# CHANGELOG

すべての重要な変更点を Keep a Changelog のフォーマットに従って日本語で記載します。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 削除 (Removed)
- 非推奨 (Deprecated)
- セキュリティ (Security)

※ 内容は現在のコードベースから推測して作成しています。

## [Unreleased]

（今後の変更をここに記載してください）

---

## [0.1.0] - 2026-04-18

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装。

### Added
- 基本情報
  - パッケージメタ情報を `src/kabusys/__init__.py` に追加（__version__ = "0.1.0"）。
- 設定関連
  - Settings クラス (`src/kabusys/config.py`)
    - 環境変数から各種設定を取得するプロパティ群を実装（J-Quants、kabuAPI、LINE、DBパス、監視閾値、実行環境 判定等）。
    - .env の自動読み込み機能を実装（プロジェクトルートの検出: .git / pyproject.toml を基準、.env/.env.local の読み込み、OS 環境変数の保護）。
    - `.env` の自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応。
  - .env パーサーの実装（引用符付き値、export プレフィックス、インラインコメント処理に対応）。
- 設定ユーティリティ / CLI
  - 対話式設定ウィザード (`src/kabusys/config_setup.py`)
    - `.env` の初期作成・更新を支援する CLI。
    - J-Quants / kabu API 等の必須項目、デフォルト値、シークレット扱い等をサポート。
  - 設定検証 CLI (`src/kabusys/validate_config.py`)
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック。
    - config/*.yaml の存在チェックおよび PyYAML があればパース検証を行う。
    - 本番（live）向けの追加ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告）。
- 実行スクリプト
  - 実行エンジン起動スクリプト (`src/kabusys/run_execution.py`)
    - プロセス優先度設定、SQLite/ DuckDB 接続、paper_trading 環境時の専用 DB 分離、BrokerClientFactory によるブローカー生成。
    - Engine の起動/監視ループ、停止フラグ（data/stop_requested.flag）による安全停止、PID ファイル管理。
    - RiskManager / OrderManager / Reconciler の組み立てと ExecutionEngine 起動処理。
  - 監視（SystemMonitor）起動スクリプト (`src/kabusys/run_monitoring.py`)
    - プロセス優先度設定、監視用 SQLite DB 初期化（本番 sqlite_path を常に使用）、DuckDB 接続、SystemMonitor のポーリングループ。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）、停止フラグ検出による終了。
- 監視 DB 初期化呼び出しの整備
  - `init_monitoring_db` を両スクリプトで呼び出し、監視テーブルの存在を保証（冪等）。
- ロギング / プロセス制御ユーティリティ
  - ロギング設定ユーティリティ (`src/kabusys/utils/logging_setup.py`)
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - ログディレクトリ自動作成、環境変数 `LOG_DIR` / `LOG_LEVEL` の解決、既存ハンドラのクリア処理を実装。
    - ファイルハンドラ作成失敗時はコンソールのみで継続するフォールバックを実装。
  - プロセス優先度制御ユーティリティ (`src/kabusys/utils/process_priority.py`)
    - Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity 固定機能（最初の N コアに固定）を実装（権限不足や未対応 OS は警告でスキップ）。
- ポートフォリオ構築モジュール
  - portfolio_builder (`src/kabusys/portfolio/portfolio_builder.py`)
    - シグナルの候補選別（スコア降順、タイブレークルール）、等金額配分・スコア加重配分の計算関数を実装。
  - risk_adjustment (`src/kabusys/portfolio/risk_adjustment.py`)
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
    - unknown セクターの扱いや、レジーム未知時のフォールバックなどの挙動を定義。
  - position_sizing (`src/kabusys/portfolio/position_sizing.py`)
    - allocation_method（risk_based / equal / score）に基づく株数算出ロジックを実装。
    - 単元株（lot_size）での丸め、1銘柄上限、aggregate cap（available_cash に対するスケーリング）、cost_buffer による保守的見積りを実装。
    - スケールダウン時の残差処理（fractional remainder に基づく追加配分）を実装。
  - portfolio パッケージエクスポートを提供 (`src/kabusys/portfolio/__init__.py`)。
- リサーチ / ファクター計算（基礎実装の開始）
  - `src/kabusys/research/factor_research.py` にモメンタムなどのファクター計算設計と一部定数・関数の土台を実装（DuckDB 接続を想定）。※ ファイル末尾で途中実装の痕跡あり（未完の関数あり）。
- ツール
  - Paper Trading 検証レポート生成 (`src/kabusys/tools/paper_verification_report.py`)
    - paper_trading 用 SQLite DB から稼働率、注文成功率、送信率、レイテンシ（P95 など）を集計してコンソールにレポート出力。
    - 閾値定義（稼働率 99%、注文成功率 90% 等）と Pass/Fail 判定ロジックを実装。
    - コマンドライン引数: --from / --to / --db に対応。環境変数 PAPER_TRADING_SQLITE_PATH をサポート。
- その他
  - tools パッケージ初期化ファイルを追加 (`src/kabusys/tools/__init__.py`)。
  - utils パッケージ初期化ファイルを追加 (`src/kabusys/utils/__init__.py`)。

### Changed
- ログ出力先のポリシー
  - StreamHandler は stdout を使用して stdout/stderr のリダイレクト運用を容易にする設計に変更。
- .env 読み込み順序の明確化
  - OS 環境 > .env.local > .env の優先度で読み込む実装。
- DB パスの扱い
  - paper_trading 環境では paper_sqlite_path を使用して本番 DB と分離するよう実装。

### Fixed
- エラー耐性の強化
  - run_monitoring のループ内および run_execution のスレッド監視で例外発生時にログを残して次ループへ継続するようにした（監視・実行の耐障害性向上）。
  - ログディレクトリ作成失敗時にファイルハンドラ作成をスキップし、プロセスが停止しないように修正。

### Removed
- （今回のコードベースでは明示的な削除は無し。初期リリースのため該当なし）

### Deprecated
- （該当なし）

### Security
- .env は Git にコミットしないよう .env 作成ヘッダで明示（config_setup に注意書き）。
- 必須環境変数未設定時に ValueError で明確に失敗させる設計により、秘密情報の未設定を検出しやすくしている。

---

補足 / 既知の注意点（コードベースからの推測）
- `research/factor_research.py` の一部関数が途中で終わっている箇所があり、実装途中であることがうかがえます（将来的な拡張予定）。
- position sizing の価格欠損（price が 0.0）の扱いについて TODO コメントあり：フォールバック価格（前日終値や取得原価）を使う検討が必要。
- process priority / cpu affinity は権限やプラットフォーム依存のため、権限不足時には警告を出して安全にスキップする実装になっています。
- validate_config は PyYAML 非インストール時に YAML 内容の検証をスキップする仕様です（警告表示）。

以上。今後のリリースでは機能追加（ファクター群の完全実装、戦略詳細の実装、テスト・CI の整備、ドキュメントの拡充など）を CHANGELOG に追記してください。