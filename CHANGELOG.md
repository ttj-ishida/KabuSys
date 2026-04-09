# Changelog

すべての変更は Keep a Changelog の規約に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

このリポジトリは semantic versioning を採用しています。

## [Unreleased]

## [0.1.0] - 2026-04-09
初回リリース。自動売買システム「KabuSys」のコア機能を実装した最初のバージョン。

### Added
- パッケージ初期化
  - kabusys.__version__ = 0.1.0 を導入。公開モジュール一覧 (__all__) を定義。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込みを実装。
  - プロジェクトルート検出機能を追加（.git または pyproject.toml を探索）。CWD に依存しない自動ロード。
  - .env のパース機能を実装（export プレフィックス対応、シングル/ダブルクォート、エスケープ、インラインコメント対応）。
  - ロード優先順位: OS 環境変数 > .env.local > .env（.env.local は上書きモード）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - Settings クラスを提供し、各種必須/省略可能設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - データベースパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
    - Paper Trading の動作モード（PAPER_FILL_MODE）のバリデーション（instant/partial/never/reject）
    - 監視関連（PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/MEM/DISK 閾値）
    - 環境種別（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーションおよびヘルパー is_live/is_paper/is_dev

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順、タイブレークに signal_rank を使用して上位 N 件を選択。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等金額にフォールバック（WARNING ログ）。
  - risk_adjustment:
    - apply_sector_cap: セクターごとの既存エクスポージャーを算出し、max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を提供（bull/neutral/bear → 1.0/0.7/0.3）。未知レジームは 1.0 にフォールバック（WARNING ログ）。
  - position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数算出を実装。
      - risk_based: 許容リスク率 (risk_pct) と stop_loss_pct から目標株数を算出し単元 (lot_size) に丸め。
      - equal/score: weight に基づく配分、max_position_pct / max_utilization を考慮。
      - aggregate cap: 全銘柄コストが利用可能現金を超える場合にスケールダウンし、単元単位の再配分ロジック（端数処理）を実装。
      - cost_buffer により手数料・スリッページを保守的に見積もる。

- 研究（ファクター計算・特徴量探索） (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離 (ma200_dev) を DuckDB の prices_daily から計算。
    - calc_volatility: 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金 (avg_turnover)、出来高比率 を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（最新財務レコードを target_date 以前から取得）。
    - 各関数はデータ不足時に None を返す等の安全処理を実装。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズンの将来リターンを一度のクエリで取得（horizons の検証・上限 252 日）。
    - calc_ic: Spearman（ランク）相関による IC 計算。データ不足（有効レコード < 3）時は None。
    - rank: 同順位は平均ランクにするランク付けユーティリティ（丸めによる ties 検出漏れ対策あり）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出。

- AI 関連 (kabusys.ai)
  - news_nlp:
    - raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）でセンチメントを算出し ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算 calc_news_window（JST を基準に UTC 変換）。
    - バッチ処理（1 API コールで最大 _BATCH_SIZE=20 銘柄）、1銘柄あたり記事本数/文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - JSON Mode を意識したレスポンスバリデーション、数値化と ±_SCORE_CLIP（±1.0）でのクリップ。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ（最大 _MAX_RETRIES）。
    - DB 書き込みは冪等的に: 対象コードを限定して DELETE → INSERT（部分失敗時に他コードを保護）。DuckDB executemany の空リスト制約に対応。
    - API キーが未設定の場合は ValueError を送出。API 失敗時はスキップして継続するフェイルセーフ設計。
  - regime_detector:
    - ETF 1321 の ma200 乖離とマクロニュース（キーワード）を合成して市場レジームを判定。
    - マクロニュース評価は独立した LLM 呼び出しで実施、API 失敗時は macro_sentiment=0.0 としてフォールバック。
    - 判定ロジック: ma200 の寄与度 70%、マクロ 30%、スコアを -1..1 にクリップし閾値で bull/neutral/bear を決定。
    - 判定結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - look-ahead バイアス防止の設計（target_date 未満のデータのみ使用、datetime.today()/date.today() を参照しない）。

- 監視ログ永続化 (kabusys.monitoring.monitoring_db)
  - SQLite ベースの MonitoringDB 初期化スクリプトを追加（system_status, trade_logs, positions, risk_logs などのテーブル定義とインデックス作成）。冪等にテーブル作成。

- モジュール公開 API
  - kabusys.portfolio、kabusys.research、kabusys.ai などの __init__ を整備し、主要関数を公開。

### Changed
- （初回リリースのため "Changed" は未適用）  

### Fixed
- （初回リリース）.env パーサーや各モジュールで多数の防御的実装を追加:
  - .env のクォート内エスケープ処理、インラインコメント判定、export プレフィックス対応などの細かなパースケースに対応。
  - OpenAI API 呼び出しにおける JSON パース失敗や余分なテキスト混在ケースを補正して復元を試みる処理を追加。
  - DuckDB / SQLite 周りの互換性（executemany の空リスト制約）を考慮した安全な DB 書き込みパスを実装。
  - 各所でデータ不足や例外時に安全なフォールバック（None / 0.0 / 1.0 等）を返すようにして、運用時に例外が全体を停止させない設計とした。

### Security / Reliability
- OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を参照。未設定の場合は明示的に例外を出す箇所と、フェイルセーフで 0.0 を使用して継続する箇所を適切に使い分け。
- datetime.today() / date.today() を参照せず、外部から target_date を渡す設計としてルックアヘッドバイアスを排除。
- ログ出力と警告を多用して不整合やデータ不足を可視化。

### Known limitations / TODO
- position_sizing の lot_size は全銘柄共通（将来的には銘柄別 lot_map を受け取る設計へ）。
- apply_sector_cap は price が欠損 (0.0) の場合にエクスポージャーが過少見積もりとなる可能性がある旨の TODO コメントあり。将来的に価格フォールバックを実装予定。
- 一部の DB スキーマ/インデックスは拡張が想定される（monitoring_db の途中まで実装）。
- external OpenAI SDK の挙動（status_code の有無など）に対する互換性考慮が入っているが、将来の SDK 変更には追加対応が必要。

--- 

注: 上記は現行コードベースから推測して作成した CHANGELOG です。実際のリリースノートとして公開する際は、テスト結果・マイナー調整・ドキュメント追記などの変更を反映してください。