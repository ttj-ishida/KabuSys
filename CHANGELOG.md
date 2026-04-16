# Changelog

すべての重要な変更は Keep a Changelog の慣習に従って記述しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、本 CHANGELOG は与えられたソースコードの内容から推測して作成したもので、実際のコミット履歴とは差異がある可能性があります。

## [Unreleased]

### Added
- ニュースNLP スコアリングの骨組みを追加（kabusys/ai/news_nlp.py）。
  - OpenAI (gpt-4o-mini) を用いた銘柄別センチメント scoring の設計を実装。
  - バッチ処理、トークン肥大化対策、スコアクリッピング、エクスポネンシャルバックオフ等の仕様を定義。
  - ニュース集計ウィンドウ計算ユーティリティ calc_news_window を追加。

### Changed
- なし（Unreleased のため変更点は現状仕様/追加のみ）

### Fixed
- なし

### Notes / WIP
- kabusys/ai/news_nlp.py は途中で切れている（処理の途中でソースが終端しているため、完全実装は未完）。実運用前に残りの処理（記事フェッチ、API 呼び出し、DB 書き込みなど）を実装・テストする必要あり。

---

## [0.1.0] - 2026-04-16

初回公開リリース（推定）。以下はこのコードベースで提供される主要機能と修正点です。

### Added
- 実行用エントリポイント
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite DB を使用し、本番 DB と分離（`PAPER_TRADING_SQLITE_PATH`）。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading 時は MockBrokerClient を使用する想定）。
    - 停止フラグ / PID ファイル対応（data/stop_requested.flag, data/execution.pid）。
    - スレッドで ExecutionEngine を起動し、安全に停止を監視するループを実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、不正値は警告してフォールバック）。
    - 監視処理は環境に関わらず本番用 sqlite_path を使用する旨の挙動。

- 設定・環境管理
  - kabusys/config.py: Settings クラスを実装。
    - .env / .env.local の自動ロード機能（OS 環境変数は保護、`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
    - 必須環境変数取得のヘルパー `_require()`。
    - 多数のプロパティ（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定等）を提供。
    - PAPER_FILL_MODE の入力検証とデフォルト値。
    - `paper_sqlite_path`（paper trading 用 DB）プロパティ。

- ポートフォリオ構築関連（純粋関数群）
  - kabusys/portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア順選択（タイブレーク: signal_rank）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（全スコア 0 の場合は等配分にフォールバック）。
  - kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター別エクスポージャーに基づく候補除外ロジック。unknown セクターは上限適用除外。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear 辺りのマッピング）。
  - kabusys/portfolio/position_sizing.py
    - calc_position_sizes: 複数の割当方式（risk_based / equal / score）をサポート。
    - lot_size（単元）丸め、per-stock 上限（max_position_pct）適用、aggregate cap に基づくスケーリング、cost_buffer（手数料・スリッページ考慮）対応。
    - スケーリング後の残差配分ロジック（fractional remainders を lot 単位で解消）。

- 実用ユーティリティ
  - kabusys/utils/process_priority.py
    - プロセス優先度設定ユーティリティ（Windows / POSIX 差分吸収）。set_process_priority, set_cpu_affinity を提供。
    - 権限不足や未対応 OS の場合は警告してスキップする堅牢設計。

- リサーチ / ファクター計算
  - kabusys/research/factor_research.py
    - calc_momentum, calc_volatility, calc_value を実装（DuckDB 接続を受け prices_daily / raw_financials を参照）。
    - 各種窓幅や欠損ハンドリング（十分な過去データがない場合は None）。
  - kabusys/research/feature_exploration.py
    - calc_forward_returns: 将来リターンをホライズン単位で計算。
    - calc_ic: スピアマンランク相関（IC）計算。レコード不足時は None を返す。
    - rank, factor_summary: ランク付け、基本統計量サマリ。

- ツール
  - kabusys/tools/paper_verification_report.py
    - Paper Trading 検証レポート生成 CLI を追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ等を集計し PASS/FAIL 判定を行う。
    - CLI オプション: --from, --to, --db（PAPER_TRADING_SQLITE_PATH 環境変数で代替可）。
    - デフォルトしきい値（稼働率 99%、P95 <= 200ms 等）を定義。

- パッケージ初期化
  - kabusys/__init__.py にバージョン定義 (__version__ = "0.1.0") とエクスポート一覧を追加。

### Changed
- なし（初期リリース想定）

### Fixed
- なし（初期リリース想定）

### Security
- 環境変数の取り扱いにおいて OS の既存環境変数を保護する設計を採用（.env のロードで protected set を使用）。

### Notes / Implementation details
- DuckDB を利用した分析コンポーネント（research・AI）と、SQLite を監視/発注ログ用に併用する二層構成。
- run_monitoring と run_execution は起動時にプロセス優先度を high に設定する仕組みを採用（set_process_priority）。
- Paper Trading 環境では DB を分離し、本番 DB への影響を避ける設計。
- 各計算関数は DB を直接更新せず純粋関数的に結果を返す方針（テスト性を重視）。
- 一部コードに TODO / 注意コメントあり（価格欠損時のフォールバック、将来的な lot_size per-stock 対応など）。

---

今後の TODO / 注意点（コードからの推測）
- kabusys/ai/news_nlp.py は未完（ファイルが途中で切れている）。API 呼び出し→レスポンス検証→DB 書き込みの実装・テストが必要。
- position_sizing の将来的拡張点として銘柄別 lot_size 情報の導入（現状は全銘柄共通の単元扱い）。
- apply_sector_cap は price_map に欠損 (0.0) があると過少見積もりになるため、フォールバック価格の導入検討がコメントされている。
- 自動 .env ロードはプロジェクトルート検出に依存する（.git / pyproject.toml）。配布後の挙動確認が必要。

---

参考: バージョンはソース内の __version__ に基づき 0.1.0 と推定しています。必要であれば実際のコミット履歴に即した修正・日付調整を行ってください。