# Changelog

すべての変更は Keep a Changelog に準拠して記録します。  
フォーマット: https://keepachangelog.com/（日本語注記）

現在のパッケージバージョン: 0.1.0

## [Unreleased]

（現時点で保留中の変更はありません）

---

## [0.1.0] - 2026-04-21

初回リリース。以下の主要機能・ユーティリティ群を実装しました。

### Added
- 全体
  - パッケージ初版をリリース（`__version__ = "0.1.0"`）。
  - プロジェクト構成に沿った CLI / モジュール群を実装。
- 起動スクリプト
  - `run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60秒）。
    - 停止用フラグファイル（`data/stop_requested.flag`）を検知してループを終了。
    - 起動時にプロセス優先度を "high" に設定。
    - DuckDB と SQLite（監視 DB）へ接続し初期化を行う。
  - `run_execution.py`
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（`data/paper_trading.db`）を使用して本番 DB と分離。
    - ブローカークライアントのファクトリ化（Mock / 実装）に対応。
    - 停止フラグ検知でエンジンを安全に停止。
    - 起動時にプロセス優先度を "high" に設定。
- 設定関連
  - `config.py`
    - 環境変数ベースの設定管理クラス `Settings` を実装。
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を探索）。
    - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
    - Paper Trading 用の `paper_sqlite_path`、`paper_fill_mode`（instant|partial|never|reject）のバリデーションを実装。
    - 監視閾値（CPU/MEM/DISK）や PID / kill flag のパスなど多数の設定プロパティを提供。
  - `config_setup.py`
    - .env を対話式に生成・更新するウィザード CLI を実装。
    - 各設定項目の説明・デフォルト・シークレット入力に対応し `.env` を安全に書き出す。
  - `validate_config.py`
    - 起動前に .env および config/*.yaml の設定不備を検出する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML のパースチェックを実装。
    - `--strict` オプションで警告も失敗扱いにできる。
- ログ / プロセス制御ユーティリティ
  - `utils/logging_setup.py`
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定する共通ユーティリティを実装。
    - LOG_DIR 環境変数 / 引数による出力先変更、ログレベル解決の優先順を実装。ファイル出力に失敗した場合はフォールバックしてコンソール出力のみで継続。
  - `utils/process_priority.py`
    - psutil を利用してプラットフォームに依存しないプロセス優先度設定（high/normal/low）を実装。
    - CPU affinity を最初 N コアに固定する `set_cpu_affinity` を提供（利用不可時は警告を出してスキップ）。
- ポートフォリオ構築（純関数群）
  - `portfolio/portfolio_builder.py`
    - シグナルのソート・候補選定 (`select_candidates`)、
    - 等金額配分 (`calc_equal_weights`)、
    - スコア加重配分 (`calc_score_weights`) を実装。全銘柄スコアがゼロの場合は等配分にフォールバックして警告を出す。
  - `portfolio/risk_adjustment.py`
    - セクター集中制限を適用する `apply_sector_cap` を実装（"unknown" セクターは制限対象外）。
    - 市場レジームに基づく投下資金乗数 `calc_regime_multiplier`（bull/neutral/bear）を実装。未知レジームは 1.0 でフォールバック。
  - `portfolio/position_sizing.py`
    - position sizing ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）に基づいたスケーリングと残差配分アルゴリズムを実装。
    - price 欠損・0 のハンドリングとログ出力に対応。
- リサーチ / ファクター
  - `research/factor_research.py`
    - DuckDB 接続を利用したモメンタム等のファクター計算設計を実装（モメンタムの計算関数群の骨格を実装）。
    - （注）ファイル末尾での calc_momentum 実装が途中で終わっているため、現在は WIP（今後完成予定）。
- ツール
  - `tools/paper_verification_report.py`
    - Paper Trading の検証レポート出力スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、レイテンシ（avg/max/P95）。
    - P95 計算、期間フィルタ、閾値判定（デフォルト閾値: uptime >= 99%、fill >= 90%、send >= 95%、P95 <= 200ms）を実装。
    - DB パスのオーバーライド（環境変数または --db）に対応。

### Changed
- 環境自動読み込み
  - .env の読み込みロジックは OS 環境変数を保護するため `.env` → `.env.local` の順で読み込み、既存 OS 変数は上書きしない挙動を採用。
  - `export KEY=val` 形式やクォート付き値、行内コメントの扱いを細かく処理するパーサを実装。誤った .env フォーマットによる読み込み失敗を低減。
- ロギング
  - StreamHandler を stdout にし、cron/Task Scheduler からのリダイレクトを想定した運用をデフォルトに設定。
- DB ハンドリング
  - 監視（monitoring）モジュールは環境に関わらず監視用 sqlite_path（デフォルト `data/monitoring.db`）を使用するように設計（本番とテストの分離ルールに留意）。

### Fixed
- 設定検証
  - `validate_config` において、YAML パーサ未インストール時はパース検証をスキップし警告を出すようにして UX を改善（PyYAML がない環境での実行を許容）。
- エラー耐性
  - 起動ループ内での予期しない例外はログに例外情報を残して次のポーリングに進むよう変更。監視ループ・エンジンの安定性向上。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

## 補足・注意事項（移行 / 運用メモ）
- .env の自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト環境などで利用）。
- Paper Trading と Live（本番）は DB を分離する設計です。`KABUSYS_ENV=paper_trading` 時は `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）を使用します。
- 監視プロセス（run_monitoring）は監視用の sqlite（`SQLITE_PATH`）を使用します。開発環境・本番環境に関わらず監視 DB は `SQLITE_PATH` を参照する点に注意してください。
- `PAPER_FILL_MODE` は "instant" | "partial" | "never" | "reject" のいずれかを指定する必要があります。不正値は起動時に例外を発生させます。
- `process_priority.set_process_priority` は psutil の権限・OS 機能に依存します。権限不足の場合は警告を出してスキップします。
- `research/factor_research.py` の一部（calc_momentum など）は未完の部分があり、今後完成予定です。現状は骨格実装（定義・定数）中心です。

---

今後の予定（例）
- factor_research の完全実装（モメンタム / ボラティリティ / バリュー等）。
- 単体テスト・CI 整備、型注釈・ドキュメントの充実。
- ExecutionEngine / Broker クライアントの追加テストとペーパートレード挙動の検証強化。