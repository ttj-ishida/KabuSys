# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

## [Unreleased]

（現在のスニペットでは未リリース／未確定の事項はありません。AI ニュース NLP モジュールの一部が与えられたコード断片で途中切れになっているため、実装完了・追加の調整を行う可能性があります。）

---

## [0.1.0] - 2026-04-17

初回公開リリース。主な追加機能・実装内容は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンを `0.1.0` として定義（src/kabusys/__init__.py）。

- 実行・監視エントリポイント
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加（src/kabusys/run_execution.py）。
    - BrokerClientFactory によるブローカークライアント抽象化を利用。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite DB を使用して本番 DB と分離（PAPER_TRADING_SQLITE_PATH）。
    - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag による外部停止制御を実装。
    - プロセス優先度を起動時に "high" に設定する呼び出しを追加。
    - 監視テーブルの冪等的初期化（init_monitoring_db）を実行。
    - 実行 PID 管理のための pid_file 用意（data/execution.pid デフォルトパス）。

  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトへフォールバック）。
    - 監視プロセスは環境にかかわらず本番 sqlite_path を使用して監視データを一元管理。
    - data/stop_requested.flag による停止、KeyboardInterrupt による正しいクリーンアップを実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定・環境変数管理
  - Settings クラスを追加（src/kabusys/config.py）。
    - .env ファイル自動読み込み（プロジェクトルートを .git や pyproject.toml から検出）。
    - 読み込み順: OS 環境 > .env.local（上書き）> .env（未設定時に補完）。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env の行パーサは `export KEY=val` 形式、クォート文字列、インラインコメント処理などをサポート。
    - 各種プロパティを提供: J-Quants / kabu API / LINE / DB パス / PID/kill flag パス /閾値設定（CPU/MEM/DISK） / 環境（development/paper_trading/live）/ログレベル等。
    - PAPER_FILL_MODE のバリデーション（instant|partial|never|reject）。
    - env/log_level の値検査（不正値で ValueError を送出）。

- モニタリング DB 初期化ユーティリティ
  - init_monitoring_db 呼び出しにより監視用テーブルが存在することを保証（冪等処理）。

- Portfolio（銘柄選定・配分・株数決定）
  - portfolio_builder:
    - select_candidates: BUY シグナルのソート（score 降順、signal_rank タイブレーク）と上位 N 選出。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算し、max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた投下資金乗数を返す（未知レジームは 1.0 でフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注株数決定を実装。
      - risk_based: ポジションあたりリスクベースで株数算出（risk_pct, stop_loss_pct を使用）。
      - equal/score: weight を用いた配分。per-position および aggregate（available_cash）上限を考慮。
      - 単元（lot_size）丸め、cost_buffer による保守的コスト見積り、aggregate cap 超過時のスケーリングと端数再配分ロジックを実装。
      - price 欠損時はスキップする旨のロギング。

- 研究（research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率を DuckDB の prices_daily から算出。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比を計算（欠損ハンドリングを含む）。
    - calc_value: raw_financials と prices_daily を結合し PER/ROE を算出（target_date 以前の最新財務レコード取得）。
    - いずれの関数も DuckDB 接続を受け取り SQL ベースで計算。外部 API や pandas 等に依存しない設計。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）を一括取得する SQL 実装（horizons 検証あり）。
    - calc_ic / rank: スピアマンランク相関（IC）計算、ランク処理（同率は平均ランク）。
    - factor_summary: 各カラムの基本統計（count, mean, std, min, max, median）を標準ライブラリで実装。

- ツール
  - tools/paper_verification_report:
    - Paper Trading の検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - DB（デフォルト data/paper_trading.db）からシステム安定性、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計。
    - 判定基準（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し PASS/FAIL 判定を出力。
    - P95 計算や日付フィルタを実装。コマンドライン引数 --from/--to/--db をサポート。

- AI ニュース NLP（OpenAI 連携）
  - ai/news_nlp:
    - raw_news と news_symbols を集約し、銘柄ごとにテキストをトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）して OpenAI（gpt-4o-mini）にバッチ送信してセンチメント（-1.0〜1.0）を取得。
    - バッチサイズ、JSON Mode による厳密なレスポンス検証、429/ネットワーク/5xx に対する指数バックオフリトライ、スコア ±1.0 のクリップを実装。
    - タイムウィンドウ計算ユーティリティ calc_news_window（JST 基準の前日 15:00 ～ 当日 08:30 を UTC に変換）を追加。
    - API キー未設定時に ValueError を送出する明示的チェックを実装。

- ユーティリティ
  - process_priority:
    - set_process_priority(level): Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を設定。アクセス権限不足時は警告でスキップ。
    - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアにピン留めする機能（引数検証あり）。権限不足や未対応環境では警告でスキップ。

### Changed
- （該当なし：初回リリースのため新規実装が中心）

### Fixed
- （該当なし：初回リリース）

### Removed
- （該当なし）

### Security
- OpenAI API キー未設定時に明示的にエラーを出すことで誤った無認証呼び出しを防止。

### Notes / Known limitations / TODOs
- apply_sector_cap のコメントにある通り、price が欠損（0.0）の場合はエクスポージャーが過小見積もられる可能性があるため将来的にフォールバック価格（前日終値等）を導入する検討が必要。
- position_sizing は現状単元株数 lot_size を全銘柄共通で想定している。将来的には銘柄別 lot_map を受け取る拡張予定。
- ai/news_nlp のコードスニペットは与えられたソースの最後が途中で切れている（ファイル末尾が不完全に見える）ため、実装の残り部分（記事抽出関数の後続処理や最終的な DB 書き込み部分）が抜けている可能性がある。完全な実装・統合テストを推奨。
- research モジュールは DuckDB のテーブル構造（prices_daily, raw_financials 等）に依存するため、実データロードと照合した追加のバリデーションが必要。

---

この CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴やリリースノートが存在する場合は、そちらに合わせて補正してください。