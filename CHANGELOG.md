# Changelog

すべての変更は Keep a Changelog の形式に従って記述しています。  
フォーマット: https://keepachangelog.com/ja/

なお、本 CHANGELOG はソースコードの実装内容から推測して作成したものであり、実際のコミット履歴に基づくものではありません。

## [Unreleased]

- 小さな改善・ドキュメント調整（実装上の細部は次回リリースに反映予定）。

## [0.1.0] - 2026-04-18

初期リリース

### Added（追加）
- 全体
  - パッケージ初期版を追加。自動売買システム「KabuSys」のコア機能群を実装。
  - バージョンは `__version__ = "0.1.0"`。

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを提供。バックグラウンドスレッドでエンジンを実行し、停止フラグ（data/stop_requested.flag）や pid ファイル（data/execution.pid）に対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを提供。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で調整可能（デフォルト 60 秒）。

- 設定関連
  - config.py: 環境変数/`.env` の自動読み込み機能を実装。
    - プロジェクトルートを `.git` または `pyproject.toml` から検出して `.env` / `.env.local` を読み込む。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動読み込みを無効化可能。
    - `.env` パース機能: `export` プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントを考慮して安全にパース。
    - 必須環境変数を取得する `_require()` を実装（未設定時は ValueError）。
    - Paper trading 用設定（`PAPER_TRADING_SQLITE_PATH`, `PAPER_FILL_MODE` 等）を追加。
    - 環境種別（development / paper_trading / live）やログレベルの検証ロジックを提供。
  - settings インスタンスを `settings = Settings()` として公開。

- 設定ツール / 検証
  - config_setup.py: 対話式ウィザードで `.env` を初期作成・更新する CLI を実装。
    - シークレット項目は表示をマスク、選択肢やデフォルトを提示して入力支援。
    - 最終的に `.env` を安全なテンプレート形式で書き出す。
  - validate_config.py: 起動前の設定検証 CLI を実装。
    - 必須環境変数・KABUSYS_ENV・LOG_LEVEL・DB パスや `config/*.yaml` の存在・パースをチェック。
    - `--strict` オプションで警告も失敗扱いにできる。

- ロギング / プロセス管理
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - コンソール出力は stdout、ファイル出力は日次ローテート（TimedRotatingFileHandler、30 日保持）。
    - 環境変数 `LOG_DIR` / `LOG_LEVEL` を尊重。ファイル出力の失敗時はコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度（および CPU affinity）設定ユーティリティを追加。
    - Windows / POSIX (Linux/Mac/FreeBSD) の差分を吸収して `set_process_priority("high"|"normal"|"low")` を提供。
    - `set_cpu_affinity` によりプロセスを先頭 N コアにピン留め可能。
  - 起動スクリプト（execution / monitoring）は起動直後にプロセス優先度を "high" に設定する。

- データベース
  - DuckDB と SQLite を併用する設計を採用。
    - デフォルトパス: DuckDB `data/kabusys.duckdb`、SQLite `data/monitoring.db`（Paper trading は `data/paper_trading.db` を使用）。
  - 監視用 DB の初期化関数 `init_monitoring_db` を呼び出し、監視テーブルの存在を保証（冪等）。

- 実行系（Execution）
  - Broker クライアントファクトリを導入（BrokerClientFactory.create(settings)）。`KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を利用し、本番 DB とは完全分離された paper_trading DB に記録する設計。
  - RiskManager / OrderManager / Reconciler / ExecutionEngine 等の依存関係を組み立てる起動フローを実装。
  - RiskConfig のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。
  - ExecutionEngine は PID ファイルを扱い、停止フラグにより安全に停止可能。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順（同点は signal_rank 小さい方を優先）で候補選定。
    - calc_equal_weights: 等分配重みを実装。
    - calc_score_weights: スコア比率で正規化して重みを返す。全スコアが 0 の場合は等分配にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中度上限に基づき新規候補を除外（unknown セクターは除外対象としない）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3; 未知は 1.0 にフォールバックして警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に対応。lot_size（単元）で丸め、per-position 上限や aggregate 上限（available_cash）を考慮してスケーリング・再配分を行う。cost_buffer により保守的なコスト見積りが可能。

- 研究 / ファクター計算
  - research/factor_research.py: Momentum, Value, Volatility, Liquidity 等のファクター計算設計を追加（DuckDB 経由で prices_daily / raw_financials を参照して計算する方針）。モメンタム計算（calc_momentum）のスケッチを含む。

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成 CLI を追加。
    - 指定期間（--from, --to）やデータベースパス（--db）を受け取り、稼働率、注文成功率、送信率、P95 レイテンシ等を出力。
    - 基準値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し、PASS/FAIL を判定してレポートを表示。

### Changed（変更）
- 監視周りの挙動
  - run_monitoring: Monitoring は KABUSYS_ENV にかかわらず監視用に本番 sqlite_path を使用する設計（環境による分離は行わない）。ポーリングループは停止フラグファイルを監視して安全終了する。

- .env ローダーの優先度
  - 自動ロード順序を OS 環境変数 > .env.local > .env として実装。`.env.local` は OS 環境を上書き（ただし既存の OS 環境変数は保護）。

- ログ設定
  - 一貫したログフォーマットと日次ローテーションを導入。既存ハンドラがある場合は一度クリアしてから再設定することで二重出力を防止。

### Fixed（修正 / 安全強化）
- run_monitoring: 環境変数 `MONITOR_POLL_INTERVAL` が不正（非整数または 0 以下）な場合、警告を出してデフォルト（60 秒）にフォールバックするように修正。time.sleep に不正値が渡らないように防御的実装を行った。

- config.py / .env パーサー
  - クォート付き値のバックスラッシュエスケープ処理、`export ` プレフィックス対応、インラインコメント処理などを実装し、より堅牢に .env を読み込めるようにした。

- validate_config
  - PyYAML が未インストールの場合は YAML 検証をスキップして警告を出す。config/*.yaml が存在しない場合は警告を出し、生成方法のヒントを表示。

- position_sizing
  - 価格情報が欠けている（0 または None）銘柄はスキップして安全に処理を継続するようにした（ログにデバッグメッセージを出力）。

### Security（セキュリティ）
- `.env` に機密情報が含まれるため、config_setup.py により生成される `.env` のテンプレートに「絶対に Git にコミットしないこと」を明記。

### Notes（備考 / 実装上の注意）
- 一部モジュール（研究系ファクター計算など）は設計／スケッチ段階の関数を含み、データ前提（prices_daily / raw_financials テーブル等）に依存します。実データを用いた追加検証・テストが必要です。
- Paper trading 用の MockBrokerClient や ExecutionEngine の具象実装（注文送信ロジックなど）は本 CHANGELOG 作成元コード内の他モジュールに依存しています。外部 API 呼出しや実売買に関する取り扱いは設定（KABUSYS_ENV）により明確に分離されているため、本番運用時は設定を慎重に確認してください（validate_config の live ガード参照）。

---

保守性向上や本番運用を想定した安全弁（停止フラグ、PID、ログ回転、プロセス優先度、設定検証等）が多く実装されています。次回リリースではテストカバレッジ、ファクター計算の完成度向上、ExecutionEngine / Broker の E2E テスト、さらなるドキュメントの充実が期待されます。