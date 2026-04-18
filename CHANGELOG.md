# Changelog

すべての notable な変更は Keep a Changelog のフォーマットに従って記載しています。  
バージョン番号はパッケージの __version__（0.1.0）に合わせています。

全般的な注記
- 本リリースは初期機能セットの提供を目的とした最初の公開バージョンです。
- 環境変数はプロジェクトルートの .env / .env.local ファイルと OS 環境変数からロードされます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## [0.1.0] - 2026-04-18

### Added
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を "high" に設定し、スレッドでエンジンを実行。停止フラグ（data/stop_requested.flag）検知で安全に停止。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（既定: data/paper_trading.db）を使用し、本番 DB と分離（MockBrokerClient を使用する設計に準拠）。
    - 起動時に監視テーブルの初期化を行い、DuckDB への接続も確立。
    - エンジンの PID を data/execution.pid に書き込む設計（pid_file 指定）。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 起動時にプロセス優先度を "high" に設定。停止フラグ（data/stop_requested.flag）でループ終了。
    - 監視用 DB 初期化処理を実行。注: 監視は環境（KABUSYS_ENV）にかかわらず settings.sqlite_path（本番監視 DB）を使用する挙動。

- 設定関連
  - config.py
    - Settings クラスを追加し、環境変数から各種設定（J-Quants・kabu API・DBパス・ログ等）を安全に取得する API を提供。
    - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。.env と .env.local の読み込み順序を実装。クォートや export 形式に対応した .env パーサを実装。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START 等のプロパティを提供。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新が行える CLI を追加（python -m kabusys.config_setup）。secret 項目のマスク表示、既存値の再利用、.env 書き出し機能を提供。
  - validate_config.py
    - 起動前の設定検証ツールを追加（python -m kabusys.validate_config）。必須環境変数や DB パス、config/*.yaml の存在・パース（PyYAML があれば）をチェック。--strict オプションで警告を FAIL 扱いにできる。

- ロギング / プロセスユーティリティ
  - utils/logging_setup.py
    - 全体のロギング設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。LOG_DIR/LOG_LEVEL の解決をサポート。ログディレクトリ作成に失敗した際はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - プロセス優先度設定（Windows および POSIX 対応）と CPU affinity 設定ユーティリティを追加。psutil ベースで例外や権限不足を安全に扱う。set_process_priority("high" | "normal" | "low")、set_cpu_affinity(n) を提供。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定・重み算出機能を追加（select_candidates, calc_equal_weights, calc_score_weights）。スコアゼロ時のフォールバックロジックを含む。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。unknown セクターの扱いやレジーム不明時のフォールバックを明示。
  - portfolio/position_sizing.py
    - 発注株数計算ロジックを実装。allocation_method="risk_based" / "equal" / "score" をサポート。単元株（lot_size）で丸め、単銘柄上限・aggregate 上限（available_cash）に基づくスケーリングロジックを実装。手数料・スリッページ想定の cost_buffer を考慮。

- 解析 / レポートツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。期間フィルタ（--from/--to）、DB パス指定（--db / PAPER_TRADING_SQLITE_PATH 環境変数）に対応。稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）・リスク却下数などを計算し PASS/FAIL を判定する閾値を定義。

- 研究用モジュール（雛形）
  - research/factor_research.py（未完）
    - モメンタム等のファクター計算モジュールの骨組みを追加（DuckDB 接続を受け prices_daily / raw_financials を参照する想定）。関数 calc_momentum の冒頭実装（定数・説明）を含む（ファイルは途中で切れているが基本設計を含む）。

### Changed
- none（初回リリースのため既存からの変更履歴は該当なし）

### Fixed
- none（初回リリース）

### Security
- 環境ファイル (.env) は生成時に「絶対に Git にコミットしないこと」と明記。config_setup の出力テンプレートに注意文を追加。

### Notes / 注意点
- 監視（run_monitoring）は設計上「環境（KABUSYS_ENV）にかかわらず settings.sqlite_path（監視用 SQLite、デフォルト data/monitoring.db）＝本番監視 DB」を使用する挙動です。環境分離を期待する場合は運用ドキュメントや環境変数で sqlite_path を適切に切り替えてください。
- run_execution は paper_trading モード時に paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用することで本番 DB と分離する設計です。
- process_priority および CPU affinity の設定は権限やプラットフォームに依存し、失敗した場合は警告ログを出して続行します（例: 権限不足や未対応 OS）。
- logging_setup はログディレクトリの作成に失敗するとファイルロギングをスキップしますが、コンソール出力（stdout）は必ず設定されます。

---

今後予定（例）
- research/factor_research.py の完遂（ファクター計算の実装）。
- ExecutionEngine / Broker の詳細実装・エラーハンドリングの強化。
- 単体テスト・CI 設定、ドキュメント整備（運用手順、デプロイ手順）。

この CHANGELOG はコードベースから推測して作成しています。実際のコミット履歴がある場合はそちらを優先してマージしてください。