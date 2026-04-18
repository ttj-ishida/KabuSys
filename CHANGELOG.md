# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

現在のリリース方針:
- バージョンはパッケージの __version__ に合わせて管理します（現行: 0.1.0）。
- 重要な追加・変更・修正は本ファイルに日本語で記載します。

## [Unreleased]
- （次版の変更点をここに記載）

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション骨格を追加（kabusys パッケージ初期リリース）。
  - バージョン: src/kabusys/__init__.py: __version__ = "0.1.0"

- 実行エントリスクリプトを追加:
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60秒）。
    - 監視は常に本番用 sqlite_path を使用する旨を明示。
    - 停止はプロジェクト直下 data/stop_requested.flag によるファイルベースのフラグで制御。
  - run_execution.py
    - ExecutionEngine を起動するスクリプト（スレッドでセッション実行）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用し、発注は MockBrokerClient に分離。
    - 停止フラグ検知時に安全に停止処理を実行。
    - 実行用 PID ファイルを data/execution.pid に出力する想定。

- 設定・環境管理:
  - Settings クラスを追加（src/kabusys/config.py）。
    - .env 自動読み込み機能を提供（プロジェクトルートを .git / pyproject.toml で検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
    - .env の読み込みは .env（初期）→ .env.local（上書き）で実施。OS 環境変数は保護（上書き禁止）。
    - .env パースで export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメント等に対応。
    - 各種設定プロパティを提供（J-Quants トークン、kabu API、LINE トークン、DB パス、監視閾値、環境判定ユーティリティなど）。
    - PAPER_FILL_MODE の検証（有効値: "instant"、"partial"、"never"、"reject"）。
    - KABUSYS_ENV と LOG_LEVEL の妥当性検証。

- 設定検証 CLI を追加:
  - validate_config.py
    - .env と config/*.yaml の項目チェックを実行。
    - 必須環境変数未設定やプレースホルダ検出、DB パスの親ディレクトリ存在チェック、YAML パースチェック（PyYAML があれば）を行う。
    - KABUSYS_ENV=live の場合の本番向けガード（LINE 設定の確認、KILL_FLAG_CLEAR_ON_START の警告）を実装。
    - --strict オプションで警告をエラー扱いにできる。

- .env 作成ウィザード CLI を追加:
  - config_setup.py
    - 対話式ウィザードで .env の初期作成/更新を支援。
    - 秘匿項目はマスク表示・入力をサポート。出力はテンプレ化された .env（Git にコミットしない旨のヘッダを付加）。
    - デフォルト値、選択肢、説明文を提供し、保存前に確認プロンプトを表示。

- ログ設定ユーティリティを追加:
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定。
    - 既存ハンドラをクリアしてから再設定し、二重設定を防止。
    - ログレベルは引数 > 環境変数 > デフォルト ("INFO") の順で解決。
    - ログディレクトリは引数 > 環境変数 > デフォルト ("logs") の順で解決。ディレクトリ作成失敗時はファイルハンドラをスキップして stdout のみで継続。

- プロセス優先度ユーティリティを追加:
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。
    - psutil ベースで優先度設定を行い、権限不足や未対応 OS は警告してスキップ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（例外時は警告）。

- ポートフォリオ構築ロジック（純粋関数群）を追加:
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順＋signal_rank によるタイブレークで候補選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化配分（全スコアが0のときは等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限（既存保有に基づいて新規候補を除外、"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた資金乗数（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未知は警告して1.0フォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") による株数算出、単元株丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り、残差に基づく追加配分ロジックを実装。

- 調査ツールを追加:
  - tools/paper_verification_report.py
    - ペーパートレード結果を SQLite（デフォルト: data/paper_trading.db）から解析してレポート出力する CLI。
    - 指標: 稼働率 (uptime)、注文成功率 (fill_rate)、送信率 (send_rate)、P95 レイテンシ等。
    - CLI オプションで期間指定 (--from / --to) と DB パス (--db) を指定可能。
    - デフォルトの合格基準（閾値）を定義（例: uptime >= 99%、fill_rate >= 90% 等）。

- research/factor_research.py（骨格）を追加（DuckDB を使ったファクター計算に着手）。
  - Momentum / Value / Volatility / Liquidity などを想定した設計・定数定義と calc_momentum の枠組みを導入（duckdb 接続前提）。

### Changed
- （初版のため特段の「変更」はなし。今後のリリースで履歴を追加）

### Fixed
- （初版のため特段の「修正」はなし）

### Security
- 環境変数ファイル (.env) は絶対に Git にコミットしない旨を config_setup のヘッダに明記。

### Notes / Implementation details and behavior highlights
- DB 接続:
  - duckdb と sqlite3 を併用（分析用に DuckDB、監視/履歴用に SQLite）。
  - run_monitoring は監視 DB として Settings.sqlite_path（本番）を常に使用する点を明示。
  - run_execution は KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用し、本番 DB と分離する。

- 停止制御:
  - data/stop_requested.flag によるファイルベースの停止フラグを採用（監視・実行スクリプトともに検知して安全に停止）。

- ログ:
  - コンソール出力は stdout を使用（cron 等で stdout/stderr をまとめてリダイレクトする運用を想定）。
  - 日次ローテーション・30世代保持。

- 耐障害性:
  - run_monitoring のポーリングループでは monitor.check_once() で例外が発生してもループを続行し、例外内容はログ出力して次回ポーリングへフォールバック。
  - 各所で権限不足や外部ライブラリ未導入時に処理をスキップし、警告ログを出すことでフェイルセーフを確保。

- 設定検証:
  - validate_config は PyYAML があれば config/*.yaml のパース検証を行い、未インストール時は警告してスキップする実装。

- 純粋関数設計:
  - portfolio と research モジュールは副作用を持たない純粋関数群として実装（単体テストが容易な設計）。

---

将来のリリース案（例）
- ユニットテスト追加（各純粋関数・CLI のテスト）
- Strategy / Execution の詳細実装（ブローカ連携、実注⽤の安全弁）
- ファクター計算の最適化・バッチ化
- モニタリングのアラート通知（LINE 連携）やメトリクスの可視化

もし特定の変更点をより詳しく記載してほしい箇所があれば教えてください（例: run_execution の起動フロー、position_sizing のスケーリングロジック等）。