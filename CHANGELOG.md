# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このファイルは、コードベースから推測される機能追加・設計意図・注意点を元に作成しています。

全体方針:
- バージョンはパッケージ内の __version__ に合わせて 0.1.0 を初回リリースとしています。
- コード中の CLI やユーティリティ群、ポートフォリオ構築ロジック、監視/実行エンジン起動スクリプト等をまとめて記載しています。

## [Unreleased]
- （現状なし）

## [0.1.0] - 2026-04-22

Added
- 基本アプリケーション構成と CLI／ユーティリティ群を追加。
  - パッケージバージョン: 0.1.0 (`src/kabusys/__init__.py`)
- 環境設定管理
  - .env ファイル自動読み込み（プロジェクトルートの検出: .git または pyproject.toml を基準）を実装。OS 環境変数を保護しつつ .env/.env.local を読み込む仕様（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。詳細: `src/kabusys/config.py`
  - .env パースの強化:
    - `export KEY=val` 形式対応
    - シングル/ダブルクォート値のバックスラッシュエスケープ処理対応
    - クォートなし行でのインラインコメント（直前が空白/タブの場合のみ）処理
- Settings クラスによる環境変数ラッパーを追加（プロパティ経由で各設定を取得）。
  - KABUSYS_ENV のバリデーション（development/paper_trading/live）
  - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）
  - DB パス、PID/kill flag、閾値等のプロパティを提供（デフォルト値あり）
- 設定ウィザード CLI を追加
  - `python -m kabusys.config_setup` で対話的に .env を作成/更新可能。書き込み処理は安全設計（既存値の再利用、シークレット値のマスク表示）。 (`src/kabusys/config_setup.py`)
- 設定検証 CLI を追加
  - `python -m kabusys.validate_config` で .env と config/*.yaml の存在・基本妥当性チェック。`--strict` オプションで警告も失敗扱いにできる。YAML パーサが無ければ YAML 内容チェックはスキップ。 (`src/kabusys/validate_config.py`)
- 起動スクリプトを追加
  - 監視ループ: `src/kabusys/run_monitoring.py`
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用。
    - 停止フラグファイル（data/stop_requested.flag）を検知してループ終了。
    - プロセス優先度を起動時に "high" に設定。
  - 実行エンジン起動: `src/kabusys/run_execution.py`
    - KABUSYS_ENV=paper_trading の場合は専用の Paper DB（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカクライアント生成、OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine を起動。
    - 停止フラグでセッションを安全に停止、PID ファイルを扱う設計。
- ロギング基盤を追加
  - 統一的な logging 設定ユーティリティ `setup_logging(app_name, log_dir, level)`（StreamHandler を stdout に出力、TimedRotatingFileHandler で日次ローテーション・30日保持）。ログディレクトリ作成失敗時はファイル出力をスキップする安全設計。 (`src/kabusys/utils/logging_setup.py`)
- プロセス優先度 / CPU アフィニティユーティリティを追加
  - psutil を使い Windows / POSIX の差を吸収する `set_process_priority(level)`、`set_cpu_affinity(cpu_count)` を提供。失敗時は警告ログを出してスキップ。 (`src/kabusys/utils/process_priority.py`)
- ポートフォリオ構築モジュール（純粋関数群）
  - 候補選定 / 重み計算: `select_candidates`, `calc_equal_weights`, `calc_score_weights`（`src/kabusys/portfolio/portfolio_builder.py`）
    - スコア降順、同点は signal_rank 昇順でタイブレーク。スコア全0 の場合は等金額にフォールバック。
  - セクター集中とレジーム乗数: `apply_sector_cap`, `calc_regime_multiplier`（`src/kabusys/portfolio/risk_adjustment.py`）
    - 既存保有のセクター暴露を計算し上限超過セクターの新規候補を除外。unknown セクターは上限の対象外。
    - レジーム別乗数: bull=1.0, neutral=0.7, bear=0.3（未知レジームは 1.0 にフォールバック）。
  - 株数決定とリスク制限: `calc_position_sizes`（`src/kabusys/portfolio/position_sizing.py`）
    - allocation_method により risk_based / equal / score を実装。
    - 単元株 (lot_size) 単位で丸め、per-stock 上限（max_position_pct）や aggregate cap（available_cash）を考慮したスケールダウンロジックを実装。手数料・スリッページ想定の cost_buffer を加味した保守的見積り。
- Paper Trading 検証レポートツールを追加
  - `python -m kabusys.tools.paper_verification_report` で paper_trading DB から稼働率・注文成功率・送信率・レイテンシ等の指標を算出して PASS/FAIL を判定。閾値はソース内定義（稼働率 99%、成立率 90% など）。 (`src/kabusys/tools/paper_verification_report.py`)
- データ解析・リサーチ用モジュール（骨格）
  - DuckDB 接続を受けてファクターを計算するモジュールの導入（`src/kabusys/research/factor_research.py`）。モメンタムや MA200、ATR、流動性などの計算方針・定数が定義されている。

Changed
- なし（初回リリース想定）

Fixed
- なし（初回リリース想定）

Security
- 環境ファイルの注意喚起: config_setup が .env にシークレット値を保存する点について、.env を絶対に Git にコミットしない旨を明記。

Notes / Usage highlights
- 環境ロード順序: OS 環境変数 > .env.local > .env。OS 環境変数は保護され上書きされない。
- 起動時プロセス優先度はデフォルトで "high" に設定される（起動スクリプト内で最初に実行）。
- 監視ループは MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（正の整数で指定、無効値はデフォルト 60 秒にフォールバック）。
- Paper Trading と本番の DB は分離（PAPER_TRADING_SQLITE_PATH / SQLITE_PATH）。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存され、30 日分保持。
- process_priority と CPU affinity は psutil に依存。権限不足や未対応プラットフォームでは無害にスキップする設計。

Known limitations / TODO
- factor_research モジュールは設計方針および定数が整備されているものの、ファイル末尾が途中で切れており（本コードベースでは実装が未完の箇所がある可能性がある）完全な関数実装が必要。
- position_sizing の価格欠損時のフォールバックは TODO コメントあり（将来的に前日終値や取得原価などのフォールバックが望まれる）。
- 単元株（lot_size）を銘柄別に持つ拡張や、より細かい手数料/スリッページモデルの導入は将来検討事項。

---

この CHANGELOG はコードの現在の状態から推測して作成しています。実際のリリースノートとして利用する場合は、コミット履歴やリリース目的に合わせて調整してください。