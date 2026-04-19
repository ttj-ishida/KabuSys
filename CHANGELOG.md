# CHANGELOG

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。  

注: 以下の変更点・機能説明はコードベースから推測して記載しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-19

初回リリース — KabuSys ベース機能を実装。

### Added
- 実行スクリプト / デーモン類
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite（data/paper_trading.db をデフォルト）を使用することで本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定するフックを追加。
    - 停止制御用のフラグファイル（data/stop_requested.flag）と実行 PID 管理（data/execution.pid）をサポート。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - スレッド監視による安全な停止処理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境に関わらず本番 sqlite_path を使用することを明記。
    - 停止フラグ検知でループを終了する仕組みを実装。
- 設定・環境管理
  - config.py: 環境変数と .env 自動ロード機能の実装
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順序をサポート。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
    - 各種設定プロパティ（DB パス、API トークン、PAPER_FILL_MODE、しきい値など）を Settings クラスで提供。
    - 環境値の検証（enum・範囲チェック）を行う設計。
  - config_setup.py: 対話式 .env 作成ウィザードを実装（CLI）。
    - J-Quants や kabu API の必須項目、ログ設定、DB パス等を対話的に入力して .env を生成/更新。
  - validate_config.py: 起動前の設定検証 CLI を実装。
    - 必須環境変数のチェック、KABUSYS_ENV の妥当性、DB パスと config/*.yaml の存在チェック、production ガード（LINE 設定など）を提供。
    - --strict モードで警告を失敗扱いにできる。
- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選択。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア重み配分（全スコア 0 のとき等金額フォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を抑える候補フィルタ。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数算出、単元株丸め、aggregate cap のスケーリングロジック、cost_buffer 対応。
  - portfolio/__init__.py で主要関数を公開。
- ユーティリティ
  - utils/logging_setup.py
    - 標準化されたロギング設定ユーティリティ。コンソール（stdout）と日次ローテーションファイルハンドラをルートロガーに設定。
    - ログディレクトリ自動作成（失敗時はファイル出力をスキップ）・ログレベル解決ロジックを提供。
  - utils/process_priority.py
    - Windows / POSIX を吸収したプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティを実装。権限不足などのケースは警告でスキップ。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite を読み取り、稼働率・注文成功率・送信率・レイテンシ（avg/max/P95）等の指標を集計してレポート出力。
    - 指標閾値（稼働率99%、成功率90% など）に基づく PASS/FAIL 判定を実装。
    - --from / --to / --db 等の CLI オプションをサポート。
- 研究 / ファクター計算（骨格）
  - research/factor_research.py
    - DuckDB を使ったファクター計算モジュール（モメンタム、移動平均乖離、ATR, ボラティリティなど）を設計方針付きで実装（calc_momentum 等の基盤実装開始）。※ファイル末尾で途中までの実装を含む。
- パッケージ化
  - src/kabusys/__init__.py にバージョン (0.1.0) を設定。
  - パッケージ構造に tools, portfolio, utils, monitoring, execution, research 等を整備。

### Changed
- 初期リリースのため該当なし（新規実装が中心）。

### Fixed
- 初期リリースのため該当なし。

### Security
- 秘匿値（API トークン等）は .env による管理を想定し、config_setup の出力で .env をコミットしない旨を注意書き。実行時は環境変数からの取得を推奨。

### Notes / 使用上の注意（コードから推測）
- 実行 / 監視プロセスは起動時にプロセス優先度を高く設定しようとしますが、権限不足や未対応 OS の場合は警告ログを出してスキップします。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能。0 以下や不正値は無視されデフォルト 60 秒にフォールバックします。
- run_execution は paper_trading モード時に専用 DB を使用して本番とデータ分離を行います。PAPER_FILL_MODE による約定挙動の差分（instant/partial/never/reject）をサポート。
- config.py は自動的に .env を読み込みます。CI/テスト等で自動読み込みを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- tools/paper_verification_report の P95 はサンプル数とソートによる簡易算出を行っています（厳密な統計ライブラリは使用していない）。

---

その他、ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）や config/*.yaml の存在・スキーマは期待されており、validate_config CLI による事前チェックが推奨されます。

（以上）