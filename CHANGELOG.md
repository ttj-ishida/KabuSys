# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の書式に準拠しています。  
（内容はリポジトリ内のソースコードをもとに推測して作成しています）

なお、各項目には該当する主なモジュール／ファイル名を併記しています。

## [Unreleased]
（なし）

---

## [0.1.0] - 2026-04-18
初回公開リリース（推測）。日本株自動売買システム「KabuSys」の基礎コンポーネントを追加。

### Added
- 基本パッケージ初期化とバージョン定義を追加（src/kabusys/__init__.py）。
- 環境設定関連
  - Settings クラスによる環境変数ラッパーを追加（src/kabusys/config.py）。
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / LOG_LEVEL / KABUSYS_ENV 等の取得を提供。
    - PAPER_FILL_MODE の妥当性チェック実装（instant/partial/never/reject）。
    - 環境判定ヘルパー（is_live, is_paper, is_dev）。
  - .env 自動読み込み機能をプロジェクトルート（.git または pyproject.toml）から実行する仕組みを追加。
  - .env の対話式生成ウィザードを追加（src/kabusys/config_setup.py）。
    - J-Quants / kabuステーション / DB パス / LINE 通知などの設定項目を対話形式で作成・更新可能。
- 設定検証 CLI を追加（src/kabusys/validate_config.py）。
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DBパスの存在確認、config/*.yaml の存在・パース検証（PyYAML があれば内容検証）など。
  - --strict オプションで警告も失敗扱いにできる。
- 起動スクリプト
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）検知によりループを終了。
  - Execution エンジン起動スクリプト（src/kabusys/run_execution.py）
    - KABUSYS_ENV=paper_trading 時は paper_trading 用専用 SQLite（data/paper_trading.db）を使用して、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動と監視。
    - 停止フラグ・PID 管理（data/execution.pid, data/stop_requested.flag）。
- 実行・監視共通ユーティリティ
  - ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler をルートロガーへ設定。
    - 既存ハンドラをクリアして二重設定を回避、ログディレクトリ作成失敗時はファイル出力をスキップ。
  - プロセス優先度 / CPU アフィニティ設定ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差を吸収して優先度を設定（high/normal/low）。
    - set_cpu_affinity により最初の N コアに固定可能（権限やプラットフォーム依存で安全にフォールバック）。
- ポートフォリオ構築関連（純粋関数群：DB 参照なし）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、同点は signal_rank でタイブレーク）
    - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有を考慮して同一セクター比率が閾値超過の際に新規候補を除外）
    - calc_regime_multiplier（regime: bull/neutral/bear に対応、未知値はフォールバック）
  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes：risk_based / equal / score の割当方式に対応
    - 単元株（lot_size）丸め、max_position_pct の適用、available_cash に応じた aggregate スケーリング、cost_buffer を考慮した保守見積り
- ツール類
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）を算出して PASS/FAIL 判定を出力。
    - 日付フィルタ（--from/--to）および DB パス指定（--db / PAPER_TRADING_SQLITE_PATH）対応。
    - デフォルト閾値を定義（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。
- リサーチ基盤（骨組み）
  - factor_research モジュール（src/kabusys/research/factor_research.py）にモメンタム等の計算ロジックの枠組みを追加（DuckDB を用いる設計）。モジュールはモメンタム / MA / ATR / 流動性等を想定している（実装は継続中）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- なし（初回リリース）

---

注記（推測）
- .env のパース実装は export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメント処理などに対応しており、実運用での堅牢性を向上させる設計になっています（src/kabusys/config.py）。
- モジュールはデータベース（SQLite / DuckDB）を分離することで paper_trading モードと本番の混同を避ける設計です（run_execution.py、Settings）。
- ログ出力は stdout を用いる設計になっており、cron 等でのリダイレクト運用を意識しています（utils/logging_setup.py）。

もしこの CHANGELOG をリポジトリの履歴と照合したい場合は、追加で参照してほしい箇所（特定ファイルやコミット）を指定してください。必要に応じて各変更に対する詳細な説明や移行手順（例: .env の既存設定を新仕様に合わせる手順）も作成します。