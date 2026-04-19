CHANGELOG
=========

フォーマット: Keep a Changelog 準拠（日本語）
日付: 2026-04-19

[Unreleased]
------------

- 開発中の機能や既知の未実装箇所があります（例: research.calc_momentum の実装途中など）。
- 一部の TODO や改善余地（価格フォールバック、銘柄別 lot_size 等）がコード内に残されています。詳細はソース内コメント参照。

[0.1.0] - 2026-04-19
-------------------

初回公開リリース。日本株自動売買システム "KabuSys" のコア機能群を追加しました。主な変更点は以下の通りです。

Added
- パッケージ全体
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
  - モジュール群を整理してエクスポート（portfolio 等）。

- 設定・環境管理
  - Settings クラスによる環境変数ラッパー実装（src/kabusys/config.py）。
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - 必須環境変数取得用の _require ヘルパ。
    - 各種既定値（DUCKDB_PATH、SQLITE_PATH、KABU_API_BASE_URL 等）を定義。
    - PAPER_FILL_MODE のバリデーション（instant / partial / never / reject）。
    - KABUSYS_ENV / LOG_LEVEL の検証ロジックと is_live/is_paper/is_dev プロパティ。
  - .env の対話式作成・更新ウィザード（src/kabusys/config_setup.py）。
    - 各設定項目の説明表示、既存値の再利用、秘密値のマスク表示機能付き。
    - .env ファイルの読み書き（安全なテンプレート出力）。

- 設定検証ツール
  - validate_config CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在・パースチェック。
    - --strict オプションで警告をエラー扱いにできる。

- 実行・監視ランチャ
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）。
    - プロセス優先度を High に設定して起動。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント生成（paper/live 分岐を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - data/stop_requested.flag の検出で安全に停止。
    - 実行時 PID ファイル書き出しを行う（data/execution.pid を想定）。

  - SystemMonitor ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出しデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して DB を参照。
    - 停止フラグ（data/stop_requested.flag）でループを終了。
    - 例外をキャッチしてログ出力しつつ次回ポーリングまで待機。

- 監視・分析の基盤
  - 監視 DB 初期化ヘルパ（init_monitoring_db 呼び出しを各起動処理内で実施し冪等性を担保）。
  - DuckDB 接続サポート（デフォルトパス: data/kabusys.duckdb）。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で候補選定（タイブレークで signal_rank を使用）。
    - calc_equal_weights / calc_score_weights: 等重配分とスコア加重配分（スコア全0 は等重にフォールバック）。
  - リスク調整（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター集中上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear）。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: risk_based / equal / score の配分方式に対応。lot_size（単元株）丸め、aggregate cap によるスケールダウン、コストバッファの考慮。

- ユーティリティ
  - 統一ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）。
    - stdout 出力用 StreamHandler と 日次ローテーションファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップ。
  - プロセス優先度 / CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分吸収。set_process_priority(level) により高優先度設定を試行。
    - set_cpu_affinity(cpu_count) による CPU ピンニング（実行環境で権限が必要な場合は警告でスキップ）。

- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）。
    - 指定期間または DB 全期間の検証レポートを標準出力に出力。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出。
    - 合否判定（閾値: 稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）を実装。
    - PAPER_TRADING_SQLITE_PATH 環境変数 または --db オプションで DB パス指定可。

- リサーチ
  - ファクター計算モジュール骨格（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity の設計方針と定数を実装。DuckDB 経由で prices_daily / raw_financials を参照して計算する方針。
    - calc_momentum 関数の実装開始（途中まで）。将来的に DuckDB SQL + Python で完全実装予定。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Removed
- なし（初回リリース）

Known issues / Notes
- factor_research.calc_momentum 等、一部関数は実装途中です（ソース内に start_da 等の未完了コードの痕跡あり）。
- position_sizing / apply_sector_cap における価格欠損時の挙動は TODO コメントで改善案が記載されています（価格が 0.0 の場合の過少見積りの可能性）。
- process priority / cpu affinity の設定は権限不足やプラットフォームの制約により失敗する場合があり、その場合は警告を出して安全にスキップします。
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされます。テスト環境等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- config/*.yaml のパース検証は PyYAML がインストールされている場合にのみ実行されます。未インストール時は警告が出ます。

開発メモ（実装上のポイント）
- 起動系スクリプトは最初にプロセス優先度を高くした上でログを初期化し、DB 初期化（監視テーブルの作成保証）を行うことで起動安定性を高めています。
- run_execution は paper_trading と live を明確に分離し、ペーパートレードは data/paper_trading.db に記録するように設計されています（DB 分離により誤発注リスクを低減）。
- run_monitoring は MONITOR_POLL_INTERVAL を環境変数で上書き可能にして運用時の柔軟性を確保しています。不正な値に対する防御処理あり。

ライセンス・貢献
- 本リリースは初回公開版です。貢献・バグ報告・改善提案はリポジトリの Issue / PR を通じて受け付けてください。

以上。