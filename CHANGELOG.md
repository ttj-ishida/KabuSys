# CHANGELOG

すべての注目すべき変更履歴をこのファイルに記載します。  
フォーマットは「Keep a Changelog」準拠です。

注: 本ファイルはコードベースから推測して自動生成されています。実際のリリース履歴や日付は適宜調整してください。

## [Unreleased]

- 特になし（次回リリースに向けての変更は未確定）

## [0.1.0] - 2026-04-17

初期リリース（推定）。以下の主要機能・モジュールを追加しました。

### Added
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - パッケージ公開用のモジュールエクスポート（data, strategy, execution, monitoring）。

- 設定・環境読み込み（kabusys.config）
  - .env / .env.local ファイルの自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を導入。
  - `.env` のパース強化:
    - export プレフィックス対応（`export KEY=val`）。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - 行内コメントの取り扱い（クォート有無での挙動差異）。
  - 必須環境変数取得ヘルパ `_require` を導入（未設定時に分かりやすい例外メッセージ）。
  - Settings クラスを導入し、アプリケーション全体の設定を提供（DBパス、APIトークン、監視閾値、環境判定等）。
  - 環境値バリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。

- 実行・監視用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - Paper Trading 環境（KABUSYS_ENV=paper_trading）では専用の SQLite（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）を使用して本番 DB と完全分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（paper 環境では Mock を想定）。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine を組み立ててセッションをスレッドで実行。stop flag による優雅な停止機構。
    - デフォルトの RiskConfig パラメータを設定（max_position_pct=0.20 等）および初期 portfolio value に broker.get_available_cash() を利用。
    - PID ファイル / stop flag パスを使用。

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はログ警告のうえデフォルトへフォールバック。
    - 監視処理は環境にかかわらず本番用の sqlite_path を使用する設計。
    - stop flag ファイル検知による監視ループの停止および例外ハンドリングを実装。

- データベース連携
  - SQLite と DuckDB の両方に接続するユーティリティ的な使用パターンを導入（init_monitoring_db を呼んで監視テーブルを保証）。
  - DuckDB を用いた分析 / 研究処理のための接続整備。

- ユーティリティ
  - process_priority モジュールを追加:
    - プラットフォーム抽象化を行い Windows / POSIX（Linux, Darwin, FreeBSD）でプロセス優先度（nice / HIGH_PRIORITY_CLASS）設定を提供。
    - CPU affinity 設定関数 set_cpu_affinity を追加（第一 N コアにピン留め）。
    - 権限不足や未対応 OS に対する安全なフォールバック（ログ警告）。
  - 環境変数に基づく細かな監視閾値（CPU/MEM/DISK）や PID/KILL フラグ関連設定を Settings で提供。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で上位 N を返す。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア比率で重みを計算。全スコアが 0 の場合は警告して等配分へフォールバック。
  - risk_adjustment:
    - apply_sector_cap: セクター集中度に基づく候補除外ロジックを実装（売却予定銘柄を除外して既存エクスポージャを計算）。"unknown" セクターは制限適用除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を返す（未知レジームは 1.0 で警告）。
  - position_sizing:
    - calc_position_sizes: 重み／候補／リスクパラメータ等から各銘柄の発注株数を算出。
    - リスクベース（risk_based）および equal/score アロケーションに対応。
    - 単元株（lot_size）で丸め、per-position 上限、aggregate cap（available_cash）によりスケールダウンするアルゴリズムを実装。
    - cost_buffer（スリッページ・手数料見積り）を考慮した保守的見積りと、残余キャッシュにより端数をlot単位で再配分するロジックを実装。
    - price 欠損時のスキップやデバッグログを用意。
    - 将来的拡張として銘柄別 lot_size（TODO）や価格フォールバックの注釈を残す。

- 研究（research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンおよび MA200 乖離を DuckDB の prices_daily から計算。
    - calc_volatility: ATR20、相対ATR、20日平均売買代金、出来高比などを計算。true_range の NULL 伝播を適切に扱う実装。
    - calc_value: raw_financials と prices_daily を組み合わせて PER, ROE を算出（target_date 以前の最新決算を取得）。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズンの将来リターンを一度のクエリで取得。horizons 引数のバリデーションあり。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。有効レコード数 3 未満で None を返す。
    - rank: 同順位は平均ランクとする実装（丸めによる ties 検出の対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ関数（None を除外）。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI API（gpt-4o-mini 想定）を使ったニュース記事のセンチメントスコアリング機能を追加。
  - ニュース収集ウィンドウ計算（JST 基準 → UTC 変換）を提供（calc_news_window）。
  - score_news 関数で:
    - raw_news と news_symbols から銘柄ごとに記事を集約（記事数・文字数のトリム）。
    - 最大バッチサイズ、再試行ポリシー（エクスポネンシャルバックオフ）、429/5xx/ネットワークエラーのリトライ対応。
    - レスポンス検証、スコアの ±1.0 クリップ、部分更新（対象コードのみ置換）で部分失敗耐性を確保。
  - 実装は API キー（引数または環境変数 OPENAI_API_KEY）を必要とする。失敗時は例外で明確に通知。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成 CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計。
    - デフォルト閾値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 200ms）を定義し Pass/Fail 判定を行う。
    - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数）をサポート。
    - DB テーブル欠如やデータ不足時のフェイルセーフ処理（OperationalError を捕捉して N/A を返す）。

### Changed
- なし（初期リリースに該当するため、過去バージョンからの「変更」は特になし）。

### Fixed
- なし（初期リリース）。

### Deprecated
- なし。

### Removed
- なし。

### Security
- OpenAI API キーや各種トークンは Settings 経由で環境変数から取得する設計。機密情報はコードにハードコードしない方針を明記。

---

補足（コード内の注意点・今後の改善候補）
- apply_sector_cap の価格欠損時（price == 0.0）によりエクスポージャが過小評価される可能性があるため、将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO コメントあり。
- position_sizing は現状全銘柄共通の lot_size（デフォルト 100）を想定。将来的な拡張として銘柄別 lot_map を受け取る案あり。
- news_nlp のファイル末尾が途中で切れている（このCHANGELOGは公開されているコードの内容を基に作成）。実装の残り部分（_fetch_articles 等）がある前提で設計されている。
- 自動 .env ロードは便利だが、テストや CI での指定に `KABUSYS_DISABLE_AUTO_ENV_LOAD` を用意して制御可能。

以上がコードベースから推測したリリースノート（CHANGELOG）です。実際のコミット履歴やリリースノートが存在する場合は、本CHANGELOGをベースに適宜修正してください。