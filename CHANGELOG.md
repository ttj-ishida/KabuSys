# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
注: 以下の内容は提示されたコードベースから推測して作成したリリースノートです。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-18
初回公開リリース。

### Added
- 全体
  - パッケージ初版を追加（package metadata: `__version__ = "0.1.0"`）。
  - コマンドライン用スクリプト群を追加:
    - 実行エンジン起動スクリプト: `src/kabusys/run_execution.py`
      - `KABUSYS_ENV=paper_trading` の場合は専用のペーパートレード用 SQLite を使用し、本番 DB と完全に分離（デフォルト: `data/paper_trading.db`）。
      - エンジンの PID 管理用ファイル (`data/execution.pid`) と停止フラグ (`data/stop_requested.flag`) をサポート。
      - ブローカークライアント抽象化を経由して Mock 実装 / 実ブローカーを切替可能（`BrokerClientFactory`）。
    - 監視ポーリング起動スクリプト: `src/kabusys/run_monitoring.py`
      - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
      - 監視は環境にかかわらず本番用の sqlite パスを使用して初期化。
  - 設定管理:
    - `.env` 自動読み込みと Settings クラス: `src/kabusys/config.py`
      - プロジェクトルートを `.git` または `pyproject.toml` から発見して `.env` / `.env.local` を自動読み込み（環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
      - `.env` のパースは `export ` プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（クォート外のみ）に対応。
      - 設定プロパティ群を提供（DB パス、KABUSYS_ENV、ログレベル、Paper Trading 関連 etc.）と基本的なバリデーション（`KABUSYS_ENV` / `LOG_LEVEL` / `PAPER_FILL_MODE` 等）。
  - 設定ユーティリティ:
    - 対話式環境設定ウィザード: `src/kabusys/config_setup.py`
      - `.env` の対話的作成・更新を支援。シークレット項目はマスク表示し、保存前に確認を促す。
    - 設定検証 CLI: `src/kabusys/validate_config.py`
      - 必須環境変数の存在確認、`KABUSYS_ENV` の妥当性、DB パスの親ディレクトリ確認、`config/*.yaml` の存在と（PyYAML があれば）パース検証、live 環境向けのガードチェック等を実施。`--strict` で警告を失敗扱いにできる。
  - ロギング / プロセス管理ユーティリティ:
    - 統一ロギング設定: `src/kabusys/utils/logging_setup.py`
      - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。`LOG_LEVEL` / `LOG_DIR` / 引数で上書き可能。ログディレクトリ作成失敗時はファイル出力を無効化しコンソールのみで継続。
    - プロセス優先度 / CPU affinity ユーティリティ: `src/kabusys/utils/process_priority.py`
      - Windows / POSIX（Linux, macOS, FreeBSD）を吸収したインターフェースで優先度を設定（"high"/"normal"/"low"）。`psutil` 利用。アクセス権限不足等は警告を出してスキップ。
  - ポートフォリオ構築関連（純関数群: DB 非依存・メモリ計算）:
    - 候補選定・重み計算: `src/kabusys/portfolio/portfolio_builder.py`
      - シグナルをスコア降順でソートする `select_candidates`、等分配 `calc_equal_weights`、スコア加重 `calc_score_weights`（全スコアが 0 の場合は等分配にフォールバック）。
    - セクター集中制限・レジーム乗数: `src/kabusys/portfolio/risk_adjustment.py`
      - セクター上限を超える場合に新規候補を除外する `apply_sector_cap`（"unknown" セクターは除外対象外）。
      - レジームに応じた投下資金乗数を返す `calc_regime_multiplier`（"bull"/"neutral"/"bear" をハンドルし、未知値は警告とともに 1.0 にフォールバック）。
    - 株数決定・リスク制限・単元丸め: `src/kabusys/portfolio/position_sizing.py`
      - `risk_based` / `equal` / `score` の配分方式に対応し、損切り率・リスク許容率、単元株（lot）丸め、aggregate cap によるスケールダウン・再配分ロジックを実装。
    - 上記をパッケージ公開: `src/kabusys/portfolio/__init__.py`
  - ペーパートレード検証レポート生成スクリプト: `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH`）から統計を集計し、稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）等を出力。閾値比較により PASS/FAIL を判定。
  - 研究用ファクター計算モジュール（途中実装）: `src/kabusys/research/factor_research.py`
    - Momentum / Value / Volatility / Liquidity に関する計算方針と定数群を追加。DuckDB 接続を受け取り prices_daily / raw_financials を用いて計算する設計。

### Changed
- .env 読み込みの安全性と柔軟性を強化
  - `export KEY=val` 形式や引用符内のバックスラッシュエスケープ、インラインコメントの扱いなどを詳細にサポート。
  - 自動読み込み時の既存 OS 環境変数保護ロジック（`protected`）を導入し、`.env.local` を使って OS 環境を上書き可能に。

- ロギング挙動
  - コンソール出力を stdout に明示（cron/スケジューラでのリダイレクトに配慮）。
  - ログディレクトリ作成失敗時にファイルハンドラ生成をスキップするフォールバックを追加。

- プロセス優先度設定
  - Windows / POSIX の差分を吸収する実装に統一。失敗時には警告を出して処理を継続。

### Fixed
- .env のパースに関する細かい不具合対策（引用符・エスケープ・コメントの扱い）を行い、意図しないトリミングやコメント誤認を回避。

### Notes / Known limitations
- research/factor_research.py は設計と一部機能（計算関数定義の開始）を含むものの、提示されたコードは途中で切れており完全実装は未完了。利用時は該当関数の実装完了が必要。
- 一部のファイルに TODO コメント（例: 価格欠損時のフォールバック策、銘柄別 lot_size の拡張等）が残っているため、将来的な改善余地あり。
- `psutil`、`duckdb`、`PyYAML` など外部依存があるため、本番導入時には環境に応じたパッケージインストールが必要。
- `config/*.yaml` のデフォルト生成スクリプト（言及あり）や、実際の ExecutionEngine / BrokerClient の具体実装はこの差分からは推測できないため、本番接続には追加設定・実装が必要。

---

作成者: 自動生成（コード内容から推測）  
注: 実際のリリースノート作成時はコミット履歴や PR 説明を参照して確定情報を反映してください。