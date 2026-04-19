# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。  
過去の変更は下に、新しい変更は上に記載します。

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 実行用エントリポイントを追加
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。プロセス優先度設定、SQLite / DuckDB 接続、Broker クライアント生成、OrderManager / OrderRepository / RiskManager / Reconciler の組み立て、スレッドでのエンジン実行と停止フラグ検出を実装。
  - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグファイル検出で終了。
- 設定管理
  - config.py: 環境変数・.env の自動読み込み、.env パースロジック、Settings クラスを実装。J-Quants / kabuステーション / LINE / DB / 監視・システム関連の設定プロパティを提供。環境（development/paper_trading/live）やログレベルの検証を行う。
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。既存 .env の読み込み、入力プロンプト、保存機能を含む。
  - validate_config.py: 起動前の設定検証 CLI を追加。.env 必須項目の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス・config/*.yaml の存在チェック、本番環境向けガードを実装。--strict モードに対応。
- ペーパートレード検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite DB から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数）を集計してレポート出力するスクリプトを追加。期間フィルタ（--from/--to）および DB パス指定に対応。合格基準の閾値を定義（稼働率 99% など）。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定・重み計算関数（select_candidates, calc_equal_weights, calc_score_weights）を追加。スコアがゼロの際のフォールバックやソートルールを定義。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を追加。セクター未登録銘柄は "unknown" 扱いで除外免除などの挙動を明記。
  - portfolio/position_sizing.py: 各銘柄の発注株数を決定するロジック（risk_based / equal / score の配分方式、lot_size 単位への丸め、aggregate cap によるスケーリング、コストバッファの取り込みなど）を実装。
  - portfolio/__init__.py: 上記関数群をパッケージ公開。
- ユーティリティ
  - utils/logging_setup.py: ルートロガーの統一設定ユーティリティを追加。stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler を設定。ログディレクトリ作成失敗時のフォールバック処理、環境変数 LOG_LEVEL / LOG_DIR の尊重。
  - utils/process_priority.py: クロスプラットフォームに対応したプロセス優先度設定および CPU affinity 設定ユーティリティを追加（Windows / POSIX 対応、権限不足時は警告でスキップ）。
- 研究用モジュール（部分実装）
  - research/factor_research.py: DuckDB を使った定量ファクター計算の下地を追加（モメンタム / MA200 / ATR / 出来高系などの定義と計算方針）。（実装途中の関数が存在）

### 変更 (Changed)
- 実行/監視スクリプトの設計方針
  - 監視（monitoring）は環境に関係なく本番 sqlite_path を使用して監視データを一元化するように明記。
  - 実行（execution）は KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite を使用して本番 DB と完全分離する挙動を採用。
- ログの取り扱い
  - logging_setup によって全スクリプトで統一されたログ出力形式・ローテーションが利用可能に。標準出力は stdout を使用する仕様に統一。

### 修正 (Fixed)
- .env パースの堅牢化
  - config.py の .env パーサが export 先頭表記やクォート文字、インラインコメントやエスケープシーケンスに対応するよう強化。これによりより柔軟で現実的な .env 記述に耐性を持たせた。
- process_priority の例外処理強化
  - 権限不足や未サポート OS での呼び出し時に警告を出して処理を継続するように改善。

### ドキュメント (Documentation)
- 各モジュールに詳細な docstring と使用例・設計メモを多数追加（PortfolioConstruction.md 等の設計文書に準拠する旨がコメントで記載）。
- config_setup と validate_config の利用方法 / 推奨ワークフローが CLI ヘルプと docstring に追加。

### 注意事項 (Notes)
- run_execution/run_monitoring は停止制御にファイルベースのフラグ（data/stop_requested.flag, data/execution.pid, data/kill.flag 等）を使用するため、運用時は該当ディレクトリと権限設定に注意してください。
- paper_trading 時の挙動（MockBrokerClient と専用 DB 使用）や PAPER_FILL_MODE の有効値（instant/partial/never/reject）は Settings で検証され、無効値は起動時に例外になります。
- research/factor_research.py は設計方針と一部定数・型定義が整っていますが、完全実装（全関数の完結）はまだ途中です。

### 既知の問題 (Known issues)
- position_sizing の価格欠損時の挙動は TODO コメントで示している通り、将来的に前日終値等でのフォールバックを実装する余地があります。
- config/*.yaml の内容検証は PyYAML に依存しており、未インストールの場合は検証がスキップされます（validate_config で警告）。

## 以前のリリース
- （初期リリースのため履歴なし）

--- 

今後の変更はこのファイルに記載します。変更提案や誤記の指摘があればご連絡ください。