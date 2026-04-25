# CHANGELOG

すべての重要な変更履歴を Keep a Changelog 準拠の形式で日本語で記載します。以下の内容は、提供されたコードベースの実装から推測して作成したリリースノートです。

フォーマット:
- Unreleased：今後の変更予定（コードベースから推測できる改善候補）
- 各リリースは [バージョン] - リリース日 の見出しで記載
- セクションは Added / Changed / Fixed / Security / Deprecated / Removed を想定

注意: 実際のコミット履歴がないため、各項目はソースコードから推測した機能追加・修正点です。

## [Unreleased]
- Changed
  - ログ出力やエラー処理の細かな改善（例: ファイルハンドラ作成失敗時の挙動や警告メッセージの改善）。
  - position sizing や allocation のさらに細かなチューニング（lot 単位調整、コストバッファの取り扱い改善など）。
- Added
  - モニタリングのポーリング間隔や実行モード周りの運用ユーティリティ（MONITOR_POLL_INTERVAL 周りの追加設定の洗練）。
  - research モジュールの追加ファクター（momentum 等）の実装完了・拡張（未完成の関数の完成、テスト追加）。
- Fixed
  - 環境変数自動読み込みのエッジケースや .env パースの追加ユースケースへの対応強化（コメント扱い、クォート処理の堅牢化）。
- Deprecated / Removed / Security
  - なし（将来の明示的な置換や削除を検討）。

---

## [0.1.0] - 2026-04-25
初回公開リリース（コードベースから推測）。以下はこのバージョンで導入された主要な機能と修正点です。

Added
- 基本アプリケーション構成
  - パッケージメタ情報として `kabusys.__version__ = "0.1.0"` を導入。
- 環境設定・管理
  - Settings クラスを実装し、環境変数経由で設定を統一的に取得できるようにした。
    - J-Quants／kabuステーション／LINE／DBパス／監視閾値／実行環境（KABUSYS_ENV）等をプロパティで提供。
    - KABUSYS_ENV, LOG_LEVEL 等の値検証（有効値チェック）を追加。
  - 自動 .env ロード機能を実装（プロジェクトルートの検出 .git / pyproject.toml を基準）。
  - .env の対話式ウィザード（config_setup）を追加：.env の初期作成・更新をサポート。
- 設定検証 CLI
  - validate_config を実装し、必須環境変数・パス・config/*.yaml の基本チェックや本番環境向けガードを提供。
  - --strict オプションで警告を失敗扱いにするモードを追加。
- 実行エンジン / 監視
  - run_execution：ExecutionEngine 起動スクリプトを追加。paper_trading モード時の DB 分離（data/paper_trading.db）と MockBrokerClient の利用方針を導入。
    - 起動時にプロセス優先度を "high" に設定するフロー。
    - 停止フラグ (data/stop_requested.flag) と PID 管理 (data/execution.pid) による外部停止制御。
  - run_monitoring：SystemMonitor 用のポーリング起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番用 sqlite_path を参照する方針を明記。
- ロギング / プロセス管理ユーティリティ
  - logging_setup：root ロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション）を設定するユーティリティを追加。ログディレクトリ自動作成とファイルハンドラの失敗回避を実装。
  - process_priority：Windows / POSIX を吸収するプロセス優先度設定ユーティリティを追加（nice / HIGH_PRIORITY_CLASS 等）。CPU affinity 設定関数 set_cpu_affinity も提供。
- ポートフォリオ構築（純粋関数群）
  - portfolio モジュールを追加（ポートフォリオ構築ロジックをメモリ内で実行）。
  - portfolio_builder:
    - select_candidates: スコア降順で候補選定（signal_rank でタイブレーク）。
    - calc_equal_weights, calc_score_weights: 等金額・スコア重み計算。スコア合計が 0 の場合は等金額にフォールバック。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮し、"unknown" セクターは除外）。
    - calc_regime_multiplier: 市場レジームに応じた乗数（bull/neutral/bear、未知時はフォールバックと警告）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数計算を実装。lot_size（単元株）で丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap とスケールダウンロジックを導入。
- Research / Factor 計算（初期実装）
  - research.factor_research にモメンタム等を計算するための基礎コードを追加（DuckDB 接続を受け取り prices_daily 等のテーブルを参照する設計）。移動平均やリターン、ATR、出来高ベースの指標を想定。
- 運用・解析ツール
  - tools.paper_verification_report：Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等の指標を集計して PASS/FAIL を判定するレポートを出力。
    - デフォルト閾値を定義（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200 ms）。
    - SQLite DB（PAPER_TRADING_SQLITE_PATH）からの集計に対応。
- DB 初期化ヘルパ
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視用テーブルの存在を保証する処理を追加（冪等）。

Changed
- ログ出力先
  - ログの標準出力には stdout を使用する設計に統一（cron 等の運用を想定した一本化）。
- run_execution / run_monitoring の運用設計
  - 起動直後にプロセス優先度を上げるフローを共通で追加しており、優先度設定失敗時は警告で継続する設計。

Fixed
- .env パースの堅牢化
  - export キーワード対応、クォート内のエスケープ処理やインラインコメント処理、クォートなしのコメント認識などを実装し、.env の実用性を向上。
- position_sizing のスケーリング
  - aggregate cap 超過時のスケールダウンロジックと lot 単位での再配分アルゴリズムを導入し、端数配分の安定化を実施。
- 設定検証のガード
  - validate_config による本番環境（live）向けの追加チェック（LINE トークン、KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。

Security
- 機密情報の扱い
  - config_setup のウィザードで J-Quants / kabu API のトークンやパスワードを "secret" として扱い、表示時にマスクする等の配慮を実装。

Deprecated
- なし

Removed
- なし

---

参考:
- 本 CHANGELOG は提供されたソースコードからの推測に基づいて作成しています。実際のコミット履歴やリリースノートに合わせて内容を調整してください。必要であれば、各ファイルごとにより詳細な変更点（関数追加や内部アルゴリズムの変更）を抜粋して追記できます。