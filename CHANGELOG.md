# Changelog

すべての重要な変更点を記録します。フォーマットは Keep a Changelog に準拠しています。  
現在のバージョンは __0.1.0__（リリース日: 2026-04-18）です。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-18

### Added
- 基本パッケージ初期版を追加。パッケージメタ情報として `__version__ = "0.1.0"` を定義。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するためのエントリポイント。
    - プロセス優先度を "high" に設定して起動。
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）検知でセッション停止。
    - PID ファイル（data/execution.pid）を取り扱う設定をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用エントリポイント。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト: 60秒）。
    - Monitoring は KABUSYS_ENV に依らず本番用の sqlite_path を使用する設計。
    - 停止フラグ検知でループを終了。
- 設定管理
  - config.py
    - 環境変数読み込み・ラッパー `Settings` を実装。
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - .env のパースはクォートやエスケープ、インラインコメント等に対応する堅牢な実装。
    - 主要設定項目（J-Quants, kabu API, DuckDB/SQLite パス、ログ設定、監視しきい値、環境判定等）をプロパティで提供。
    - `PAPER_FILL_MODE` に対するバリデーション（有効値: instant|partial|never|reject）。
- 設定ユーティリティ / CLI
  - config_setup.py
    - 対話式ウィザードで `.env` を初期作成・更新するツール。
    - J-Quants / kabu API の必須項目の入力支援、デフォルト表示、シークレット項目のマスク表示などをサポート。
    - 生成される `.env` テンプレートのフォーマットを定義。
  - validate_config.py
    - 起動前の設定検証ツール。
    - 必須環境変数未設定の検査、KABUSYS_ENV の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース検証（PyYAML が無ければスキップ）等を実行。
    - `--strict` オプションで警告をエラー扱いにできる。
- ポートフォリオ構築モジュール（pure function 群）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順、タイブレークルール）、等金額配分、スコア加重配分（全銘柄スコアが 0 の場合は等配分にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中上限の適用（特定セクターが上限を超える場合の候補除外）。
    - 市場レジームに応じた投下資金乗数の計算（bull/neutral/bear マッピング、未知レジームでフォールバック）。
  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく銘柄ごとの発注株数計算。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）に基づくスケールダウンロジック、手数料・スリッページ見積りのための cost_buffer を考慮。
  - portfolio/__init__.py で主要関数をエクスポート。
- 監視・実行共通ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで共通利用するロギング初期化ユーティリティ。
    - stdout への StreamHandler（stdout 使用）と日次ローテートする TimedRotatingFileHandler（デフォルト logs/<app>.log、30日保持）を設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールログのみで継続。
    - ログレベルの解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）。
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定ユーティリティ（high/normal/low）および CPU affinity 設定関数。
    - 権限不足や未対応プラットフォーム時は警告ログを出して安全にスキップ。
- モニタリング DB 初期化フック（monitoring.monitoring_db への init 関数を利用）を各起動時に呼び出してテーブルの冪等な準備を保証。
- tools/paper_verification_report.py
  - ペーパートレード履歴（SQLite）から検証レポートを生成する CLI ツールを追加。
  - 指標:
    - 稼働率（uptime％）、ポーリング総数、エラー数
    - 注文成功率（Filled / Created）、送信率（Sent / Created）、リスク却下数
    - API レイテンシ（avg / max / P95）
  - 基準値（しきい値）を定義し、PASS/FAIL 判定を出力（デフォルト基準: 稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）。
  - CLI 引数で期間指定（--from / --to）と DB パス指定（--db）に対応。
- research/factor_research.py
  - DuckDB 接続を使ったファクター計算モジュールを追加（モメンタム / MA200 / ATR / 流動性等を設計に沿って計算する設計方針を記載）。
  - DuckDB の prices_daily / raw_financials テーブル参照で動作することを想定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env パーサーの堅牢化
  - export プレフィックス、クォート中のバックスラッシュエスケープ、インラインコメント処理、空行/コメント行スキップ等に対応。これにより多様な .env 書式に耐性を持たせた。

### Security
- 秘密情報（J-Quants リフレッシュトークン、kabu API パスワード等）は対話式ウィザードではマスク表示され、.env テンプレート生成時にも注記を追加（.env を Git にコミットしないよう明示）。

### Notes / Known limitations
- run_monitoring は Monitoring 用 DB に常に production の sqlite_path を使用する設計（KABUSYS_ENV に依らない）。ペーパートレードと本番 DB の分離は run_execution のみに適用される点に注意してください。
- process_priority / cpu_affinity の設定は権限や OS に依存するため、失敗した場合はログに警告を出してスキップされます。
- config/*.yaml の中身検証には PyYAML が必要。インストールされていない場合は検証をスキップして警告を出します。
- portfolio / position_sizing の価格フォールバック（価格データ欠損時の扱い）については TODO コメントがあり、将来的に改善の余地があります。

---

（今後のリリースでは Unreleased セクションに変更点を追加してください。）