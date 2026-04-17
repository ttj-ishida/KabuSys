# Changelog

すべての著名な変更点は Keep a Changelog の形式に従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-17

### Added
- 初回リリース: KabuSys の基本モジュール群を追加。
- 実行・監視エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite (data/paper_trading.db を既定) を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler 等を組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグ (data/stop_requested.flag) の検出で安全に停止。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視情報を記録。
    - 停止フラグ検知・KeyboardInterrupt ハンドリングを実装。
- 設定管理
  - config.py: .env ファイル自動読み込み機能を追加。  
    - プロジェクトルートを .git / pyproject.toml から検出して .env, .env.local を読み込む（OS 環境変数を保護）。
    - export 形式・クォート・コメントの扱いに対応する堅牢なパーサを実装。
    - Settings クラスを導入し、各種環境変数（DB パス、Paper Trading 設定、監視閾値、ログレベル、環境モード等）へのアクセスを簡素化。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化が可能。
- ポートフォリオ構築モジュール
  - portfolio_builder.py: 候補選定 (select_candidates) / 等金額配分 (calc_equal_weights) / スコア加重配分 (calc_score_weights) を追加。  
    - スコア全0 の場合は等金額配分へフォールバックし、警告を出力。
  - risk_adjustment.py: セクター集中制限 (apply_sector_cap) と市場レジーム乗数 (calc_regime_multiplier) を追加。  
    - セクター上限超過時に当該セクターの新規候補を除外。unknown セクターは制限を適用しない。
    - レジームに応じた投下資金乗数を返す（bull/neutral/bear 対応、未知レジームはフォールバック）。
  - position_sizing.py: 株数決定ロジックを追加。  
    - risk_based / equal / score の各配分方式に対応。
    - 単元株 (lot_size)、コストバッファ、per-position / aggregate cap、スケールダウンと残差処理（lot 単位で追加配分）を実装。
- 研究（Research）モジュール
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算を実装。DuckDB の prices_daily / raw_financials を参照して SQL ベースで計算。
    - mom_1m/3m/6m、MA200 乖離、ATR20、相対 ATR、20日平均売買代金などを算出。
  - research/feature_exploration.py: 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ、ランク化ユーティリティを実装。外部ライブラリに依存せず標準ライブラリのみで処理。
  - research.__init__ により主要関数を公開。
- AI ニュース NLP モジュール
  - ai/news_nlp.py: raw_news を OpenAI API (gpt-4o-mini) でセンチメント解析し ai_scores テーブルへ書き込むためのロジックを追加。設計上の主な機能:
    - タイムウィンドウ計算（JST 基準の前日 15:00 〜 当日 08:30 を UTC に変換）。
    - 銘柄ごとに記事を集約しトークン肥大化対策（記事数・文字数でトリム）。
    - 最大バッチサイズ 20、JSON Mode 期待のレスポンス検証、スコア ±1.0 にクリップ。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ。
    - 部分失敗時の既存スコア保護のため、対象コードのみを置換する更新戦略を採用。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。CLI から期間指定が可能。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を集計し、PASS/FAIL 判定（閾値はファイル内で定義）。
    - DB が存在しない場合のメッセージや、SQLite 接続時の例外サニタイズを実装。
- ユーティリティ
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。  
    - Windows / POSIX の差分を吸収し、アクセス権限等の失敗時は警告を出してスキップ。
    - set_process_priority(level) / set_cpu_affinity(cpu_count) を提供。
- DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視テーブルの存在を保証する処理を run_execution と run_monitoring に追加（冪等）。

### Changed
- パッケージメタ情報
  - __init__.py に __version__="0.1.0" を追加してバージョン管理を導入。
  - package の __all__ を整備して主要サブパッケージを公開。

### Fixed
- 環境変数・.env 取り扱いの強化
  - _parse_env_line により export 形式やクォート内のバックスラッシュエスケープ、行内コメントの扱いを改善。これにより .env の柔軟性と堅牢性を向上。

### Notes / その他
- 設計方針として、以下を意図的に遵守:
  - 本番発注ロジックと研究/解析ロジックを分離（DuckDB を研究用に利用し、ExecutionEngine はブローカーを通じた実取引を想定）。
  - データベースパスや API キー等の機密情報は環境変数で管理し、.env 自動読み込みを OS 環境変数を破壊しない形で実行。
  - 外部依存（psutil, duckdb, openai など）に対しては失敗時にフェールセーフ（警告ログ・スキップ）する実装を行い、運用の安定性を優先。

もしこの CHANGELOG に追記・修正したい点があれば、どの箇所をどう変更したいかを教えてください。