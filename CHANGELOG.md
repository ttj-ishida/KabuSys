# Changelog

すべての重要な変更点をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

注意: 本 CHANGELOG はソースコードから推測して作成しています。実装意図や細部はソースを参照してください。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-21

初回リリース（初期実装）。主な追加・実装点は以下の通りです。

### Added
- 基本アプリケーション情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（`src/kabusys/__init__.py`）。

- 環境設定・管理
  - 環境変数読み込み・管理モジュール `kabusys.config` を追加。
    - プロジェクトルート（`.git` または `pyproject.toml`）を基準に自動で `.env` / `.env.local` をロードする仕組みを実装。
    - 必須/任意の環境変数取得メソッドを提供（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`）。
    - 各種パスやフラグ、閾値、環境名（`development` / `paper_trading` / `live`）の取得ロジックを実装。
    - `PAPER_FILL_MODE` のバリデーション（"instant" / "partial" / "never" / "reject"）を実装。

  - 対話式 .env 作成ウィザード CLI `kabusys.config_setup` を追加。
    - `.env` の初期作成・更新を対話的に行うためのウィザード、既存値の読み込み・マスク表示、保存用ヘッダを実装。

  - 設定検証 CLI `kabusys.validate_config` を追加。
    - 必須環境変数の有無、`KABUSYS_ENV` / `LOG_LEVEL` の妥当性、DB パスの親ディレクトリ存在チェック、`config/*.yaml` の存在/パースチェック（PyYAML がない場合は警告）などを行う。
    - `--strict` オプションにより警告も失敗として扱うモードを提供。

- 起動スクリプト
  - 監視用スクリプト `kabusys.run_monitoring` を追加。
    - `SystemMonitor` を用いたポーリングループの起動。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 停止フラグ（`data/stop_requested.flag`）でループ終了。
    - 監視用 DB は環境に依らず本番向け `sqlite_path` を使用する旨の仕様。

  - 実行エンジン起動スクリプト `kabusys.run_execution` を追加。
    - `KABUSYS_ENV=paper_trading` 時は Paper Trading 用の専用 SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用し、本番 DB と分離。
    - ブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 等の組み立て、`ExecutionEngine` の `run_session` をバックグラウンドスレッドで起動。
    - 停止フラグ検知時の安全停止処理を実装（フラグ検出でエンジン停止／起動抑止）。
    - 実行時 PID 書き出しパスの取り扱い。

- ポートフォリオ構築
  - `kabusys.portfolio` パッケージを実装（純粋関数群）。
    - `portfolio_builder`:
      - シグナルのスコア降順選定（`select_candidates`）。
      - 等金額配分（`calc_equal_weights`）とスコア加重配分（`calc_score_weights`）。全スコアが 0 の場合は等金額にフォールバックして警告。
    - `risk_adjustment`:
      - セクター集中制限を適用する `apply_sector_cap`（当日売却予定銘柄はエクスポージャー計算から除外、`unknown` セクターは制限対象外）。
      - 市場レジームに基づく乗数 `calc_regime_multiplier`（`bull`/`neutral`/`bear`、未知レジームは 1.0 にフォールバックして警告）。
    - `position_sizing`:
      - 発注株数計算 `calc_position_sizes` を実装（allocation_method: `risk_based` / `equal` / `score`）。
      - 単元株丸め（lot_size）、per-position 上限、aggregate cap（利用可能現金に対するスケーリング）を考慮。
      - コストバッファ（手数料・スリッページ見積り）を適用して保守的に投資額を見積る。スケールダウン時の残差配分ロジックを実装。

- ユーティリティ
  - ログ設定ユーティリティ `kabusys.utils.logging_setup` を追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション／30 日分保持）を設定。
    - 既存ハンドラを再設定して二重登録を防止。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度 / CPU Affinity ユーティリティ `kabusys.utils.process_priority` を追加。
    - Windows / POSIX（Linux/macOS/FreeBSD）差分を吸収して `set_process_priority`（high/normal/low）を提供。
    - `set_cpu_affinity` により最初の N コアに固定する機能を提供（権限や未実装 API へのフォールバックに安全対処）。

- 監視 DB 初期化
  - `init_monitoring_db` の呼び出しにより、監視用テーブルが存在することを保証（冪等）。

- Paper Trading 向け検証ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - Paper Trading 用 SQLite（デフォルト `data/paper_trading.db`）からデータを集計してレポート出力。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなど。
    - P95 計算、しきい値（稼働率 >= 99%, fill >= 90%, send >= 95%, P95 <= 200 ms）に基づく PASS/FAIL 判定を実装。
    - 日付フィルタ（--from/--to）や `--db` オプションに対応。

- リサーチ（ファクター）モジュール雛形
  - `kabusys.research.factor_research` にモメンタム等のファクター計算（DuckDB を利用する設計）の雛形を追加（モジュール内に定数や関数スケルトンを含む）。

### Changed
- （初期リリースのため履歴なし）

### Fixed / Hardening
- .env パーサーの強化（`kabusys.config`）
  - クォート文字列内のバックスラッシュエスケープ処理、クォートなし時のインラインコメント判定などを実装し、実際の .env ファイルでの多様な記法に対応。
  - `.env` 読み込み失敗時に警告を出して処理を継続する実装。

- 起動スクリプトの耐障害性向上
  - `MONITOR_POLL_INTERVAL` の不正値に対して警告しデフォルトにフォールバックするバリデーションを追加（`run_monitoring`）。
  - `run_monitoring` / `run_execution` ともに DB コネクションを finally ブロックで確実にクローズするように実装。
  - 停止フラグ検出および KeyboardInterrupt を捕捉して安全に終了するロジックを追加。

- ロギング設定のフォールバック
  - ログディレクトリ作成やファイルハンドラ作成に失敗した場合でも、コンソール出力のみで動作を継続するように実装（`logging_setup`）。

- プロセス優先度 / CPU affinity のエラー処理
  - 権限不足や未実装 API に対して警告を出し、安全に処理をスキップするように強化（`process_priority`）。

- ポートフォリオ計算の安全弁
  - `apply_sector_cap` はセクターが不明（`unknown`）な銘柄を除外しないことで誤って候補を排除しない設計に変更。
  - `calc_score_weights` は全スコアが 0 の場合に等金額配分にフォールバックしてログ警告を出す。
  - `calc_regime_multiplier` は未知レジームに対して 1.0 にフォールバックし警告を出す。
  - `calc_position_sizes` の aggregate cap 適用時に、lot_size 単位での残差配分アルゴリズムを導入してより安定した丸め処理を実現。

### Security
- 現時点でクリティカルなセキュリティ修正は含まれていません。環境変数やシークレット（例: API トークン）は `.env` に保存する際の運用上の注意を README 等で周知してください（`.env` を絶対にコミットしない旨の注記を `config_setup` に含む）。

---

今後の改善案（コードから推測）
- `research.factor_research` の各ファクター計算関数の完成（DuckDB を使った実装の拡充）。
- 単体テストと型注釈の拡充（特に DB 周りと position sizing の境界ケース）。
- ログやメトリクスの構造化（JSON ログ等）や外部監視連携の強化。
- 銘柄ごとの単元株（lot_size）をマスタデータから取得する拡張（現状はグローバルな `lot_size` を使用）。

※ 本 CHANGELOG はコードベースの現状を元に生成しています。実際のコミット履歴（git log）と差異がある可能性があります。