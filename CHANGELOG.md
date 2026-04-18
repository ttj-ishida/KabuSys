CHANGELOG
=========

すべての重要な変更履歴を記載します。本ファイルは "Keep a Changelog" の形式に準拠しています。

フォーマットの意味:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated: 廃止予定
- Removed: 削除
- Security: セキュリティに関する修正

[0.1.0] - 2026-04-18
-------------------

Added
- 基本アプリケーション骨格を実装（初期公開リリース v0.1.0）。
  - パッケージ情報:
    - バージョン: __version__ = "0.1.0"
    - パッケージ名: kabusys

- 環境・設定管理
  - 自動 .env 読み込み機能（プロジェクトルートの .env / .env.local）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - .git または pyproject.toml を基準にプロジェクトルートを探索（CWD 非依存）。
  - 高機能な .env パーサ実装:
    - export KEY=val 形式に対応。
    - クォート（シングル/ダブル）内のバックスラッシュエスケープ処理対応。
    - クォート無しの値でインラインコメント（#）の扱いをスマートに処理。
  - Settings クラスで環境変数を型付きプロパティとして提供:
    - DB パス (DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH)
    - API トークン/パスワード（必須項目は未設定時にエラー）
    - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject"）
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - ログレベルの検証 等

- 設定支援 CLI
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新するスクリプト。
    - 秘匿項目は表示をマスク。
    - デフォルト値・選択肢の提示、保存前の確認を実装。
    - .env の書式は Git にコミットしないことを強調。

- 設定検証 CLI
  - validate_config.py: .env と config/*.yaml の検証ツール。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
    - DUCKDB/SQLITE の親ディレクトリ存在チェック（起動時自動作成を考慮）。
    - PyYAML があれば YAML ファイルのパース検証を実施（未インストール時は警告）。
    - --strict オプションで警告を FAIL として扱える。

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動用スクリプト。
    - プロセス優先度を "high" に設定して起動。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用（本番 DB と完全分離）。
    - BrokerClientFactory を使用して実ブローカ／Mock を切替可能（ドキュメントに記載）。
    - PID ファイル管理（data/execution.pid）、停止フラグ (data/stop_requested.flag) を監視して安全に停止。
    - リスクマネージャ・オーダーマネージャ・リコンシリエータ等の初期化を行う。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用（監視データは共通 DB）。
    - 停止フラグ (data/stop_requested.flag) を検出してループを終了。
    - 例外発生時はログに例外を記録して次ループまで待機。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル決定順: 引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"。
  - utils/process_priority.py:
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - psutil を用い、権限不足等の例外は警告でスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順（同点は signal_rank）で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重（スコア全0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限（既存保有のエクスポージャーに基づき新規候補を除外）。
      - unknown セクターは上限適用外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。
      - 未知のレジームは警告を出して 1.0 でフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes:
      - allocation_method に応じて発注株数を計算 ("risk_based" / "equal" / "score")。
      - 単元株（lot_size）丸め、1 銘柄上限・アグリゲート上限、cost_buffer（手数料・スリッページ保守見積）対応。
      - 利用可能現金に対するスケールダウン（端数は lot_size 単位で残差分を大きい順に配分）。
      - risk_based 時の基本ロジック（risk_pct, stop_loss_pct 使用）。

- 解析・ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成スクリプト（SQLite DB から指標を集計）。
    - 指標: 稼働率(uptime_pct)、注文成功率(fill_rate)、送信率(send_rate)、P95 レイテンシ、リスク却下数 など。
    - PASS/FAIL 判定用しきい値を実装:
      - 稼働率 >= 99%
      - 成功率 >= 90%
      - 送信率 >= 95%
      - P95 latency <= 200 ms
    - CLI オプションで期間 (--from / --to) と DB パス (--db) を指定可能。
    - PAPER_TRADING_SQLITE_PATH 環境変数を尊重。デフォルト: data/paper_trading.db

- 研究用コード
  - research/factor_research.py:
    - ファクター計算の骨格を実装（モメンタム、MA200乖離、ATR、流動性系等を想定）。
    - DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。関数定義と定数群を実装中。

Changed
- N/A（初期リリースのため変更履歴なし）

Fixed
- N/A（初期リリースのため修正履歴なし）

Deprecated
- N/A

Removed
- N/A

Security
- N/A

Notes / 運用上の注意
- 環境分離:
  - 実行コンポーネント (execution) は KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite DB (data/paper_trading.db) を使い本番 DB と完全に分離する設計です。運用時は環境変数設定を確認してください。
  - 監視コンポーネント (monitoring) は環境にかかわらず監視用 sqlite_path を使用します（監視データは一貫して収集される想定）。
- 停止・強制終了:
  - 停止フラグ: data/stop_requested.flag を作成すると実行中プロセスが安全に停止します。
  - Kill Switch 関連設定は本番 (KABUSYS_ENV=live) では特に注意が必要です。validate_config の警告を参照してください。
- ロギング:
  - デフォルトは logs/<app_name>.log に日次ローテートで出力。ログディレクトリが作れない環境ではコンソールのみで継続します。
- 依存:
  - 一部機能は psutil、duckdb、PyYAML 等の外部パッケージを使用します。validate_config は PyYAML が無ければ YAML 検証をスキップします。

今後の予定（例）
- factor_research の完全実装（モメンタム / バリュー / ボラティリティ / 流動性ファクターの SQL 実装）。
- ExecutionEngine 周りの詳細実装とテスト充実（ブローカープラグインの拡充、エラーハンドリング強化）。
- 単体テスト・統合テストの追加、および CI の整備。

----------------------------------------
参考: Keep a Changelog — https://keepachangelog.com/en/1.0.0/