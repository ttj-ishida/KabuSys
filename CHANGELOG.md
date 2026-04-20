# Changelog

すべての変更は「Keep a Changelog」規約に準拠して記載しています。  
日付はコードベースから推測した初回リリース日を使用しています。

全般的な注記:
- 本リリースは初期機能群の導入を想定しています（バージョン 0.1.0）。
- 環境変数や .env の自動読み込み、Paper Trading 用の完全分離 DB、ロギング・プロセス設定ユーティリティ、ポートフォリオ構築ロジック、検証ツール、監視/実行の起動スクリプトなどを含みます。

## [Unreleased]
（今後の変更をここに記載してください）

## [0.1.0] - 2026-04-20

### Added
- 基本パッケージ情報
  - パッケージメタ情報を追加（src/kabusys/__init__.py、__version__ = "0.1.0"）。  

- 実行・監視プロセス
  - 実行エンジン用起動スクリプトを追加（src/kabusys/run_execution.py）。
    - ExecutionEngine をスレッドで起動、停止フラグ（data/stop_requested.flag）による安全停止をサポート。
    - Paper Trading 環境では MockBrokerClient を利用し、paper_trading 用 SQLite（data/paper_trading.db）に記録するよう分離。
    - プロセス優先度を起動時に "high" に設定。
    - PID ファイル管理（data/execution.pid）をサポート。
    - リスク管理（RiskManager）とオーダー管理（OrderManager）、reconciler の組み立てを行う起動フローを実装。
  - システム監視用起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor をポーリングで定期実行。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視処理は環境に関わらず本番用 sqlite_path を参照して監視テーブルを初期化・使用。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了、KeyboardInterrupt にも対応。
    - duckdb と sqlite の接続初期化を実装。

- 設定管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - 環境変数をプロパティ経由で取得（J-Quants、kabu API、LINE、DB パス、監視閾値など）。
    - KABUSYS_ENV、LOG_LEVEL 等の検証ロジックを備える。
    - .env 自動読み込み（プロジェクトルートの検出に .git / pyproject.toml を使用）を実装。優先順位: OS 環境変数 > .env.local > .env。
    - .env パースはクォート/エスケープ、コメント処理、export プレフィックス対応などを実装。
    - Paper Trading 用の設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）や監視閾値（CPU/MEM/DISK）も管理。

  - 対話式環境設定ウィザードを追加（src/kabusys/config_setup.py）。
    - .env の初期作成・更新を支援。シークレット項目はマスク表示。保存前に確認プロンプトを実装。

  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数の存在チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース（PyYAML があれば）を検証。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や Kill Flag の自動クリア設定）を実装。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で候補選定（同点タイブレーク: signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分。スコア合計が 0 の場合は等金額にフォールバック（警告ログ）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有を考慮したセクター上限チェック（max_sector_pct）。当日売却予定銘柄を除外するオプションをサポート。unknown セクターは制限適用除外。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未定義はフォールバック 1.0、警告ログ）。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づき発注株数計算。
      - risk_based: リスク許容率と損切り率から株数算出。
      - equal/score: ウェイトに基づく配分、per-position 上限と aggregate cap（available_cash）を考慮。
      - 単元株（lot_size）で丸め、cost_buffer を使って手数料/スリッページを保守的に見積もる。
      - available_cash を超える場合はスケーリングし、残差を lot 単位で配分するロジックを実装。

- 監視・検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を計算し、PASS/FAIL 判定を出力。
    - 閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を利用。
    - DB パスの指定を CLI (--db) または環境変数 PAPER_TRADING_SQLITE_PATH で行える。

- ユーティリティ
  - ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。
    - ログレベルとログディレクトリの解決ルール（引数 > 環境変数 > デフォルト）を実装。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX 差分を吸収して優先度設定（high/normal/low）を実行。CPU affinity 設定も提供。
    - 設定失敗時は警告ログでフォールバック。

- リサーチ（ファクター算出）
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity 系の計算方針を実装。DuckDB の prices_daily / raw_financials を参照して計算する設計（calc_momentum 等の関数を含む）。  
    - （実装は DuckDB 接続を受け取る設計で、データ不足時の None 扱いなどを考慮）

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境ファイル .env は Git にコミットしない旨をウィザードのヘッダに明示（config_setup）。

### Notes / Known limitations
- research/factor_research モジュールは DuckDB と prices_daily/raw_financials のスキーマ依存。実行には該当テーブルの存在が必要。
- calc_position_sizes の price 欠損時の扱い（price=0 の場合はスキップ）については将来的にフォールバック価格導入の余地あり（TODO コメントあり）。
- process_priority / cpu_affinity の設定は OS 権限（root 等）が必要な場合があり、権限不足時はログを出してスキップする。
- .env 自動ロードはプロジェクトルートを検出できない場合はスキップされる。自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。

---

参考: 主なファイル
- src/kabusys/run_execution.py
- src/kabusys/run_monitoring.py
- src/kabusys/config.py
- src/kabusys/config_setup.py
- src/kabusys/validate_config.py
- src/kabusys/portfolio/*
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/utils/*
- src/kabusys/research/factor_research.py

（今後のリリースでは各コンポーネントのユニットテスト結果・実運用での微調整・ドキュメント補完を予定してください。）