# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

現在のバージョン: 0.1.0

## [0.1.0] - 2026-04-19
初回リリース。

### 追加 (Added)
- 基本アーキテクチャ
  - パッケージ名: `kabusys` — 日本株自動売買システムの初期実装を追加。
  - バージョン情報: `__version__ = "0.1.0"` を設定。

- 実行エントリ / デーモン
  - run_monitoring スクリプト (`src/kabusys/run_monitoring.py`)
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書き（デフォルト 60 秒）。
    - 停止フラグファイル (`data/stop_requested.flag`) の存在で安全に停止。
    - 監視 DB は環境に関係なく本番 sqlite_path を使用して初期化。
    - duckdb 接続を同時に確立。

  - run_execution スクリプト (`src/kabusys/run_execution.py`)
    - ExecutionEngine の起動スクリプトを実装。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 専用 SQLite（デフォルト `data/paper_trading.db`）を使用し、MockBrokerClient を使って本番 DB と分離。
    - 停止フラグファイルでエンジンを安全に停止。
    - ExecutionEngine をデーモン的にスレッドで実行。

- 設定関連
  - Settings クラス (`src/kabusys/config.py`)
    - 環境変数読み込みラッパーを提供（`.env` / `.env.local` の自動読み込み機能を内蔵）。
    - 多数の設定プロパティを提供（J-Quants / kabu API / DB パス / ログ / 監視閾値など）。
    - `paper_fill_mode` の検証（有効値: "instant" / "partial" / "never" / "reject"）。
    - `env` の検証（`development` / `paper_trading` / `live`）。
    - `is_live` / `is_paper` / `is_dev` のユーティリティ。

  - 設定ウィザード CLI (`src/kabusys/config_setup.py`)
    - 対話式で `.env` を作成・更新するウィザードを実装。
    - デフォルト値・選択肢・シークレット入力の扱い、既存 `.env` の読み込みに対応。
    - 保存前の確認と `.env` ファイル書き出し機能を提供。

  - 設定検証 CLI (`src/kabusys/validate_config.py`)
    - .env と config/*.yaml の検証ツールを実装。
    - 必須環境変数のチェック、KABUSYS_ENV の妥当性、ログレベル、DB パス、YAML パース（PyYAML があれば）などを検証。
    - `--strict` オプションで警告を失敗扱いにできる。

- ログ・プロセス管理ユーティリティ
  - ログ設定ユーティリティ (`src/kabusys/utils/logging_setup.py`)
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定。
    - LOG_LEVEL / LOG_DIR / app_name に基づく設定。既存ハンドラを削除して二重設定を防止。
    - ファイルハンドラ作成失敗時はコンソール出力のみで継続。

  - プロセス優先度 / CPU affinity ユーティリティ (`src/kabusys/utils/process_priority.py`)
    - Windows / POSIX 両方に対応してプロセス優先度を設定（"high" / "normal" / "low"）。
    - CPU affinity を最初の N コアにピン留めする機能を提供。
    - psutil を利用し、権限不足や未対応 OS の場合は安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder (`src/kabusys/portfolio/portfolio_builder.py`)
    - 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。

  - risk_adjustment (`src/kabusys/portfolio/risk_adjustment.py`)
    - セクター集中制限を適用する apply_sector_cap を実装（sell_codes を除外）。
    - 市場レジームに基づく投下資金乗数 calc_regime_multiplier 実装（bull:1.0 / neutral:0.7 / bear:0.3、未知は 1.0 にフォールバック）。

  - position_sizing (`src/kabusys/portfolio/position_sizing.py`)
    - position サイズ計算機能を実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap によるスケーリング（コストバッファ対応）。
    - リスクベースの計算や利用可能現金に基づくスケールダウン処理を実装。

  - パッケージエクスポート (`src/kabusys/portfolio/__init__.py`)
    - 上記関数群をトップレベルでエクスポート。

- Paper Trading 検証ツール
  - paper_verification_report (`src/kabusys/tools/paper_verification_report.py`)
    - ペーパートレードの検証レポート生成ツールを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数等を算出。
    - デフォルト閾値を定義（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200 ms）。
    - 日付フィルタ（--from / --to）と DB パス指定オプション（--db）をサポート。
    - 空データやテーブル未存在時の耐性を持たせた実装。

- データベース連携
  - sqlite3 と duckdb の両対応を整備（monitoring / execution 両スクリプトで使用）。
  - monitoring DB 初期化用の init_monitoring_db 呼び出しを確実に行う（冪等性を想定）。

- 研究モジュール（骨組み）
  - factor_research (`src/kabusys/research/factor_research.py`)
    - Momentum / MA200 / ATR / Liquidity などのファクター計算の方針と定数を定義。
    - DuckDB 接続を受けて prices_daily / raw_financials から計算する設計。
    - 関数シグネチャや一部実装（calc_momentum の実装開始）が含まれる（未完の可能性あり）。

### 変更 (Changed)
- なし（初回リリースのため新規実装中心）。

### 修正 (Fixed)
- なし（初回リリース）。

### 注意事項 / ドキュメント補足 (Notes)
- 環境変数自動読み込み
  - デフォルトで `.env` と `.env.local` をプロジェクトルート（.git または pyproject.toml を基準）から自動的に読み込みます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- MONITOR_POLL_INTERVAL の扱い
  - 0 や負数、整数以外が設定された場合は警告を出してデフォルト（60 秒）にフォールバックします。

- ログ出力
  - コンソールは stdout に出力します（cron 等のリダイレクトと相性が良いように設計）。

- 本番（live）運用時の注意
  - validate_config で `KABUSYS_ENV=live` の場合に追加の警告チェックを行います（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の確認等）。

- Paper Trading 分離
  - paper_trading 環境はデータベースとブローカーを明示的に分離しており、本番口座に影響を与えない設計です。

---

今後の予定（例）
- factor_research の完全実装（Momentum の SQL 実装完了など）
- ExecutionEngine / SystemMonitor 周辺の詳細なテストとエンドツーエンドのドキュメント
- 銘柄別 lot_size のサポート（stocks マスタ連携）
- より詳細な CI / 静的解析ルール導入

--- 

（注）本 CHANGELOG は提供されたコードベースから推測して作成しています。実際のリリースノートはプロジェクト方針や変更履歴に合わせて調整してください。