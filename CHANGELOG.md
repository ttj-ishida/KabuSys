# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」準拠です。

## [0.1.0] - 2026-04-17

### Added
- 初回リリース。KabuSys のコア機能と開発運用ツールを実装しました。
- 実行用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用の SQLite（`Settings.sqlite_path`）を使用する設計。
    - 停止フラグファイル（data/stop_requested.flag）を検知して安全にループを終了。
    - DuckDB と SQLite の接続初期化、監視 DB テーブル初期化を行う。
    - 起動時にプロセス優先度を "high" に設定する仕組みを呼び出す。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=`paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用 DB（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離。
    - 停止フラグと PID ファイル（data/execution.pid）を扱う実行・停止ロジックを提供。
    - 起動時にプロセス優先度を "high" に設定する仕組みを呼び出す。
- 設定管理
  - config.py
    - プロジェクトルートを .git または pyproject.toml を基準に自動検出し、.env 自動読み込みを実装（OS 環境変数の保護機能あり）。
    - .env のパースを強化（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理等に対応）。
    - Settings クラスに各種設定プロパティを実装（DUCKDB/SQLITE パス、PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE の検証、PID/KILL フラグパス、閾値等）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
- 設定支援 CLI
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - シークレット入力のマスク、デフォルト値、選択肢、説明文を表示し、.env を安全に生成。
    - .env を生成する際に Git へのコミット禁止を明記。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数の検査、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在とパース検証（PyYAML が存在する場合）を実行。
    - `--strict` オプションで警告も失敗扱いにできる。
    - 本番（live）時の追加ガード（LINE トークン未設定・KILL_FLAG_CLEAR_ON_START 設定の警告）を実装。
- ポートフォリオ構築・サイズ決定ライブラリ
  - portfolio/portfolio_builder.py
    - シグナル選定（スコア降順、タイブレークルール）と等分/スコア加重の重み計算を実装。
    - スコアが全て 0 の場合は等金額配分にフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - セクター集中上限を適用する apply_sector_cap 実装（売却予定銘柄の除外や "unknown" セクターの扱いを定義）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier 実装（bull/neutral/bear とフォールバック）。
  - portfolio/position_sizing.py
    - 各種割付アルゴリズムを実装（risk_based / equal / score）。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap、コストバッファ考慮、スケーリングおよび端数再配分ロジックを実装。
    - 価格欠損時のスキップやログ出力を考慮。
- ユーティリティ
  - utils/process_priority.py
    - psutil を用いてプラットフォーム（Windows / POSIX 系）差分を吸収するプロセス優先度設定ユーティリティを追加。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足や未対応 OS の場合は安全にフォールバックして警告ログを出力。
- 研究用ファクター計算
  - research/factor_research.py
    - DuckDB を用いて momentum / volatility 等のファクター計算関数を実装（prices_daily 等テーブルを参照）。
    - SQL + Python による実装で、結果は (date, code) をキーとした dict のリストで返却。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を出力。
    - コマンドライン引数で期間指定（--from/--to）と DB パス指定（--db）に対応。
    - 判定基準として稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200ms を採用（デフォルト閾値）。
- パッケージ情報
  - __init__.py にて __version__="0.1.0" を設定し、主要サブパッケージを __all__ に公開。

### Changed
- 監視／実行スクリプトの動作安全性を強化
  - 監視ループ・エンジン実行で例外発生時にログを残してポーリングを継続する設計に変更（監視の耐障害性向上）。
  - 監視用 DB テーブルの初期化は冪等に行われるよう init_monitoring_db を呼び出す。
- .env 自動読み込みの優先順位を明確化
  - OS 環境変数 > .env.local > .env の順で読み込む挙動を実装（既存 OS 環境変数は保護）。

### Fixed
- 環境変数パースの堅牢化
  - export プレフィックスやクォート内のバックスラッシュエスケープ、インラインコメントの誤認識など、実運用で起きやすい .env フォーマットの曖昧さに対応。
- プロセス優先度設定の失敗時
  - 実行権限不足や未対応プラットフォームでの例外を捕捉し、処理を中断せず警告ログ出力にフォールバックするよう修正。

### Notes
- Paper Trading と Live の DB は分離設計
  - Paper Trading 実行時はデフォルトで data/paper_trading.db を使用し、本番監視 DB（data/monitoring.db）とは分離されます。
- 設定検証・生成ツールは運用準備（.env 作成 / 設定チェック）に利用してください。
- 実行環境が本番（KABUSYS_ENV=live）の場合、LINE 通知設定や KILL フラグの取り扱いに注意してください（validate_config と config_setup が補助します）。

---

今後の予定（例）
- strategy モジュールのアルゴリズム追加、実運用に向けた監視アラート（LINE）やメトリクス報告の強化。
- 銘柄個別の単元株サイズ対応、手数料・スリッページモデルの改善。
- ユニットテストおよび CI の整備。

（この CHANGELOG はコードベースから推測して作成しました。詳細な変更履歴や過去のコミット履歴に基づくものではありません。）