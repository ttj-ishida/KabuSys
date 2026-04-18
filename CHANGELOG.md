# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースの現状から機能追加・動作仕様を推測して作成しています。

全般的な注意
- 本ログはリポジトリ内のソースコード（src/kabusys 以下）から機能・挙動を推測してまとめたものです。実装の詳細や追加の変更は実際のコミット履歴を参照してください。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-18
初回公開リリース。

### 追加 (Added)
- コアパッケージの追加
  - kabusys パッケージ本体（バージョン 0.1.0）。
- 設定管理
  - 環境変数・.env 自動読み込み機能（kabusys.config）。
    - プロジェクトルート探索（.git または pyproject.toml を基準）により .env/.env.local を自動読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env パースの高機能化（export 付き、クォートとエスケープ、インラインコメント判定など）。
    - OS 環境変数の保護（protected パラメータ）をサポート。
  - Settings クラス（kabusys.config.Settings）で各種設定値を型付近で取得・検証。
    - 環境（KABUSYS_ENV）の厳格チェック（development / paper_trading / live）。
    - データベースパス、PID/kill flag パス、監視閾値、paper_trading 用設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）などのプロパティを提供。
- 設定支援 CLI
  - 対話式 .env 作成/更新ウィザード（kabusys.config_setup）。
    - J-Quants / kabuAPI / DB パス / LOG_LEVEL / Kill Flag の初期設定を対話形式で生成。
    - 既存 .env 読み込み、シークレット値のマスキング表示、保存確認を実装。
- 設定検証 CLI
  - 起動前チェックツール（kabusys.validate_config）。
    - 必須環境変数の確認、KABUSYS_ENV の妥当性チェック、ログレベルチェック、DB パスの親ディレクトリ確認。
    - config/*.yaml の存在確認と（PyYAML がある場合の）パース検証。
    - 本番 (live) 向けの追加警告（LINE 通知設定・KILL_FLAG_CLEAR_ON_START の危険性など）。
    - --strict オプションで警告を失敗扱いにする機能。
- 実行/監視起動スクリプト
  - 実行エンジン起動スクリプト（kabusys.run_execution）。
    - プロセス優先度を高に設定してから起動。
    - 環境により paper_trading 用の専用 SQLite DB を使用（本番 DB と分離）。
    - BrokerClientFactory を利用してブローカークライアントを生成（KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用する旨のドキュメント）。
    - ExecutionEngine をスレッドで実行し、stop flag（data/stop_requested.flag）により安全停止。
    - PID ファイル管理と停止フラグ検知ロジック。
  - 監視ループ起動スクリプト（kabusys.run_monitoring）。
    - 環境にかかわらず本番 sqlite_path を監視 DB として使用。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - stop flag による優雅なループ終了、check_once() 呼び出し時の例外捕捉。
    - DuckDB 接続の初期化（分析用 DB）と監視テーブル初期化の呼び出し。
- ロギング・プロセス管理ユーティリティ
  - 統一ロギング設定ユーティリティ（kabusys.utils.logging_setup）。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app>.log、30日保持）をルートロガーに設定。
    - ログディレクトリ自動作成と作成失敗時のフォールバック（コンソール出力のみ）。
    - ログレベル解決順: 関数引数 > 環境変数 LOG_LEVEL > デフォルト。
  - プロセス優先度/CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）。
    - Windows / POSIX（Linux、Darwin、FreeBSD）に対応した優先度設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定する機能。
    - 権限不足などの失敗時は警告ログ出力してスキップ。
- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - 候補選定・重み計算（portfolio_builder）
    - select_candidates: スコア降順・同点は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合は等分配へフォールバック）。
  - セクター制約・レジーム乗数（risk_adjustment）
    - apply_sector_cap: セクター別既存保有比率に基づき新規候補を除外（unknown セクターは適用除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（未知レジームは 1.0 でフォールバック）。
  - 口数算出・リスク制限・単元丸め（position_sizing）
    - calc_position_sizes: risk_based / equal / score の配分方式をサポート。
    - 単元株（lot_size）に丸め、1 銘柄上限・総資金上限（aggregate cap）のスケーリングと残差処理を実装。
    - cost_buffer により手数料・スリッページを保守的に見積もり。
- 研究用モジュール（kabusys.research）
  - factor_research: ファクター計算用モジュールの骨格。
    - モメンタム（1M/3M/6M）、MA200 乖離、ATR、出来高系等を計画（DuckDB の prices_daily / raw_financials を参照する設計）。
    - 返却は (date, code) ベースの dict リストを想定。
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）。
    - PAPER_TRADING_SQLITE_PATH または --db で指定した SQLite DB を解析し、稼働率・注文成功率（fill）・送信率（send）・レイテンシ（avg/max/P95）・リスク却下数を集計。
    - PASS/FAIL の閾値を定義（稼働率 99%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200 ms）。
    - 日付フィルタ（--from/--to）対応。P95 は独自実装で算出。
- 監視 DB 初期化呼び出し
  - init_monitoring_db の呼び出しが run_execution/run_monitoring で実行され、監視テーブルの存在を保証（冪等）。

### 変更 (Changed)
- -（初回リリースのため該当なし）

### 修正 (Fixed)
- -（初回リリースのため該当なし）

### 削除 (Removed)
- -（初回リリースのため該当なし）

### セキュリティ (Security)
- 環境変数の取り扱いでシークレット項目は対話表示時にマスクする等、運用上の安全性に配慮。
- .env は Git にコミットしない旨をウィザードで明示。

---

注記・既知の注意点（ソースから推測）
- position_sizing の価格が欠損（0.0）の場合にエクスポージャーが過少見積になる可能性があり、将来的にフォールバック価格を導入する旨がコメントされている。
- apply_sector_cap は "unknown" セクターを制限外とする設計になっているため、マスタの整備が不十分だと制約が正しく適用されない恐れがある。
- run_monitoring は Monitoring が環境にかかわらず本番 sqlite_path を使用する点に注意（誤って開発環境で本番 DB を参照しないよう運用での配慮が必要）。
- process_priority / cpu affinity の設定は権限不足やプラットフォーム非対応時に安全にスキップする実装だが、実行環境ごとの挙動確認が必要。

以上。必要であれば、各ファイルごとの詳細な変更点（関数一覧・挙動注釈）も生成します。