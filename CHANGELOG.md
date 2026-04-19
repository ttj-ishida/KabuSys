# CHANGELOG

全ての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」形式に準拠します。

フォーマット:
- 変更はバージョンごとに記載
- セクションは Added / Changed / Fixed / Deprecated / Removed / Security を使用

※ 日付はリリース日を示します（想定値はコードベースのスナップショットから推測して付与しています）。

## [Unreleased]
- 今後の改善予定（コード中の TODO / 未実装箇所に基づく）
  - portfolio.position_sizing: 銘柄ごとの単元（lot_size）をマスタから読み取る拡張
  - portfolio.risk_adjustment: 価格欠損時のフォールバック（前日終値や取得原価）の実装
  - research.factor_research: モジュールの未完了部分（計算ロジックの続き）を実装
  - より詳細なエラーハンドリングと単体テストの追加
  - ExecutionEngine / SystemMonitor のより詳細な監視メトリクス拡張

---

## [0.1.0] - 2026-04-19
初回リリース — 基本的な自動売買フレームワークのコア機能を提供します。

### Added
- 全体
  - パッケージ初期公開。バージョンは `__version__ = "0.1.0"`。
  - プロジェクトルートを自動検出して .env を自動ロードする仕組みを実装（.env / .env.local の順、OS環境変数を保護）。
  - .env ファイル用の対話式設定ウィザード CLI を追加（kabusys.config_setup）。
  - 設定検証 CLI を追加（kabusys.validate_config）。必須環境変数や設定ファイルの存在、KABUSYS_ENV の妥当性、ログレベル、DB パスなどを検証。`--strict` オプションで警告も失敗扱いにできる。
  - 明示的な Settings クラスを提供（kabusys.config）: 環境変数アクセスのラッパー（例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE 等）。
  - PAPER_FILL_MODE の妥当性チェック（"instant" / "partial" / "never" / "reject"）を実装。

- 実行・監視
  - Execution 起動スクリプト（kabusys.run_execution）を追加:
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB（デフォルト: data/paper_trading.db）を利用し、本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てと起動ロジックを実装。
    - stop_requested.flag による外部停止指示検知と graceful shutdown の仕組み（execution.pid の運用）。
  - Monitoring 起動スクリプト（kabusys.run_monitoring）を追加:
    - SystemMonitor の初期化とポーリングループを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒、0 以下や不正な値はデフォルトにフォールバックして警告を出力）。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨の明記。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定と重み計算（kabusys.portfolio.portfolio_builder）:
    - select_candidates: スコア降順、同点は signal_rank でタイブレーク。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分。全銘柄スコアが 0 の場合は等金額へフォールバック（警告）。
  - セクター集中とレジーム乗数（kabusys.portfolio.risk_adjustment）:
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合に新規候補を除外。unknown セクターは制限対象外。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（"bull":1.0, "neutral":0.7, "bear":0.3）。未知レジームは 1.0 でフォールバック（警告）。
  - 銘柄ごとの株数決定（kabusys.portfolio.position_sizing）:
    - allocation_method として "risk_based", "equal", "score" をサポート。
    - risk_based: risk_pct と stop_loss_pct に基づくポジションサイズ計算。
    - equal/score: ウェイトに基づく配分。単元（lot_size）丸め、per-stock 上限と aggregate cap（available_cash）によるスケーリングを実装。
    - cost_buffer による保守的コスト見積り（スリッページ/手数料考慮）とスケーリング時の端数再配分ロジック。

- ロギング・ユーティリティ
  - 統一ログ設定ユーティリティを追加（kabusys.utils.logging_setup）:
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - LOG_DIR 指定や自動ディレクトリ作成、失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - 既存ハンドラは再設定時に一度クリアして二重出力を防止。

- プロセス制御ユーティリティ
  - process_priority（kabusys.utils.process_priority）を追加:
    - Windows / POSIX (Linux, macOS, FreeBSD) に対応してプロセス優先度（high/normal/low）を設定。
    - CPU affinity 設定の補助関数 set_cpu_affinity を提供。
    - psutil によるアクセス権や未対応環境は警告を出してフォールバック。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加:
    - paper_trading DB から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）を集計してレポート出力。
    - デフォルト閾値を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200ms）で PASS/FAIL 判定を出力。
    - 日付フィルタ (--from / --to)、DB パス指定 (--db) をサポート。
    - P95 計算や欠損データへの耐性を実装。

- 監視 DB 初期化
  - monitoring_db 初期化処理（init_monitoring_db）を呼び出して監視用テーブルが存在することを保証（冪等）。

### Changed
- なし（初回リリースのため新規追加中心）

### Fixed
- なし（初回リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- .env ファイル生成スクリプトのヘッダに「.env を Git にコミットしないこと」を明記。
- 環境変数読み込み時に OS 環境変数を保護（.env.local の上書き時でも OS 環境変数は保護）。

---

## 既知の制限・注意点（コードから推測）
- portfolio.position_sizing:
  - price が欠損（0.0）の場合にエクスポージャーを過小見積る可能性がある旨の TODO コメントあり。将来的にフォールバック価格の導入が推奨される。
  - lot_size は現時点で全銘柄共通。銘柄別単元対応は今後の拡張。
- research.factor_research モジュールに未完の実装断片あり（calculation の続きが欠落しているように見える）。
- 一部ファイル IO / DB 作成に失敗した場合は警告・フォールバックを行う実装になっているが、運用上は適切なディレクトリ権限・ファイルパスの確認が必要。
- Execution / Monitoring の停止制御はファイルベースのフラグ（data/stop_requested.flag）を利用。外部からフラグ管理する運用手順が必要。

---

作成: この CHANGELOG は与えられたソースコードの内容をもとに推測して作成しています。実運用上の正式な変更履歴はコミット履歴やリリースノートに基づいて作成してください。