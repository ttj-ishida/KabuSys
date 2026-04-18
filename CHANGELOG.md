# Changelog

すべての注記は Keep a Changelog 準拠の形式で記載しています。重要な変更点、追加機能、CLI、既知の動作などをまとめています。

フォーマット:
- バージョンごとにセクションを分け、Added/Changed/Fixed/Deprecated/Removed/Security のカテゴリで記載します。

## [Unreleased]

(現時点での作業中の変更はここに記載してください)

---

## [0.1.0] - 2026-04-18

初回公開リリース。主要なモジュールおよび CLI を実装しました。日本株自動売買システム「KabuSys」の基本機能群が含まれます。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として追加。

- 起動スクリプト / デーモン類
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを実装。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite（data/paper_trading.db 等）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動・停止ロジックを実装。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) の扱いを実装。
    - RiskManager のデフォルト設定（max_position_pct 等）をデフォルトで適用し、初期ポートフォリオ価値を broker.get_available_cash() から取得。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値はログ警告を出してデフォルトへフォールバック。
    - 監視（monitoring）は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する旨を明記。
    - 停止フラグ (data/stop_requested.flag) によりループを終了。

- 設定管理
  - config.py
    - .env 自動読込機能（プロジェクトルート検出: .git または pyproject.toml を基準）を実装。
    - .env の読み込みは OS 環境変数を保護する仕組み（protected）で行う。
    - 複数の設定プロパティ（J-Quants / kabu API / DB パス / PID・kill フラグ / thresholds / env/log レベル検証等）を提供。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等 paper_trading 向け設定を追加。
    - Settings クラスとグローバル `settings` インスタンスを提供。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を実装。
    - 標準的な設定項目（KABUSYS_ENV・JQUANTS_REFRESH_TOKEN・KABU_API_PASSWORD・DB パス・LINE 通知等）をガイド付きで入力可能。
    - 既存 .env の読み込み / 値のマスク表示（シークレット） / 確認保存機能を実装。

  - validate_config.py
    - 起動前に .env と config/*.yaml の設定を検証する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在と（PyYAML があれば）パース検証、本番環境向け追加ガードなどを実装。
    - `--strict` フラグで警告を FAIL として扱うモードを提供。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - 候補選定 select_candidates（スコア降順、同点は signal_rank でブレーク）を実装。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全銘柄のスコアが 0 の場合は等金額にフォールバック）を実装。

  - portfolio.risk_adjustment
    - セクター集中制限 apply_sector_cap（既存保有のセクター別時価を計算して上限を超えるセクターの新規候補を除外）を実装。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" を map）を実装（未知レジームは 1.0 にフォールバック）。

  - portfolio.position_sizing
    - 各銘柄の発注株数を決定する calc_position_sizes を実装。
    - allocation_method に "risk_based" / "equal" / "score" をサポート。lot_size（単元株）単位で丸め、per-position 上限 / aggregate cap（available_cash を超える場合のスケーリング）を考慮。
    - cost_buffer による保守的見積もり（スリッページ・手数料）と、スケーリング後の残差に基づく再配分アルゴリズムを実装。

  - portfolio パッケージのエクスポート設定を追加。

- ユーティリティ
  - utils.logging_setup
    - 共通のロギング設定ユーティリティを実装。
    - stdout への StreamHandler（cron 等で一元的に出力を扱いやすくするため stderr ではなく stdout）と、日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ動作するフォールバックを実装。
    - 既存ハンドラのクリーンアップ（flush/close の後削除）を行うため、多重設定を防止。

  - utils.process_priority
    - プラットフォームに依存しないプロセス優先度設定を提供（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
    - set_cpu_affinity によりプロセスを先頭 N コアにピン留めする機能を実装（失敗時は警告ログでスキップ）。
    - アクセス権限不足等で設定できない場合は警告を出して安全にスキップ。

- 監視関連
  - monitoring.monitoring_db の初期化呼び出し（init_monitoring_db）を run_execution/run_monitoring で保証（監視テーブルが存在することを冪等的に確保）。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用 SQLite DB（PAPER_TRADING_SQLITE_PATH で指定可）を解析し、稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などの検証レポートを生成する CLI を実装。
    - デフォルトの合格基準（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ ≤ 200ms）を定義。
    - 日付フィルタ (--from / --to)、DB パス指定 (--db) をサポート。データ不足やテーブル欠如時には N/A を扱う実装。

- 研究用モジュール（初期実装）
  - research.factor_research
    - DuckDB 上の prices_daily / raw_financials を用いたファクター計算の基本設計およびモメンタム指標（1M/3M/6M リターン、MA200 乖離等）計算の実装開始（モジュール全体はファイル末尾にて継続実装の余地あり）。
    - 計算窓やスキャン範囲の定義、Pandas/SQL の併用で高パフォーマンスに計算する方針を採用。

### Changed
- ログ出力関連
  - 既存ハンドラを強制的にクリアしてから再設定することで、多重ハンドラ登録による重複ログ出力を防止。

- .env 読み込みの優先順位明確化
  - 自動ロード順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。

### Fixed
- .env パーサの堅牢化
  - export KEY=val 形式に対応。
  - シングル/ダブルクォート内のバックスラッシュエスケープに対応して、閉じクォートまで正しく解釈する実装を導入。
  - クォート無し値のインラインコメント判定（# の前に空白がある場合のみコメント扱い）を実装。

- run_monitoring のポーリング間隔処理
  - MONITOR_POLL_INTERVAL に不正な値（0 や負値、非数）が設定された場合は警告ログを出し、デフォルト 60 秒にフォールバックする安全化。

### Known issues / Notes
- research.factor_research 内の実装は一部で途中（ファイル末尾が途中で切れている）です。ファクター計算ロジックの続きは今後実装予定です。
- apply_sector_cap の資産評価に使う price が 0.0（欠損）の場合にエクスポージャーが過小見積りされる懸念があり、将来的に前日終値や取得原価等のフォールバック価格導入を検討しています（コードの TODO に記載）。
- process_priority / set_cpu_affinity は権限やプラットフォームの差異により成功しない場合があり、その場合は警告ログでスキップします。特に Windows と POSIX での定数の違いは考慮済み。

### Breaking Changes
- 初回リリースのため互換性破壊はありません。

### Security
- 既知のセキュリティ問題はありません。シークレット（トークン・パスワード）は .env に保存する設計のため、.env をリポジトリにコミットしないよう注意喚起（config_setup にも同様の注記あり）。

---

変更履歴は今後の開発で更新します。リリースごとに Added/Changed/Fixed 等を追記してください。