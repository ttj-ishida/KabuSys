# CHANGELOG

このプロジェクトの変更履歴は Keep a Changelog に準拠しています。  
※以下はリポジトリ内のコード内容から推測して作成したリリースノートです。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-19
初回リリース。本リリースでは自動売買システムのコアユーティリティ、起動スクリプト、設定管理、ポートフォリオ構築ロジック、検証ツールなどの基本機能を実装しました。

### 追加 (Added)
- 全体
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として公開。
  - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を探索）。

- 設定管理
  - Settings クラスによる環境変数ベースの設定取得を実装。必須項目のチェックやデフォルト値の提供を行う。
  - .env 自動読み込み機能を実装（優先順位: OS 環境変数 > .env.local > .env）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
  - `.env` パーサにて以下に対応:
    - export プレフィックス対応
    - シングル/ダブルクォートのエスケープ処理対応
    - 行内コメント処理（クォート有無に応じた正しい処理）
  - Settings 上での入力値検証:
    - `KABUSYS_ENV`（development / paper_trading / live）
    - `LOG_LEVEL`（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - `PAPER_FILL_MODE`（instant/partial/never/reject）など

- 設定補助 CLI
  - config_setup: 対話式ウィザードで `.env` を初期作成・更新する CLI を追加。
    - J-Quants / kabu API / DB パス / LINE 通知 等の設定項目を対話的に入力・保存。
  - validate_config: 起動前に .env と config/*.yaml の整合性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV チェック、ログレベルチェック、DB パスの親ディレクトリ確認、YAML ファイルの存在確認およびパース（PyYAML が利用可能な場合）。
    - `--strict` オプションで警告をエラー扱いにできる。

- 起動スクリプト / ランタイム
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は Paper Trading 用の専用 SQLite DB を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント作成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行う。
    - ExecutionEngine を別スレッドで実行し、プロジェクトルートの停止フラグ（data/stop_requested.flag）を検出して安全に停止する仕組みを実装。
    - 実行時にプロセス優先度を "high" に設定。

  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト: 60 秒）。不正値は警告のうえデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視データを記録。
    - 停止フラグ検知でループを終了。KeyboardInterrupt もハンドルしてクリーンに終了。
    - 実行時にプロセス優先度を "high" に設定。

- ロギング / プロセス制御ユーティリティ
  - logging_setup: ルートロガーを統一的に設定するユーティリティを追加。
    - コンソール出力は stdout を使用（StreamHandler）。
    - 日次ローテーションのファイル出力（TimedRotatingFileHandler）をサポートし、デフォルトで `logs/` に `<app_name>.log` を出力。ディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラをクリアして二重登録を防止。
  - process_priority: クロスプラットフォームでのプロセス優先度 / CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX 系 (Linux / macOS / FreeBSD) を吸収し、psutil を利用して nice 値や優先度クラスを設定。アクセス権限不足等は警告でスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選抜。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア正規化配分を実装。スコア合計が 0 の場合は等金額配分にフォールバックして警告を出す。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限 (max_sector_pct) を適用して候補をフィルタリング。既存ポジションのセクター別時価を計算して制限を判断（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知のレジームは 1.0 でフォールバックし警告を出す。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づいて発注株数を決定。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、総投下上限（available_cash）を考慮。必要に応じてスケーリングと残余の再配分を行う。
    - cost_buffer を用いた手数料・スリッページの保守的見積もりを実装。
    - risk_based 方式では risk_pct / stop_loss_pct に基づくポジションサイズ算出。

- 研究 / ツール
  - research.factor_research: DuckDB を用いたファクター計算モジュールを追加（モメンタム/MA/ATR 等を想定）。設計方針と定数を定義。モメンタム計算関数の骨組みを実装（ファイル末尾は一部未完）。
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計してレポート出力。
    - PASS/FAIL のしきい値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。
    - 日付フィルタ（--from / --to）と DB パス指定（--db）をサポート。

### 変更 (Changed)
- 起動時のプロセス優先度設定を起動スクリプトの最初に行うように統一（run_execution/run_monitoring）。
- logging_setup でログディレクトリ作成に失敗した場合の挙動を明確化（ファイルハンドラをスキップしてコンソールのみで継続）。

### 注意 / 実装メモ
- config/.yaml の検証は PyYAML がインストールされていない場合はスキップされる（validate_config が警告を出す）。
- apply_sector_cap 内の価格欠損（price が 0.0）を扱う TODO があり、将来的にフォールバック価格（前日終値など）を導入する想定。
- position_sizing の将来拡張点: 銘柄ごとの lot_size をサポートするための設計変更（コメントで表明）。
- research.factor_research モジュールは設計・定数は整っているが、一部関数実装が途中で終了している（ファイル末尾が未完）。
- run_monitoring は監視 DB に常に本番用 sqlite_path を使用する設計（環境に依存しない監視を意図）。

### 削除 (Removed)
- なし

### 廃止予定 (Deprecated)
- なし

### セキュリティ (Security)
- なし

---

変更点や実装方針に誤りや補足が必要であれば、どのファイル・機能に関してかを指定していただければ、追記・修正した CHANGELOG を作成します。