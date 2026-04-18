# Changelog

すべての変更は Keep a Changelog 規約に準拠して記載しています。  
慣例: 追加 (Added), 変更 (Changed), 修正 (Fixed), 削除 (Removed), 非推奨 (Deprecated), セキュリティ (Security)。

## [Unreleased]

（現在の差分はありません）

## [0.1.0] - 2026-04-18

リリース v0.1.0 — KabuSys の初期公開版。日本株自動売買システムのコア機能群を実装しています。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 環境/設定管理
  - .env の自動ロード機構（プロジェクトルート検出: `.git` または `pyproject.toml` を探索）。
  - .env ファイルパーサ（引用符、エスケープ、`export ` プレフィックス、インラインコメント処理に対応）。
  - 環境変数読み込みの優先順位: OS 環境変数 > .env.local > .env。
  - `Settings` クラスによる環境変数ラッパー（各種 API トークン、DB パス、監視閾値、実行環境フラグ等をプロパティとして提供）。
  - 自動ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD`。

- 設定ウィザード & 検証 CLI
  - 対話式 `.env` 作成/更新ウィザード (`kabusys.config_setup.run_wizard`)。
  - `.env` の書き出しテンプレート（機密項目はマスク表示）。
  - 起動前検証ツール `kabusys.validate_config`（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス確認、config/*.yaml の存在とパース検査を実行）。
  - `--strict` オプションで警告を失敗扱いにできる。

- 実行スクリプト（起動エントリポイント）
  - 実行エンジン起動スクリプト `run_execution.py`
    - `KABUSYS_ENV=paper_trading` 時に本番 DB と分離して `data/paper_trading.db` を使用。
    - `BrokerClientFactory` によるブローカークライアント生成。
    - `ExecutionEngine` の組立て（OrderRepository / OrderManager / RiskManager / Reconciler を統合）。
    - デーモン化されたスレッドでセッション実行、停止フラグ (`data/stop_requested.flag`) による安全停止。
    - 実行時 PID ファイル保管 (`data/execution.pid`)。
  - 監視ループ起動スクリプト `run_monitoring.py`
    - `SystemMonitor` を用いた定期チェック。ポーリング間隔は `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番 `sqlite_path` を使用（監視は本番 DB を参照する設計）。
    - 停止フラグ検知でループを終了。

- 監視 DB 初期化
  - `init_monitoring_db` を介した監視用テーブルの冪等初期化（監視・実行両方から呼び出し可能）。

- ロギング / プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティ `kabusys.utils.logging_setup.setup_logging`
    - stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler（デフォルト logs/、30日保持）を構成。
    - 既存ハンドラのクリーンアップ（重複登録防止）。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
  - プロセス優先度 / CPU Affinity 設定ユーティリティ `kabusys.utils.process_priority`
    - Windows / POSIX（Linux, Darwin, FreeBSD）間の差分吸収。
    - `set_process_priority("high"|"normal"|"low")`、`set_cpu_affinity(n)` を提供。
    - 権限不足や未対応 OS の場合は警告を出し安全にフォールバック。

- ポートフォリオ構築ライブラリ（純粋関数）
  - 候補選定: `select_candidates`（スコア降順、同点は signal_rank 昇順）。
  - 重み計算: `calc_equal_weights`, `calc_score_weights`（全スコア 0 の場合は等分配にフォールバック）。
  - セクター集中制限: `apply_sector_cap`（既存保有比率に基づきセクター上限を超える場合に候補を除外。unknown セクターは制限対象外）。
  - レジーム乗数: `calc_regime_multiplier`（"bull"/"neutral"/"bear" を正規化、未知値は警告して 1.0 にフォールバック）。
  - ポジションサイジング: `calc_position_sizes`
    - `risk_based` / `equal` / `score` の配分方式に対応。
    - 単元株単位で丸め、per-position と aggregate の上限チェック、必要時スケーリング＆残余配分ロジックを実装。
    - コストバッファ（スリッページ・手数料想定）を考慮した保守的推定。

- 研究用ファクター計算基盤
  - DuckDB 接続を受け取り価格・財務データからファクター（Momentum/Value/Volatility/Liquidity 等）を算出するための枠組み（`kabusys.research.factor_research`）。（注: ファイルは一部省略/続きあり）

- ツール
  - Paper Trading 検証レポート生成スクリプト `kabusys.tools.paper_verification_report`
    - ペーパートレード用 SQLite（デフォルト `data/paper_trading.db`）から指標を集計しレポート出力。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数 等。
    - 判定閾値（初期値）を定義: 稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms。
    - 日付フィルタ（--from / --to）対応、P95 計算ロジック実装。

### Changed
- ログ出力先のデフォルトを stdout に明示（StreamHandler を stdout に設定）。cron/Task Scheduler の出力リダイレクト運用を想定。
- `.env` 読み込みの挙動を明確化
  - .env を読み込む際、既存 OS 環境変数は保護（上書きされない）。`.env.local` は上書き可能。
  - 自動ロードのスイッチを提供（テストでの制御を容易に）。

- 実行・監視起動時にプロセス優先度を最初に設定（`set_process_priority("high")`）して安定稼働を優先。

### Fixed
- .env パーサの堅牢化
  - クォートされた値内でのバックスラッシュエスケープ処理をサポート。
  - `export KEY=val` 形式や行頭コメント・空行を正しく無視するよう改善。
  - クォート無し値のインラインコメント判定ロジックを実装（`#` の直前に空白がある場合のみコメント扱い）。
- ログハンドラ二重登録の防止（既存ハンドラを flush/close してから削除）。

### Known issues / Notes
- portfolio.risk_adjustment.apply_sector_cap:
  - 価格が欠損（0.0）の場合にエクスポージャーが過少見積もられる可能性があり、その旨 TODO コメントで記載。将来的に前日終値等でのフォールバックを検討。
- position_sizing:
  - 将来的に銘柄別 unit（lot_size）をサポートするための拡張を予定（現状は全銘柄共通単元を想定）。
- research.factor_research はファイルの後半が未表示／続きあり。実装は prices_daily / raw_financials に依存する設計。
- Paper Trading と本番 DB の分離は設計上保証されているが、運用時の環境変数設定ミスに注意（`validate_config` で事前検証推奨）。

### Security
- .env ファイルは絶対にリポジトリにコミットしない旨を `config_setup` の書き出しテンプレートに明記。
- 一部機密項目（API トークン・パスワード）はウィザードでマスク表示。

---

（注）この CHANGELOG は提示されたソースコード内容からの推測に基づき記載しています。実際のコミット履歴／リリースノートと異なる場合があります。