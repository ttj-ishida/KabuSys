# Changelog

すべての注記は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]

（今後の変更をここに記載）

## [0.1.0] - 2026-04-18

初回リリース。自動売買システム "KabuSys" の基本コンポーネントを実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading SQLite DB を使用し（デフォルト: data/paper_trading.db）、MockBrokerClient を使って本番 DB と分離。
    - プロセス優先度を起動直後に "high" に設定。
    - 停止フラグ（data/stop_requested.flag）や pid ファイル（data/execution.pid）に対応し、外部からの停止要求をサポート。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番の sqlite_path を使用する挙動を実装。
    - 停止フラグ検知でループ終了、KeyboardInterrupt による整然とした停止処理。

- 設定関連
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数を保護）。
    - .env パーサーは export プレフィックス・クォート・エスケープ・インラインコメントを考慮して堅牢に解析。
    - Settings クラスを実装し、J-Quants / kabuAPI / DB パス / 監視閾値 等のプロパティを提供。値検証を行い不正な設定は例外を発生させる。
    - PAPER_FILL_MODE の検証（有効値: instant / partial / never / reject）や PAPER_TRADING_SQLITE_PATH 指定をサポート。
  - config_setup.py
    - .env 初期作成・更新の対話式ウィザードを実装。既存値の読み込み、シークレットマスク、デフォルト提示、保存確認などを提供。
  - validate_config.py
    - 起動前の設定検証 CLI を実装。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パス・config/*.yaml の存在チェック、`--strict` モード（警告を FAIL 扱い）をサポート。
    - PyYAML が未インストールの場合は YAML 検証をスキップして警告を表示。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - BUY シグナルの候補選定（スコア降順、signal_rank でタイブレーク）。
    - 等金額配分 calc_equal_weights、スコア加重 calc_score_weights（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存ポジションのセクター別時価を計算して新規候補を除外）。
    - 市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear とフォールバック挙動）。
  - portfolio/position_sizing.py
    - 発注株数決定ロジック calc_position_sizes を実装。
    - risk_based, equal, score の配分方式をサポート。
    - 単元（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金を超えた場合のスケーリング）を実装。
    - コストバッファ（slippage/手数料見積り）に基づく保守的な計算、残差を使った再配分ロジックを実装。

- ユーティリティ
  - utils/logging_setup.py
    - 全アプリ共通のログ初期化ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - プロセス優先度と CPU affinity 設定ユーティリティを追加。Windows / POSIX（Linux, Darwin, FreeBSD）双方に対応。失敗時は警告を出してフォールバック。

- 解析・レポート
  - tools/paper_verification_report.py
    - ペーパートレードの検証レポート生成ツールを追加。
    - 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均 / 最大 / P95）を算出し PASS/FAIL 判定（デフォルト閾値を採用）。
    - 日付フィルタ（--from / --to）、DB パス指定（--db / 環境変数）をサポート。
  - research/factor_research.py（ファクター計算モジュールの実装開始）
    - モメンタム等ファクター計算のための基盤を実装（DuckDB 接続を受け取って prices_daily / raw_financials を参照する設計）。現状モメンタム期間定数等を含む。

- パッケージ情報
  - __init__.py にてバージョンを "0.1.0" に設定。

### 変更 (Changed)
- ログ管理の方針
  - stdout を StreamHandler に用いることで、タスクスケジューラや cron からのリダイレクト運用を容易に。

### 修正 (Fixed)
- .env パースの安定化
  - 引用符・エスケープ・コメント処理を改善し、一般的な .env フォーマットに対する互換性を強化。

### 注意点 / 既知の制約 (Notes)
- run_monitoring は「環境にかかわらず本番 sqlite_path を使用する」設計上、本番 DB を参照するため開発環境で起動する際は注意が必要（意図的な仕様）。
- position_sizing の価格欠損時（price <= 0）はスキップする実装となっており、将来的に価格フォールバック（前日終値等）を追加する余地がある旨コメントで記載。
- research/factor_research.py はファクター計算の基盤を含むが、完全実装は継続予定（ファイル末尾で未完の可能性あり）。

---

その他、内部実装のログ・警告メッセージや例外処理により運用時のトラブルシュートを支援する設計になっています。今後のリリースでは以下を予定しています（例）:
- ExecutionEngine / BrokerClient の詳細実装とテストカバレッジの追加
- factor_research の完全実装と DuckDB ベースのバッチ解析
- 単体テスト・CI 設定・ドキュメント充実

<!-- バージョン履歴は上から新しい順に記載してください。 -->