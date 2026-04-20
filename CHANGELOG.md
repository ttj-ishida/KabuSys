# Changelog

すべての注目すべき変更は、Keep a Changelog の形式に従って記載しています。  
このファイルは、コードベースから推測できる機能追加・設計意図・挙動を元に作成しています。

フォーマット:
- Unreleased: 今後の変更予定や既知の注意点
- [0.1.0] - YYYY-MM-DD: 初回リリース（このコードスナップショットに相当）

## [Unreleased]
- 開発中の機能・今後の改善候補
  - research.factor_research の実装続き（スニペットが途中で終わっているため、まだ完成していない箇所あり）。
  - 各モジュールに対する追加テスト、エラーハンドリングの強化、edge-case の補完。
  - 単体テスト・統合テスト、CI ワークフローの整備（コードからは未確認）。
  - 将来的な拡張案:
    - 銘柄ごとの lot_size を stocks マスタで管理する設計（position_sizing の TODO）。
    - price のフォールバックロジック（risk_adjustment の TODO コメント参照）。

---

## [0.1.0] - 2026-04-20

### Added
- 基本パッケージとバージョン情報
  - パッケージ初期バージョンを定義: __version__ = "0.1.0"（src/kabusys/__init__.py）。

- 環境設定・管理
  - Settings クラス（src/kabusys/config.py）を追加:
    - 環境変数から各種設定（J-Quants トークン、kabu API、DB パス、Paper Trading 設定、監視閾値など）を取得。
    - KABUSYS_ENV（development/paper_trading/live）の検証。
    - PAPER_FILL_MODE（instant/partial/never/reject）や PAPER_TRADING_SQLITE_PATH のサポート。
    - 環境判定用プロパティ（is_dev/is_paper/is_live）。
  - 自動 .env ロード機能:
    - プロジェクトルート（.git または pyproject.toml 基準）を探索して .env / .env.local を読み込み（OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
  - .env パース実装はクォート・エスケープ・インラインコメント等に対応。

- 設定ウィザード / バリデーション CLI
  - 対話式 .env 生成ウィザード（src/kabusys/config_setup.py）を追加:
    - 主要設定項目の対話入力、既存 .env の読み込み・上書き、保存機能。
  - 設定検証ツール（src/kabusys/validate_config.py）を追加:
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検査（PyYAML 利用時）。
    - --strict オプションで警告を FAIL 扱いにできる。

- 実行系スクリプト
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）を追加:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用し MockBrokerClient を利用（本番 DB と完全分離）。
    - プロセス優先度を High に設定、PID ファイル管理、停止フラグ（data/stop_requested.flag）による安全停止。
    - ExecutionEngine 起動前に監視テーブルの初期化を行う（init_monitoring_db 呼び出し）。
  - Monitoring 起動スクリプト（src/kabusys/run_monitoring.py）を追加:
    - 環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - ポーリング間隔を MONITOR_POLL_INTERVAL 環境変数で上書き可能（デフォルト 60 秒）。不正値は警告の上デフォルトにフォールバック。
    - 停止フラグ検知でループ終了、KeyboardInterrupt のハンドリング、DB 接続のクリーンアップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - 銘柄候補選定（select_candidates）、等ウェイト（calc_equal_weights）、スコア加重（calc_score_weights）。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - セクター集中制限 apply_sector_cap、レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - allocation_method（risk_based / equal / score）に応じた株数算出。
    - 単元株（lot_size）丸め、per-stock 上限・aggregate 上限、cost_buffer を考慮したスケールダウンアルゴリズムを実装。
    - 将来の拡張点として銘柄別 lot_size のサポートをコメントで示唆。

- ユーティリティ
  - logging_setup（src/kabusys/utils/logging_setup.py）
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定。
    - ログレベル・ログディレクトリは引数、環境変数、デフォルトの順に解決。ディレクトリ作成失敗時はファイル出力をスキップして警告を出す。
  - process_priority（src/kabusys/utils/process_priority.py）
    - Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity 設定関数 set_cpu_affinity を提供。
    - 権限不足や未サポート環境では警告を出してスキップ。

- 監視 / 監査関連
  - 監視 DB 初期化ユーティリティ（init_monitoring_db の使用箇所が存在、実装ファイルは別）との連携を想定。
  - Monitoring と Execution の両スクリプトで監視テーブルの存在を保証（冪等に init_monitoring_db を呼出し）。

- Paper Trading 向けツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）を追加:
    - 指定期間の system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を算出してレポート出力。
    - Pass/Fail 判定閾値を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。
    - DB パスを --db または PAPER_TRADING_SQLITE_PATH 環境変数で指定可能。
    - latency の P95 を計算するユーティリティを実装。

### Changed
- CLI/起動フロー設計
  - すべての起動スクリプトで共通の logging_setup を利用するよう統一。
  - プロセス優先度を起動直後に設定することで、起動中の競合を軽減。

### Fixed
- .env パースの堅牢化（config._parse_env_line）
  - export プレフィックスの扱い、クォート内のバックスラッシュエスケープ、インラインコメント判定の改善により .env の取り扱いバグを低減。

### Security
- .env の取り扱いに関する注意喚起を config_setup.py のコメントに明記（.env を Git にコミットしないこと）。

### Notes / Known issues
- research.factor_research が途中で切れている（実装継続必要）。本リリースの other modules と組み合わせる際は未完成箇所に注意してください。
- position_sizing の price 欠損時（price == 0）は現在スキップされる設計。将来的にフォールバック価格を導入することを推奨。
- process_priority / set_cpu_affinity はプラットフォームや実行ユーザ権限に依存するため、権限不足時にはログに警告が出るのみで動作が継続されます。

---

以上。ご要望があれば、この CHANGELOG をプロジェクトの実際のコミット履歴に合わせて調整（バージョン履歴の分割や日付修正、追加の変更カテゴリ分割など）します。