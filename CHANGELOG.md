CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠します（https://keepachangelog.com/ja/）。

注: 以下の履歴は提供されたコードベースの内容から推測して作成したものです。実際のコミット履歴がある場合はそちらを元に調整してください。

Unreleased
----------

- なし

0.1.0 - 2026-04-19
------------------

Added
- 基本アプリケーションスケルトンを追加
  - パッケージメタ情報: kabusys/__init__.py にバージョン 0.1.0 を追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV が paper_trading の場合は専用の paper DB を使用して MockBrokerClient による分離動作をサポート。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) による制御。
    - ExecutionEngine をスレッドで動作させ、停止フラグ検知時に安全に停止する処理を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用。
    - 停止フラグ検知でループを終了、KeyboardInterrupt をハンドリングしてクリーンに終了。
- 設定管理
  - config.py: .env の自動読み込み機構を実装（プロジェクトルートの検出、.env/.env.local の読み込み順序）。
    - .env パーサーは export プレフィックス、シングル・ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
    - OS 環境変数を保護するための上書き制御を実装。
    - Settings クラスを提供し、J-Quants や kabu API、DB パス、監視閾値、環境 (KABUSYS_ENV) やログレベル等のプロパティ（バリデーション付き）を公開。
    - PAPER_FILL_MODE の妥当性チェック（"instant"|"partial"|"never"|"reject"）を実装。
- 設定ユーティリティ / CLI
  - config_setup.py: 対話式ウィザードで .env を生成/更新する CLI を追加（項目定義、既存 .env 読み込み、シークレット表示マスク、保存）。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML ファイル存在・パースチェック（PyYAML がない場合は警告）、本番環境向けの追加ガード（LINE設定や KILL_FLAG_CLEAR_ON_START の検出）。
    - --strict モードで警告を FAIL 扱いにできる。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定する setup_logging を追加。
    - 既存ハンドラを一旦クリアして二重設定を防止。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - LOG_LEVEL / LOG_DIR の解決順を実装。
  - utils/process_priority.py:
    - set_process_priority(level) により Windows / POSIX の差分を吸収してプロセス優先度を設定。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアに固定する補助機能を追加。
    - 権限不足や未対応 OS の場合は警告を出してスキップする安全設計。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順でソート、上位 N 件を選択。
    - calc_equal_weights: 等金額配分の重み生成。
    - calc_score_weights: スコアに比例した重み生成。全てのスコアが 0 の場合は等配分へフォールバック（警告）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 同一セクターの既存保有比率が上限を超える場合、当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に基づく投下資金乗数を返す（未知レジームは 1.0 にフォールバックし警告）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method("risk_based"/"equal"/"score") に応じて発注株数を計算。
      - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap、cost_buffer（手数料・スリッページ見積）を加味したスケーリング、残余の分配ロジックなどを実装。
      - 価格欠損や 0 価格はスキップ、過不足に対してログ出力。
- リサーチ / ファクター計算（骨格）
  - research/factor_research.py:
    - ファクター計算の設計と定数を実装（Momentum / Value / Volatility / Liquidity を想定）。
    - calc_momentum の実装を開始（ファイル末端で実装途中の箇所あり）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を用いて計算する設計。
- ペーパートレード検証ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用の SQLite（デフォルト data/paper_trading.db）を読み、稼働率・注文成功率・送信率・レイテンシ（P95）等を集計してレポート出力。
    - デフォルトの合格基準（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）を定義。
    - 日付フィルタや --db オプションに対応。
- 監視用 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を使用して起動時に監視テーブルの存在を保証（冪等）。

Changed
- 初リリースのため該当なし。

Fixed
- 初リリースのため該当なし。

Security
- 初リリースのため該当なし。

Notes / Known issues
- research/factor_research.calc_momentum 等、リサーチモジュールに未完の実装（ソースが途中で切れている箇所あり）。本リリースでは設計と一部実装を提供しているが、完全なファクター算出は今後の実装が必要。
- position_sizing の価格欠損（price が 0.0 の場合）ではエクスポージャーや算出が過小推定される旨の TODO コメントあり。将来的に前日終値などのフォールバック価格を検討する必要がある。
- .env 自動読み込みはプロジェクトルートの検出に依存する（.git または pyproject.toml）。検出できない場合は自動読み込みをスキップする挙動に注意。

Acknowledgements
- この CHANGELOG は提供されたコードから推測して作成しています。実際の変更履歴やコミットメッセージがある場合はそちらを優先してご利用ください。