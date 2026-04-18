CHANGELOG
=========

すべての注目すべき変更点を記録します。フォーマットは "Keep a Changelog" 準拠です。

0.1.0 - 2026-04-18
-----------------

Added
- 基本アプリケーション
  - 初期リリース: パッケージ名 kabusys、バージョン 0.1.0 を追加。
  - モジュール構成: data/、strategy/、execution/、monitoring/ 等をエクスポートするパッケージ初期化。

- 環境・設定管理 (`kabusys.config`, `kabusys.config_setup`, `kabusys.validate_config`)
  - .env 自動ロード機能:
    - プロジェクトルート（.git または pyproject.toml を基準）を探索して .env を自動読み込み。
    - 読み込み優先順: OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書き不可）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - 高度な .env パーサ実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理などに対応。
  - Settings クラス:
    - アプリ設定をプロパティとして提供（J-Quants トークン、kabu API パスワード、DB パス、Paper Trading 用設定、監視閾値など）。
    - 設定値検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の有効値チェック）。
    - 本番/ペーパートレード状態の判定プロパティ（is_live / is_paper / is_dev）。
  - 対話式設定ウィザード (`kabusys.config_setup`):
    - .env の初期作成 / 更新を支援。秘密項目をマスクして表示し、ファイルに書き出す。
    - デフォルト値や選択肢をサポート。
  - 設定検証 CLI (`kabusys.validate_config`):
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
    - DUCKDB/SQLITE のパス親ディレクトリ存在チェック（警告）。
    - config/*.yaml の存在確認（PyYAML がなければ検証をスキップし警告）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 設定や Kill Switch 設定の警告）。
    - --strict オプションで警告も失敗扱いにできる。

- 実行系起動スクリプト
  - 実行エンジン起動 (`run_execution.py`):
    - プロセス優先度を最初に "high" に設定（`kabusys.utils.process_priority` を利用）。
    - DB: KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と分離。
    - DuckDB は分析用に接続。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading では MockBrokerClient を想定）。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てとバックグラウンドスレッドでの起動。
    - 停止制御: プロジェクトの data/stop_requested.flag を確認して安全に停止。PID ファイル出力サポート。
    - RiskManager にデフォルトパラメータを設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。初期ポートフォリオ値を broker.get_available_cash() から取得。

  - 監視ループ起動 (`run_monitoring.py`):
    - プロセス優先度を "high" に設定。
    - 監視は常に本番向け sqlite_path を使用（環境に関わらず監視 DB を本番パスで接続）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正値はログ警告とともにデフォルトへフォールバック。
    - 停止フラグ（data/stop_requested.flag）でループ終了。例外発生時はログを残して次サイクルへ継続。

- ロギング・プロセスユーティリティ (`kabusys.utils`)
  - logging_setup:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテート、30 日保管）を設定。
    - ログディレクトリは引数 > LOG_DIR 環境変数 > デフォルト logs/ の優先順で決定。ディレクトリ作成失敗時はファイルハンドラをスキップして stdout のみで継続。
    - 既存ハンドラの二重登録防止（再設定時に既存ハンドラを flush/close して削除）。
  - process_priority:
    - Windows / POSIX(Linux, Darwin, FreeBSD) を吸収してプロセス優先度を設定。アクセス拒否や未対応OSでは警告ログを出し安全にフォールバック。
    - CPU affinity を最初の N コアに固定するユーティリティを提供（設定失敗時は警告でスキップ）。

- ポートフォリオ構築ライブラリ (`kabusys.portfolio`)
  - portfolio_builder:
    - select_candidates: score 降順（同点時 signal_rank 昇順）で候補上位 N を返す。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア重み配分。全銘柄スコアが 0.0 の場合は等金額にフォールバックし警告を出す。
  - risk_adjustment:
    - apply_sector_cap: 既存ポジションを基にセクターごとのエクスポージャーを算出し、max_sector_pct を超えるセクターの新規候補を除外。sell_codes（当日売却予定）をエクスポージャー計算から除外可能。unknown セクターは制限対象外。
    - calc_regime_multiplier: マーケットレジームに応じた資金投下乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 へフォールバックして警告ログを出す。
  - position_sizing:
    - calc_position_sizes: allocation_method に応じて銘柄ごとの発注株数を決定（risk_based / equal / score）。
    - risk_based: 損切り幅と許容リスク率からベース株数を計算。単元（lot_size）丸め、1 銘柄上限と aggregate cap を考慮。
    - aggregate cap の場合はスケーリング処理を行い、残余キャッシュで fractional 残差の大きい順に lot 単位で追加配分するロジックを実装。
    - lot_size, cost_buffer（手数料・スリッページ見積り）を考慮。

- ツール
  - Paper Trading 検証レポート (`kabusys.tools.paper_verification_report`):
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）から指標を集計しレポートを出力。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、API レイテンシ（avg/max/P95）など。
    - P95 計算ユーティリティ、期間フィルタ（--from / --to）、CLI オプション --db で DB パス指定可能。
    - デフォルトの判定閾値を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）と PASS/FAIL 判定を出力。

- リサーチ
  - factor_research モジュールの骨組み (`kabusys.research.factor_research`):
    - DuckDB 接続を受けて momentum / value / volatility / liquidity 等のファクターを算出する設計方針と初期定数群を追加。
    - calc_momentum の実装を開始（ファイル末尾が一部切れているがモメンタム指標（1M/3M/6M, MA200 乖離等）を計算する設計）。

Changed
- N/A（初期リリースのため変更履歴はありません）

Fixed
- N/A（初期リリースのため修正履歴はありません）

Removed
- N/A

Security
- .env を絶対に Git にコミットしないよう README に注意喚起する記述を .env 書き込みヘッダに追加（config_setup で生成する .env に注意書き）。

Notes / Migration
- 起動スクリプトは内部で SQLite/DuckDB を直接開くため、既存の DB ファイルのパスは環境変数（SQLITE_PATH / DUCKDB_PATH / PAPER_TRADING_SQLITE_PATH）で適切に指定してください。
- 本番運用時は KABUSYS_ENV を "live" に設定すると追加の警告が出ます。Kill Switch（KILL_FLAG_*）の設定は慎重に行ってください。
- process_priority の設定や CPU affinity は OS / 実行権限に依存します。権限不足時はログ警告でフォールバックします。

開発者向け補足
- .env の高度なパース実装により、引用符内エスケープやインラインコメントの取り扱いが改善されていますが、極端に複雑な .env 記述は想定していません。
- paper_trading 環境では実際の注文は行われない前提で MockBrokerClient を利用する設計になっています（BrokerClientFactory に実実装を差し替えることで動作）。
- factor_research モジュールは DuckDB のテーブル構造（prices_daily / raw_financials 等）に依存します。分析環境構築時はスキーマを合わせてください。

------------

今後の予定（例）
- factor_research のファクター実装完了（全ファクター・正規化処理）。
- モニタリングの拡張（アラート送信、LINE 通知の統合）。
- execution 側のユニットテスト強化とシミュレーション検証用ツール群の整備。