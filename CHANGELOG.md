CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" 準拠の形式で記載しています。主にコードベースの新規追加・重要な動作仕様をコードから推測してまとめています。

フォーマット:
- Unreleased: 今後の変更
- 各リリースは日付付きで記載

Unreleased
----------
- なし

0.1.0 - 2026-04-25
------------------
Initial release

Added
- 基本ライブラリ群を追加
  - パッケージメタ情報: kabusys.__version__ = 0.1.0
  - ロジックをモジュール単位で分離（config, utils, portfolio, execution, monitoring, research, tools 等）。
- 環境設定まわり
  - Settings クラス (src/kabusys/config.py)
    - .env 自動ロード機能（プロジェクトルートの .env / .env.local）（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
    - 多数の設定プロパティを提供（J-Quants / kabu API / DB パス / PID /閾値 / 環境モード 等）
    - env 値や PAPER_FILL_MODE / LOG_LEVEL の妥当性チェックを実施し、不正値は例外を送出
  - 環境設定ウィザード CLI (src/kabusys/config_setup.py)
    - 対話式で .env を作成・更新するウィザード。秘密項目はマスク表示、デフォルトや選択肢対応。
  - 設定検証 CLI (src/kabusys/validate_config.py)
    - 必須環境変数・KABUSYS_ENV・ログレベル・DB パス・config/*.yaml の存在/パース等を検査
    - --strict オプションで警告を失敗扱いにできる
- 実行・監視用スクリプト
  - 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
    - プロセス優先度を高設定して起動
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用し、本番 DB と分離
    - BrokerClientFactory を利用してブローカークライアントを生成、ExecutionEngine を起動（PID ファイルと停止フラグ対応）
    - RiskManager / OrderManager / Reconciler 等の組み立てロジックを含む
  - 監視ループ起動スクリプト (src/kabusys/run_monitoring.py)
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視データは本番 DB を参照）
    - 停止フラグファイル検出でループを安全に終了
- ロギング・プロセスユーティリティ
  - 統一ログ設定ユーティリティ (src/kabusys/utils/logging_setup.py)
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）を設定
    - 既存ハンドラをクリアして重複登録を防止、LOG_DIR / LOG_LEVEL の解決順を実装
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続
  - プロセス優先度・CPU affinity ユーティリティ (src/kabusys/utils/process_priority.py)
    - cross-platform（Windows / POSIX）でのプロセス優先度設定（psutil ベース）
    - CPU affinity 固定用の set_cpu_affinity を提供
    - 権限不足や未対応 OS 時はワーニングでスキップ
- ポートフォリオ構築ライブラリ (src/kabusys/portfolio/*)
  - 銘柄選定・重み計算 (portfolio_builder)
    - select_candidates: スコア降順で候補選択
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重（全スコア 0 の場合は等配分へフォールバック）
  - セクター制限・レジーム乗数 (risk_adjustment)
    - apply_sector_cap: セクター集中超過時に候補除外（unknown セクターは除外対象外）
    - calc_regime_multiplier: market レジームに基づく投下資金乗数（bull/neutral/bear）
  - 株数決定・リスク制限 (position_sizing)
    - calc_position_sizes: allocation_method に応じた発注株数計算（risk_based / equal / score）
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積り
    - aggregate スケールダウン時に端数処理（lot 単位）を行う再分配ロジックを実装
- Paper Trading 用検証ツール (src/kabusys/tools/paper_verification_report.py)
  - SQLite（デフォルト data/paper_trading.db）から検証指標を集計してレポートを出力
  - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、リスク却下数、API レイテンシ（avg/max/P95）
  - Pass/Fail の閾値定義（稼働率 99% など）および日付フィルタ対応
- 研究用ファクター計算（骨子）
  - research/factor_research.py にモメンタム等ファクター計算の設計と一部実装を追加（DuckDB 接続を前提）

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Removed
- なし（初期リリース）

Security
- なし特記事項。ただし .env ファイルは絶対にリポジトリにコミットしない旨を明記するウィザードの出力あり。

Notes / 動作上の重要なポイント（コードからの推測）
- .env の自動読み込みはプロジェクトルートが検出できる場合にのみ行われる。CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化可能。
- PAPER_TRADING 実行時は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番の monitoring DB とは分離される設計。
- 監視プロセスは監視データ用に常に Settings.sqlite_path（本番 DB）を利用する仕様になっているため、監視運用時は sqlite_path に注意が必要。
- run_execution/run_monitoring はプロセス優先度を最初に "high" に設定し、PID ファイルや停止フラグ（data/stop_requested.flag 等）で外部からの制御を受ける。
- Settings の一部プロパティは不正な値で例外を投げるため、起動前に validate_config を実行して警告・エラーを確認することを推奨。
- logging_setup はログディレクトリ作成に失敗した場合でもプロセスは継続し、コンソールログのみで稼働するようフォールバックする。

将来の改善候補（注記）
- position_sizing の lot_size を銘柄毎に持てるよう拡張（stocks マスタとの連携）
- risk_adjustment の price 欠損時のフォールバック（前日終値・取得原価等）
- research モジュールの完全実装（factor 計算の SQL / 正規化処理の追加）
- monitoring_db / system_monitor 等の詳細実装に基づく監視ルール強化

以上。