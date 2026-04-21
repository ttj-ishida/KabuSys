# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

なお、本リリースはリポジトリに含まれるコードベースから推測して記載しています。

## [0.1.0] - 2026-04-21

### 追加
- 基本バージョン情報を追加
  - pakage version: `__version__ = "0.1.0"` を設定。

- 実行用エントリスクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視用 DB は KABUSYS_ENV に依らず本番用 sqlite_path を使用。
    - 停止フラグ（data/stop_requested.flag）検出でループ終了。
    - プロセス優先度を起動時に "high" に設定。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を利用して paper_trading 用 DB（data/paper_trading.db、環境変数で上書き可）に記録し本番 DB と分離。
    - 停止フラグ・PID 管理、バックグラウンドスレッドでの実行制御を実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - 環境変数の読み込み/公開用 Settings クラスを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく `.env` / `.env.local` 自動ロード（OS 環境変数を優先・保護）。
    - `.env` のパースはクォート・エスケープ・コメントを考慮（export プレフィックス対応）。
    - 各種設定（DB パス、PID/kill flag、しきい値、KABUSYS_ENV/LOG_LEVEL 判定、paper_trading の挙動など）をプロパティとして提供。
    - PAPER_FILL_MODE の検証（有効値: instant|partial|never|reject）。
  - config_setup.py
    - .env を対話式に生成・更新するウィザード CLI を追加。シークレット項目のマスク、既存値の読み込み、保存内容の確認を行う。
    - 生成される .env のテンプレートと注意事項（Git へコミットしない等）を出力。
  - validate_config.py
    - 起動前に .env と config/*.yaml の検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在およびパース検証（PyYAML がない場合は警告）。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ロギング & プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 共通ロギングセットアップ関数 `setup_logging()` を追加。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler、30 日保持）によるファイル出力を設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - 既存ハンドラをクリアして二重登録を防止。
  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加（Windows/Linux/Mac の差分を吸収）。
    - `set_process_priority(level)` と `set_cpu_affinity(cpu_count)` を提供。権限不足等の失敗は警告でスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定関数 `select_candidates()`（スコア降順、同点は signal_rank でタイブレーク）。
    - 等金額配分 `calc_equal_weights()`、スコア加重 `calc_score_weights()`（全スコアが 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 `apply_sector_cap()`（既存保有からセクター別エクスポージャーを計算して候補除外）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier()`（"bull":1.0,"neutral":0.7,"bear":0.3、未知レジームはフォールバック 1.0）。
    - いくつかの注意（価格欠損時の過少見積り等）がコメントで記載。
  - portfolio/position_sizing.py
    - 株数決定ロジック `calc_position_sizes()` を実装。
    - allocation_method: "risk_based" / "equal" / "score" に対応。
    - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer 等を考慮した aggregate cap のスケーリング処理（小数端数の配分ロジック含む）。
    - price 欠損時のスキップ、portfolio_value や available_cash に応じた調整を実装。

- リサーチ（ファクター計算）
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールを追加（モメンタム、移動平均乖離、ATR、出来高等の算出方針を含む設計）。
    - 設計方針と定数が定義され、関数 calc_momentum() 等の実装開始（部分的に実装）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシなどを算出。閾値を定義して PASS/FAIL を判定。
    - DB パスは引数 `--db` / 環境変数 `PAPER_TRADING_SQLITE_PATH` / デフォルト順で解決。
    - P95 計算、欠損値ハンドリング、出力フォーマットを実装。

- パッケージ初期化
  - kabusys/__init__.py にパッケージ説明と __all__ を追加。

### 変更
- なし（初回リリースのため、既存機能の変更履歴はありません）。

### 修正
- なし（初回リリースのため、既知のバグ修正履歴はありません）。

### 注意点 / 既知の挙動
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされる。
- .env ローダーは OS 環境変数を保護する（.env.local の override=True でも OS 環境変数は上書きされない）。
- run_monitoring は監視 DB に常に settings.sqlite_path を使用するため、監視ログは env に関わらず同一 DB に記録される点に注意。
- PAPER_FILL_MODE の不正値は Settings 側で ValueError を投げるため、起動前に validate_config でチェックすることを推奨。
- process_priority / cpu_affinity の設定は権限不足やプラットフォーム未対応時に警告してスキップする設計。
- portfolio モジュールでは価格欠損（price=0 等）に関する挙動が一部コメントで指摘されており、将来的なフォールバック実装（前日終値やコスト推定等）が検討されている。

---

今後のリリースでは以下の点を予定している（実装済みファイルからの推測）:
- research モジュールのファクター計算の完成と統合テスト
- ExecutionEngine / BrokerClient の詳細実装と e2e テスト
- config/*.yaml のサンプル生成スクリプトとドキュメント整備

（必要であれば、本 CHANGELOG を基により詳細な変更点やリリース手順を追記します。）