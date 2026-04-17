CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に準拠しています。

Unreleased
----------

（現時点のコードは 0.1.0 としてリリース済み想定のため、Unreleased に新規差分はありません。）

0.1.0 - 2026-04-17
------------------

Added
- 基本機能の初期実装（初回リリース）。
  - 自動売買システムのコアモジュール群を提供。
- 実行／監視用エントリポイント
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番と分離。
    - BrokerClientFactory により実行時に適切なブローカークライアントを生成。
    - OrderRepository、OrderManager、RiskManager（既定設定を含む）、Reconciler を組み立ててエンジンを起動。
    - 停止フラグ（data/stop_requested.flag）検出で安全に停止。
    - 実行 PID を data/execution.pid に書き出す想定（Engine に渡す）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する設計（監視 DB と発注 DB の切り分け）。
    - 停止フラグ検出でループ終了。
- 設定管理・ウィザード・検証
  - config.py
    - Settings クラスで環境変数を集中管理。
    - .env 自動読み込み（.env → .env.local、OS環境変数保護）と、複雑な .env 行のパーシング（export プレフィックス、クォート内のエスケープ、インラインコメント処理）に対応。
    - PAPER_FILL_MODE 等の値チェック、各種パスの Path 化、KABUSYS_ENV のバリデーションを実装。
  - config_setup.py
    - .env の初期作成・更新を対話式で行うウィザード CLI。
    - デフォルト値/選択肢、シークレット表示、保存プレビューを実装。
  - validate_config.py
    - 起動前チェック CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス（親ディレクトリ存在確認）、config/*.yaml の存在および（PyYAML がある場合）パースチェックを実装。
    - --strict モードで警告を FAIL 扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順、同点は signal_rank によるタイブレーク。
    - calc_equal_weights, calc_score_weights（全スコア 0 の場合は等重にフォールバックし警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（売却予定銘柄を除外できる）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score 方式の株数算出。
    - lot_size 単位で丸め、1 銘柄上限・aggregate cap（利用可能現金に基づくスケーリング）を実装。
    - cost_buffer を使った保守的コスト見積と残余配分ロジック（小数端数の分配）。
- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度設定ユーティリティ（Windows と POSIX の差分吸収）。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。アクセス拒否等は警告を出してスキップ。
- 研究 / ファクター計算
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュール（Momentum / Volatility 等）。
    - calc_momentum, calc_volatility 等（200 日 MA、ATR、1/3/6 ヶ月リターン等）を SQL ウィンドウ関数で実装。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成 CLI。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（P95）などを算出し PASS/FAIL 判定（閾値はソース内定義）。
    - DB パスはコマンドライン --db / 環境変数 PAPER_TRADING_SQLITE_PATH / デフォルトの順で解決。
- パッケージメタ
  - __init__.py に __version__ = "0.1.0" を設定。

Changed
- .env 読み込みロジック
  - 自動ロードを行う際、既存 OS 環境変数は保護して .env(.local) を上書きしない実装（テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD を設定可能）。
  - export KEY=val、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを考慮した堅牢なパーサを導入。
- DB ハンドリング
  - run_execution/run_monitoring で DuckDB / SQLite の接続確立と初期化（init_monitoring_db の呼び出し）を明確化。
- 監視と実行の分離
  - 監視は本番 monitoring DB を使用する一方、paper_trading 実行は paper_trading 用 DB に分離（安全設計）。

Fixed
- 環境変数や設定ファイルのバリデーションメッセージを改善し、仮のプレースホルダ値を検出して警告を出すようにした（validate_config.py）。
- position sizing / risk adjustment のエッジケース（価格欠損、ゼロ除算、score が全て 0 の場合）に対するフォールバックとログ出力を追加。

Deprecated
- （なし）

Removed
- （なし）

Security
- 環境ファイルの初期 .env を生成する際に注意喚起をファイル先頭へ追記（.env を絶対に Git にコミットしない旨）。

注記 / 実装上の注意
- PAPER_FILL_MODE の有効値（instant/partial/never/reject）は Settings.paper_fill_mode によって厳格に検証されます。不正な値は起動時に例外を送出します。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値（0 以下や非数）を検出してデフォルト 60 秒にフォールバックします。
- process_priority の設定は権限や OS に依存するため失敗する場合があり、その際は警告を出して処理を継続します。
- position_sizing の lot_size は現在グローバル共通の想定（将来的に銘柄別拡張を想定した TODO コメントあり）。
- DuckDB を利用するファクター計算は prices_daily / raw_financials テーブルのみを参照し、本番の発注や外部 API にはアクセスしない設計。

今後の予定（例）
- 銘柄別 lot_size のサポート（マスタ参照）
- position_sizing の単体テスト充実化（エッジケースの網羅）
- run_execution/run_monitoring の systemd / container 向けのデプロイ設定例追加
- research モジュールの追加ファクター実装とパフォーマンス最適化

---