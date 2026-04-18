# CHANGELOG

すべての重要な変更点を記載します。本ドキュメントは「Keep a Changelog」フォーマットに準拠します。

既知の制約や TODO も併記しています。コードベースからの推測に基づく内容のため、実際の変更履歴と差異がある可能性があります。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

初回公開リリース。主要な機能・ユーティリティ群を実装しました。

### Added（追加）

- CLI / 起動スクリプト
  - `run_execution.py`: 実際の注文実行エンジン起動スクリプトを追加。プロセス優先度を上げて起動し、`KABUSYS_ENV=paper_trading` の場合は Paper Trading 用の専用 SQLite DB を使用する（`data/paper_trading.db` がデフォルト）。停止フラグ・PID 管理に対応。
  - `run_monitoring.py`: システム監視ポーリングループ起動スクリプトを追加。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番用の `sqlite_path` を使用する設計。

- 設定・検証・セットアップ
  - `config.py`: 環境変数ラッパー `Settings` を実装。`.env` 自動読み込み（プロジェクトルート検出）機能と高度な `.env` パーサ（クォート・エスケープ・インラインコメント対応）を提供。各種設定値（DB パス、Kill Switch、しきい値、PAPER_FILL_MODE 検証等）をプロパティとして提供。
  - `config_setup.py`: 対話式ウィザードで `.env` を生成/更新するツールを追加。シークレットのマスク表示やデフォルト値、保存前確認を実装。
  - `validate_config.py`: 起動前設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスや config/*.yaml 存在確認（PyYAML があればパース検証）を行い、`--strict` で警告を失敗扱いにできる。

- ポートフォリオ構築（純関数群）
  - `portfolio/portfolio_builder.py`: シグナル選定（スコア降順、タイブレークに `signal_rank`）および等金額/スコア加重の重み計算を追加。スコア全てが 0 の場合は等金額にフォールバックし警告を出力。
  - `portfolio/position_sizing.py`: 発注株数計算ロジックを実装（`risk_based`, `equal`, `score` の各配分方式対応）。単元（lot）丸め、per-stock 上限、aggregate cap（利用可能現金に応じたスケーリング）、cost_buffer を用いた保守見積り、残余キャッシュを用いた端数配分などを実装。
  - `portfolio/risk_adjustment.py`: セクター集中上限（`apply_sector_cap`）および市場レジームに応じた投下資金乗数（`calc_regime_multiplier`）を実装。未知レジームは警告のうえフォールバック（1.0）。

- ユーティリティ
  - `utils/logging_setup.py`: ルートロガーの統一設定ユーティリティを追加。stdout への StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler、30日保持）を設定。ログディレクトリ作成失敗時はファイル出力を回避してコンソールのみで継続。
  - `utils/process_priority.py`: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定を提供。CPU affinity 設定ユーティリティも追加。権限不足や未対応 OS の場合は警告を出力してスキップ。

- モニタリング DB 初期化
  - `monitoring/monitoring_db.py` を参照する起動手順を追加（起動時に監視用テーブルを冪等的に作成）。

- Paper Trading 検証ツール
  - `tools/paper_verification_report.py`: Paper Trading 用の検証レポート生成ツールを追加。稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、APIレイテンシ（平均/最大/P95）を集計し、閾値比較で PASS/FAIL を判定。P95 算出と日付フィルタ（ISO8601 UTC 変換）に対応。

- リサーチ（ファクター計算）
  - `research/factor_research.py` にモメンタム系ファクター計算（1M/3M/6M リターン、MA200 乖離など）を実装予定のコードを追加（DuckDB 接続を受ける設計、prices_daily/raw_financials を使用）。

### Changed（変更）

- ロギング挙動
  - 全スクリプト共通で `setup_logging(app_name=...)` を呼び出してログ設定を統一。コンソール出力は stderr ではなく stdout を使用するように統一（cron / スケジューラとの互換性向上）。

- DB パスの取り扱い
  - 実行エンジン起動時に `KABUSYS_ENV` が `paper_trading` の場合は paper_trading 用の専用 SQLite（`PAPER_TRADING_SQLITE_PATH` / `data/paper_trading.db`）を使用するよう明確化。監視（monitoring）は環境にかかわらず `SQLITE_PATH`（本番用）を使う設計となっている（意図的な分離）。

### Fixed（修正 / 安全策）

- 環境変数パースの堅牢化
  - `.env` パーサでクォート付き文字列のエスケープ、インラインコメントの扱い、`export KEY=val` 形式への対応などを実装。壊れた .env による起動失敗を低減。

- ポジションサイズ計算の安全弁
  - 価格欠損（価格が None または <= 0）の銘柄をスキップすることでゼロ除算や不適切な発注を避けるように改良。

- モニタリングのポーリング設定
  - `MONITOR_POLL_INTERVAL` のバリデーションを追加（1 未満の値や非整数はデフォルト 60 秒へフォールバック）し、`time.sleep` による例外発生を防止。

### Performance

- 起動直後にプロセス優先度を上げることで、低レイテンシ要件のあるコンポーネント（Execution / Monitoring）で優先的な CPU 割当を試みる設計。

### Documentation / Misc

- パッケージメタ情報
  - `__init__.py` にバージョン `0.1.0` を設定。

- CLI ヘルプ / ユーザフロー
  - `config_setup.py` のウィザードは既存 `.env` を読み込み、Enter で既存値の再利用、保存前の確認、シークレットのマスク表示を提供。

### Known issues / TODO / Limitations

- research/factor_research.py はファイル末尾が途中で切れている（実装途中の可能性あり）。完全なファクター計算ロジックの追加・テストが必要。
- `position_sizing.calc_position_sizes` の将来的拡張として、銘柄別の `lot_size` をサポートする旨の TODO コメントあり（現状は全銘柄共通の lot_size）。
- `apply_sector_cap` の価格欠損時のエクスポージャー計算では price=0.0 による過少見積りのリスクがコメントで指摘されている（将来的にフォールバック価格の導入を検討）。
- 一部の機能（例: ブローカークライアントのファクトリ、ExecutionEngine 内部、monitoring.monitor の詳細など）は本 CHANGELOG の範囲外であり、実装の詳細は該当モジュールのテスト・レビューが必要。
- `set_process_priority` / `set_cpu_affinity` は権限不足やプラットフォーム差分で失敗する可能性があり、その場合は警告ログを出してスキップする挙動。

### BREAKING CHANGES

- なし（初回リリースのため該当なし）。

---

フォーマット: Keep a Changelog に則り、今後の変更は Unreleased セクションに追加し、リリース時にバージョン毎に移動してください。