CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記録しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（現在未リリースの変更はありません）

[0.1.0] - 2026-04-18
--------------------
初回リリース。以下の主要機能・実装を含みます。

Added
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。

- 環境・設定管理
  - .env 自動読み込み機構を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env/.env.local の読み込み、OS 環境変数を保護する仕組みを提供。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
  - 独自の .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート、エスケープ、インラインコメント処理）。
  - Settings クラスを実装し、環境変数からアプリケーション設定を取得。必須値チェック（_require）、各種パス、Paper Trading 用設定、閾値、環境判定（is_live / is_paper / is_dev）等を提供。
  - 設定ウィザード CLI を追加（src/kabusys/config_setup.py）。対話式で .env を作成／更新可能。secret 項目はマスク表示、保存前の確認機能あり。

- 設定検証 CLI
  - src/kabusys/validate_config.py を追加。必須環境変数や KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML が利用可能な場合）等を検証。
  - --strict オプションで警告をエラー扱いにできる。

- 実行用スクリプト
  - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
    - プロセス優先度を High に設定して起動。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によりブローカークライアントを生成（paper/live に応じた実装を選択する想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッド実行。停止フラグ（data/stop_requested.flag）検知で安全に停止。
    - RiskManager に初期ポートフォリオ値（broker.get_available_cash()）を使用する設定を導入。

  - 監視プロセス起動スクリプト: src/kabusys/run_monitoring.py
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値や 0 以下は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番の sqlite_path を使用して監視 DB を初期化（init_monitoring_db）。
    - SystemMonitor.check_once() 実行時の例外を捕捉してログ出力し、次ポーリングへ回復する堅牢性を確保。
    - 停止フラグ検知でループを終了し、DB 接続を確実にクローズ。

- ロギング／プロセス制御ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 共通のログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（デフォルト logs/、日次ローテーション、30 日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / 引数による解決、既存ハンドラのクリーンアップ、ログディレクトリ作成失敗時のフォールバック動作を実装。
  - src/kabusys/utils/process_priority.py
    - プラットフォーム差異を吸収したプロセス優先度設定（"high"/"normal"/"low"）を実装。Windows（psutil の優先度定数）と POSIX（nice 値）に対応。設定失敗時は警告でスキップ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity() を実装（権限不足等は警告してスキップ）。

- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定 select_candidates(): スコア降順、同点は signal_rank でタイブレーク。
    - 重み計算 calc_equal_weights() / calc_score_weights()。全スコアが 0 の場合は等金額配分にフォールバックし warn。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中上限チェック apply_sector_cap(): 既存保有のセクター別エクスポージャーを計算し、上限超過セクターの候補を除外（"unknown" セクターは除外対象外）。sell_codes による売却除外を考慮。
    - レジーム乗数 calc_regime_multiplier(): "bull"/"neutral"/"bear" に応じた乗数を返却。未知値は警告して 1.0 にフォールバック。
  - src/kabusys/portfolio/position_sizing.py
    - 各種配分方式（risk_based / equal / score）に基づいて発注株数を計算。
    - 単元株（lot_size）で丸め、per-position 上限（max_position_pct）・aggregate cap（available_cash）・cost_buffer（スリッページ等）を考慮したスケーリング処理を実装。スケールダウン後の端数配分では fractional remainder に基づき再配分して最大利用を試みる。

- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py を追加。Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を読み、期間フィルタで以下を算出してレポート出力:
    - 稼働率（system_status テーブル）
    - 注文成功率 / 送信率（trade_logs）
    - リスク却下数（risk_logs）
    - API レイテンシ（平均・最大・P95）
    - P95 計算ユーティリティを実装。閾値を定義して PASS/FAIL を判定して出力。

- データ分析 / リサーチ（骨組み）
  - src/kabusys/research/factor_research.py（モメンタム等のファクター計算ロジックの実装開始）。
    - Momentum（1M/3M/6M、MA200 乖離）や ATR/出来高等の設計方針・定数を定義。DuckDB 接続を受けて prices_daily / raw_financials を参照する想定。
    - （ファイル末尾が途中で切れているため、実装は一部のみ）

Changed
- （初回リリースのため履歴なし）

Fixed
- （初回リリースのため履歴なし）

Notes / Implementation details
- DB
  - DuckDB（analytics 用）と SQLite（監視/注文履歴用）を併用する設計。監視機能は環境にかかわらず sqlite_path（本番）を使用する点に注意。
- 安全停止
  - data/stop_requested.flag を用いたプロセス間での停止通知に対応（monitoring / execution で利用）。
- エラーハンドリング
  - 監視ループやファイル/ディレクトリ作成などで失敗してもプロセスが致命的に停止しないよう例外捕捉とログ出力でフォールバックする設計を採用。

貢献・免責
- .env ファイルには機密情報が含まれるため、README 等で .env を絶対に Git にコミットしないよう明示してください（config_setup にも注意書きあり）。

今後
- factor_research の完全実装、strategy 周りの統合テスト、銘柄別 lot_size 対応（stocks マスタの導入）などを予定。