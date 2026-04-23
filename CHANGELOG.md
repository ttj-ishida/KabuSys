# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
リリース日や説明はソースコードから推測して記載しています。

## [0.1.0] - 2026-04-23

### 追加
- 初期リリース。KabuSys の基本的な起動スクリプト、設定管理、ユーティリティ、ポートフォリオ構築ロジック、検証ツール群を実装。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV が `paper_trading` の場合はペーパートレード専用 DB（data/paper_trading.db をデフォルト）を使用し、MockBrokerClient を利用して本番 DB と分離して動作する仕組みを実装。停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。監視用 DB は環境にかかわらず本番 sqlite_path を利用するよう明示。
- 設定・環境変数管理
  - src/kabusys/config.py: Settings クラスを導入し、環境変数や `.env` ファイルから設定を読み出す仕組みを実装。自動 `.env` ロードはプロジェクトルート（.git または pyproject.toml）を起点に行う。PAPER_FILL_MODE や各種パス・閾値などのプロパティを提供。
  - src/kabusys/config_setup.py: 対話式ウィザードで `.env` を初期作成/編集できる CLI を追加（ウィザードは既存値の再利用、シークレットマスク表示、保存確認をサポート）。
  - src/kabusys/validate_config.py: 起動前チェック用 CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、DB パスの存在確認、config/*.yaml の存在・パース検証（PyYAML が利用可能な場合）や本番環境向けのガード（LINE 設定の有無、KILL_FLAG_CLEAR_ON_START の警告など）を行う。`--strict` オプションで警告も失敗扱いにできる。
- ロギング & プロセス管理ユーティリティ
  - src/kabusys/utils/logging_setup.py: ルートロガーを統一的に設定するユーティリティを追加。コンソール出力は stdout を使用し、日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を設定（既定 logs/ ディレクトリ、30 日保持）。既存ハンドラのクリア機能を備え重複設定を防止。
  - src/kabusys/utils/process_priority.py: クロスプラットフォームでプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを追加。psutil を利用し、Windows / POSIX の差分を吸収。権限不足や未対応環境では安全にフォールバックする。
- ポートフォリオ構築ロジック（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py: BUY シグナルの候補選定、等配分・スコア加重の重み計算を実装。
  - src/kabusys/portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - src/kabusys/portfolio/position_sizing.py: risk_based / equal / score の配分方式に対応した株数決定ロジックを実装。単元株（lot_size）対応、ポートフォリオ上限・個別上限・コストバッファを考慮したスケーリング処理を含む。
- ツール類
  - src/kabusys/tools/paper_verification_report.py: Paper Trading 用の検証レポート生成ツールを追加。システム稼働率、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを集計し、閾値（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200ms）に基づいた PASS/FAIL 判定を出力。日付フィルタと DB パス指定をサポート。
- 研究用モジュール（未完の箇所あり）
  - src/kabusys/research/factor_research.py: モメンタム等のファクター計算基盤を追加（DuckDB を用いた prices_daily / raw_financials の参照を念頭に実装）。calc_momentum 等の関数を実装開始（ソースが途中まで含まれる）。

### 変更
- ログ出力のデフォルト挙動を統一
  - StreamHandler は stderr ではなく stdout を用いるように変更（cron/Task Scheduler でのリダイレクト運用を考慮）。
  - ロギング設定時は既存ハンドラを一旦削除して再設定することで二重出力を防止。
- 監視プロセスの DB 接続方針を明確化
  - run_monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用して監視データを記録する設計に（モニタリングデータの一元化目的）。
- run_execution の DB 選択
  - KABUSYS_ENV=paper_trading の場合に専用の paper_sqlite_path を使用するように分離（本番 DB と完全に分離して運用可能）。

### 修正
- .env パーサー強化（src/kabusys/config.py）
  - `export KEY=val` 形式をサポート。
  - シングル／ダブルクォートで囲まれた値に対するエスケープ処理を実装（バックスラッシュエスケープ対応）。
  - クォートなし値のインラインコメント処理を改善（`#` の前が空白かタブの場合にコメントと認識）。
  - 自動ロードはプロジェクトルート未検出時や KABUSYS_DISABLE_AUTO_ENV_LOAD=1 の場合にスキップする挙動で安全化。
- process_priority の堅牢化
  - 未対応 OS や権限不足時にログ警告を出して処理をスキップするフォールバックを追加。
- position_sizing のスケーリングと丸めロジック
  - aggregate cap（総投資額が available_cash を超える場合）でのスケールダウン実装と、lot_size 単位での分配・端数処理を実装し、残余キャッシュで公平に配分するアルゴリズムを追加。
- paper_verification_report の集計ロジック
  - 空データやテーブル未存在時に sqlite3.OperationalError を捕捉してレポートを継続生成できるように耐性を追加。

### 既知の問題 / 注意点
- research/factor_research.py の実装は途中で切れている（calc_momentum の先頭が欠落）。将来的にファクター計算ロジックの完成が必要。
- position_sizing の価格欠損（price が 0.0 または欠損）の場合、エクスポージャー算出や発注株数が過少見積りされる可能性がある旨の TODO コメントあり。前日終値などのフォールバック価格対応を検討する必要がある。
- logging_setup はログディレクトリ作成に失敗した場合にファイルハンドラをスキップするため、ログ出力先の権限やパス設定に注意が必要。
- run_monitoring/run_execution は停止フラグファイル（data/stop_requested.flag）を用いる制御を行うため、運用時には該当ファイル管理（作成・削除）に留意すること。

### セキュリティ
- `.env` は絶対にリポジトリにコミットしないよう README 等で明記することを想定（config_setup が .env 生成時に警告を出す）。

---

今後の予定（想定）
- research/factor_research の完成（ファクター群の完全実装）。
- テストカバレッジ強化と CI 統合。
- 銘柄別の lot_size サポート、手数料モデルの外部化など position_sizing の拡張。
- モニタリング・実行コンポーネントのより詳細な運用ドキュメント追加。