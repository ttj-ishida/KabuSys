# Changelog

すべての注目すべき変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-18

初期公開リリース。

### Added
- 基本アプリケーション情報
  - パッケージのバージョンを `__version__ = "0.1.0"` として追加。

- 環境設定 / 設定読み込み
  - .env ファイルの自動読み込み機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env のパース機能を実装（コメント、`export KEY=val`、シングル/ダブルクォートとエスケープの扱い、インラインコメントの扱い等に対応）。
  - Settings クラスを実装し、アプリで使用する設定（API トークン、DB パス、ログレベル、環境判定、監視閾値など）をプロパティ経由で取得可能に。
  - 環境変数必須チェック（`_require`）を実装し、未設定時に明確なエラーを発生させる。

- 設定ウィザード CLI
  - `kabusys.config_setup`：対話式ウィザードで `.env` を初期作成 / 更新するスクリプトを追加。既存値の再利用、シークレットのマスク表示、選択肢サポートなどを提供。

- 設定検証 CLI
  - `kabusys.validate_config`：起動前チェック用 CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在確認、`config/*.yaml` の存在と（PyYAML があれば）パース検証、`KABUSYS_ENV=live` 時の追加ガード等を実装。
  - `--strict` オプションで警告を失敗扱いにできる。

- 実行 / 監視起動スクリプト
  - `kabusys.run_execution`：ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - 環境に応じて paper_trading 用 DB を分離（KABUSYS_ENV=paper_trading の場合は `data/paper_trading.db` を使用）し、本番 DB と完全分離。
    - BrokerClientFactory を用いたブローカークライアント生成（docstring に paper_trading 時は MockBroker を使用する旨を記載）。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立て例を記載（RiskManager のデフォルト設定を含む）。
    - 停止フラグ（`data/stop_requested.flag`）や PID ファイルの管理、スレッドでの実行制御と安全終了処理を実装。
  - `kabusys.run_monitoring`：SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 `sqlite_path` を使用する仕様。
    - 停止フラグでループを終了、例外時はログを残して次ポーリングへ回復する堅牢化。
    - 起動時にプロセス優先度を "high" に設定。

- ロギングユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション・30日保持）を自動設定。
    - ログレベルおよびログディレクトリの解決順（引数 > 環境変数 > デフォルト）をサポート。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - 既存ハンドラのクリーンアップを行い二重設定を防止。

- プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority` を追加。
    - クロスプラットフォームでプロセス優先度を設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
    - CPU affinity を最初の N コアにピン留めする機能を提供。
    - 権限不足・未対応環境では警告を出して安全にスキップ。

- ポートフォリオ構築モジュール（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - BUY シグナルの候補選定（スコア降順、タイブレーク条件）select_candidates。
    - 等金額配分 calc_equal_weights。
    - スコア加重 calc_score_weights（全スコア 0 の場合は等金額へフォールバック）。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限 apply_sector_cap（既存保有のセクターエクスポージャー計算、"unknown" セクターの扱い、売却予定銘柄の除外）。
    - 市場レジームに基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知レジームは警告して 1.0 にフォールバック）。
  - `kabusys.portfolio.position_sizing`
    - position sizing（risk_based / equal / score の allocation_method）を実装。
    - 損切り率・許容リスク率に基づく risk_based 計算、単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash によるスケールダウン）、cost_buffer（手数料・スリッページの見積り）などを反映。
  - これらはメモリ内純粋関数として実装され、DB 参照無しでユニットテストしやすい設計。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - ペーパートレード用 SQLite（環境変数 `PAPER_TRADING_SQLITE_PATH` またはデフォルト `data/paper_trading.db`）から集計を行い、稼働率、注文成立率、送信率、リスク却下数、API レイテンシ（avg / max / P95）を算出してレポート出力。
    - 判定基準（デフォルト閾値）を導入:
      - 稼働率 >= 99.0%
      - 注文成立率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付レンジ指定（--from / --to）に対応。
    - データ欠損（テーブル未存在や該当期間データなし）に対する保護処理を実装。
    - P95 計算ユーティリティを実装。

- 研究用ファクター計算（骨組み）
  - `kabusys.research.factor_research` を追加。
    - Momentum / Value / Volatility / Liquidity といったファクター群の設計ドキュメントに基づく骨組みを実装。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照する想定の関数を提供。
    - （注）calc_momentum の実装がファイル末尾で未完の状態で含まれています（このリリースでは枠組みと初期定数を提供）。

### Changed
- （初版のため履歴変更は無し）

### Fixed
- （初版のため修正項目は無し）

### Security
- 機密情報の取り扱いについて
  - `.env` の生成スクリプトで注意書きを追加: `.env は絶対に Git にコミットしないこと` を明記。
  - config バリデータはプレースホルダ値（例: `_here`, `your_value`）の検出で警告を出す。

### Notes / Usage hints
- 実行スクリプト（run_execution/run_monitoring）はそれぞれ `python -m kabusys.run_execution` / `python -m kabusys.run_monitoring` で起動可能。
- ログはデフォルトで `logs/<app_name>.log` に日次ローテーションで出力され、コンソールは stdout に出力されます。
- paper_trading モードでは DB・ブローカーが本番と分離されるため、実際の発注は行われません（MockBroker の利用を想定）。
- KABUSYS_ENV の有効値は `development` / `paper_trading` / `live`。無効な値は起動時にエラー/警告の対象となります。
- monitor のポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で変更可能。1 未満や不正な値は無視され 60 秒にフォールバック。

---

既知の制限 / TODO
- research.factor_research.calc_momentum の実装が途中で終了しているため、ファクター計算は現状で未完成の一部機能があります。今後のリリースで完了予定。
- position_sizing の lot_size は現状グローバル共通単元（デフォルト 100）に依存しているため、将来的に銘柄毎の単元対応へ拡張予定（コメントで TODO を記載）。
- apply_sector_cap は price の欠損時にエクスポージャーを過少見積もる可能性があり、フォールバック価格（前日終値等）導入を検討中。

（以降のリリースでは上記の未完・拡張ポイントを順次改善していきます）