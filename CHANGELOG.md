# CHANGELOG

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
バージョン番号はパッケージ内の __version__ に合わせています。

※この CHANGELOG はソースコードの内容から推測して作成したもので、実際のリリースノートや変更履歴と差異がある場合があります。

## [Unreleased]

- （現時点では未リリースの改修があればここに記載します）

## [0.1.0] - 2026-04-17

初回公開リリース。システム全体のコア機能を実装しています。以下は主要な追加・設計方針・既知の挙動の要約です。

### Added
- 全体
  - パッケージ初期版を追加（__version__ = 0.1.0）。
  - Settings クラスによる環境変数ベースの設定管理を実装。
    - .env / .env.local の自動読み込み（プロジェクトルート検出による。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可能）。
    - .env パーサーはコメント、`export KEY=val`、シングル/ダブルクォート、エスケープシーケンス等に対応。
    - 環境変数の必須チェックと各種検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
  - DuckDB / SQLite を使ったデータ処理基盤を採用（duckdb 接続を受け取る設計の調査／研究 API を提供）。

- 実行 / 監視関連
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用 SQLite DB を使用し、本番 DB と完全分離。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立て・起動ロジック。
    - プロセス優先度を高（High）に設定する呼び出しを追加。
    - 停止フラグ（data/stop_requested.flag）検出による安全停止対応。
  - run_monitoring.py: システム監視（SystemMonitor）ポーリングループの起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path を使用する（環境に依存せず）。
    - DuckDB 接続も確立し SystemMonitor に渡す。
    - プロセス優先度設定、停止フラグ検知、例外保護ループを実装。

- モニタリング / 可観測性
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）を利用して監視テーブルを保証（冪等）。
  - 停止・PID ファイルの扱い（pid_file_path）を設定経由で指定可能。

- Tools
  - tools/paper_verification_report.py を追加。
    - Paper Trading の検証レポート生成（期間指定可、コマンドラインツール）。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。
    - PASS/FAIL の基準値を定義（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200 ms）。
    - DB なくても安全に動作する（テーブル欠如時のフォールバック処理）。

- ポートフォリオ構築
  - portfolio モジュールを実装（純粋関数群、DB 参照なし）。
    - portfolio_builder: select_candidates、calc_equal_weights、calc_score_weights（score=0 フォールバックで警告）。
    - risk_adjustment: apply_sector_cap（セクター集中の上限適用。unknown セクターは制限除外）、calc_regime_multiplier（レジーム別乗数、未知レジームは 1.0 でフォールバック）。
    - position_sizing: calc_position_sizes（risk_based / equal / score の配置方法、lot_size 単位丸め、cost_buffer、aggregate cap によるスケールダウン、残差配分ロジック）。

- リサーチ / ファクター
  - research パッケージを追加。
    - factor_research: calc_momentum、calc_volatility、calc_value（DuckDB の prices_daily / raw_financials を参照。ウィンドウ不足時は None を返す）。
    - feature_exploration: calc_forward_returns、calc_ic（Spearman）、factor_summary、rank（タイの平均ランク処理）。
    - DuckDB SQL を多用し、標準ライブラリのみで統計処理を実装する方針。

- AI / ニューススコアリング（NLP）
  - ai/news_nlp.py を追加（OpenAI API を用いたニュースセンチメント集計）。
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して使用）。
    - 記事集約、1 銘柄あたりの文字数・記事数制限（トークン肥大化対策）。
    - バッチ処理（最大 20 銘柄 / API 呼び出し）、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアクリッピング（±1.0）。
    - 部分失敗時でも既存スコアを保護する DB 書き込み戦略（対象コードで DELETE → INSERT）。
    - API キー未設定時は ValueError を送出。

- ユーティリティ
  - utils/process_priority.py を追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収したプロセス優先度設定（high/normal/low）。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity（例外時は警告スキップ）。
    - 権限不足や未対応プラットフォームでのフォールバック・警告処理。

### Changed
- （初回リリースのため「変更」は特になし。内部設計上の注記を記載）
  - 環境依存性を低くするため、.env の自動読み込みはプロジェクトルート検出に基づく実装。
  - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を参照する旨を明示（重要な運用挙動）。

### Fixed
- 初期実装段階での堅牢性向上。
  - .env 読み込み失敗時に警告を出して継続する安全設計。
  - 各種計算関数でのゼロ除算回避・データ不足時の None 戻し。
  - process_priority / cpu_affinity の権限エラーを捕捉してログ警告にフォールバック。

### Known issues / Notes（既知の挙動・注意点）
- run_monitoring は監視データを書き込む SQLite を常に settings.sqlite_path（本番想定）に接続します。開発・テスト時に本番 DB を誤って更新しないよう注意してください。
- PAPER_TRADING（paper_trading 環境）では run_execution が paper_trading 専用 DB（PAPER_TRADING_SQLITE_PATH）を使用する設計ですが、監視はこれと分離されています。
- ai/news_nlp の処理は API キー必須であり、OpenAI 側の利用制限や課金に注意が必要です。API 呼び出し失敗時は再試行後にスキップする実装のため、一部スコアが更新されないことがあります。
- position_sizing の現在の実装では lot_size はグローバル固定（デフォルト 100）で、銘柄ごとの単元差異は未対応（将来的な拡張予定あり）。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後や異なる配置で CWD が変わると意図しない挙動になる可能性がある。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- tools/paper_verification_report は DuckDB ではなく SQLite の paper_trading DB を参照する CLI ツールです。

### Security
- 本リリースで特に報告されたセキュリティ修正はありません。環境変数管理や API キー取り扱いはユーザー側で慎重に行ってください（OPENAI_API_KEY 等）。

---

(各ファイルの実装詳細や関数の挙動はソースコード内の docstring / コメントを参照してください。)