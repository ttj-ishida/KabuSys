# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

- リポジトリ: KabuSys
- 現行バージョン: 0.1.0

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-21
初回リリース。シンプルな自動売買基盤のコア機能とユーティリティ類を実装しています。

### Added
- 実行/監視スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - プロセス優先度を "high" に設定するユーティリティを呼び出す。
    - KABUSYS_ENV が `paper_trading` のときは専用の Paper Trading SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - RiskConfig のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec 等）を設定。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) による安全な起動/停止制御。
    - 実行はデーモンスレッドで行い、停止フラグ検出で engine.stop() を呼ぶ制御を実装。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告の上でデフォルトにフォールバック。
    - 監視 DB 初期化（monitoring は環境にかかわらず本番 sqlite_path を使用する設計）。
    - 停止フラグ (data/stop_requested.flag) によるループ終了処理を実装。

- 設定・環境管理
  - config.py
    - Settings クラスを導入し、環境変数から各種設定を取得する抽象化を提供（env、log_level、DB パス、PID/kill flag パス、閾値など）。
    - PAPER_FILL_MODE のバリデーションを実装（instant/partial/never/reject）。
    - PAPER_TRADING_SQLITE_PATH 等の paper_trading 関連設定をサポート。
    - プロジェクトルート探索により .env / .env.local を自動で読み込む仕組みを追加（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env の読み込みは OS 環境変数を保護しつつ .env.local で上書き可能にする挙動を実装。

  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - シークレット項目のマスク表示、選択肢・デフォルト値対応、既存 .env の読み込み・再利用、書き込みテンプレートを実装。

  - validate_config.py
    - .env と config/*.yaml の検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config YAML の存在・パースチェック（PyYAML がある場合）。
    - KABUSYS_ENV=live 時のガード（LINE 通知設定の確認や KILL_FLAG_CLEAR_ON_START の警告）を実装。
    - --strict オプションで警告を失敗扱いに可能。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選定（同点時には signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額分配。
    - calc_score_weights: スコア加重分配（全スコアが 0 の場合は等金額にフォールバック）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター別集中上限を適用するフィルタ関数（売却予定銘柄除外、"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた資金乗数を返す。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method("risk_based"/"equal"/"score") に従い発注株数を計算。
    - 単元株（lot_size）で丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash） に従ったスケーリング処理を実装。
    - cost_buffer を加味した保守的見積と、端数処理のための remainder ベースの再配分ロジックを実装。

- ユーティリティ
  - utils/logging_setup.py
    - 共通ログセットアップ関数 setup_logging を実装。
    - stdout 出力用 StreamHandler と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続する堅牢性を確保。
    - 既存ハンドラの重複登録を避けるため、ハンドラクリアを行う。

  - utils/process_priority.py
    - set_process_priority(level) により Windows / POSIX を吸収してプロセス優先度を設定（psutil 使用）。
    - set_cpu_affinity(cpu_count) により最初の N コアにピンニングする機能を追加。
    - 権限不足や未対応プラットフォームでは警告を出してスキップする安全設計。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（P95）等を集計して PASS/FAIL を判定するしきい値を実装。
    - コマンドラインで日付範囲指定 (--from/--to) と DB パス指定 (--db) を受け付ける。
    - P95 計算、各種 NULL/データ不足への耐性を持つ。

- リサーチ（未完）
  - research/factor_research.py
    - ファクター計算モジュールの骨子を追加（モメンタム、MA200、ATR、流動性等を想定）。calc_momentum 等の実装開始（ファイル末尾は未完の状態）。

- パッケージ情報
  - __init__.py にてバージョンを "0.1.0" に設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- 環境値の堅牢化
  - MONITOR_POLL_INTERVAL の不正値検出とデフォルトフォールバックを run_monitoring に実装。
  - .env 読み込みロジックは OS 環境変数を上書きしない保護機構を導入（.env.local は上書き可能だが OS 環境は保護）。
  - logging_setup はログディレクトリ作成失敗時にファイルハンドラ作成を安全にスキップするように調整。
  - process_priority は権限不足や未対応 OS の場合に例外で落ちないようハンドリング。

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- .env は絶対に Git にコミットしないことを README 等で周知する旨のコメントを config_setup のテンプレートに記載。

### Notes / Known issues / TODO
- position_sizing.calc_position_sizes:
  - 将来的に銘柄ごとの lot_size をサポートする設計に拡張する予定（TODO コメントあり）。
- risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少評価される可能性がある旨の注記。将来的に価格フォールバックを導入予定。
- research/factor_research.py:
  - ファイル末尾が未完（calc_momentum の実装途中） — 今後の実装が必要。
- validate_config.py:
  - YAML のパースは PyYAML がインストールされている場合のみ実行。未インストール時はスキップして警告。

---

参考: 各 CLI の使い方
- 設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視ループ起動: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

もしリリースノートに追記したい詳細（例: 変更日付の修正、特定のチケット/コミットへのリンク、リスクパラメータの調整履歴など）があれば教えてください。必要に応じて改訂します。