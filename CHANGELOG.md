# Changelog

すべての重要な変更点は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-18
初期リリース。自動株式売買プラットフォーム「KabuSys」の基盤機能を実装しました。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading 時は専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を経由してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を生成・起動。
    - 停止制御: data/stop_requested.flag を検知してセッション停止、PID ファイル管理。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書きをサポート（デフォルト: 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用（監視用 DB は共通）。
    - 停止制御: data/stop_requested.flag を検知してループ終了。

- 設定・環境管理
  - config.py
    - 環境変数ラッパー Settings を導入。J-Quants / kabu API / DB パス /監視しきい値等をプロパティで提供。
    - 自動 .env ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。OS 環境変数を優先、.env.local を .env の上書きとして読み込み可能。
    - .env のパース機能を強化（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱い）。
    - Paper Trading 向け設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）を追加。PAPER_FILL_MODE の有効値検証を行う。
    - ログや kill flag 等の各種既定値をプロパティ化。
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を追加。
    - デフォルト値、シークレットマスク、選択肢表示、保存の確認などを実装。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL 値チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードを実装。
    - --strict モードで警告を失敗扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定関数 setup_logging を追加。
    - コンソール（stdout）出力と日次ローテーションファイル出力（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順や、ファイルハンドラ作成失敗時のフォールバックを実装。
  - utils/process_priority.py
    - プロセス優先度設定 set_process_priority を追加（Windows / POSIX の差分吸収）。
    - set_cpu_affinity を追加（指定コア数でプロセスをピン留め）。権限不足や未サポート環境では警告でスキップ。

- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（score 降順、同点は signal_rank 昇順）。
    - 重み計算 calc_equal_weights（等金額）、calc_score_weights（スコア正規化、全スコア 0 の場合は等分配にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有のセクター比率が上限を超える場合、新規候補を除外）。
    - レジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear をそれぞれ 1.0/0.7/0.3 にマップし、未知レジームは警告とともに 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数計算 calc_position_sizes を実装。
    - allocation_method として "risk_based", "equal", "score" をサポート。
    - リスクベース計算（risk_pct / stop_loss_pct に基づくベース株数）と、per-position 上限（max_position_pct）、aggregate cap（available_cash を超える場合のスケールダウン）、単元株（lot_size）丸めおよび余剰配分ロジックを実装。
    - cost_buffer によりスリッページ/手数料を保守的に見積もる処理を追加。

- 解析・調査用ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を集計してレポート出力。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を実装。
    - --from/--to/--db オプションで期間・DB を指定可能。
  - research/factor_research.py（ファクター計算モジュール）
    - DuckDB を用いたモメンタム等のファクター計算ユーティリティを実装（モメンタム/MA200/ATR/出来高等を想定）。（部分実装あり）

- パッケージメタ情報
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。

### Changed
- なし（初回リリースのため変更履歴はありません）。

### Fixed
- なし

### Security
- なし

注記:
- ここにまとめた内容はソースコードから推定した実装と挙動に基づく要約です。詳細な仕様や実行時のふるまいは実際のランタイム設定や外部依存（psutil, duckdb, sqlite3, PyYAML 等）によって異なります。