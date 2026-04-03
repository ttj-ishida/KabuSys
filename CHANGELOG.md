Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

[Unreleased]
------------

（現在のコードベースは初回公開リリース相当のため未リリース項目はありません）

0.1.0 - 2026-04-03
------------------

初回リリース。日本株自動売買プラットフォームのコア機能をまとめて公開します。
以下はコードベースから推測できる主な追加点・設計方針・注意点です。

Added
- パッケージ基盤
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
  - モジュール公開一覧: data, strategy, execution, monitoring（__all__）。

- 環境設定管理（kabusys.config）
  - .env 自動ロード機能を実装（プロジェクトルートの判定: .git または pyproject.toml を探索）。
  - 読み込み順序: OS環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化。
  - .env のパースは export 形式・クォート・インラインコメント等に対応する堅牢な実装。
  - 必須環境変数取得ヘルパ（_require）と Settings クラスを提供。主要設定例:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
    - OPENAI_API_KEY（AI 呼び出しは関数引数での注入も可能）
    - KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - データベースパス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH
    - 監視用ファイルパス: PID_FILE_PATH, KILL_FLAG_PATH 等
    - 環境種別検証（development/paper_trading/live）とログレベル検証

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（ai_score）を算出。
  - 機能:
    - 対象ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で計算。
    - 1 銘柄あたり最大記事数・文字数によるトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 最大 20 銘柄 / バッチでの API 呼び出し（_BATCH_SIZE）。
    - API エラー（429、ネットワーク、タイムアウト、5xx）は指数バックオフでリトライ。
    - レスポンスの厳格なバリデーション（JSON 抽出、results 配列、code/score 検証）。
    - スコアを ±1.0 にクリップし、ai_scores テーブルへ冪等的に置換（DELETE→INSERT、部分失敗時の保護）。
  - テスト容易性: _call_openai_api をパッチで差し替え可能。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の market_regime を生成。
  - マクロ判定はニュースタイトルの抽出（マクロキーワード群）→ OpenAI による JSON 出力（_SYSTEM_PROMPT）で行う。
  - フォールバック: API 失敗時は macro_sentiment=0.0、データ不足時は ma200_ratio=1.0（中立）。
  - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等処理。失敗時は ROLLBACK を試行。
  - API キーは関数引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を参照。

- データ処理・ETL（kabusys.data.pipeline / etl / jquants_client への統合インターフェース）
  - ETL 実行結果を表す ETLResult dataclass を導入（取得数・保存数・品質問題・エラー一覧等を保持）。
  - 差分取得、バックフィル、品質チェックの設計方針を実装（品質問題は収集して上位判断に委ねる）。
  - DuckDB 特性（executemany に空リスト不可など）を考慮した実装。

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - JPX カレンダーを J-Quants 経由で差分取得して market_calendar テーブルへ保存する夜間ジョブ calendar_update_job を実装。
  - 営業日判定ユーティリティ:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
  - DB 登録がない場合は曜日ベースのフォールバック（週末は非営業日）。
  - 最大探索日数制限（_MAX_SEARCH_DAYS）や健全性チェック（将来日付の異常検出）を実装。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、ATR 比率、平均売買代金、出来高比率 を計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（PBR・配当利回りは未実装）。
    - DuckDB 内 SQL を中心とした実装で外部 API へはアクセスしない。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を用いて一括取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装（有効レコード数が 3 未満なら None）。
    - rank: 同順位は平均ランクを与える実装（丸めで ties 検出の頑健化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ。

Changed
- 初回リリースのため該当なし（新規機能群をまとめて導入）。

Fixed
- 初回リリースのため該当なし。

Security
- 機密情報（API キー等）は環境変数で扱う設計。自動.env ロードは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- .env ローダーは OS 環境変数を保護するため override 挙動と protected set を導入。

Notes / Implementation details（設計上の重要ポイント）
- ルックアヘッドバイアス回避:
  - 全ての日付計算で datetime.today() / date.today() を直接参照しない設計を明示（関数引数で target_date を受ける）。
  - DB クエリは date < target_date / date = target_date のようにルックアヘッドを防止する条件を使用。
- フェイルセーフ:
  - AI API 呼び出し失敗時は例外を上位に投げず、局所的に安全な既定値（例: macro_sentiment=0.0）で継続する実装が多く含まれる。
- テスト容易性:
  - OpenAI 呼び出しをラップした内部関数（_call_openai_api）をパッチ交換可能にしている。
  - API キーは関数引数で注入可能（テストでの分離を容易にする）。
- DuckDB 互換性:
  - executemany の空リスト回避や date 型変換ユーティリティなど、DuckDB の挙動に対する互換性処理を実装。

既知の未実装 / TODO（コードから推測）
- 一部戦略（strategy）・発注（execution）・監視（monitoring）モジュールはパッケージ公開対象として存在するが、この差分では詳細実装ファイルが含まれていないため、これらは今後の実装対象と推定される。
- ファイナンシャル指標の追加（PBR・配当利回り等）は将来の拡張候補。
- news_nlp/regime_detector のプロンプト改善やモデル選択は運用でのチューニング対象。

---

この CHANGELOG はコードから読み取れる機能・設計方針を基に作成しました。リリース時の正式な文言や日付・分類はプロジェクトの方針に合わせて修正してください。