CHANGELOG
=========
すべての注目すべき変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------
（現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-09
-------------------

Added
- 初回公開リリース: KabuSys 0.1.0
  - パッケージメタ情報: __version__ = "0.1.0" を設定。

- 環境設定 / 設定管理 (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト向け）。
  - .env パーサは以下に対応:
    - export KEY=val 形式、シングル／ダブルクォート、バックスラッシュによるエスケープ、インラインコメント処理。
    - 読み込み失敗時は警告を出力して継続。
  - Settings クラスでアプリケーション設定をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD を必須（未設定時は ValueError）。
    - KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID の既定値/空許容。
    - データベースパス: DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH（デフォルト値あり、expanduser 処理）。
    - Paper Trading 用 PAPER_FILL_MODE の検証（instant/partial/never/reject のみ許容）。
    - 監視用設定: PID / KILL フラグパス、kill_flag_clear_on_start、CPU/MEM/DISK 閾値など。
    - 環境種別（KABUSYS_ENV）とログレベル（LOG_LEVEL）の妥当性検証。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- ポートフォリオ構成 (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: BUY シグナルを score 降順、同点時は signal_rank 昇順で上位 N を選択。
    - calc_equal_weights, calc_score_weights: 等金額配分およびスコア加重配分。全スコアが 0 の場合は等金額にフォールバックして WARNING を出力。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた発注株数算出。
    - lot_size（単元）考慮、max_position_pct（銘柄上限）、max_utilization（投下上限）、cost_buffer を考慮した保守的見積り。
    - aggregate cap を超える場合はスケーリングし、余りを lot 単位で残差が大きい銘柄順に再配分するアルゴリズムを実装。
    - price 欠損時はスキップしてログ出力。
  - risk_adjustment:
    - apply_sector_cap: 既存保有のセクター比率が max_sector_pct を超える場合、新規候補を除外（"unknown" セクターは除外しない）。sell_codes をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: レジーム名から投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告とともに 1.0 にフォールバック。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を DuckDB の SQL で算出。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を適切に制御。
    - calc_value: raw_financials から最新の財務データを結合して PER / ROE を計算（EPS 欠損や 0 の場合は None）。
    - すべて DuckDB 接続を受け取り外部 API を呼ばない設計。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて取得。horizons の妥当性チェック。
    - calc_ic: Spearman ランク相関（IC）を算出。有効レコードが 3 件未満なら None。
    - rank, factor_summary: 平均・分散・標準偏差・中央値等の統計要約を提供。None / NaN を除外して集計。
    - pandas 等に依存せず標準ライブラリのみで実装。

- AI 関連 (kabusys.ai)
  - news_nlp:
    - calc_news_window: ニュース収集ウィンドウ計算（JST を UTC naive に変換）。
    - score_news: raw_news と news_symbols から記事を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む。
      - バッチ処理（最大 _BATCH_SIZE=20 銘柄）／1 銘柄あたり最大記事数・文字数制限。
      - OpenAI 呼び出しはリトライ（429, 接続断, タイムアウト, 5xx）、エクスポネンシャルバックオフ。
      - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、型チェック、既知コードのみ取り込み）。
      - スコアを ±1.0 にクリップ。
      - 書き込みは対象コードのみを DELETE → INSERT する方式で冪等性と部分失敗耐性を確保（DuckDB executemany の空リスト制約に対応）。
      - テスト時に _call_openai_api をモックで差し替え可能。
  - regime_detector:
    - score_regime: ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して市場レジームを判定し market_regime テーブルへ冪等書き込み。
      - マクロニュースはキーワードで抽出（複数キーワード、最大件数制限）。
      - LLM 呼び出し失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
      - レジームスコア合成ロジック（重み付け、スケール、閾値判定）を実装。
      - OpenAI 呼び出しはニュース NLP と独立した private 実装で、テスト用の差し替えが可能。

- 監視ログ永続化 (kabusys.monitoring)
  - monitoring_db.init_monitoring_db:
    - SQLite を使った監視ログ用テーブル群（system_status, trade_logs, positions, risk_logs, ...）とインデックスを作成する冪等スクリプトを実装。

Changed / Fixed / Hardening
- DB / SQL 周りの互換性配慮:
  - DuckDB の executemany 空リスト制約を考慮した安全な書き込みロジックを採用。
  - lookahead バイアスを避けるため、prices_daily のクエリは target_date 未満条件や適切なウィンドウ設計を実施。
- API 呼び出しの堅牢化:
  - OpenAI 呼び出しのリトライ/バックオフ、429／ネットワーク断／タイムアウト／5xx に対する扱いを明確化。
  - API レスポンスの JSON パース失敗時に外側の {} を抜き出して復元するフォールバックを実装。
  - API 呼び出し失敗時に例外を投げずフォールバック値（例: macro_sentiment=0.0）で継続するフェイルセーフ設計。
- テスト性の向上:
  - datetime.today()/date.today() を参照しない（ターゲット日引数ベース）ためルックアヘッドバイアスを防止しテスト容易性を向上。
  - _call_openai_api をモック可能にしてユニットテストを容易に。

Known limitations / TODO
- sector_exposure の price 欠損時は過少見積りのリスクがあり、将来的に前日終値や取得原価でのフォールバックを検討（TODO コメントあり）。
- position_sizing の lot_size は現状全銘柄共通。将来的に銘柄別 lot_map へ拡張予定。
- calc_value は PBR・配当利回りを未実装。
- news_nlp / regime_detector による OpenAI 利用は API キーが必要（api_key 引数または OPENAI_API_KEY 環境変数）。API 呼び出し周りはコスト/プライバシー上の注意が必要。

Security
- API キー等の機密情報は環境変数経由での注入を想定。Settings は必須キーが未設定の場合に明確にエラーを出す設計。
- .env 読み込み時は既存の OS 環境変数を保護する仕組み（protected set）を導入。

その他
- ロギングを各モジュールに導入しており、デバッグ情報・警告・ユーザー向けインフォログが適切に出力される設計になっています。

---

注: 本 CHANGELOG は提示されたソースコードから推測して作成したものであり、実際のコミット履歴やリリースノートを完全に反映するものではありません。必要があれば、より詳細な差分（ファイル単位の変更点、コミットハッシュ、寄稿者一覧など）を実際のバージョン管理履歴から生成できます。