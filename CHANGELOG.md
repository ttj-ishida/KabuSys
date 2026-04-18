# Changelog

すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。  
このファイルはコードベースの現状から推測して作成した初期リリース向けの変更履歴です。

全般的な注意
- 本 CHANGELOG はソースコードの内容から機能や挙動を推測して記載しています。実際のコミット履歴ではありません。
- バージョンはパッケージの __version__（0.1.0）を基にしています。

## [Unreleased]

## [0.1.0] - 初期リリース（推定）
リリース日: 未設定

### Added
- 基本アプリケーション構成
  - パッケージ名: KabuSys、バージョン 0.1.0（src/kabusys/__init__.py）。
  - エクスポート: data, strategy, execution, monitoring モジュールを公開。

- 起動スクリプト / デーモン類
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite を使用（data/paper_trading.db をデフォルト）し、MockBrokerClient を利用して本番 DB と分離。
    - プロセス優先度を設定（high 推奨）し、PID ファイルや停止フラグで制御。
    - ExecutionEngine がブローカークライアント、OrderRepository、OrderManager、RiskManager、Reconciler 等の依存コンポーネントを組み立てて実行。
    - RiskManager のデフォルト設定を定義（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）し、initial_portfolio_value を broker.get_available_cash() から初期化。

  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）を検知して安全に終了。
    - 監視は環境にかかわらず本番の sqlite_path を使用して初期化。

- 設定 / 環境読み込み
  - config.Settings クラスを追加（環境変数を経由して設定取得）。
    - J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / システム関連設定等をプロパティとして提供。
    - KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等の値検証を実施（不正値は例外を送出）。
  - 自動 .env 読み込み機能を追加（プロジェクトルートに基づき .env と .env.local を読み込み、OS 環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化。

  - .env パーサーは以下に対応:
    - 空行・コメント行、`export KEY=val` 形式、シングル/ダブルクォート値、バックスラッシュエスケープ、インラインコメントの扱い等。

- 設定補助ツール / 検証
  - config_setup: 対話式ウィザードで .env を作成 / 更新する CLI を追加。
    - 秘匿値マスク表示、選択肢・デフォルト、入力キャンセル時の動作などをサポート。
    - 保存時はテンプレートヘッダ付きで .env を生成。

  - validate_config: 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ有無チェック、config/*.yaml の存在確認および PyYAML があればパース検証を実行。
    - KABUSYS_ENV=live に対する追加ガード（LINE 設定や Kill Switch 設定の注意喚起）。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング & プロセス制御ユーティリティ
  - utils.logging_setup: 統一的なロギング設定ユーティリティを提供。
    - stdout へ StreamHandler、日次ローテートファイルへ TimedRotatingFileHandler（logs/<app_name>.log、30日保持）を追加。
    - LOG_DIR 環境変数や引数でログ保存先・ログレベルを制御。ログディレクトリ作成に失敗した場合はファイル出力を自動的に無効化して継続。

  - utils.process_priority: クロスプラットフォームでプロセス優先度と CPU affinity を設定するユーティリティを提供。
    - Windows 用 PriorityClass と POSIX 系の nice 値を抽象化してセット可能。
    - psutil を利用、権限不足や実装未サポート時は安全にスキップ。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順かつ tie-breaker に signal_rank を使って候補選定。
    - calc_equal_weights / calc_score_weights: 等重・スコア重みを算出（スコア合計が 0 の場合は等重にフォールバックして警告）。

  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限を実装（既存保有のセクター比率に基づき新規候補を除外）。unknown セクターは適用除外。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた投下資金乗数を返す（未知は 1.0 で警告）。

  - portfolio.position_sizing:
    - calc_position_sizes: 各銘柄の発注株数決定ロジック（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）でスケーリング。
    - cost_buffer（手数料・スリッページ見積）を考慮した保守的な見積りおよび残差処理（小数点端数を lot 単位で再配分）。
    - ログ出力による価格欠損時のスキップやその他安全弁を実装。

- Paper Trading 検証ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite データベースから検証レポートを生成するスクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、レイテンシ（avg/max/P95）、リスク却下数 等。
    - PASS/FAIL 判定閾値を定義（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200 ms）。
    - 日付範囲フィルタ（--from / --to）および DB パス指定（--db）をサポート。
    - 欠損テーブルやカラムがある場合も sqlite3.OperationalError を捕捉して寛容に動作。

- データ分析（研究用）
  - research.factor_research: ファクター計算モジュール（Momentum / Value / Volatility / Liquidity）を追加（DuckDB 接続を利用する設計）。
    - calc_momentum の実装を開始（ターゲット日ベースの各種リターンや MA200 乖離を計算する意図）。
    - 設計方針として DuckDB の prices_daily / raw_financials テーブルのみを参照することで本番業務との分離を想定。
    - （注）このファイルは途中で切れているため実装は継続が必要。

### Changed
- なし（初回リリース相当の追加まとめ）

### Fixed
- なし（初回リリース相当の追加まとめ）

### Removed
- なし

### Security
- 環境変数取り扱いと .env の利用に関して注意書きと保護機構を実装（OS 環境変数を保護する protected set、.env を絶対にリポジトリにコミットしない旨の注記など）。

## 既知の制約 / TODO（コードから推測）
- research.factor_research の一部実装が途中で切れている（calc_momentum の続きが未完）。
- position_sizing の価格欠損（price が 0.0）に関して TODO コメントがあり、フォールバック価格の導入が検討されている。
- 単元株サイズの扱いは現状全銘柄共通の lot_size を仮定しており、将来的な拡張（銘柄別 lot_map）を想定。
- ログディレクトリ作成失敗やプロセス優先度設定失敗時は安全にフォールバックするが、運用上の観点からは事前確認が必要。

---

作成: 自動生成（ソースコード解析に基づく推測）