# CHANGELOG

すべての注記は Keep a Changelog 準拠です。  
重大/破壊的変更がある場合は明確に記載します。

※ 本ファイルは、提示されたコードベースの内容から推測して作成した変更履歴です。

## [Unreleased]
- ドキュメント・テスト等の未リリース作業用のプレースホルダ。

## [0.1.0] - 2026-04-19
初回公開リリース。

### Added
- 全体
  - パッケージ初期バージョンを定義 (`kabusys.__version__ = "0.1.0"`)。
  - DuckDB / SQLite を利用したデータ処理基盤を導入（設定でパスを指定可能）。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading 用データベースを分離して利用（PAPER_TRADING_SQLITE_PATH / settings.paper_sqlite_path）。
    - BrokerClientFactory によるブローカークライアント生成を組み込み（paper_trading 時は MockBroker を想定）。
    - Engine の起動・停止をスレッドで管理。data/execution.pid を PID ファイルとして使用。
    - data/stop_requested.flag による外部停止フラグ検知と安全停止処理を実装。
    - Execution 用の各種依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler）を組み立てて起動。

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB 初期化を行い、停止フラグ（data/stop_requested.flag）を検知してループ終了。
    - 監視は環境にかかわらず本番 sqlite_path を利用する仕様。

- 設定管理 / CLI
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順序と OS 環境変数保護（protected keys）を実装。
    - 複数の設定プロパティを Settings クラスとして提供（J-Quants, kabuAPI, LINE, DB パス, 監視閾値等）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）を追加。
    - KABUSYS_ENV / LOG_LEVEL 等の値検証を行うプロパティを用意。

  - config_setup.py
    - 対話式の .env 初期作成/更新ウィザードを提供（項目定義・既存値読み込み・保存）。
    - .env 書き込みテンプレート（コメント付き）を生成。

  - validate_config.py
    - 起動前の設定検証 CLI を追加（必須環境変数チェック、KABUSYS_ENV 検証、DB パス存在チェック、config/*.yaml の存在とパース検証（PyYAML 利用））。
    - --strict オプションで警告を FAIL 扱いにするモードを追加。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 設定や Kill Switch 設定の警告）を実装。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - calc_score_weights は全銘柄スコアが 0 の場合に等金額配分へフォールバックし警告を出す。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（当日売却予定の銘柄除外、"unknown" セクターは制限対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear、未知レジームはフォールバックと警告）を実装。

  - portfolio/position_sizing.py
    - 発注株数算出ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株丸め（lot_size）と 1 銘柄上限、aggregate cap によるスケールダウンロジックを実装。
    - cost_buffer により手数料・スリッページを保守的に見積もる機能を追加。
    - スケールダウン後の残余キャッシュ分を fractional remainder に基づき lot 単位で再配分するアルゴリズムを実装。
    - 価格欠損時のスキップ・ログ出力を追加。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを実装。
    - stdout 出力用 StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）を設定。
    - LOG_LEVEL / LOG_DIR 解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - 既存ハンドラをクリアして二重設定を防止。

  - utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定関数 set_process_priority(level) を実装（Windows と POSIX をサポート）。
    - CPU affinity 設定用の set_cpu_affinity(cpu_count) を追加（必要に応じて使用）。
    - 許可されない操作に対しては警告を出して安全にスキップ。

- モニタリング DB 初期化
  - monitoring/monitoring_db.py（呼び出しを確認）を起動スクリプトから利用して監視テーブルの初期化を担保（冪等に実行）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成ツールを追加（SQLite を直接参照して稼働率、注文成功率、送信率、レイテンシ等を集計）。
    - P95 計算、各種閾値（稼働率 99%, 成功率 90% 等）による PASS/FAIL 判定を実装。
    - CLI オプション --from / --to / --db をサポート。

- リサーチ
  - research/factor_research.py
    - ファクター計算モジュールの骨子を追加（モメンタム、MA200、ATR、流動性などの設計と定義定数）。
    - DuckDB 接続を受け取って prices_daily / raw_financials を参照する設計。

### Changed
- 設定自動読み込みの動作
  - .env 自動ロードはデフォルトで有効。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
  - 自動ロード時、OS 環境変数は保護される（.env.local の override でも OS 環境変数は上書きされない）。

### Fixed
- .env パーサ
  - export KEY=val 形式、シングル/ダブルクォート内でのバックスラッシュエスケープ、インラインコメントの扱いなど、実用的な .env 構文に耐性を持たせるよう修正。
  - 不正な MONITOR_POLL_INTERVAL や PAPER_FILL_MODE の値に対する警告/例外処理を追加し、デフォルトや早期エラーをわかりやすくした。

### Security
- 強制的なセキュリティ修正はなし。ただしシークレット値（J-Quants トークン、KABU_API_PASSWORD）に関しては .env ウィザードでマスク表示や注意書きを行う。

### Notes / Known limitations / TODO
- research/factor_research.calc_momentum は処理の途中で定義が途切れている（提示コードの末尾で切れている）。実装は続行中の可能性あり。
- position_sizing の注釈にある通り、将来的には銘柄別の lot_size を stocks マスタ等から与えられるよう拡張する予定。
- apply_sector_cap は price_map に欠損（0.0）があるとエクスポージャーを過少見積もる可能性があり、フォールバック価格（前日終値等）の導入が検討事項。
- プロセス優先度・CPU affinity の設定は環境によって権限不足で失敗し得るため、失敗時はログで警告して安全にスキップする実装。

---

今後のリリースでは下記のような改善が想定されます:
- factor_research の完全実装（Momentum 等の計算ロジックの完成）
- テストカバレッジの追加（ユニットテスト・統合テスト）
- docs/ への設計・運用ドキュメントの追加
- 監視・アラートの強化（LINE 通知の実装確認、Alert Rules の追加）

（以上）