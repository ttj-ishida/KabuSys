# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。  
バージョン番号はパッケージ内の `kabusys.__version__` に合わせています。

※ 内容はコードベースから推測して作成しています（実装意図・動作を要約）。詳細は該当ソースをご参照ください。

## [Unreleased]

（現時点で未リリースの追加・修正をここに記載してください）

---

## [0.1.0] - 2026-04-18

Added
- プロジェクト初期実装（初回リリース相当）。
- 実行/監視ランナー
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。プロセス優先度を設定し、SQLite/DuckDB 接続を確立して実行エンジンをスレッドで起動。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動と安全停止（stop flag と pid ファイルを使用）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。check_once() の例外はログ出力して次ポーリングへ継続。
- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml）。
    - 高度な .env パーサ実装（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理）。
    - Settings クラスを導入し環境変数アクセスをプロパティ化。J-Quants / kabu API / LINE / DB パス / 監視閾値 / システムフラグ等の取得と検証を提供。
    - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）や KABUSYS_ENV の検証を実装。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。既存 .env 読み取り、秘密項目のマスク表示、選択肢・デフォルト対応、保存確認を提供。
- 設定検証 CLI
  - validate_config.py
    - .env と config/*.yaml の設定を事前検証する CLI を追加。
    - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML がない場合は警告）を実施。
    - `--strict` オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築ライブラリ
  - portfolio.portfolio_builder
    - 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全0 の場合は等配分へフォールバックし警告を出す。
  - portfolio.risk_adjustment
    - セクター集中制限 (apply_sector_cap) を実装。既存ポジションのセクター別エクスポージャ計算、上限超過セクターの候補除外、"unknown" セクター無視の挙動を定義。
    - レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull:1.0, neutral:0.7, bear:0.3、未知は警告の上 1.0 フォールバック）。
  - portfolio.position_sizing
    - 各銘柄の発注株数算出ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）での丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）によるスケーリング、cost_buffer（手数料・スリッページ見積り）考慮、残差配分ロジックを提供。
- 研究（ファクター計算）
  - research.factor_research
    - DuckDB を用いたファクター計算モジュールを追加（prices_daily / raw_financials を参照）。
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、相対 ATR）、流動性指標（20日平均売買代金・出来高比率）計算関数を実装。データ不足時は None を返す設計。
- ユーティリティ
  - utils.process_priority
    - クロスプラットフォームでプロセス優先度設定（Windows の priority class / POSIX の nice）と CPU affinity 固定ユーティリティを実装。権限不足や未対応 OS では警告を出してスキップする堅牢設計。
- ツール
  - tools.paper_verification_report.py
    - Paper Trading 用 SQLite DB から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計して検証レポートを生成する CLI を追加。
    - デフォルト閾値（稼働率 ≥ 99%, 成功率 ≥ 90%, 送信率 ≥ 95%, P95レイテンシ ≤ 200ms）で PASS/FAIL を判定。
    - 日付フィルタ (--from / --to)、DB パス指定 (--db) に対応。
- パッケージ初期化
  - kabusys.__init__ にバージョン文字列 (0.1.0) とエクスポート一覧を追加。

Changed
- 一貫したログ出力と例外ハンドリングを導入（起動時の env ログ、ループ内例外の捕捉、優先度設定失敗時の警告など）。
- DB 初期化処理: monitoring 用テーブルの初期化を起動前に行う（init_monitoring_db を用いて冪等に保証）。

Fixed
- run_monitoring の MONITOR_POLL_INTERVAL 読み取りで不正値（0や負数、非整数）を検出した場合にデフォルトへフォールバックするよう修正（time.sleep に渡す不正値回避）。
- .env 読み込み実装の堅牢化（読み込み失敗時に警告出力して継続）。

Security
- .env 作成ウィザードや README 警告で .env を Git にコミットしないよう明示（config_setup.py の出力ヘッダ）。

Notes / Implementation details
- Paper Trading と本番 DB の明確な分離を意図しており、paper_trading 環境時は専用 SQLite を使用する設計になっています（run_execution, Settings.paper_sqlite_path, tools）。
- DuckDB は分析用途（research, execution engine の一部）で参照する想定（duckdb_path 設定）。
- stop/kill フラグや pid ファイル経由のプロセス管理を採用し、手動停止や自動監視からの通知に対応します。
- 一部の関数はデータ欠損を想定して None を返す実装になっており、呼び出し側でのフォールバック処理が容易になっています。

---

メンテナンス/今後の改善候補（コードから推測）
- position_sizing: 銘柄別の lot_size 管理（stocks マスタからの取得）への拡張。
- apply_sector_cap: 価格欠損時のフォールバック（前日終値/取得原価の導入）。
- .env パーサの追加ユースケース（複雑なエスケープ/複数行クォートなど）への対応テスト強化。
- research.factor_research のさらなるファクター追加・単体テスト整備。
- 実運用でのモニタリングアラート送信（LINE 等）やメトリクス収集の統合。

<!--
参考: Keep a Changelog — https://keepachangelog.com/en/1.0.0/
-->