# Changelog

すべての主要な変更は「Keep a Changelog」フォーマットに準拠して記載します。  
このファイルは、リポジトリの現在のコードベース（初期リリース相当）から推測して作成した変更履歴です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現時点では未リリースの差分はありません。将来の変更はここに記載してください。）

---

## [0.1.0] - 2026-04-17
初期リリース。システム全体のコア機能（設定管理、監視、実行エンジン、ポートフォリオ構成、研究用ファクター計算、ニュースNLP バッチ処理ユーティリティ、ユーティリティ関数群、検証用ツール等）を実装。

### Added
- 全体
  - パッケージ初期化とバージョン設定を追加（kabusys.__version__ = "0.1.0"）。
  - Keep a Changelog ベースでの初回公開相当の機能群を追加。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env/.env.local の自動ロード機構を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 環境変数パース処理を実装（コメント・クォート・export 形式対応、エスケープ対応）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - 必須環境変数チェック（_require）を実装。
  - 各種設定プロパティを提供（DBパス、PID/フラグパス、しきい値、環境判定等）。
  - PAPER_FILL_MODE のバリデーションを実装（instant/partial/never/reject を許容）。

- 実行系 / デーモン起動スクリプト
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor をポーリングで定期実行するループを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用する旨をドキュメント化。
    - 停止フラグ（data/stop_requested.flag）検知で安全終了。
    - 起動時にプロセス優先度を "high" に設定。
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - ExecutionEngine の組み立てと別スレッドでの実行を実装。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て。
    - 停止フラグと実行 PID の取り扱い（data/execution.pid, data/stop_requested.flag）。
    - 起動時にプロセス優先度を "high" に設定。

- 監視 DB 初期化ユーティリティ
  - monitoring_db 初期化用の呼び出しを run 系で利用（冪等にテーブルを準備）。

- ユーティリティ（src/kabusys/utils/process_priority.py）
  - プラットフォーム差を吸収するプロセス優先度設定機能を実装（Windows と POSIX に対応）。
  - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
  - 権限不足や未対応 OS に対する安全なフォールバック / 警告ログあり。

- ポートフォリオ構築（src/kabusys/portfolio/*.py）
  - 候補選定と重み計算（portfolio_builder.py）
    - select_candidates（スコア降順、signal_rank によるタイブレーク）
    - calc_equal_weights（等配分）
    - calc_score_weights（スコア正規化、全て0のとき等配分にフォールバック）
  - セクター集中制限・レジーム乗数（risk_adjustment.py）
    - apply_sector_cap（既存ポジションのセクター別時価を評価し、上限超過セクターの新規候補を除外）
    - calc_regime_multiplier（regime に応じた投下資金乗数、未知レジームはフォールバック）
  - 建玉サイズ決定（position_sizing.py）
    - risk_based / equal / score の allocation_method に対応した株数計算
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）によるスケールダウン（再割付アルゴリズム含む）
    - cost_buffer による保守的コスト見積り対応

- 研究・ファクター計算（src/kabusys/research/*.py）
  - factor_research.py:
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20, 相対ATR, 20日平均売買代金, 出来高比率）、バリュー（PER, ROE）計算を DuckDB で実装。
    - データ不足時の None 処理、SQLウィンドウ関数を利用した効率的な実装。
  - feature_exploration.py:
    - 将来リターン計算（horizons の一括取得）、IC（Spearman ρ）計算、ファクター統計サマリーを実装。
    - 副関数 rank（同順位は平均ランク）を実装。
  - research パッケージのエクスポート（zscore_normalize を含む）。

- AI / ニュース NLP（src/kabusys/ai/news_nlp.py）
  - ニュースのタイムウィンドウ計算（JST 基準 → UTC 変換）を実装（calc_news_window）。
  - OpenAI を使った銘柄別センチメント集約・バッチ送信の設計（gpt-4o-mini, JSON出力厳格化）。
  - バッチサイズ、トークン肥大化対策（記事数・文字数制限）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアの ±1.0 クリップ、部分成功時の部分更新戦略を設計。
  - APIキー未設定時には ValueError を投げる。

- ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 用検証レポート生成 CLI を実装。
  - デフォルト DB パスは data/paper_trading.db、--db で上書き可能。
  - 指標:
    - 稼働率（uptime_pct）閾値 99.0%
    - 注文成功率（fill_rate）閾値 90.0%
    - 送信率（send_rate）閾値 95.0%
    - P95 レイテンシ閾値 200 ms
  - 各種クエリ（system_status / trade_logs / risk_logs など）を集計して判定を出力。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーの取り扱いは引数または環境変数で解決し、未設定時は明示的にエラーを返すことで誤った無害化を防止。

### Notes / Important behavior
- 監視（run_monitoring.py）は「環境（KABUSYS_ENV）にかかわらず production の sqlite_path を使用する」実装になっています。本番/ペーパーを分離したい場合は設定の見直しが必要です。
- run_execution は paper_trading 環境時に paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を利用することで本番 DB とロギングを分離します。
- .env ロードはプロジェクトルートを基準に行うため、パッケージ化後でも CWD に依存しない仕様です。テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用してください。
- process priority / CPU affinity の設定は権限やプラットフォーム依存のため失敗時は警告を出して安全にスキップします。
- ニュース NLP モジュールは高信頼な JSON 出力を前提にしており、部分失敗に備えた書き込み保護（既存スコアを不必要に上書きしない設計）を採用しています。

---

将来のリリースでは以下を想定：
- ExecutionEngine / SystemMonitor 内部の詳細な実装（ログ、メトリクス、再起動戦略など）の拡充
- ニュース NLP の完全実装（_fetch_articles 等の未完部分の実装、OpenAI の実際の呼び出し・レスポンス処理の完成）
- テストカバレッジと CI の追加
- 銘柄ごと単元株数のマスタ対応などの拡張

（以上）