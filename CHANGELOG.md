# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
バージョンの推定はソース内の __version__（0.1.0）およびファイル実装状況に基づき初期リリースとして作成しています。

## [Unreleased]
- （今後の変更・修正を記載）

---

## [0.1.0] - 2026-04-17

初期リリース（コードベースから推測した主要機能群・CLI・モジュール実装）

### Added
- 全体
  - パッケージ初期実装。バージョン: 0.1.0。
  - パッケージ説明: "KabuSys - 日本株自動売買システム" を提供。

- 設定・環境管理
  - Settings クラス（kabusys.config）を導入し、環境変数から各種設定を取得。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を自動読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - 環境変数パース機能（クォート・エスケープ・コメント対応）を実装。
  - 必須環境変数チェック用ヘルパー _require を提供。
  - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値など）。
  - PAPER_TRADING 用の分離された SQLite パス（data/paper_trading.db 等）をサポート。
  - PID / kill flag 関連の設定項目をサポート。

- CLI / 管理スクリプト
  - 環境設定ウィザード（kabusys.config_setup）
    - 対話式で .env を初期作成・更新するウィザード。
    - デフォルト値・選択肢・シークレット表示（マスク）・保存確認機能を実装。
  - 設定検証ツール（kabusys.validate_config）
    - .env と config/*.yaml の存在・妥当性検証を行う CLI。
    - --strict モードで警告を失敗扱いにできる。
    - YAML パーサ未導入時のフォールバック（警告）とファイルパース検証を提供。
    - KABUSYS_ENV=live 用の追加ガード（LINE 未設定、KILL_FLAG_CLEAR_ON_START 設定など）を検出。
  - 実行エンジン起動スクリプト（kabusys.run_execution）
    - ExecutionEngine の起動フローを実装（プロセス優先度設定、DB 接続、コンポーネント組み立て、スレッド起動、停止フラグ監視）。
    - paper_trading 環境では MockBrokerClient（Factory 経由）を使用し、本番 DB と分離して data/paper_trading.db を使用。
    - デフォルトでプロセス優先度を "high" に設定（kabusys.utils.process_priority）。
    - 停止フラグ（data/stop_requested.flag）と pid ファイル（data/execution.pid）を扱う。
  - 監視ループ起動スクリプト（kabusys.run_monitoring）
    - SystemMonitor を用いたポーリングループを実行（デフォルト 60 秒）。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔上書き（不正値はデフォルトへフォールバック）。
    - 監視 DB（monitoring）は環境にかかわらず本番 sqlite_path を使用する旨の実装。
    - 停止フラグ検知でループを終了し、例外発生時はログを出して次のポーリングへ継続。
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から期間指定でレポートを生成。
    - 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）などを出力。
    - Pass/Fail の閾値（稼働率 99%、注文成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
    - P95 計算、日付フィルタ（ISO8601 UTC 変換）、NULL/データ欠損時の N/A 表示を実装。

- ポートフォリオ構成（純粋関数群）
  - portfolio.portfolio_builder
    - 候補選定（select_candidates：スコア降順、同点は signal_rank のタイブレーク）。
    - 重み計算（等金額: calc_equal_weights、スコア加重: calc_score_weights）。
    - スコア全体が 0 の場合は等金額へフォールバックし警告ログを出力。
  - portfolio.risk_adjustment
    - セクター集中制限（apply_sector_cap）：既存保有のセクター比率が閾値を超える場合に新規候補を除外（"unknown" セクターは除外対象外）。
    - レジーム乗数（calc_regime_multiplier）："bull"/"neutral"/"bear" に対する乗数を提供（未知は 1.0 でフォールバックし警告）。
    - 注: セクター評価で price が 0.0 の場合の欠損リスクに関する TODO コメントあり。
  - portfolio.position_sizing
    - position sizing ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - risk_based: 損切り幅、risk_pct に基づく発注株数計算。
    - equal/score: ウェイトに基づく配分、per-position 上限・aggregate cap（available_cash）でのスケーリング。
    - lot_size（単元株）を考慮した丸め処理、および cost_buffer（手数料・スリッページ見積り）を考慮した保守的見積り。
    - aggregate cap 超過時のスケーリングと remainder を考慮した追加配分ロジック（lot 単位で再配分）を実装。
    - TODO: 銘柄別 lot_size を将来的にサポートする旨の注釈あり。

- 研究（research）
  - research.factor_research
    - DuckDB の prices_daily / raw_financials を用いた定量ファクター計算を実装する設計。
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（ATR 20）、流動性（20日平均売買代金）等の計算ロジックを実装。
    - データ不足時の None 処理、営業日ベースの窓サイズ考慮、DuckDB SQL を利用した集計を実装。

- ユーティリティ
  - utils.process_priority
    - クロスプラットフォームでプロセス優先度（Windows の priority class / POSIX の nice 値）を設定するユーティリティ。
    - psutil を利用し、権限不足や未対応プラットフォームでは警告を出してフォールバック。
    - CPU affinity 設定ヘルパー（set_cpu_affinity）を実装（引数に None を渡すと設定しない）。
    - サポート OS の一覧（Linux/Darwin/FreeBSD）を考慮。

- パッケージ API
  - kabusys.__init__ により、主要モジュール（data, strategy, execution, monitoring 等）の公開とバージョン定義を追加。

### Changed
- n/a（初期リリースのため特定の変更履歴は無し。実装上の設計注釈・ TODO をコード内に記載）

### Fixed
- n/a（初期リリース）

### Deprecated
- n/a

### Removed
- n/a

### Security
- 外部通信に関わる機密情報（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）は .env により管理し、config_setup において .env を Git にコミットしない旨を明示している。

---

## 既知の注意点 / TODO（コード注釈に基づく）
- position_sizing:
  - 銘柄ごとの単元数（lot_size）を将来的に銘柄マスタで扱うことを検討する旨の TODO がある。
- risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）だとセクターエクスポージャーが過少見積りされる可能性があると注記。前日終値や取得原価を使うフォールバックが必要になる場合あり。
- monitor / execution:
  - stop flag / pid file に依存する単純な運用制御を行っているため、他の運用手順（サービスマネージャ等）との整合に注意が必要。
- process_priority:
  - 権限不足や未対応 OS では優先度設定がスキップされる。運用環境では適切な実行権限を確認すること。

---

作成にあたって:
- CHANGELOG はソースコードの内容（関数名、CLI ヘルプ文字列、コメント、デフォルト値、TODO）から推測して作成しました。リリースノートとして公開する際は、実際の変更履歴（コミット、Issue、リリース日）に合わせて日付・詳細を更新してください。