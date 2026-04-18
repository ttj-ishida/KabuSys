# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

現在のリリース履歴は、コードベースの内容から推測して作成しています。日付はこのファイル生成日です。

※ 本ドキュメントはコード内のコメント・実装から推測して作成しています。実際の変更履歴と異なる場合があります。

## [0.1.0] - 2026-04-18

### Added
- プロジェクト初期実装を追加（KabuSys v0.1.0 想定）。
- 実行エントリ／デーモン起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを実装。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離（MockBrokerClient を利用する想定）。
    - プロセス優先度を "high" に設定するユーティリティ呼び出しを行う。
    - 停止フラグ（data/stop_requested.flag）と実行 PID ファイル（data/execution.pid）による起動制御 / 停止制御を実装。
    - スレッドで ExecutionEngine.run_session を実行し、停止フラグで engine.stop() を呼び出す制御を実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず production の sqlite_path を使用する挙動（明示的に本番 DB を参照する仕様）。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。
- 設定・環境管理
  - config.py
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml）。
    - .env / .env.local の読み込み順と保護（OS 環境変数保護）を実装。
    - 環境変数取得ラッパ（Settings クラス）を導入。各種設定（DB パス、ログレベル、KABUSYS_ENV、paper_trading 用の PAPER_FILL_MODE 等）をプロパティとして提供。
    - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
  - config_setup.py
    - 対話式の .env ウィザードを実装。主要設定項目（J-Quants トークン、kabu API パスワード、DB パス、ログレベル、KILL_FLAG クリア設定など）を対話で作成・更新可能。
    - 既存 .env を読み込み、Enter で既存値を再利用する UX を実装。
  - validate_config.py
    - 起動前チェック CLI を実装。必須環境変数の存在チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在/パース確認（PyYAML がインストールされている場合）。
    - --strict オプションで警告を FAIL 扱いにできる。
    - live 環境用の追加ガード（LINE 通知設定未設定の警告、KILL_FLAG_CLEAR_ON_START の危険性警告）を実装。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定する統一ロギング設定を実装。
    - ログレベル・ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。ログディレクトリ作成に失敗した場合はファイル出力をスキップする頑健性を確保。
  - utils/process_priority.py
    - Windows / POSIX（Linux/macOS/FreeBSD）差分を吸収したプロセス優先度設定（set_process_priority）を実装。失敗時は警告でスキップ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装（アクセス拒否や未対応環境では警告でスキップ）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、タイブレークは signal_rank）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有のセクター暴露を計算し、上限超過セクターの新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" マップ、未知レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 株数決定ロジック calc_position_sizes を実装。
    - allocation_method="risk_based"（リスクベース） / "equal" / "score" をサポート。
    - 単元株（lot_size）で丸め、max_position_pct・max_utilization・cost_buffer を考慮した aggregate cap のスケーリング処理を実装。
    - スケーリング時の端数処理（lot_size 単位で残余キャッシュに応じた追加配分）を実装。
- リサーチ / ファクター計算（下準備）
  - research/factor_research.py
    - Momentum 等ファクター計算のための設計・定数と calc_momentum の導入（DuckDB 接続を想定）。（実装の一部が途中まで含まれる）
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを実装。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）等を計算して判定（PASS/FAIL）。
    - デフォルト DB は data/paper_trading.db。PAPER_TRADING_SQLITE_PATH または --db で指定可能。
    - P95 計算、期間フィルタ、閾値（稼働率 99%、fill 90%、send 95%、P95 latency 200 ms）を導入。
- パッケージ情報
  - __init__.py にてバージョン __version__ = "0.1.0" を設定。

### Changed
- （初回リリース）多数のモジュールを一括追加したため、実装の注意点をドキュメント内コメントとして明記。
  - logging_setup は stdout を使用するように明示（cron 等で stdout/stderr を一本化する運用を想定）。
  - run_monitoring では monitoring 用 DB 初期化（init_monitoring_db）を行い、duckdb も接続する設計を採用。
  - run_execution は起動時に監視テーブルの存在を保証するため init_monitoring_db を呼び出す（冪等な初期化）。

### Fixed
- （該当なし / 初期リリースのため特定のバグ修正履歴なし）

### Known issues / 注意点
- factor_research.calc_momentum の実装が途中で切れている（ファイル末尾が途中）。ファクター計算の完成・テストが必要。
- position_sizing, risk_adjustment 内に将来の拡張を示す TODO が存在：
  - price が欠損（0.0）の場合のフォールバック価格（前日終値や取得原価など）の利用が未実装で、現状では過少見積りのリスクあり。
  - 単元株（lot_size）は現状グローバル固定で 100 を想定。将来的には銘柄別 lot_map を導入予定。
- ログディレクトリの作成に失敗した場合、ファイルハンドラが無効化されるがコンソール出力は継続する設計（運用上の確認を推奨）。
- process_priority / set_cpu_affinity は権限やプラットフォームによっては動作しない可能性がある（警告を出してスキップする実装）。
- config 自動ロードはプロジェクトルートの検出に依存するため、配布後や特殊なデプロイ環境では自動ロードをスキップする可能性がある。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- run_monitoring はコメントにある通り「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」ため、開発環境で誤って本番 DB を参照しないよう注意が必要。

### Security
- .env は絶対に Git にコミットしないこと（config_setup の出力ヘッダで明記）。

---

（今後のリリースでは機能追加・改善・バグ修正を個別に記載してください）