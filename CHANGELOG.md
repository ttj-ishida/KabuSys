# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
### Added
- 監視ループ / 実行エンジンの起動スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグファイル（data/stop_requested.flag）で安全に終了。
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading 時は Paper Trading 用 DB を使用し MockBroker を利用する挙動を想定。停止フラグ / PID ファイル管理機能を搭載。

### Changed
- ログ設定の堅牢化
  - utils/logging_setup.py: stdout への出力および日次ローテーションのファイル出力（TimedRotatingFileHandler）を統一的に設定。ログディレクトリ作成失敗時はファイル出力をスキップして警告出力にフォールバック。
- プロセス優先度関連の扱いを改善
  - utils/process_priority.py: Windows/Linux/macOS を跨いだ優先度設定（nice / HIGH_PRIORITY_CLASS）と CPU affinity 設定ユーティリティを提供。アクセス権限不足や未対応 OS は警告してスキップ。

### Fixed
- .env 読み込みの堅牢化
  - config.py: .env/.env.local の自動読み込みを実装（プロジェクトルートを探索）。クォート付き値や export 形式、コメント処理など幅広い .env 形式を正しくパース。OS 環境変数を保護するための上書きロジックを追加。自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。

---

## [0.1.0] - 2026-04-25
初回リリース — 基本的な自動売買基盤を提供します。

### Added
- 設定管理
  - src/kabusys/config.py: Settings クラスを導入し、環境変数経由で各種設定（API トークン、DB パス、環境種別、ログレベル、監視閾値、Paper Trading 設定など）を取得。必須キーチェック用の _require を用意。
  - .env 自動ロード（.env / .env.local、プロジェクトルート検出）により CWD に依存しない設定の読み込みを実現。

- CLI ツール
  - src/kabusys/validate_config.py: 起動前の設定検証ツール。必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在検査、KABUSYS_ENV=live 時の追加ガード等を実装。--strict モードで警告を FAIL 扱いにできる。
  - src/kabusys/config_setup.py: 対話式ウィザードにより .env の初期作成/更新を支援。デフォルト値・選択肢・シークレット入力をサポート。

- 実行コンポーネント（起動スクリプト）
  - src/kabusys/run_execution.py: ExecutionEngine の起動スクリプトを提供。paper_trading の際は paper_sqlite_path を使用して本番 DB と分離。BrokerClientFactory を経由したブローカクライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組立て、スレッドによるエンジン実行と停止フラグ検知を実装。
  - src/kabusys/run_monitoring.py: SystemMonitor の起動スクリプトを提供。Monitoring は環境にかかわらず本番 sqlite_path を使用する旨を明記。

- モジュール: Portfolio 構築ロジック（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py: シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコアが全てゼロの時は等配分にフォールバック。
  - src/kabusys/portfolio/risk_adjustment.py: セクター集中上限を適用する apply_sector_cap、マーケットレジームに応じた資金乗数 calc_regime_multiplier を実装。未知レジームは警告してフォールバック。
  - src/kabusys/portfolio/position_sizing.py: position sizing ロジックを実装（risk_based / equal / score の割当方式）。単元株丸め、per-position 上限、aggregate cap スケーリング、cost_buffer による保守的評価などを実装。

- ユーティリティ
  - src/kabusys/utils/logging_setup.py: ルートロガーに対する統一的なログ設定ユーティリティを提供。ログレベル解決順やログディレクトリ解決順を定義。
  - src/kabusys/utils/process_priority.py: 前述のプロセス優先度 / CPU affinity ユーティリティを提供。

- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py: ペーパートレード用 SQLite DB から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計し、PASS/FAIL 判定でレポート出力するツールを提供。PAPER_TRADING_SQLITE_PATH 環境変数とコマンドラインオプションをサポート。

- リサーチ（ファクター計算）骨組み
  - src/kabusys/research/factor_research.py: Momentum / Value / Volatility / Liquidity 等のファクター計算を行うモジュールの骨組みを追加（DuckDB 接続を受けて prices_daily / raw_financials を参照）。モメンタム計算関数群の実装方針と初期定数を定義（実装途中の箇所あり）。

- パッケージメタ
  - src/kabusys/__init__.py: バージョン __version__ = "0.1.0" を設定。

### Changed
- DB 関連
  - DuckDB と SQLite を併用する設計を導入（duckdb_path / sqlite_path）。monitoring 用テーブル初期化関数 init_monitoring_db を起動時に呼び出して冪等に監視テーブルを保証。

### Fixed
- 停止/停止フラグ関連の安全性向上
  - run_execution/run_monitoring: 起動直後に停止フラグを検知した場合は即座に起動を中止するロジックを追加。監視ループ中の例外はログ出力して次回ポーリングまで待機する。

### Security
- .env の取り扱いに関する注意喚起を config_setup.py のヘッダに記載（.env を絶対にリポジトリにコミットしないこと）。

---

## Notes / 今後の改善案（ソースから推測）
- factor_research.py の一部が未完（コメント末尾で途中終了）であるため、ファクター算出ロジックの完成・テストが必要。
- position_sizing の lot_size を銘柄毎に持たせる等の拡張や、price が欠損した場合のフォールバック価格導入（TODO コメントあり）。
- ログ出力／ファイルハンドラのエラーに対するより詳細な運用ドキュメント化。
- 実行エンジンの Graceful shutdown、長時間停止時のリカバリや PID ファイルの管理ポリシーの明文化。

---

（注）上記は提供されたソースコードの内容から推測して記載した変更履歴です。実際のコミット履歴とは異なる場合があります。必要であれば、より細かなファイル単位の差分記述や日付・コミット参照（SHA）を付与します。