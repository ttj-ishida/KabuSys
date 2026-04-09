CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に準拠して記載しています。  
バージョン名はパッケージ内の __version__ 値（src/kabusys/__init__.py）に基づきます。

Unreleased
----------

- （該当なし）

v0.1.0 - 2026-04-09
-------------------

Added
- パッケージ初回リリース: kabusys 0.1.0
  - パッケージ公開情報:
    - __version__ = "0.1.0"
    - top-level __all__ に ["data", "strategy", "execution", "monitoring"] を定義

- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（配布後も安定）
  - .env パーサを実装（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント取り扱い）
  - _load_env_file による上書き (override) / 保護（protected: OS 環境変数を保護）をサポート
  - Settings クラスを提供し、主要設定をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など必須値の取得（未設定時は ValueError）
    - KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID 等のオプション設定
    - DB パス: DUCKDB_PATH, SQLITE_PATH（展開・expanduser 対応）
    - Paper Trading 用設定: PAPER_FILL_MODE（instant/partial/never/reject を検証）、PAPER_TRADING_SQLITE_PATH
    - 監視設定: PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/MEM/DISK 閾値
    - システム設定: KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（DEBUG..CRITICAL の検証）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - score_news(conn, target_date, api_key=None)
      - 前日 15:00 JST 〜 当日 08:30 JST のニュースウィンドウを計算して対象記事を収集（calc_news_window を提供）
      - raw_news と news_symbols を結合して銘柄ごとに最新記事を集約（1 銘柄あたり _MAX_ARTICLES_PER_STOCK 件・文字数トリム）
      - 銘柄をチャンク（最大 20 銘柄）で OpenAI (gpt-4o-mini) に送信し JSON Mode で結果を取得
      - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ
      - レスポンスの厳密なバリデーション実装（_validate_and_extract）
        - JSON 抽出の復元ロジック（前後テキスト混入に対応）
        - results リスト・各要素の code/score 検証、未知コードの無視、スコアを ±1.0 にクリップ
      - 成功分のみ ai_scores テーブルに置換的（DELETE → INSERT）に書き込み（部分失敗時に既存スコアを保護）
      - API キー解決: 引数優先、なければ環境変数 OPENAI_API_KEY（未設定時は ValueError）
      - テスト容易性: _call_openai_api をモック可能に設計
    - calc_news_window(target_date) を公開（UTC naive datetime を返す、JST ウィンドウを扱う）
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321（日経225連動）の直近 200 日 MA 乖離を計算（_calc_ma200_ratio、データ不足時は中立=1.0 を返す）
      - raw_news からマクロ経済キーワードでフィルタしたタイトルを抽出（_fetch_macro_news）
      - OpenAI (gpt-4o-mini) によるマクロセンチメント評価（_score_macro）、API エラー時はフォールバック macro_sentiment=0.0
      - MA（重み 70%）とマクロ（重み 30%）を合成して regime_score を算出しラベル化（'bull'/'neutral'/'bear'）
      - market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）
      - API キー解決は news_nlp と同様、テスト差し替え可能な _call_openai_api を用意
      - フェイルセーフ: LLM 呼び出し失敗やパース失敗時に例外伝播させず中立値で継続
    - 設計全体で lookahead バイアスを避ける実装（date.today() を参照しない）

- データ / ETL / カレンダー (kabusys.data)
  - カレンダー管理 (calendar_management)
    - JPX カレンダー夜間バッチ更新（calendar_update_job）を実装
      - market_calendar の最終取得日確認 → J-Quants API 差分取得 → 保存（jquants_client.fetch_market_calendar / save_market_calendar）
      - バックフィル（直近 _BACKFILL_DAYS を再取得）と健全性チェック（将来日付の異常検知）
    - 営業日判定ユーティリティを実装:
      - is_trading_day(conn, d), is_sq_day(conn, d), next_trading_day(conn, d), prev_trading_day(conn, d), get_trading_days(conn, start, end)
      - DB に登録がある場合は DB 値優先、未登録日は曜日ベースでフォールバック（一貫性確保）
      - _MAX_SEARCH_DAYS による探索上限で無限ループ防止
  - ETL パイプライン (pipeline.py / etl.py)
    - ETLResult データクラスを実装（取得数・保存数・品質問題・エラー等を保持）
      - has_errors, has_quality_errors, to_dict を提供（監査ログ用変換）
    - ETL 設計方針と定数（backfill、calendar lookahead、最小データ日など）を定義
    - kabusys.data.etl で ETLResult の公開エイリアスを提供

- 研究用機能 (kabusys.research)
  - factor_research: 定量ファクター計算関数を実装
    - calc_momentum(conn, target_date): mom_1m/3m/6m、ma200_dev（データ不足時は None）
    - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover, volume_ratio（ウィンドウデータ条件に基づく）
    - calc_value(conn, target_date): per, roe（raw_financials の最新報告を使用）
    - 実装は DuckDB SQL と窓関数を用いた効率的なクエリベース
  - feature_exploration: 特徴量評価ユーティリティ
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン計算（デフォルト [1,5,21]）
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）計算
    - rank(values): 同順位は平均ランクとなるランク化ユーティリティ（丸めで ties 対策）
    - factor_summary(records, columns): count/mean/std/min/max/median を計算
  - research.__init__ で zscore_normalize を kabusys.data.stats から再エクスポート（統一インターフェース）

General notes / design decisions
- DuckDB を主要なローカル分析 DB として使用。各関数は DuckDBPyConnection を受ける設計。
- 外部 API 呼び出し（OpenAI、J-Quants）は明示的に扱い、失敗時はフェイルセーフ（多くは中立値 or スキップ）で継続する設計。
- ルックアヘッドバイアス防止に配慮し、内部処理で datetime.today()/date.today() を直接参照しないよう実装。
- DB への書き込みは可能な限り冪等性（DELETE → INSERT / ON CONFLICT）を確保。
- テスト容易性を考慮し、OpenAI 呼び出し部分はモック差替え可能に実装（内部の _call_openai_api をパッチ可）。
- 必須環境変数: OPENAI_API_KEY（AI 機能）、JQUANTS_REFRESH_TOKEN（データ取得）、KABU_API_PASSWORD（kabu API）など。未設定時は明確な例外メッセージを出力。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーなどの機密情報は環境変数経由で注入することを推奨。自動 .env ロードは無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Known issues / Limitations
- 一部 DuckDB バインドの互換性（executemany に空リスト不可など）をコード内でワークアラウンドしているが、将来の DuckDB バージョン差分に注意が必要。
- 外部 API の挙動（特に OpenAI のレスポンス形式）に起因するパースの脆弱性は、レスポンス復元とバリデーションで緩和しているが、完全保証は不能。

---