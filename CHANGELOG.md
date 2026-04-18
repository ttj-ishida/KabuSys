CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。

[Unreleased]
-----------

- （現時点のスナップショットはまだリリースされていません。以下はコードベースから推測した初期リリース内容です）

[0.1.0] - 2026-04-18
-------------------

Added
- プロジェクト初期リリース。主要な機能群・CLI・ユーティリティを追加。
  - アプリケーションメタ情報
    - kabusys パッケージのバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。
  - 設定管理
    - .env 自動読み込み機構を実装（プロジェクトルートを .git / pyproject.toml から探索）。環境変数で自動ロードを無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）（src/kabusys/config.py）。
    - 独自の .env パーサを実装。export 形式、シングル/ダブルクォート内のエスケープ、インラインコメント処理をサポート（src/kabusys/config.py）。
    - Settings クラスを追加し、主要な設定（J-Quants / kabu API / DB パス / Paper Trading 切替 / 監視しきい値 等）を環境変数から安全に取得できるようにした（src/kabusys/config.py）。
    - PAPER_FILL_MODE の検証（有効値: instant, partial, never, reject）や KABUSYS_ENV/LOG_LEVEL のバリデーション実装。
  - 設定ヘルパー CLI
    - 対話式 .env 作成・更新ウィザードを追加（python -m kabusys.config_setup）。各項目の説明・デフォルト提示・シークレットマスク等に対応（src/kabusys/config_setup.py）。
    - 設定検証 CLI を追加（python -m kabusys.validate_config）。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在およびパース（PyYAML があれば内容検証）等をチェックし、errors/warnings/infos を出力（src/kabusys/validate_config.py）。
  - 実行 / 監視ランチャー
    - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
      - KABUSYS_ENV=paper_trading 時は paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離。
      - BrokerClient を BrokerClientFactory で生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
      - 停止フラグ（data/stop_requested.flag）を監視して安全に停止。PID ファイル管理（data/execution.pid）をサポート。
      - RiskManager のデフォルト設定（max_position_pct / max_utilization / rate_limit_per_sec / circuit_breaker 等）を組み込み、initial_portfolio_value を broker.get_available_cash() で初期化。
    - 監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
      - MONITOR_POLL_INTERVAL 環境変数（デフォルト 60 秒）でポーリング間隔を上書き可能。0 以下や不正値はデフォルトにフォールバック。
      - 監視は環境にかかわらず本番 sqlite_path を使用する仕様（監視データは常に同一 DB に記録）。
      - 停止フラグ（data/stop_requested.flag）検知でループ終了。
  - ツール
    - Paper Trading 向け検証レポート生成スクリプトを追加（python -m kabusys.tools.paper_verification_report）。
      - 稼働率、注文成功率（fill rate）、送信率（send rate）、レイテンシ（avg/max/P95）などを集計してレポート出力。
      - デフォルト DB パスは env / 引数で指定可能（PAPER_TRADING_SQLITE_PATH / --db）。
      - レポート用の閾値を定義（稼働率 99%、fill_rate 90%、send_rate 95%、P95 latency 200 ms）。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - 候補選定・重み付け（select_candidates / calc_equal_weights / calc_score_weights）（src/kabusys/portfolio/portfolio_builder.py）。
      - スコア降順ソート、タイブレークロジック、スコアが全て 0 の場合のフォールバック等を実装。
    - セクター集中制限とレジーム乗数（apply_sector_cap / calc_regime_multiplier）（src/kabusys/portfolio/risk_adjustment.py）。
      - セクター別既存エクスポージャ計算、上限超過セクターの候補除外、未知レジームへのフォールバックロジックを実装。
    - ポジションサイジング（calc_position_sizes）（src/kabusys/portfolio/position_sizing.py）。
      - risk_based / equal / score の割当方式をサポート。lot_size（単元株）丸め、max_position_pct や aggregate cap（available_cash に基づくスケールダウン）、cost_buffer による保守的評価、残差処理（端数の優先付け）を実装。
    - 上記は DB 非依存の純粋関数として設計（メモリ内計算）。
  - ユーティリティ
    - ロギングセットアップユーティリティ（setup_logging）を追加（src/kabusys/utils/logging_setup.py）。
      - stdout への StreamHandler、日次ローテーション（TimedRotatingFileHandler）でログファイル出力（logs/<app_name>.log、30 日分保持）。
      - LOG_DIR / LOG_LEVEL の解決順、既存ハンドラのクリーンアップ、ファイル出力失敗時のフォールバック等に対応。
    - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
      - Windows / POSIX の差分を吸収して set_process_priority(level)（high/normal/low）や set_cpu_affinity(cpu_count) を提供。権限不足や未対応 OS は警告してスキップ。
  - リサーチ（ファクター計算）の骨格
    - factor_research モジュールの骨格を追加（src/kabusys/research/factor_research.py）。
      - Momentum / Value / Volatility / Liquidity 等の計算設計、DuckDB 接続を受けて prices_daily / raw_financials を参照する方針を実装。モメンタム計算関数 calc_momentum の実装開始（未完の断片あり）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 環境変数・シークレット取り扱いに関する注意点をドキュメントおよび config_setup に明示（.env は Git へコミットしないこと）。

Notes / 実装上の注意（開発者向け）
- .env の自動読み込みはプロジェクトルートが特定できない場合はスキップされるため、パッケージ配布後の環境やテスト環境での挙動に注意。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定する。
- run_monitoring は監視 DB として常に Settings.sqlite_path（本番相当）を使用する設計。Paper Trading と監視データを完全に分離したい場合は設定の見直しが必要。
- process_priority / cpu_affinity は権限や OS 依存のため、失敗時は警告を出して処理を継続する設計。
- factor_research の一部は実装途中の断片が含まれる（calc_momentum が途中で終わっているファイル断片が存在）。追加実装・テストが必要。

お問い合わせやリリースノート補足の要望があれば、コード中の該当ファイルを参照して追記します。