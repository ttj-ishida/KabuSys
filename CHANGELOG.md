# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  
このプロジェクトの初期リリースに相当するリリースノートを、コードベースの内容から推測して作成しています。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-19

最初の公開リリース相当。システム全体の起動スクリプト、設定管理、ユーティリティ、ポートフォリオ構築ロジック、ペーパートレード用検証ツールなど、コア機能を実装しました。

### Added
- 基本モジュールとパッケージ構成を追加
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`
  - エクスポート: data, strategy, execution, monitoring モジュール群を公開

- 起動スクリプト
  - run_execution: ExecutionEngine 起動用スクリプトを追加
    - 起動時にプロセス優先度を "high" に設定
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番DBと分離（BrokerClientFactory により MockBrokerClient を選択）
    - DB 初期化（監視テーブルの冪等初期化）、duckdb 接続
    - Engine のデーモンスレッド起動と停止フラグ（data/stop_requested.flag）監視、PID ファイル出力
    - デフォルトのリスク設定（RiskConfig）を組み込み

  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
    - 監視は環境に関わらず本番 sqlite_path を使用する設計
    - 停止フラグ検出でループを終了。例外発生時もログを残して次回ポーリングへ継続

- 設定管理・ウィザード・検証
  - `kabusys.config.Settings` を実装
    - .env 自動読み込み（プロジェクトルートを .git / pyproject.toml で検出）
    - 各種環境変数のプロパティ化（J-Quants、kabuAPI、データベースパス、監視閾値、ログレベルなど）
    - env 値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）
    - paper_trading 判定ヘルパー（is_paper, is_live, is_dev）
  - `kabusys.config_setup`：対話式 .env 作成/更新ウィザードを追加
    - 初期テンプレート生成、既存 .env の読み込み、秘密値はマスク表示、.env の書き込みをサポート
  - `kabusys.validate_config`：設定検証 CLI を追加
    - 必須/任意環境変数、DB パス、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードなど
    - --strict モードで警告を失敗扱いにできる

- ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`
    - stdout (StreamHandler) と 日次ローテート (TimedRotatingFileHandler) をルートロガーに設定
    - LOG_DIR 作成失敗時はファイル出力をスキップしてコンソールのみで継続
    - 既存ハンドラの適切なクローズ／入れ替え処理を実装
  - `kabusys.utils.process_priority`
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供
    - 設定失敗時は警告ログを出して安全にフォールバック
  - 環境ファイルパーサ
    - export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応する .env パーサを実装

- ポートフォリオ構築（純粋関数群: DB 参照なし）
  - portfolio_builder
    - select_candidates: スコア降順で上位 N を選択（タイブレーク: signal_rank）
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア比率で配分（スコア合計が 0 の場合は等金額にフォールバック）
  - risk_adjustment
    - apply_sector_cap: セクター集中上限を計算し、閾値超過セクターの新規候補を除外
      - "unknown" セクターは除外対象外（適用しない）
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）および未知レジーム時のフォールバック
  - position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数計算
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash によるスケーリング）、cost_buffer（手数料/スリッページ見積）対応
      - risk_based: risk_pct, stop_loss_pct を使ったリスクベース算出
      - スケールダウン時の残差配分ロジックを実装

- 研究 / ファクター計算（骨組み）
  - research/factor_research.py を追加
    - DuckDB を用いたモメンタム、ボラティリティ、流動性、バリュー等のファクター計算を想定した設計と定数を実装（prices_daily / raw_financials テーブル参照）
    - 設計上は (date, code) をキーとする dict のリストで出力し、Zスコア正規化ユーティリティと組み合わせる想定

- ペーパートレード検証ツール
  - tools/paper_verification_report.py を追加
    - Paper Trading SQLite（PAPER_TRADING_SQLITE_PATH または --db 引数）から各種指標を集計してレポートを出力
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（avg/max/P95）
    - P95 パーセンタイル計算、期間フィルタ対応（--from / --to）
    - 合否判定: 各閾値（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 出力

### Changed
- 標準出力のロギング取り扱い方針
  - StreamHandler を stdout に向けることで、cron や Task Scheduler など外部のリダイレクト運用に配慮

- DB ハンドリング方針
  - 監視（monitoring）系は常に本番の sqlite_path を見る仕様（監視の観点で一貫性を担保）
  - 実行（execution）系は paper_trading 環境時に専用の paper_sqlite_path を使用して本番データと分離

### Fixed
- 環境変数の読み込み/解析に関する堅牢性向上
  - クォート・エスケープ・インラインコメント処理や `export KEY=val` 形式のサポートを追加し、.env 自動ロードの信頼性を改善

### Notes / Implementation details
- stop/kill フラグはプロジェクトルートの data ディレクトリ内フラグファイル（例: data/stop_requested.flag, data/kill.flag）で制御する設計
- ロギングハンドラの二重登録を防止するため、既存ハンドラを一旦 flush/close してから再設定する実装
- process priority / cpu affinity の設定は環境によって失敗する可能性があるため、失敗時は警告でフォールバックする（安全第一）
- 一部モジュール（例: monitoring_db, SystemMonitor, ExecutionEngine の内部実装、戦略本体など）はこの変更履歴が対象とするコードの外にあり、それらと連携することを前提としている

---

今後のリリースでは以下を想定して改善・追加を行う予定です（コードからの推測）:
- strategy 実装とバックテストフローの追加
- ファクター計算の完全実装および正規化ユーティリティの統合
- 単体テスト・CI の整備、型注釈の補完
- 監視アラートの外部通知（LINE など）連携の強化

ご要望があれば、各項目をさらに細分化してコミット単位やファイル単位で対応箇所を明記します。