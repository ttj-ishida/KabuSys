# Changelog

すべての重要な変更はこのファイルに記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。  

## [Unreleased]

---

## [0.1.0] - 2026-04-25

初回リリース。以下の主要機能・ユーティリティ群を追加しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。
- 設定管理
  - 環境変数 / .env を扱う Settings クラスを追加（`kabusys.config`）。
  - .env 自動ロード機能をプロジェクトルート（.git または pyproject.toml を基準）から実装。
  - 自動ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` サポート。
  - .env のパース機能を強化（`export KEY=val`、シングル/ダブルクォート、エスケープ、インラインコメントの扱い等に対応）。
  - 多数の設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境種別 / ログレベル 等）。
  - `PAPER_FILL_MODE` のバリデーション（有効値: "instant" / "partial" / "never" / "reject"）。
  - Paper Trading 用 DB パス (`PAPER_TRADING_SQLITE_PATH`) と production/paper の分離をサポート。
- 設定ウィザード & 検証 CLI
  - `.env` を対話的に生成・更新するウィザード (`kabusys.config_setup`) を追加。
  - 設定検証 CLI (`kabusys.validate_config`) を追加。必須環境変数やパス、YAML ファイルの存在・パース（PyYAML が利用可能な場合）をチェック。`--strict` オプションで警告も失敗扱いにできる。
- 起動スクリプト
  - 監視プロセス起動スクリプト `run_monitoring.py` を追加。ポーリングループ、停止フラグ検知、例外処理、ポーリング間隔の環境変数上書き（`MONITOR_POLL_INTERVAL`）を提供。監視モジュールは環境にかかわらず production の sqlite_path を使用する仕様。
  - 実行エンジン起動スクリプト `run_execution.py` を追加。`KABUSYS_ENV=paper_trading` 時は MockBrokerClient を用いて paper_trading 専用 DB に記録する（本番 DB と分離）。スレッドで ExecutionEngine を起動し、停止フラグを監視して安全に停止するロジックを実装。
- ロギング & プロセス制御ユーティリティ
  - 統一的なロギング初期化ユーティリティ `kabusys.utils.logging_setup.setup_logging` を追加。stdout 出力（StreamHandler）と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をフォールバック。
  - プロセス優先度 / CPU affinity 設定ユーティリティ `kabusys.utils.process_priority` を追加。Windows / POSIX を抽象化して優先度設定を行い、失敗時は警告ログでスキップする。
- ポートフォリオ構築モジュール
  - 銘柄選定・配分関連の純粋関数群を追加（`kabusys.portfolio` 以下）。
    - `select_candidates`: スコア降順で候補を選択。
    - `calc_equal_weights`, `calc_score_weights`: 等配分・スコア加重配分を実装（スコア合計が 0 の場合は等配分にフォールバック）。
    - `apply_sector_cap`: セクター集中上限チェック（既存保有時価を考慮し、上限超過セクターの候補除外）。"unknown" セクターは上限適用対象外にした。
    - `calc_regime_multiplier`: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームは警告を出して 1.0 にフォールバック。
    - `calc_position_sizes`: risk_based / equal / score の配分ロジック、単元株（lot_size）丸め、個別上限および aggregate cap（利用可能現金に合わせてスケールダウン）を実装。cost_buffer による保守的見積りも反映。
- Paper Trading 検証レポート
  - `kabusys.tools.paper_verification_report` を追加。paper_trading の SQLite DB からシステム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（P95 含む）などを集計してレポート出力する CLI を提供。閾値判定（PASS/FAIL）を行う。DB が存在しない場合のエラー表示や、テーブルが無い場合のフォールバックを備える。
- リサーチ基盤（ファクター計算）
  - `kabusys.research.factor_research` にモメンタム等のファクター計算の基盤を追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計）。モメンタム系（1M/3M/6M、MA200乖離等）の基礎実装を開始。

### Changed
- ログ設定の一元化により、各起動スクリプトで同様のログ設定を行わず `setup_logging` を呼ぶ設計に統一。
- .env の読み込み順序と保護（OS 環境変数を overwrite しない挙動）を明確化（`.env` → `.env.local`、`.env.local` は上書き可能だが OS 環境変数は保護）。
- 実行エンジンと監視で共通の監視テーブルが存在することを保証するため起動時に `init_monitoring_db` を呼ぶ（冪等）。

### Fixed
- 監視ループのポーリング間隔環境変数（`MONITOR_POLL_INTERVAL`）が不正値のときに安全にデフォルトにフォールバックするように修正（0 以下や非数値を警告して 60 秒を使用）。
- 起動時に既存のログハンドラが二重設定される問題を防ぐため、`setup_logging` が既存ハンドラをきれいに閉じてから再設定するようにした。
- プロセス優先度設定で権限不足や未対応プラットフォームで例外が飛ぶのを抑制し、警告ログでスキップするように改善。

### Security
- .env を生成するウィザードで生成された `.env` を Git にコミットしないようヘッダコメントで明記（機密情報保護の注意喚起）。

---

今後の予定（例）
- factor_research の各ファクター実装の完了（Value / Volatility / Liquidity 等）。
- ExecutionEngine / BrokerClient の詳細実装とテストカバレッジ拡充。
- 単体テスト・統合テストの追加と CI 設定。
- 監視・アラート（LINE通知等）の強化。