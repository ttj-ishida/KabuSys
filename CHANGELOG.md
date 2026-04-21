# Changelog

すべての重要な変更は Keep a Changelog の形式で記録します。
このファイルは人間が読める変更履歴を提供することを目的としています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-21

### Added
- 初回リリース。KabuSys のコアユーティリティと起動スクリプト群を追加。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 停止フラグ (data/stop_requested.flag) 検知による安全停止。
    - Monitoring は環境に依らず本番用 `sqlite_path` を使用。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - `KABUSYS_ENV=paper_trading` のときは Mock ブローカーを使用し、paper_trading 用 DB（デフォルト `data/paper_trading.db`）に記録して本番 DB と完全分離。
    - 停止フラグ検知でエンジン停止、PID ファイル管理。
  - config.py
    - 環境変数と設定値を一元管理する Settings クラスを提供。
    - プロジェクトルートの自動検出（.git または pyproject.toml に基づく）と .env / .env.local の自動ロード（OS 環境変数は保護）。
    - .env のパース強化（export 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理など）。
    - Paper Trading 向けの設定（`PAPER_FILL_MODE`、`PAPER_TRADING_SQLITE_PATH`）や監視関連閾値等を提供。
  - config_setup.py
    - 対話式 .env 作成ウィザード。既存 .env の読み込み・編集、シークレットのマスク表示、保存機能を提供。
    - .env のテンプレート書き込み機能（Git へコミットしない旨の警告を含む）。
  - validate_config.py
    - 起動前の設定検証 CLI を提供。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの存在チェック（親ディレクトリの存在を警告）、config/*.yaml の存在と（PyYAML があれば）パース検証。
    - `--strict` オプションで警告も FAIL 扱いにできる。
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプト。
    - 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出し PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ、DB パス指定（引数または環境変数）に対応。
  - portfolio モジュール（純粋関数群）
    - portfolio_builder.py
      - シグナル選別（スコア降順・タイブレーク処理）、等重・スコア重み計算（全スコア 0 の場合フォールバック）。
    - risk_adjustment.py
      - セクター集中制限の適用（既存保有を考慮して当日売却予定は除外、"unknown" セクターは適用外）。
      - 市場レジーム乗数計算（"bull"=1.0、"neutral"=0.7、"bear"=0.3、未知レジームは 1.0 にフォールバック）。
    - position_sizing.py
      - 発注株数算出（allocation_method: risk_based / equal / score）。
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer を考慮した保守的見積り、残差分の追加配分ロジックを実装。
  - utils/logging_setup.py
    - 起動スクリプト共通のロギング設定ユーティリティ。
    - stdout StreamHandler と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定（既存ハンドラのクリーンアップも実施）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続する耐障害性を実装。
  - utils/process_priority.py
    - クロスプラットフォームのプロセス優先度設定ユーティリティ（Windows / POSIX の差分吸収）。
    - CPU affinity 設定ヘルパーも提供。
    - 設定失敗時は警告を出して安全にスキップ。
  - research/factor_research.py（ファクター計算基盤）
    - DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 系ファクターを計算する設計を追加（関数インターフェースと定数群を導入、モメンタム計算関数の開始部分を実装）。

### Changed
- 初回公開のため変更履歴は主に「追加」事項で構成。

### Fixed
- ログ設定:
  - ログディレクトリ作成に失敗した場合でも stdout のログ出力が使えるようにし、ファイルハンドラ作成失敗時に警告を出して処理を継続するように改善。
- 環境変数読み込み:
  - .env の自動ロードで OS 環境変数が上書きされないよう保護（`.env.local` を上書き可能にしつつも OS 環境変数は保持）。
- run_monitoring / run_execution:
  - 停止フラグ検知（data/*.flag）による安全停止処理を追加し、KeyboardInterrupt ハンドリングでリソース（DB 接続等）をきちんとクローズするようにした。
- position_sizing:
  - aggregate cap のスケーリングと残差配分アルゴリズムを導入し、available_cash を超えた場合に再配分して単元株丸めの問題を扱うように改善。

### Security
- config_setup に .env を絶対に Git にコミットしない旨の注意を明記。
- シークレット項目（トークン / パスワード）を対話ウィザードでマスク表示。

### Notes / Implementation details
- DB:
  - 実行系・監視系ともに SQLite（監視 DB / paper_trading DB）と分析用 DuckDB の両方を使用する設計。
  - Monitoring は常に本番用 sqlite_path を参照する設計だが、Execution は `KABUSYS_ENV` に応じて paper_trading 用 DB を使用（分離）。
- 環境変数:
  - 主要な環境変数名とデフォルト値（例: `DUCKDB_PATH`, `SQLITE_PATH`, `LOG_LEVEL`, `KABUSYS_ENV` 等）は Settings クラスのプロパティで管理。
  - `PAPER_FILL_MODE` の値検証を実装（有効値: "instant" | "partial" | "never" | "reject"）。
- ロギング:
  - 全アプリケーションで統一的なログ設定を行い、ログレベル解決順やログディレクトリ解決順を明確化。
- フォールバックと耐障害性:
  - ファイルハンドラ作成失敗や psutil による優先度設定失敗などは警告ログを出して安全にスキップする実装。

---

今後予定（参考）
- research/factor_research の各ファクター計算の完全実装とテスト追加。
- 戦略・実行コンポーネント（execution/*.py）のユニットテスト、BrokerClient のモック整備。
- config/*.yaml を基にした構成のより詳細なバリデーション強化。