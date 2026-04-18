# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このファイルでは主にコードベースから推測した機能追加・仕様・挙動をまとめています。

## [0.1.0] - 2026-04-18

### 追加 (Added)
- パッケージ初期リリース相当の主要コンポーネントを追加。
  - 実行用スクリプト
    - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV が `paper_trading` の場合はペーパートレード用 DB/モックブローカーを使用する（data/paper_trading.db を想定）。
    - run_monitoring.py: SystemMonitor のポーリングループを起動するエントリポイント。MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応。監視は環境にかかわらず本番 sqlite_path を使用する仕様。
  - 設定関連
    - config.py: Settings クラスによる環境変数ラッパーを導入。自動 .env ロード（プロジェクトルートの .env / .env.local、OS 環境変数の保護、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）と多くの設定プロパティを提供（J-Quants / kabuAPI / DB パス / 各種しきい値など）。
    - config_setup.py: 対話式 .env 作成・更新ウィザード（CLI）。
    - validate_config.py: 起動前の設定検証 CLI。必須環境変数、KABUSYS_ENV・LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在/パース確認、`--strict` モードをサポート。
  - ユーティリティ
    - utils/logging_setup.py: 標準化されたロギング設定ユーティリティ。stdout ストリームハンドラと日次ローテートされたファイル出力を設定。LOG_DIR/LOG_LEVEL の解決・ディレクトリ作成失敗時のフォールバックなどを備える。
    - utils/process_priority.py: プロセス優先度および CPU affinity 設定ユーティリティ。Windows / POSIX の差を吸収して set_process_priority / set_cpu_affinity を提供。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py: 候補選定(select_candidates)、等金額重み(calc_equal_weights)、スコア加重(calc_score_weights) を実装。
    - portfolio/position_sizing.py: 発注株数計算（calc_position_sizes）。risk_based / equal / score の配分方式、lot_size・コストバッファ・aggregate cap に基づくスケーリングや端数処理を実装。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに基づく乗数(calc_regime_multiplier) を実装。
  - リサーチ
    - research/factor_research.py: ファクター計算モジュール（モメンタム / MA / ATR / 流動性等）の骨組みを追加（DuckDB 接続を受け SQL/Python で処理する設計、モメンタム計算関数の実装開始）。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプト。system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ等を集計し PASS/FAIL を判定する。閾値（稼働率99%、成立率90%、送信率95%、P95 latency 200ms）を定義。
  - パッケージ初期化
    - __init__.py: パッケージバージョン `__version__ = "0.1.0"` を追加。

### 変更 (Changed)
- 環境変数読み込みの挙動を整理
  - 自動ロード順序: OS 環境 > .env.local > .env。OS 環境変数は保護され .env/.env.local によって上書きされない。
  - .env のパース強化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、コメントルール改良などを実装。
- run_* スクリプトの起動時に共通処理を導入
  - setup_logging(app_name=...) による統一ログ設定。
  - set_process_priority("high") による優先度設定（できる環境のみ）。
  - DB 接続時に monitoring 用テーブルを冪等に初期化する init_monitoring_db の呼び出しを追加。
- Execution / Monitoring の DB 分離ポリシー
  - 実行エンジンは paper_trading 環境のとき paper_sqlite_path（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
  - 監視プロセスは環境にかかわらず settings.sqlite_path（デフォルト: data/monitoring.db）を使用。
- ポートフォリオ計算の挙動改善
  - calc_score_weights: 全銘柄スコアが 0 の場合は等金額配分にフォールバックして警告ログを出力。
  - calc_position_sizes: lot_size 単位での丸め、per-position の上限チェック、aggregate cap によるスケールダウン（端数の再配分ロジック）を実装。価格欠損時のスキップやコストバッファの考慮あり。
- apply_sector_cap の設計
  - "unknown" セクターはセクター上限チェックの対象外として扱い、誤って除外されにくくした。

### 修正 (Fixed)
- 環境変数値の妥当性チェックやフォールバックを強化
  - MONITOR_POLL_INTERVAL に不正値（0 や負、非整数）が設定されていた場合にデフォルト（60秒）にフォールバックして警告ログを出すようにした。
  - Settings.paper_fill_mode において無効なモードが設定された場合に ValueError を投げるようにして早期検出。
  - Settings.env / Settings.log_level の不正値検出を追加（ValueError を送出）。
- ロギング設定でログディレクトリ作成に失敗してもプロセスが継続できるようにフォールバック実装（ファイルハンドラをスキップしてコンソールのみで継続）。
- process_priority の実行時エラー（権限不足など）を捕捉して警告ログに変換、プロセス継続可能にした。

### 非互換性 (Breaking Changes)
- 直接の破壊的変更は意図的には行っていませんが、設定読み込みの自動化や環境変数の保護ルールにより、以前の期待動作と異なる動作をする可能性があります:
  - .env の上書きルール: OS 環境変数は常に優先され、.env.local/.env による上書きが抑止されます（意図的な保護）。
  - Settings クラスは一部プロパティで不正値に対し ValueError を投げます。起動スクリプトはこの例外を捕捉していない場合、起動失敗となるため事前に validate_config を実行することを推奨します。

### ドキュメント / 使い方（補足）
- CLI/ツール
  - .env 作成: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - 実行エンジン起動: python -m kabusys.run_execution
  - 監視起動: python -m kabusys.run_monitoring
  - Paper 検証レポート生成: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 重要な環境変数（主要）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - DUCKDB_PATH（DuckDB ファイル、デフォルト: data/kabusys.duckdb）
  - LOG_LEVEL / LOG_DIR / MONITOR_POLL_INTERVAL / PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番でのアラート用）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env の自動ロードを無効化可能（テスト時に便利）

### セキュリティ (Security)
- シークレット値（J-Quants トークン、kabu API パスワード、LINE トークン等）は .env に保存する想定。config_setup の出力に注意し、.env を絶対に Git 等にコミットしないことを明記。

---

今後の予定（想定）
- research/factor_research のファクター群（Value/Volatility/Liquidity）の完全実装とユニットテスト追加。
- ExecutionEngine / Monitoring の統合テスト、ブローカークライアント抽象化のユニットテスト強化。
- 銘柄別単元（lot_size）をマスタに持たせるなど position_sizing の拡張。
- config/*.yaml のスキーマ定義と厳密なバリデーション（現状はファイル存在と YAML パースのみ）。

（注）本 CHANGELOG は提供されたコードベースからの推測に基づいて作成しています。実際のコミット履歴や開発の意図とは差異がある場合があります。必要であれば実コードを元に差分を確認して調整できます。