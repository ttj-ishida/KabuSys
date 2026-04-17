# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。セマンティックバージョニングに従います。

## [Unreleased]

（現在のスナップショットは初回リリース相当の内容のため、未リリース項目はありません）

## [0.1.0] - 2026-04-17

概要: KabuSys の初期安定版リリース。環境設定/検証ツール、監視・実行エントリポイント、ポートフォリオ構築ロジック、リサーチ（ファクター計算）、ユーティリティ群、ペーパートレード検証レポートなど、主要な機能を純粋関数・CLI 形式で収録しています。

### Added
- 基本パッケージ情報
  - パッケージバージョンを定義（src/kabusys/__init__.py: __version__ = "0.1.0"）。

- 環境設定 / 管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - 環境変数からの設定取得をプロパティ化（J-Quants、kabu API、LINE、DB パス、監視閾値、各種フラグなど）。
    - KABUSYS_ENV の検証（development / paper_trading / live）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - paper_trading 用 SQLite パスの分離（PAPER_TRADING_SQLITE_PATH）。
  - .env 自動読み込み機能を追加（プロジェクトルート検出、.env/.env.local 読み込み、OS 環境変数保護、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
  - 高機能な .env パーサ（引用符対応、export 形式、インラインコメント処理、エスケープ処理）を実装。

- 設定ウィザード / 検証 CLI
  - 環境設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話式で .env を作成・更新。シークレット項目マスク表示、デフォルト/選択肢対応。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数・パス・config/*.yaml の存在と YAML パースチェック（PyYAML があれば内容検証）。
    - --strict モードで警告を FAIL 扱いにできる。

- 実行 / 監視エントリポイント
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使い、paper_trading 用 DB を使用して本番と完全分離。
    - PID ファイル管理、停止フラグ（data/stop_requested.flag）検知、スレッドでエンジン実行・安全停止。
    - 初期 RiskConfig のデフォルト値を設定し、broker.get_available_cash() を初期ポートフォリオ値として使用。
  - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒、無効値は警告してフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を参照する旨を明示。
    - 停止フラグ検知でループ終了、例外発生時にログ出力して次ポーリングまで待機。

- ポートフォリオ構築（純粋関数群）
  - 候補選定 / 重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順＋タイブレーク）、calc_equal_weights、calc_score_weights（スコア全て 0 の場合のフォールバック）。
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有比率に応じた候補除外、"unknown" セクターは免除）。
    - calc_regime_multiplier（bull/neutral/bear のマッピングと未知レジームフォールバック）。
  - 株数決定・丸め・スケーリング（src/kabusys/portfolio/position_sizing.py）
    - allocation_method に応じた計算（risk_based / equal / score）。
    - lot_size（単元）での丸め、max_position_pct / max_utilization の考慮、cost_buffer を用いた保守的見積り。
    - aggregate cap 超過時のスケールダウンロジックと残余キャッシュを用いた lot 単位の追加配分。

- リサーチ（ファクター計算）
  - ファクター計算モジュールを実装（src/kabusys/research/factor_research.py）。
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離率（データ不足は None）。
    - calc_volatility: ATR、相対 ATR、20日平均売買代金、出来高比率等の計算（DuckDB を使用）。

- ペーパートレード検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率、送信率、リスク却下数、P95 レイテンシ等を算出。
    - 判定閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 <= 200ms）を定義し PASS/FAIL を出力。
    - --from/--to/--db オプション対応。PAPER_TRADING_SQLITE_PATH 環境変数により DB 指定可。

- ユーティリティ
  - process_priority と CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX を吸収した set_process_priority(level)（high/normal/low）。
    - set_cpu_affinity(cpu_count) によるプロセスコア固定（実行環境で利用可能な場合）。
    - 権限不足や未対応プラットフォーム時は警告して安全にスキップ。

- DB 初期化
  - init_monitoring_db の呼び出しをエントリポイントで行い、監視テーブルが存在することを保証（冪等）。

### Changed
- .env ロードの挙動
  - 自動ロード順序を OS 環境 > .env.local > .env とし、既存 OS 環境変数を保護するように変更。
  - .env.local は .env を上書きするが、OS 環境変数は上書きされない。
- 監視・実行起動時に最初にプロセス優先度を設定するよう統一（run_monitoring.py / run_execution.py）。
- run_monitoring: MONITOR_POLL_INTERVAL の検証強化（0/負値/非数時に警告しデフォルトへフォールバック）。

### Fixed
- .env のパースと読み書きの堅牢化
  - export プレフィックス、単一/二重引用符内のバックスラッシュエスケープ、インラインコメント処理などに対応（src/kabusys/config.py）。
  - config_setup による .env 書き出しテンプレートを追加（コメント付き、Git にコミットしないよう注記）。
- run_execution/run_monitoring の DB クローズ処理を finally で確実に実行。
- Paper レポートの P95 計算と欠損データ時の N/A ハンドリングを追加。

### Security
- .env ファイルに関する注意喚起を config_setup のヘッダに追加（絶対に Git にコミットしないこと）。
- 設定検証で本番環境（KABUSYS_ENV=live）の注意喚起（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険性）。

### Notes / Implementation details
- run_execution は paper_trading モード時に本番 sqlite を使わず paper_trading.db を利用するため、本番とペーパートレードは論理的に分離されています。
- ポートフォリオ構築・サイズ計算は外部の DB 参照を行わず純粋関数で実装されており、ユニットテスト容易性を意図しています。
- リサーチ系は DuckDB を利用して大規模時系列データを SQL ベースで効率的に集計します。
- process_priority や CPU affinity の設定は権限が不足する環境や未対応プラットフォームで例外を投げずログ警告でフォールバックします。

（今後）:
- 個別銘柄の lot_size を銘柄毎に管理する拡張（stocks マスタの導入）や、position_sizing のさらに詳細なコストモデル導入が予定されています。