# Changelog

すべての注目すべき変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

## [0.1.0] - 2026-04-18

初回リリース。ローカル開発からペーパートレード・本番運用までを想定した日本株自動売買フレームワークの基礎を実装しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを設定: `kabusys.__version__ = "0.1.0"`。

- 設定管理
  - Settings クラスを実装（`kabusys.config`）。
    - 環境変数から各種設定値を取得するプロパティ群を提供（J-Quants, kabu API, DB パス, ログレベル, モニタ閾値等）。
    - KABUSYS_ENV（development / paper_trading / live）の検証ロジックを内蔵。
    - paper_trading 用の専用 SQLite パスや PAPER_FILL_MODE の検証を実装。
  - .env 自動ロード機能を実装:
    - プロジェクトルート（.git または pyproject.toml）探索に基づき `.env` / `.env.local` を自動読み込み。
    - 読み込み順序: OS 環境変数 > .env.local > .env。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` によって無効化可能。
  - .env 解析は引用符・エスケープ・コメント・`export KEY=val` 形式に対応。

- 設定支援 CLI / 検証ツール
  - 対話式設定ウィザード `kabusys.config_setup` を追加。
    - .env の初期作成 / 更新を支援するインタラクティブなプロンプトを提供。
  - 設定検証 CLI `kabusys.validate_config` を追加。
    - 必須環境変数、KABUSYS_ENV の妥当性、DB パス、config/*.yaml の存在・パース（PyYAML があれば内容検証）等をチェック。
    - `--strict` オプションで警告も失敗扱いにできる。

- 実行エントリスクリプト
  - `run_execution.py`（ExecutionEngine 起動スクリプト）を追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は専用（モック）ブローカクライアントを使用し、データベースを本番と分離（`data/paper_trading.db` デフォルト）。
    - 監視用テーブルの初期化を行い、ExecutionEngine をデーモンスレッドで起動/監視する仕組みを提供。
    - 停止フラグ（`data/stop_requested.flag`）と PID ファイル（`data/execution.pid`）の取り扱いを実装。
    - RiskManager / OrderManager / Reconciler 等の組み立て例を示す（リスク設定やレート制限などの初期値を含む）。
  - `run_monitoring.py`（SystemMonitor ポーリングループ起動スクリプト）を追加。
    - 起動時にプロセス優先度を "high" に設定。
    - 環境にかかわらず本番の sqlite_path を使用して監視テーブルを初期化。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 停止フラグの検出および例外時のログ出力とリトライ継続を実装。

- 監視 / DB 初期化
  - `init_monitoring_db` 呼び出し箇所を追加し、監視テーブルが存在することを保証（冪等）。

- ロギングユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を実装。
    - stdout 出力用 StreamHandler と 日次ローテートの TimedRotatingFileHandler（デフォルト logs/、30日保持）をルートロガーに設定。
    - ログレベル・ログディレクトリは引数・環境変数で解決。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

- プロセス優先度 / CPU 固定ユーティリティ
  - `kabusys.utils.process_priority` を実装。
    - Windows / POSIX の差異を吸収してプロセス優先度（high/normal/low）を設定（psutil 利用）。
    - CPU affinity を最初の N コアに固定するユーティリティを提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にフォールバック。

- ポートフォリオ構築ライブラリ（純粋関数）
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定 select_candidates（スコア降順、タイブレーク処理）。
    - 等配分 calc_equal_weights、スコア加重 calc_score_weights（全スコア 0 の場合は等分配へフォールバック）。
  - `kabusys.portfolio.position_sizing`:
    - calc_position_sizes 実装（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer（手数料/スリッページ見積り）を考慮した丸め・スケーリングロジック。
    - aggregate cap 超過時のスケールダウンと残余配分アルゴリズムを実装。
  - `kabusys.portfolio.risk_adjustment`:
    - apply_sector_cap（セクター集中上限チェック、当日売却予定銘柄の除外対応）。
    - calc_regime_multiplier（レジームに応じた投下資金乗数: bull/neutral/bear、および未知レジームのフォールバック）。

- 研究・ファクター計算基盤（DuckDB）
  - `kabusys.research.factor_research` を追加（Momentum 等のファクター計算を意図）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照してモメンタム、MA200 乖離、ATR、流動性指標等を計算する設計。
    - （注）ファイル末尾に実装途中の箇所あり（calc_momentum の続きが未保存/未完了の可能性あり）。将来的に完全実装予定。

- ツール
  - Paper Trading の検証レポート生成スクリプト `kabusys.tools.paper_verification_report` を追加。
    - ペーパートレード用 SQLite（環境変数 PAPER_TRADING_SQLITE_PATH またはデフォルト data/paper_trading.db）から各種指標を算出。
    - 指標: 稼働率、注文成功率（fill rate）、送信率（send rate）、リスク却下数、API レイテンシ（avg/max/P95）等。
    - CLI オプション: --from, --to（日付フィルタ）, --db（DB パス）。合格閾値（uptime 99%、fill 90%、send 95%、P95 latency 200ms）を設定し PASS/FAIL を出力。

### Changed
- 初期設計として以下の挙動を採用（以後のリリースで調整予定）:
  - 監視コンポーネントは常に「本番」監視 DB を参照（monitoring は環境に依存せず sqlite_path を使用）。
  - Execution は環境に応じて本番 DB と paper_trading DB を切り替え（`Settings.is_paper` 判定）。

### Fixed
- 起動パターンに関する堅牢性向上:
  - ログハンドラの二重登録を防ぐため、既存ハンドラを flush/close の上でクリアしてから再設定するように修正。
  - プロセス優先度設定や CPU affinity 設定は権限エラー時に安全にスキップして警告を出力するようにして、起動失敗に至らないように修正。

### Notes / Migration
- .env の自動ロードはデフォルトで有効です。テストや特殊環境で自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- PAPER_TRADING 環境での発注はモックブローカを通じて専用 DB（`data/paper_trading.db`）にのみ記録され、本番 DB と完全に分離されます。
- `MONITOR_POLL_INTERVAL` は整数秒を期待します。0 以下や整数以外を指定した場合は警告を出しデフォルト 60 秒にフォールバックします。
- factor_research モジュールはまだ拡張予定箇所があります。利用時は現状の実装範囲を確認してください。

### Known issues / TODO
- `kabusys.research.factor_research` の一部（calc_momentum の続き）が未完/ファイル末尾で切れているため、完全なファクター計算実装は次リリースで対応予定。
- position_sizing の将来的拡張として、銘柄別の lot_size を stocks マスタから取得する設計への改修を検討（現状はグローバル lot_size を想定）。
- apply_sector_cap の価格欠損時の挙動は現在 price_map の 0.0 を許容しているため、実運用では前日終値等のフォールバック導入を推奨。

---

今後のリリースでは、研究モジュールの完全実装、より詳細な監視アラート送信（LINE 通知等）、ExecutionEngine とブローカ実装の拡充、ユニットテストおよび CI の整備を予定しています。