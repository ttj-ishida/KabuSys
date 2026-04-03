# Changelog

すべての注目すべき変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠します。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]

---

## [0.1.0] - 2026-04-03

初回公開リリース — 日本株自動売買システム「KabuSys」基盤モジュール群を追加。

### 追加 (Added)
- パッケージのエントリポイント
  - src/kabusys/__init__.py
    - バージョン情報 (__version__ = "0.1.0") と主要サブパッケージのエクスポート（data, strategy, execution, monitoring）。

- 設定・環境変数管理
  - src/kabusys/config.py
    - .env ファイルまたは環境変数からの設定読み込み機能を提供。
    - プロジェクトルート探索（.git または pyproject.toml を基準）により、CWD に依存せず自動ロードを実行。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env パースの細かい挙動を実装:
      - export KEY=val 形式対応
      - シングル/ダブルクォート内のバックスラッシュエスケープ対応
      - クォートなし値でのインラインコメント認識（直前が空白/タブの場合）
    - _load_env_file による上書き制御（override）と OS 環境変数保護（protected set）。
    - Settings クラスを提供し、J-Quants/LINE/kabu関連・データベースパス・監視用設定・閾値・環境/ログレベル検証プロパティを公開。
    - 必須キー取得用の _require を実装（未設定時は ValueError）。

- AI（NLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメント評価して ai_scores テーブルへ書き込む。
    - 処理の特徴:
      - 対象ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 変換済み）
      - 1銘柄あたり最新記事の上限（_MAX_ARTICLES_PER_STOCK）、文字数制限（_MAX_CHARS_PER_STOCK）
      - バッチサイズ（_BATCH_SIZE）単位で API 呼び出し
      - RateLimit/ネットワーク/タイムアウト/5xx に対して指数バックオフでリトライ
      - レスポンスのバリデーション（JSON 抽出、results 配列、code と score の検証、数値チェック）
      - スコアは ±1.0 にクリップ
      - 書き込みは部分失敗に備えて、取得できたコードのみ DELETE→INSERT による置換（冪等性・既存データ保護）
      - テスト容易性: _call_openai_api を unittest.mock.patch で差し替え可能
    - 関数: calc_news_window, score_news, 内部ユーティリティ（_fetch_articles, _score_chunk, _validate_and_extract 等）

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む。
    - 処理の特徴:
      - ma200_ratio 計算でルックアヘッド防止（date < target_date 条件）
      - マクロニュースは news_nlp.calc_news_window と同じウィンドウを使用してタイトルを抽出（キーワードによるフィルタ）
      - OpenAI 呼び出し（gpt-4o-mini）で JSON 出力を期待。API 失敗時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）
      - 冪等的 DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）。失敗時は ROLLBACK（失敗ログを出力）
      - テスト容易性: _call_openai_api を差し替え可能
    - 関数: score_regime, 内部ユーティリティ（_calc_ma200_ratio, _fetch_macro_news, _score_macro 等）

- 研究（Research）モジュール
  - src/kabusys/research/:
    - factor_research.py
      - Momentum, Value, Volatility, Liquidity 等のファクター計算を実装:
        - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）
        - calc_volatility: 20日 ATR（atr_20）/ 相対ATR(atr_pct) / avg_turnover / volume_ratio
        - calc_value: PER, ROE（raw_financials から最新の報告データを取得）
      - DuckDB 上で SQL を用いて安全に計算（外部 API にはアクセスしない）
      - データ不足時は None を返す設計
    - feature_exploration.py
      - calc_forward_returns: 将来リターン（horizons はデフォルト [1,5,21]、最大 252 日制限）を一度のクエリで取得
      - calc_ic: スピアマンランク相関（IC）を計算（有効レコード < 3 の場合 None）
      - rank: 同順位を平均ランクで扱う実装（丸めにより ties の検出安定化）
      - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算
    - research/__init__.py で主要関数をエクスポート（zscore_normalize の再エクスポート含む）

- データプラットフォーム（Data）モジュール
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ロジックを実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
      - DB 登録がない/不完全な場合は曜日ベースでフォールバック（土日を非営業日扱い）
      - calendar_update_job: J-Quants API からの差分取得・バックフィル・健全性チェック・保存処理（fetch/save を jquants_client に委譲）
      - 最大探索範囲やバックフィル等の安全ガードを実装（_MAX_SEARCH_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS 等）
  - src/kabusys/data/pipeline.py
    - ETL パイプラインの基礎（差分取得・保存・品質チェック）のインターフェース実装
    - ETLResult データクラスを定義（target_date / fetched/saved counts / quality_issues / errors 等）および to_dict メソッド
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得のための基盤を定義
  - src/kabusys/data/etl.py
    - pipeline.ETLResult の再エクスポート

- テスト・開発支援
  - 各種 OpenAI 呼び出し用ラッパー関数（_call_openai_api）をモジュール内に定義し、単体テスト時に差し替え可能にしている。
  - 環境自動ロードを無効化するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供し、テスト実行環境での副作用を軽減。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- 環境変数読み込み時に OS 環境変数を protected set として扱い、.env による上書きを制御することで意図しない環境値の上書きを防止する設計。
- OpenAI API キーが未設定の場合は明確に ValueError を発生させることで不整合な状態での API 呼び出しを防止。

### 注意事項 / 既知の制約
- OpenAI（gpt-4o-mini）を利用する機能は API キー（OPENAI_API_KEY）が必須。api_key 引数で注入可能。
- DuckDB を前提として実装されているため、呼び出し側は DuckDB 接続オブジェクトを渡す必要がある。
- 一部の DB 操作は DuckDB のバージョン差異（list 型バインドや executemany の空リスト扱い等）を考慮した実装になっている。
- news_nlp と regime_detector は LLM の応答に依存するため、API レスポンスの不正・API エラー時はフェイルセーフとしてスコアを 0.0 にフォールバックまたは該当銘柄をスキップする挙動となる。
- 日付処理はルックアヘッドバイアスを避けるため、内部で datetime.today()/date.today() を参照しない設計（target_date を必須で受け取る）。

--- 

今後のリリースでは、strategy / execution / monitoring の具体的な発注・監視ロジック、データ品質チェックモジュールの詳細実装、より細かいテストケースやドキュメントの追加を予定しています。