CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。

[未リリース]
------------

- なし

[0.1.0] - 2026-04-20
-------------------

追加 (Added)
- パッケージ初版リリース。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き対応（デフォルト 60 秒）。
    - 停止フラグ (data/stop_requested.flag) 検知で安全にループ終了。
    - Monitoring は実行環境に関わらず本番用 sqlite_path を使用する挙動。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録して本番 DB と分離。
    - 停止フラグ検知で Engine の停止を試みる仕組み。
    - PID ファイル (data/execution.pid) の取り扱い（Engine に渡す）。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - クォート付き/無しの .env 行パースを強化（export プレフィックス、エスケープ、コメントの扱い）。
    - Settings クラスを導入し、環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）をプロパティ経由で取得。
    - PAPER_FILL_MODE の検証、PAPER_TRADING_SQLITE_PATH / DUCKDB_PATH / SQLITE_PATH 等のパスプロパティを提供。
    - KABUSYS_ENV / LOG_LEVEL 等の妥当性検査を実装（無効値は ValueError）。

- 設定ツール
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を追加。
    - 各設定項目に説明、既存値の読み込み、シークレット扱い、選択肢サポートを実装。
    - .env 書き込みテンプレートを提供（Git へのコミット禁止注意書き含む）。

  - validate_config.py
    - 起動前に .env と config/*.yaml の設定検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML があれば）等を実装。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築モジュール (kabusys.portfolio)
  - portfolio_builder.py
    - select_candidates: BUY シグナルのソート/上位選定を実装（スコア降順、同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を実装。スコア合計が 0 の場合は等配分へフォールバックし警告を出力。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェックを実装。既存ポジションのセクター別時価を計算し、上限を超えたセクターの候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear → 1.0/0.7/0.3）を実装。未知レジームは警告とともに 1.0 にフォールバック。
  - position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数計算を実装。
    - risk_based: リスク許容率、ストップロス、単元株丸め、最大ポジション比率を考慮。
    - aggregate cap（利用可能現金を超える場合のスケーリング）、cost_buffer を考慮した保守的見積もり、残差配分ロジック（lot 単位での再分配）を実装。
    - lot_size（現状デフォルト 100）や将来の拡張ポイントを注記。

- ユーティリティ
  - utils/logging_setup.py
    - setup_logging を追加。ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしコンソールのみで継続。
    - 既存ハンドラのクリーンアップを行い二重設定を防止。
  - utils/process_priority.py
    - set_process_priority(level) を追加。Windows / POSIX の差分を吸収してプロセス優先度を設定（例: high/normal/low）。
    - set_cpu_affinity(cpu_count) を追加（最初の N コアに固定）。アクセス権限や未サポート環境では警告を出してスキップ。
    - psutil に依存しつつ例外ハンドリングで安全に動作。

- モニタリング関連
  - monitoring.monitoring_db.init_monitoring_db を使用して監視テーブルの初期化を行う呼び出しを run_monitoring / run_execution に導入（冪等に保証）。
  - run_monitoring/run_execution 側で DuckDB 接続（duckdb）も作成して分析用途に対応。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成ツールを追加。SQLite（デフォルト data/paper_trading.db）を参照して以下を集計:
      - システム稼働率（system_status）: 総ポーリング数, エラー数, 稼働率
      - 注文統計（trade_logs）: Created, Filled, Sent カウント → 注文成功率・送信率
      - リスク却下数（risk_logs）
      - レイテンシ（avg, max, P95）および P95 計算ロジック
    - デフォルト閾値（稼働率 99%, 成功率 90%, 送信率 95%, P95 200ms）に基づいて PASS/FAIL を判定。
    - コマンドラインから日付範囲 (--from/--to) と DB パス (--db) を指定可能。

- リサーチ / ファクター計算（部分実装）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity を計算する設計を追加。DuckDB 接続を受け prices_daily / raw_financials を参照する想定。
    - モジュールは設計方針・定数・関数骨格を含む（実装途中、以降の関数実装が続く）。

仕様上の注記 (Notable behavior)
- .env 自動読み込みはデフォルトで有効。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- .env の読み込み順序: OS 環境 > .env.local > .env（.env.local は上書き、OS 環境は保護）。
- MONITOR_POLL_INTERVAL の不正値（非整数や 0 以下）を検出するとデフォルト（60 秒）にフォールバックし警告をログ出力。
- Settings の env/log_level 等は妥当性検査を行い、無効な値で ValueError を投げる（起動前の検証が推奨される）。
- Paper Trading 環境では DB を完全分離（PAPER_TRADING_SQLITE_PATH を使用）し、本番 DB に影響を与えない設計。
- ログはデフォルトで stdout 出力と logs/<app_name>.log に日次ローテーションで出力される。ログディレクトリ作成に失敗した場合はファイル出力を無効化して stdout のみで継続する。

既知の制限 (Known issues / TODO)
- portfolio.risk_adjustment.apply_sector_cap:
  - price が欠損 (0.0) の場合にエクスポージャーが過少見積りされる可能性があり、将来的に前日終値等のフォールバック価格を導入予定。
- position_sizing.calc_position_sizes:
  - 現在 lot_size はグローバル（全銘柄共通）。将来的に銘柄別 lot_map を受け取る拡張を検討。
- research/factor_research.py:
  - ファクター計算の実装が途中まで（ファイル末尾で実装中断）。完全実装とテストが必要。

開発者向けメモ
- パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" を参照。
- 起動スクリプトはモジュールとして実行可能:
  - python -m kabusys.run_monitoring
  - python -m kabusys.run_execution
- 設定ウィザード / 検証:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

お問い合わせ
- この CHANGELOG に記載の挙動や設計判断について不明点があれば、差分元のコードを参照してください。