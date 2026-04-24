# Changelog

すべての変更は「Keep a Changelog」形式に準拠して記載しています。

以下はコードベースから推測して作成した変更履歴です。日付は推定（リリース日: 2026-04-24）です。

## [Unreleased]
- ドキュメント化やテスト、追加のファクター計算の実装などの作業を予定。

## [0.1.0] - 2026-04-24

### Added
- 基本アプリケーションパッケージを追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するためのエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定する仕組みを導入。
    - 停止用フラグファイル（data/stop_requested.flag）を検知して安全に停止。
    - デーモンスレッドでエンジンを実行し、停止指示時に engine.stop() を呼び出すループを提供。

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を参照する設計。
    - 停止フラグの検知、例外ハンドリング、接続クローズ処理を実装。

- 設定管理と補助 CLI
  - config.py
    - .env ファイル自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順序および OS 環境変数保護機構を実装。
    - 複数の設定プロパティを持つ Settings クラスを提供（DB パス、API トークン、環境判定、しきい値など）。
    - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。

  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を実装。
    - ユーザー対話による入力、既存 .env 読み込み、秘密値のマスキング表示、保存確認をサポート。
    - デフォルト・選択肢と説明文を備えた項目定義を提供。

  - validate_config.py
    - 起動前に .env と config/*.yaml の簡易検証を行う CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ存在チェック、YAML パースチェック（PyYAML があれば実行）を実装。
    - --strict オプションで警告を失敗扱いにする機能を追加。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順・タイブレーク）を実装。
    - 等配分 calc_equal_weights、スコア重み calc_score_weights（全スコア=0 の場合は等配分へフォールバック）を実装。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有の時価ベースで判定）と候補フィルタリングを実装。unknown セクターは除外対象にしない挙動。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームは警告のうえ 1.0 でフォールバック。

  - portfolio/position_sizing.py
    - calc_position_sizes: 複数の配分方式（risk_based / equal / score）に基づく発注株数計算を実装。
    - 単元株（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap（available_cash）判定とスケーリング、cost_buffer を加味した保守的見積り、残差処理による追加配分ロジックを実装。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログセットアップ関数 setup_logging を追加。
    - stdout 出力用 StreamHandler と日次ローテーション（TimedRotatingFileHandler、30日保持）をルートロガーに設定。
    - ログディレクトリ自動作成、失敗時のフォールバック（コンソールのみ）処理を実装。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト。

  - utils/process_priority.py
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を追加。
    - Windows / POSIX (Linux/macOS/FreeBSD) を吸収する実装。権限不足などがあれば警告ログでスキップ。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 入出力: SQLite（PAPER_TRADING_SQLITE_PATH または --db）から集計し、稼働率・注文成功率・送信率・レイテンシ等を算出。
    - P95 レイテンシ計算、閾値（稼働率 99%、成立率 90% など）による PASS/FAIL 判定を実装。
    - 日付フィルタ (--from/--to) をサポート。

- 研究用モジュール（途中実装）
  - research/factor_research.py
    - ファクター計算の設計（Momentum/Value/Volatility/Liquidity）を追加。DuckDB 接続を受け取る想定。
    - モメンタム計算関数 calc_momentum の骨子（定数・説明）を実装。以降の詳細実装は継続予定（ファイル末尾で未完）。

- パッケージ初期化
  - __init__.py にて __version__ = "0.1.0" を設定。

### Changed
- ログ出力の挙動
  - logging_setup は stdout を使用しているため、cron やスケジューラでのリダイレクトを想定した出力設計となっている。
  - 既存ハンドラがある場合は一旦 flush/close してから再設定することで二重出力を防止。

- .env 自動ロードのポリシー
  - プロジェクトルートが特定できない場合は自動ロードをスキップするようにした（配布後の安全性向上）。
  - .env.local を .env の上書きとして読み込む（OS 環境変数は保護）。

### Fixed / Robustness
- 設定値バリデーション・フォールバック
  - MONITOR_POLL_INTERVAL が不正（整数でない、0 以下など）の場合は警告を出してデフォルト 60 秒にフォールバック（run_monitoring）。
  - PAPER_FILL_MODE の不正値は Settings で ValueError を投げるように検証。
  - sqlite / duckdb 接続は finally ブロックで確実にクローズするように実装。
  - YAML の検証は PyYAML 未インストール時にスキップし、警告を出すことで依存性に柔軟に対応。

- 例外ハンドリング
  - monitor.check_once() 実行時の例外は catch してログ出力し、次のポーリングへ継続（run_monitoring）。
  - process_priority / cpu_affinity の実行は権限エラーや未実装環境を捕捉して警告を出す。

### Security
- .env の取り扱い注意喚起を config_setup のヘッダに明記（.env を Git 管理しない旨）。

### Notes / Implementation Details
- run_execution は paper_trading 環境用に DB を分離しており、MockBrokerClient を使う設計を想定（コメント記載）。
- apply_sector_cap は当日売却予定銘柄（sell_codes）を既存エクスポージャー計算から除外できる仕様。
- calc_regime_multiplier は未知のレジーム時にログ警告を出し 1.0 でフォールバック。
- calc_position_sizes の aggregate cap 実装は、スケールダウン後に lots 単位で残余キャッシュを利用して追加配分を試みるアルゴリズムを持つ。
- paper_verification_report のレポート閾値や出力フォーマットはハードコードされているため、将来的に外部設定化が可能。

---

開発者向け: 上記はソースコードの読み取りから推測した変更点です。実際のコミット履歴やリリースノートと異なる場合があります。必要であれば、コミットログや PR を基にした正確な CHANGELOG 生成をサポートします。