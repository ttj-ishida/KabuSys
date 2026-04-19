# Changelog

すべての変更は「Keep a Changelog」形式に従って記載しています。  
このファイルはリポジトリ内のコードから推測した変更点・機能一覧をもとに作成しています（実際のコミット履歴とは異なる場合があります）。

フォーマット:
- Unreleased: 今後の変更
- 各バージョン: リリース日（推定: 本ファイル作成日）

注意: 実装の一部（例: research/factor_research の一部関数）は未完/途中実装の箇所が含まれます。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 全体
  - 初期リリース。日本株自動売買システム "KabuSys" の基本モジュール群を提供。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト / ランタイム
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を利用し、Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を使用する（本番 DB と完全分離）。
    - プロセス優先度を起動直後に High に設定する仕組みを組み込む。
    - stop_requested.flag による外部停止フラグ検知を実装。デーモンスレッドでエンジンを実行し、フラグ検知時に停止させるロジックを提供。
    - 起動時に監視テーブルの初期化を保証（init_monitoring_db 呼び出し、冪等処理）。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックする。
    - monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する（監視用 DB を明示的に本番パスで扱う）。
    - stop_requested.flag による停止処理を実装。
    - SQLite / DuckDB 接続を作成し、終了時にクローズする。

- 設定・環境管理
  - config.py
    - Settings クラスを導入し、環境変数経由の設定を統一的に取得する API を提供。
    - `.env` 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。`.env.local` は `.env` 上書き、ただし OS 環境変数は保護（protected）される。
    - 環境変数パース実装（クォート/エスケープ/コメント処理など）を独自で実装して安全な読み込みを提供。
    - 各種設定プロパティ:
      - J-Quants / kabu API トークン取得
      - DB パス (DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH)
      - PAPER_FILL_MODE の検証（有効値: instant/partial/never/reject）
      - PID/kill flag パス、しきい値 (CPU/MEM/DISK) 等
      - KABUSYS_ENV の検証（development/paper_trading/live）
      - LOG_LEVEL の検証
      - is_live / is_paper / is_dev ヘルパー

  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - J-Quants / kabu パスワード等のシークレット取り扱い、選択肢表示、既存値の再利用、保存前の確認を実装。
    - デフォルト値や説明文を含む項目定義を提供。

  - validate_config.py
    - 起動前に .env や config/*.yaml の設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 検証、ログレベル検証、DB パス存在チェック（親ディレクトリ）、config YAML の存在とパースチェック（PyYAML があれば内容検証）、本番環境向けガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
    - `--strict` オプションで警告も FAIL 扱いにするオプションを提供。

- ロギング・ユーティリティ
  - utils/logging_setup.py
    - 全アプリケーションで共通に使えるロギング設定ユーティリティを実装。
    - stdout へ出力する StreamHandler と、日次ローテートする TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30 日保持）をルートロガーに設定。
    - 既存ハンドラの重複登録防止（再設定時は既存を flush/close して削除）。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップし、stdout のみで継続。

- プロセス制御ユーティリティ
  - utils/process_priority.py
    - Windows/Linux/macOS の差を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を設定するユーティリティを実装。
    - CPU affinity 設定用 set_cpu_affinity を提供（N コアに固定）。
    - 権限不足や未対応 OS の場合は警告を出して処理をスキップする設計。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルから候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコアが全て 0 の場合は等分配にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有のセクター比率が上限を超える場合、新規候補を除外）。
    - market レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をマップ、未知のレジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - weight と候補を受けて各銘柄の発注株数を計算する calc_position_sizes を実装。
    - `risk_based`, `equal`, `score` の allocation_method をサポート。
    - 単元株（lot_size）丸め、per-position max, aggregate cap によるスケーリング、コストバッファの考慮、残差処理（lot 単位での追加配分）を実装。

- 解析/検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から指標を集計して検証レポートを生成する CLI を追加。
    - 指標:
      - 稼働率（system_status テーブル）
      - 注文成功率 / 送信率（trade_logs テーブル）
      - リスク却下数（risk_logs）
      - レイテンシ（平均 / 最大 / P95。P95 は集合値から算出）
    - PASS/FAIL 基準値を定義（稼働率 >= 99%, 成立率 >= 90%, 送信率 >= 95%, P95 <= 200ms）。
    - コマンドライン引数 `--from`, `--to`, `--db` をサポート。

- リサーチ（ファクター計算）
  - research/factor_research.py
    - DuckDB の prices_daily/raw_financials を用いたファクター計算モジュールを追加（モメンタム / MA / ATR / Liquidity 等を想定）。
    - calc_momentum の初期実装（関数定義、定数、設計方針）を含むが、一部実装は未完（ファイル末尾が途中で切れている）。

### 変更 (Changed)
- なし（初回リリースのため「追加」が中心）

### 修正 (Fixed)
- なし（初回リリースのため既存バグ修正履歴はなし。ただし各モジュールでエラー時に警告／例外処理を行う設計を採用）

### 廃止 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- なし（機密情報は .env のシークレット項目として扱う設計。`.env` は絶対に Git にコミットしない旨の注意書きを config_setup に記載）

---

補足メモ（実装上の注意・既知点）
- config.py の自動 .env ロードはプロジェクトルートの検出に依存するため、配布後や CWD が異なる場合の動作に注意が必要（プロジェクトルートが見つからないと自動ロードをスキップする）。
- process_priority の優先度変更や cpu_affinity の設定は権限や OS に依存し、失敗時は警告を出してスキップする安全設計。
- portfolio/position_sizing の価格欠損（price が 0.0）の扱いに TODO コメントが存在。将来的に前日終値や取得原価でのフォールバックが検討される。
- research/factor_research.py は計算ロジックの大枠があるものの、末尾が途切れており完全実装ではないため実運用には追加実装が必要。

もし実際のコミット履歴やリリース日が必要であれば、git の履歴を基に正確な CHANGELOG を生成できます。必要であればその手順・出力もサポートします。