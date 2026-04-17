# CHANGELOG

すべての重要な変更はこのファイルに記載します。フォーマットは Keep a Changelog に準拠します。
https://keepachangelog.com/ja/1.0.0/

なお、この CHANGELOG は提供されたコードベースから推測して作成しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

初回リリース。日本株自動売買システム「KabuSys」の基本モジュール群を追加しました。主な追加点は以下の通りです。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 として追加。

- 環境設定・管理
  - Settings クラス（src/kabusys/config.py）
    - .env 自動ロード機能（プロジェクトルートの .env と .env.local）。
    - 環境変数のパース実装（export 形式、シングル/ダブルクォート、インラインコメント対応）。
    - 必須/オプション設定、各種プロパティ（J-Quants, kabu API, DB パス, PID/kill flag, 監視閾値 等）。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
    - 環境（development / paper_trading / live）・ログレベルの検証。
  - 環境設定ウィザード CLI（src/kabusys/config_setup.py）
    - 対話式で .env を生成/更新するウィザード。
    - 複数の設定項目（J-Quants トークン、kabu API パスワード、DB パス、LINE 設定、KABUSYS_ENV など）をサポート。
    - .env の書式テンプレートと保存機能（保存時に注意書き）。
  - 設定検証ツール（src/kabusys/validate_config.py）
    - 起動前に .env と config/*.yaml（存在する場合）の整合性をチェック。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML が存在する場合）。
    - --strict モードで警告を FAIL 扱いにできる。

- 実行系および監視
  - Execution 起動スクリプト（src/kabusys/run_execution.py）
    - プロセス優先度を高く設定して起動。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用（data/paper_trading.db デフォルト）および MockBrokerClient を利用可能な設計（BrokerClientFactory 経由）。
    - Engine の組み立て（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理（data/execution.pid）。
    - デーモンスレッドでの実行と安全な停止処理。
  - Monitoring 起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループを開始。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 監視 DB は環境に関わらず本番 sqlite_path を使用（監視テーブル初期化含む）。
    - 停止フラグ検知で安全終了、例外発生時はログを残して次回ポーリングへ続行。

- データベース初期化（監視用）
  - init_monitoring_db を参照する起動フローを追加（監視テーブルの冪等初期化を保障）。

- 実用ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows/Linux/Mac 等のプラットフォーム差を吸収してプロセス優先度を設定。
    - set_process_priority(level: "high" | "normal" | "low")
    - set_cpu_affinity(cpu_count: Optional[int])
    - 権限不足や未対応 OS では警告を出してスキップするフェイルセーフ。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - BUY シグナルのソーティング（score 降順, signal_rank タイブレーク）。
    - 等配分 calc_equal_weights、スコア加重 calc_score_weights（全スコア 0 の場合は等配分にフォールバック）。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap：セクター集中上限（max_sector_pct）による候補除外ロジック。unknown セクターは除外されない仕様。
    - calc_regime_multiplier：市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは警告して 1.0 でフォールバック。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes：allocation_method（risk_based / equal / score）に基づく株数算出。
    - 単元株（lot_size）で丸め、per-position 上限・aggregate cap（available_cash）でスケール調整、cost_buffer を考慮した保守的見積り、残差処理で lot 単位の再配分を実装。

- リサーチ / ファクター計算
  - factor_research（src/kabusys/research/factor_research.py）
    - DuckDB を用いたファクター計算（prices_daily, raw_financials を参照）。
    - モメンタム（1m/3m/6m リターン、MA200 乖離）、ボラティリティ（ATR20 等）、流動性指標等を提供。
    - 日付ウィンドウやデータ不足時の None 扱いなどを明記。

- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading DB（デフォルト data/paper_trading.db）から以下を算出して標準出力レポートを生成：
      - 稼働率（uptime）、注文成功率（fill rate）、送信率、リスク却下数、API レイテンシ（avg/max/P95）。
    - Pass/Fail 判定基準を定義（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 latency <= 200ms）。
    - --from / --to / --db オプション対応。

### 変更 (Changed)
- （初回リリースのため変更履歴なし）

### 修正 (Fixed)
- （初回リリースのため修正履歴なし）

### 注意事項 / 実装上のポイント
- .env 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- .env の自動読み込み時、既存 OS 環境変数は保護され（.env.local でも上書きされない）、.env.local は override=True（ただし OS 環境のキーは保護）で読み込む。
- run_monitoring は監視用 DB の初期化を行うが、本番 sqlite_path を使う（KABUSYS_ENV に依らず）。
- run_execution は paper_trading 時に paper_sqlite_path を使用して本番 DB と完全分離する設計。
- process_priority や CPU affinity の設定は権限不足や未対応環境で例外を上げず警告で済ませるため、安全に起動できる。
- PAPER_FILL_MODE 等の環境変数に不正値を与えると ValueError を投げるため、validate_config の実行を推奨。

### 既知の制限 / TODO（README 等へ移行予定）
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別 lot_map 対応を検討）。
- apply_sector_cap の price が欠損(0.0) の場合にエクスポージャーが過少見積りされる旨の注記あり（フォールバック価格の導入を検討）。
- factor_research は prices_daily / raw_financials の整備が前提。データ不足時は None を返す設計。

---

今後のリリースでは、以下の点を想定しています：
- ExecutionEngine / BrokerClient の詳細な実装やテスト補強
- 運用を想定した監視アラート（LINE 通知等）の追加強化
- 銘柄別 lot_size、手数料モデルの改良、より詳細なレポート出力形式の追加

（以上）