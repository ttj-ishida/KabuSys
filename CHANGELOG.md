# Changelog

すべての注目すべき変更はここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

- リリースポリシー: 変更はセマンティックバージョニングに従います。
- 日付: リリース日が不明な場合は省略しています（本ファイルはコードベースから推測して作成しています）。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-17

Added
- コア機能
  - パッケージ初期化（kabusys）とバージョン管理（__version__ = "0.1.0"）を追加。
  - Settings クラスによる環境変数ベースの設定管理を実装。
    - 自動 .env 読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env/.env.local の優先順制御（OS 環境変数の保護機構あり）。
    - 各種設定プロパティを提供（J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 環境種別等）。
    - 一部設定で入力検証（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）を実装。

- 実行関連
  - run_execution.py：ExecutionEngine を起動するエントリポイントを追加。
    - プロセス優先度を「high」に設定する処理を起動時に実行。
    - Paper Trading 環境では専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動し、スレッドで実行。停止フラグ検出で安全に停止。
    - RiskManager のデフォルト構成（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 閾値, max_drawdown 等）を導入。
    - PID ファイルの扱いと停止フラグ（data/stop_requested.flag）の監視を実装。

- 監視関連
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。不正値は警告後デフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視データを記録（意図的な挙動）。
    - プロセス優先度設定・停止フラグ検出・例外ハンドリングを備えたループ。

- データベース / 分析
  - DuckDB と SQLite を組み合わせてデータ処理・分析基盤を提供（各モジュールで接続を受け取る設計）。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder.py
    - select_candidates(): BUY シグナルをスコア降順・タイブレークは signal_rank でソートして上位 N を選択。
    - calc_equal_weights(), calc_score_weights(): 等金額配分とスコア加重配分を実装。全スコアが 0 の場合は等金額にフォールバック（警告）。
  - risk_adjustment.py
    - apply_sector_cap(): 既存保有を基にセクター集中上限(max_sector_pct)をチェックし、上限超過セクターの新規候補を除外。unknown セクターは除外しない仕様。
    - calc_regime_multiplier(): 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知のレジームは警告のうえ 1.0 でフォールバック。
  - position_sizing.py
    - calc_position_sizes(): allocation_method（risk_based / equal / score）に応じた株数算出を実装。
      - risk_based: リスク許容率（risk_pct）・ストップロスで株数を決定。
      - equal/score: 重みに基づく配分、per-position 上限・aggregate cap を考慮。
      - 単元株（lot_size）で丸め、コストバッファ(cost_buffer)を考慮した保守的見積り。
      - aggregate cap 超過時はスケールダウンし、切り捨て後の端数は残余キャッシュで lot 単位の再配分を行う（再現性確保のため安定ソート）。
    - 中間計算で 0 価格など欠損がある場合はスキップする設計。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research.py
    - calc_momentum(): 1M/3M/6M リターン、MA200 乖離率を DuckDB 上の prices_daily から計算。データ不足時は None。
    - calc_volatility(): ATR(20) / ATR% / 20日平均売買代金 / 出来高比を計算。true_range の NULL 伝播を厳密に扱う。
    - calc_value(): raw_financials と prices_daily を組み合わせて PER/ROE を算出（target_date 以前の最新財務データを取得）。
  - feature_exploration.py
    - calc_forward_returns(): 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。horizons の妥当性検査あり。
    - calc_ic(): ファクター値と将来リターンの Spearman ランク相関（IC）を計算。有効レコード 3 未満は None を返す。
    - rank(), factor_summary(): ランク変換（同順位は平均ランク）と基本統計量サマリを実装（None 値は除外、数値の有限性チェックあり）。
  - research パッケージは zscore_normalize（kabusys.data.stats から）などと合わせて分析ワークフローを構成。

- AI / ニュース NLP（kabusys.ai.news_nlp）
  - ニュース記事を OpenAI（gpt-4o-mini）でセンチメント解析し、銘柄別スコアを ai_scores テーブルへ書き込むためのスケルトンを実装。
    - ニュース集計ウィンドウ計算（JST ベース → UTC 変換）を実装（calc_news_window）。
    - バッチ処理設計（1 API コールで最大 20 銘柄）、トークン肥大化対策（記事数・文字数の上限）を導入。
    - リトライポリシー（429/ネットワーク/5xx 共通の指数バックオフ、最大リトライ回数指定）とレスポンスバリデーション方針を明記。
    - スコアは ±1.0 にクリップし、部分失敗時に既存スコアを保護するため対象コードに絞って置換（DELETE → INSERT）する運用方針を明記。
    - API キー解決（引数優先、なければ OPENAI_API_KEY 環境変数）と未設定時に例外。

- ツール
  - tools/paper_verification_report.py：Paper Trading 用検証レポート生成 CLI を追加。
    - 引数で期間指定 (--from / --to) と DB パス指定 (--db) をサポート。環境変数 PAPER_TRADING_SQLITE_PATH とデフォルトパス（data/paper_trading.db）による解決。
    - システム安定性（稼働率・エラー数）、注文統計（Created/Filled/Sent）、リスク却下数、レイテンシ（avg/max/P95）を集計して判定（PASS/FAIL）を出力。
    - P95 は標本抽出で計算（_p95）、閾値はソースで定義（稼働率 99.0%, 成立率 90.0% 等）。
    - DB テーブルが存在しない場合やクエリエラー時は graceful に N/A や 0 を使って継続。

- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム差を吸収したプロセス優先度設定（Windows の priority class / POSIX の nice 値）。
    - set_cpu_affinity() を実装してプロセスを最初の N コアにピン固定可能。入力検証と例外ハンドリング（権限不足など）あり。
    - 未対応 OS や権限不足の場合は警告を出してスキップするフェイルセーフ。

Changed
- 設定・環境読み込みの挙動を明確化
  - .env の自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
  - .env のパースはクォート・エスケープ・インラインコメントに対応（より柔軟な .env 記述を許可）。

Fixed
- 実行中・監視処理の堅牢性向上
  - run_monitoring のポーリング中に check_once() が例外を投げてもループを継続するように例外ハンドリングを追加。
  - run_execution が停止フラグを検出した場合、安全にエンジン停止処理を呼ぶよう改善。

Notes / 既知の制限
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある旨の TODO コメントあり（将来的に前日終値等でフォールバック予定）。
- ai/news_nlp.py:
  - 実装は堅牢化方針（バッチ/リトライ/検証）を含むが、ソースの末尾で処理が途中で切れている箇所があるため（ここで提供されたコード断片では）完全実行可能な状態ではない可能性あり。API 呼び出し周りの詳細実装・エラーハンドリングの追加が想定される。
- set_process_priority / set_cpu_affinity:
  - 権限不足や未対応プラットフォームの場合、処理は警告を出してスキップする設計。運用環境での動作確認が必要。
- run_monitoring:
  - 監視は常に本番 sqlite_path を使用する設計（意図的）。テストや paper_trading 実行時の注意が必要。

---

（この CHANGELOG は提供されたコード内容から推測して作成しています。実際のリリースノートとして使用する場合は、日付や影響範囲、破壊的変更の有無などをプロジェクトの運用方針に合わせて調整してください。）