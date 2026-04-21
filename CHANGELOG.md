# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
日付および内容は、提供されたコードベースから推測してまとめたものです。

全体方針:
- 本プロジェクトは日本株自動売買システム「KabuSys」の初期実装を含みます。
- 環境変数／.env による設定、自動読み込み、対話式セットアップ、設定検証、監視・実行の起動スクリプト、ポートフォリオ構築ロジック、ユーティリティ類、Paper Trading 検証ツールなどを実装しています。

## [Unreleased]
- 次回リリースに向けた未反映の改善点・ドキュメント整備を予定

---

## [0.1.0] - 2026-04-21
初回公開（推測） — 基本機能の実装とユーティリティ整備

### Added
- 基本モジュール
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`
  - Settings/設定管理: `kabusys.config.Settings`
    - .env 自動読み込み（プロジェクトルートの検出: `.git` または `pyproject.toml` を基準）
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能
    - 各種環境変数プロパティ（J-Quants, kabu API, DB パス、監視閾値、環境種別等）
    - `paper_trading` 用 DB パス・fill mode 支持（`PAPER_TRADING_SQLITE_PATH`, `PAPER_FILL_MODE`）
- 起動・運用スクリプト
  - 監視ループ起動スクリプト: `src/kabusys/run_monitoring.py`
    - `SystemMonitor` を用いたポーリングループ
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）
    - 停止用フラグファイル detection (`data/stop_requested.flag`)
    - 監視モジュールは常に本番用の sqlite_path を使用（環境に依らない）
  - 実行エンジン起動スクリプト: `src/kabusys/run_execution.py`
    - `ExecutionEngine` をスレッドで実行、停止フラグで安全停止
    - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し paper DB（分離）へ記録
    - PID ファイルサポート（`data/execution.pid`）
- 設定関連 CLI
  - 環境設定ウィザード: `src/kabusys/config_setup.py`
    - 対話式に .env を生成・更新
    - パスワード等はシークレット扱い（表示はマスク）
    - .env の書式テンプレート出力
  - 設定検証 CLI: `src/kabusys/validate_config.py`
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認
    - config/*.yaml の存在・パース検証（PyYAML がインストールされている場合）
    - `--strict` モードで警告を失敗扱いにできる
- ツール
  - Paper Trading 検証レポート: `src/kabusys/tools/paper_verification_report.py`
    - 稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を集計して PASS/FAIL を判定
    - 日付フィルタ（--from/--to）および DB パス指定（--db または env）対応
    - デフォルト閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）
- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - select_candidates, calc_equal_weights, calc_score_weights
  - `kabusys.portfolio.risk_adjustment`
    - apply_sector_cap（セクター集中制限）, calc_regime_multiplier（レジーム乗数）
  - `kabusys.portfolio.position_sizing`
    - calc_position_sizes（リスクベース・等分配・スコア加重の株数算出、単元株丸め、aggregate cap スケーリング）
- ユーティリティ
  - ロギングセットアップ: `kabusys.utils.logging_setup.setup_logging`
    - stdout StreamHandler と日次ローテートの TimedRotatingFileHandler をルートロガーへ設定
    - ログディレクトリの解決順（引数 > LOG_DIR > デフォルト logs/）、ログレベルの解決順（引数 > LOG_LEVEL > INFO）
    - ファイル出力失敗時はコンソールのみで継続
  - プロセス優先度/CPU affinity: `kabusys.utils.process_priority`
    - set_process_priority(level) — Windows / POSIX を吸収して優先度を設定
    - set_cpu_affinity(cpu_count) — 利用するコア数固定（利用不可時は安全にスキップ）
    - 権限不足や未対応 OS の場合は警告を出してスキップ
- インフラ
  - DuckDB / SQLite の接続ポイント（スクリプトでの接続確立とクローズ処理）
  - 監視用 DB 初期化の呼び出し（冪等: init_monitoring_db）

### Changed
- .env 読み込みロジックを堅牢化（`kabusys.config._parse_env_line`）
  - `export KEY=val` フォーマット対応
  - シングル/ダブルクォート内のバックスラッシュエスケープ対応
  - クォートなし値に対する inline コメント処理（スペース直前の `#` をコメントと見なす挙動）
  - ロード順: OS 環境変数 > .env.local（上書き）> .env（未設定のみ）
  - `protected` セットを使って OS 環境変数の上書きを防止
- `MONITOR_POLL_INTERVAL` の不正値（非整数・0以下）に対してデフォルト（60 秒）へフォールバックし警告を出力
- run_execution の paper_trading 動作
  - 本番 DB とペーパートレード DB を完全に分離（`paper_sqlite_path` を使用）
  - 起動前に停止フラグが立っている場合は起動を中止
- position sizing のロジック
  - 単元株（lot_size）単位での丸め処理、aggregate cap によるスケールダウン、残余キャッシュを利用した再配分を実装
  - cost_buffer による保守的コスト見積りを導入
- risk_adjustment の振る舞い
  - セクター不明（"unknown"）はセクター上限制約の対象外にする
  - レジーム乗数で未知のレジームは警告して 1.0 でフォールバック

### Fixed
- ロギングディレクトリ作成失敗時にファイルハンドラ追加でクラッシュする問題を回避（コンソール出力のみで継続）
- プロセス優先度設定で権限エラーが発生する環境での例外によるクラッシュを抑止し、警告ログに置き換え
- Paper Verification レポートでテーブルが存在しない場合の例外をキャッチして N/A / 0 の既定値へフォールバック

### Security
- .env ファイルを生成する `config_setup` にて、生成された .env を絶対に Git にコミットしない旨を明記
- 機密値（`JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `LINE_CHANNEL_ACCESS_TOKEN` 等）は対話式入力でマスク表示

### Notes / Implementation details
- Execution 側の RiskManager 初期設定にはデフォルト値を設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。初期ポートフォリオ値はブローカーの `get_available_cash()` を参照して取得する。
- Monitoring は環境に関わらず本番の sqlite_path（監視 DB）を使用する設計（監視データは本番 DB に保存される想定）。
- Paper Trading 検証ツールはデフォルトで `data/paper_trading.db` を参照。存在しない場合はエラーメッセージを出力。
- `research.factor_research` モジュールはファクター計算（モメンタム・ボラティリティ等）を行う設計で、一部実装（calc_momentum の開始部分）を含む。DuckDB を用いて prices_daily / raw_financials を参照する方針。

### Known limitations / TODO（推測）
- 一部モジュールで外部依存（psutil, duckdb, yaml 等）が必要。環境にない場合は機能が制限される旨のドキュメント整備が必要。
- ファイル I/O（ログディレクトリ作成、DB 作成権限など）に関する権限問題に対する運用手順を明示する必要あり。
- factor_research の実装が途中（ファイル末尾で truncation の痕跡あり） — 完全実装・単体テストの追加が必要。
- 単体テスト・統合テストの記載は現状含まれていない。CI での環境変数取り扱い（テスト用の KABUSYS_DISABLE_AUTO_ENV_LOAD 等）の整備が望ましい。

---

今後のリリースでは以下の改善を想定しています（例）:
- factor_research の完実装とベンチマーク
- CLI ドキュメントおよび運用手順の整備（systemd / supervisor / cron などでの起動例）
- 追加の監視アラート経路（LINE 通知の実稼働確認、Webhook など）
- 単体テスト・テストカバレッジの追加

以上。