# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
バージョン付けは semantic versioning を想定しています。

## [Unreleased]

### Added
- ドキュメント化されているいくつかの TODO / 改善候補を記載（今後の対応予定）。
  - position_sizing: 将来的な銘柄別 lot_size サポートの設計メモ。
  - risk_adjustment: price 欠損時のフォールバック価格（前日終値等）利用の検討。

### Changed
- MONITOR_POLL_INTERVAL の扱いに関するログ・検証を強化する予定（不正値はデフォルトにフォールバック）。

### Known issues
- ai/news_nlp モジュールの末尾が途中で切れている（処理続きが未実装／ファイル断端）。OpenAI 呼び出し後の記事集約以降の処理が未完。安全策として現状では未完成部分はスキップされることを想定。
- DuckDB の executemany に関する注意（空パラメータの扱い）あり — 部分失敗時の保護ロジックが実装要検討。

---

## [0.1.0] - 2026-04-16

初回リリース。以下の主要機能と実装を含みます。

### Added
- 基本パッケージ情報
  - パッケージバージョン定義: __version__ = "0.1.0"

- 設定管理 (kabusys.config)
  - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
  - .env パースの強化:
    - export プレフィックス対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - インラインコメント（クォートなし・直前に空白がある場合）対応。
  - 必須環境変数検査 helper (_require)。
  - 各種設定プロパティ:
    - J-Quants / kabu API / LINE 設定
    - DB パス (DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH)
    - 監視・PID・kill flag のパス
    - CPU/MEM/DISK 閾値
    - 環境判定（development / paper_trading / live）と log level 検証

- 実行エントリ・監視エントリ
  - run_execution:
    - ExecutionEngine の起動ラッパー。paper_trading 環境では paper DB に分離。
    - BrokerClientFactory 経由でブローカークライアント生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立ててエンジンを起動。
    - 停止フラグ（data/stop_requested.flag）検知による優雅な停止。
    - PID ファイル管理（data/execution.pid）。
    - RiskManager のデフォルトパラメータを明示的に設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）。
  - run_monitoring:
    - SystemMonitor の単純ポーリングループ起動スクリプト。
    - 環境にかかわらず監視は本番 sqlite_path を使用する設計。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 停止フラグ検知処理。
    - 起動時にプロセス優先度を high に設定。

- データベース初期化
  - monitoring 用テーブルを初期化する init_monitoring_db 呼び出し（冪等）。

- ユーティリティ
  - process_priority:
    - クロスプラットフォームでプロセス優先度設定（Windows の PRIORITY_CLASS、POSIX 系の nice 値）。
    - CPU affinity 固定セット関数 (set_cpu_affinity) を提供。
    - 権限不足や未対応環境での安全なフォールバック/ログ。

- Portfolio コンポーネント (kabusys.portfolio)
  - portfolio_builder:
    - BUY シグナルの候補選定（スコア降順、同点時は signal_rank）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全てのスコアが 0 の場合は等金額配分にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限ロジック（既存保有時価ベースでセクター上限に達している場合に新規候補を除外）。
    - calc_regime_multiplier: market regime に応じた資金乗数（bull/neutral/bear -> 1.0/0.7/0.3、未知レジームは 1.0 でフォールバック）。
    - 「unknown」セクターはセクター上限の対象外という設計。
  - position_sizing:
    - calc_position_sizes: allocation_method (risk_based / equal / score) に基づく発注株数算出。
    - リスクベースの算出（risk_pct, stop_loss_pct を使用）。
    - lot_size（現状は全銘柄共通）に基づく丸め処理。
    - aggregate cap（利用可能現金を超える場合のスケールダウン）と残差処理（lot 単位で再配分）。
    - cost_buffer による保守的なコスト見積り。

- Research / ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比を計算。
    - calc_value: PER, ROE（raw_financials と prices_daily 組合せ）。
    - DuckDB を用いた SQL ベースの実装（prices_daily/raw_financials）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算。
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算。
    - rank: 同順位の平均ランク処理を含む安定したランク関数。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - research パッケージ公開 API を整備（zscore_normalize は外部モジュールからインポートして公開）。

- ツール
  - paper_verification_report:
    - Paper Trading 用の検証レポート生成スクリプト（CLI）。
    - 検証基準を定義（稼働率、注文成功率、送信率、P95 レイテンシ）と PASS/FAIL 判定ロジック。
    - SQLite DB（デフォルト data/paper_trading.db）から各種統計を集計してコンソール出力。
    - 日付フィルタ（--from / --to）および --db オプション対応。

- AI ニュース NLP (部分実装)
  - ai/news_nlp:
    - raw_news を銘柄別に集約し OpenAI（gpt-4o-mini）にバッチ送信して ai_scores テーブルへ書き込む設計を導入。
    - バッチサイズ、最大記事数、最大文字数、タイムウィンドウ計算（JST基準→UTC変換）を実装。
    - API 呼び出しのリトライ（429/ネットワーク/5xx）と指数バックオフ方針を実装。
    - レスポンスの JSON バリデーション、スコアの ±1.0 クリップ、部分置換（削除→挿入）による更新戦略を採用。
    - 注意: ファイル末尾が途中で切れているため、完全な実行パスは未完。

### Changed
- 開発設計において「監視は環境に依存せず本番 sqlite_path を使用する」方針を明確化（run_monitoring）。
- run_execution は paper_trading 環境での DB 分離を明確に実装（settings.is_paper を参照）。

### Fixed
- .env パースの不正入力対策を強化（不正な行はスキップ、クォート内エスケープ処理、コメント処理の改善）。
- MONITOR_POLL_INTERVAL の不正値検出時にログで警告しデフォルトへフォールバックする挙動を導入。
- process_priority の未対応 OS / 権限エラー時に例外を送出せずログ警告で安全にスキップするよう改善。

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キー未設定時は明示的に例外を投げる（ai/news_nlp）ことで誤操作を防止。

---

注記:
- ソース内に複数の TODO / 注意書き（price 欠損時の取扱い、将来の拡張点、DuckDB executemany の注意等）があるため、運用上の注意点としてデプロイ時に確認してください。
- ai/news_nlp の未完部位はリリース運用前に実装完了・テストが必要です。