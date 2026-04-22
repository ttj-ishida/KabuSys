# Changelog

すべての重要な変更は "Keep a Changelog" のフォーマットに準拠して記載しています。  
このファイルはコードベース（初期リリース相当）の内容から推測して作成しています。

## [Unreleased]

（なし）

## [0.1.0] - 初期リリース（推定）

### 追加 (Added)
- 基本アプリケーションパッケージを追加（kabusys）。
  - バージョン: 0.1.0（src/kabusys/__init__.py）
- 実行用スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV に応じた挙動:
      - paper_trading の場合は MockBrokerClient を使用し、専用の PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録して本番 DB と完全分離。
    - プロセス優先度を "high" に設定（set_process_priority を呼び出し）。
    - SQLite（paper_trading 用は分離）と DuckDB に接続。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立ててセッションをスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）および pid ファイル（data/execution.pid）に対応。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグを検知して安全終了。KeyboardInterrupt にも対応。
- 環境設定・検証ツールを追加
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI。
    - 入力項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、各種パス、LINE トークンなど）を定義。
    - シークレットのマスク表示、デフォルト値のサポート、保存確認を実装。
  - validate_config.py
    - .env や config/*.yaml の基本検証ツール。
    - 必須/任意環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ確認、YAML パース（PyYAML がある場合）、本番環境向けのガードチェック等を実装。
    - --strict モードで警告も FAIL 扱いにできる。
- 設定管理モジュール（config.py）
  - .env 自動読み込み機能（プロジェクトルートを .git / pyproject.toml で検出）。
  - .env / .env.local の読み込み順（OS 環境変数を保護）。
  - .env パーサ: export プレフィックス、クォート（シングル／ダブル）、バックスラッシュエスケープ、インラインコメント処理などに対応。
  - Settings クラスで環境変数に基づくプロパティを提供（パス解決、紙トレ用 DB パス、PAPER_FILL_MODE 検証、閾値等）。
- ロギングユーティリティ（utils/logging_setup.py）
  - ルートロガー設定ユーティリティを提供（setup_logging）。
  - stdout への StreamHandler（stdout 使用）と日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）を設定。
  - LOG_DIR 作成失敗時はファイル出力をスキップしてコンソールのみで継続。
- プロセス優先度・CPU affinity ユーティリティ（utils/process_priority.py）
  - Windows / POSIX 差分を吸収してプロセス優先度を設定（high/normal/low）。
  - CPU affinity を最初の N コアにピン留めする set_cpu_affinity を提供。
  - 権限不足や未対応 OS の場合は警告を出してスキップ。
- ポートフォリオ構築モジュール（portfolio）
  - portfolio_builder.py
    - select_candidates: スコア降順 + signal_rank によるタイブレークでの候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア全て 0 の場合は等金額にフォールバック）。
  - risk_adjustment.py
    - apply_sector_cap: セクター別上限（max_sector_pct）に基づく候補除外。unknown セクターは上限対象外。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームは警告して 1.0 フォールバック）。
  - position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") による発注株数計算。
    - 単元（lot_size）で丸め、per-position 上限・aggregate cap（available_cash）でスケーリング、cost_buffer を考慮した保守的計算、残差に基づく追加配分ロジックを実装。
- Paper Trading 検証レポートツール（tools/paper_verification_report.py）
  - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH / --db）から各種指標を集計してレポート出力。
  - 指標例: システム稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）、リスク却下数等。
  - CLI オプション: --from, --to（日付フィルタ）, --db。閾値による PASS/FAIL 判定を出力。
- research モジュール（一部）
  - factor_research.py のモメンタム計算関数 calc_momentum（DuckDB を用いた prices_daily 参照）、および計算に使う定数群を追加（設計方針・説明コメント含む）。
- モニタリング DB 初期化フック
  - init_monitoring_db を呼んで監視テーブルの存在を保証する処理を監視・実行スクリプトで実行。

### 変更 (Changed)
- ログハンドラの初期化ロジックを統一
  - 既存ハンドラがあれば flush/close してから削除し再設定することで二重設定を防止。
- .env 読み込みロジック
  - プロジェクトルート探索を __file__ ベースで行い、CWD に依存しない自動ロードに変更。

### 修正 (Fixed)
- MONITOR_POLL_INTERVAL の不正値（0 や負値、数値でない文字列）に対するフォールバック処理を追加（警告出力）。
- position_sizing のスケーリングロジックで lot_size 単位で丸める際の端数配分アルゴリズムを実装し、残余資金を有効活用する振る舞いを確保。

### 注意事項 / マイグレーション (Notes)
- .env ファイルは自動読み込みされる（.env → .env.local の順、OS 環境変数を保護）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番稼働時は KABUSYS_ENV=live を設定することで追加のガードチェックが有効になります（LINE 設定や KILL_FLAG_CLEAR_ON_START の注意喚起等）。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と明確に分離されます。PAPER_TRADING_SQLITE_PATH を設定して使用してください。
- ログ出力先ディレクトリの作成に失敗するとコンソールのみの出力になります。運用環境では logs/ ディレクトリへの書き込み権限を確認してください。
- process_priority の設定は OS 権限に依存します。権限不足時は警告が出て設定はスキップされます。

---

この CHANGELOG はソースコードからの推測に基づいて作成しています。実際の変更履歴やリリースノートが必要な場合は、コミット履歴やリリース管理情報（タグ・日付）を参照して正確な履歴に更新してください。