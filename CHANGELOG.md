Keep a Changelog に準拠した形式で、コードベースから推測できる変更履歴（日本語）を作成しました。

CHANGELOG.md
=============
すべての注記は https://keepachangelog.com/ja/ に従います。

<!-- Unreleased セクション（今後の変更用） -->
Unreleased
----------
- 未リリースの変更はここに記載します。

[0.1.0] - 2026-04-09
-------------------
初回リリース。日本株自動売買プラットフォーム「KabuSys」の基盤機能を実装・公開。

Added
- パッケージ基礎
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。
  - 主要サブパッケージを __all__ で公開: data, strategy, execution, monitoring（空もしくは未実装のモジュールを含む可能性あり）。
- 設定 / 環境変数管理（kabusys.config）
  - .env ファイル自動読み込み機能を実装（プロジェクトルート判定: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロード無効化可能。
  - robust な .env パーサ実装（export プレフィックス、クォート文字列とエスケープ、インラインコメント等に対応）。
  - 環境設定をラップする `Settings` クラスを提供。J-Quants / kabu API / LINE / DB / モニタリング / システム設定等をプロパティ経由で取得。
  - 値検証を実装（PAPER_FILL_MODE の有効値チェック、KABUSYS_ENV / LOG_LEVEL の許容値チェック等）。未設定の必須変数は `_require` で ValueError を送出。
  - Path を返すプロパティは expanduser 対応（例: DUCKDB_PATH, SQLITE_PATH 等）。
- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント ai_score を計算して `ai_scores` テーブルへ書き込み。
  - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を `calc_news_window` として提供。
  - バッチ処理（最大 _BATCH_SIZE=20 銘柄）で API 呼び出し。1 銘柄あたりは記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
  - API 呼び出しに対して 429/ネットワーク断/タイムアウト/5xx を対象とした指数バックオフのリトライ実装。失敗はスキップして処理継続（フェイルセーフ）。
  - API レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code と score の存在、既知コードのみ採用、数値チェック）。スコアは ±1.0 にクリップ。
  - DuckDB への書き込みは部分失敗に強い設計（取得できた銘柄のみ DELETE→INSERT で置換）。DuckDB executemany の注意点に対応。
  - テスト容易性向上のため、内部の API 呼び出し関数をモック置換可能に設計（unittest.mock.patch で差し替え可能）。
- AI 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロ記事の LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を日次判定する `score_regime` を実装。
  - ma200 計算は target_date 未満のデータのみを使用してルックアヘッドを防止。データ不足時は中立値 (1.0) をフェールセーフとして使用。
  - マクロ記事抽出はキーワードベースでフィルタ、LLM 呼び出し失敗時は macro_sentiment = 0.0 として継続。
  - OpenAI 呼び出しに対するリトライ（429/接続エラー/タイムアウト/5xx の扱い）とレスポンスパースの安全化。
  - market_regime テーブルへの書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装し、失敗時は ROLLBACK を試みる。
- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）:
    - JPX カレンダーを扱うためのユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB の market_calendar を優先し、未取得日は曜日ベース（土日除外）でフォールバックするローグロジックを採用。
    - next/prev の探索は最大 _MAX_SEARCH_DAYS の範囲で安全制限。
    - 夜間バッチ更新 job（calendar_update_job）で J-Quants から差分取得・保存（バックフィルと健全性チェックを実装）。
  - ETL パイプライン（pipeline）:
    - 差分更新、idempotent 保存（jquants_client の save_* を想定）、品質チェック（quality モジュール）を実施する ETL の基本設計。
    - ETL 実行結果を表す `ETLResult` データクラスを提供（品質問題・エラーの収集、has_errors / has_quality_errors 等のプロパティ、to_dict）。
    - デフォルトのバックフィル挙動・カレンダー先読み日数や最小データ開始日などを定義（_DEFAULT_BACKFILL_DAYS, _CALENDAR_LOOKAHEAD_DAYS, _MIN_DATA_DATE 等）。
  - etl モジュールから `ETLResult` を再エクスポート。
  - jquants_client との連携を想定した実装（fetch / save による差分取得と保存）。
- 研究用モジュール（kabusys.research）
  - ファクター計算（research.factor_research）:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials から計算する関数を提供（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None の扱い、戻り値は (date, code) をキーとする dict のリストを返す設計。
  - 特徴量探索（research.feature_exploration）:
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト 1,5,21 営業日）へのリターンをまとめて取得可能。horizons のバリデーションを実装。
    - IC（Information Coefficient）計算（calc_ic）: factor と forward リターンのスピアマンランク相関を実装（有効レコード < 3 の場合は None）。
    - ランク付けユーティリティ（rank）: 同順位は平均ランクで処理し、丸めによる ties 検出を安定化。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。
  - 一部ユーティリティをパッケージ __all__ で公開。
- ロギングとデバッグ情報
  - 各モジュールに logger を設置し、重要な分岐・フェールセーフ・処理開始/完了に関するログ出力を充実。

Changed
- （初回リリースのため履歴なし）

Fixed
- （初回リリースのため履歴なし）

Security
- OpenAI API キーや Kabusys の重要なパラメータは Settings 経由で管理され、必須キー未設定時は明示的にエラーを上げることで誤設定の検出を容易にした。

Notes / Design decisions
- ルックアヘッドバイアス対策として、すべてのスコアリング・レジーム判定関数は datetime.today() / date.today() を直接参照しない。必ず caller が target_date を渡す仕様。
- OpenAI 呼び出し周りはテスト可能性のため内部関数をモック可能に分離している（ユニットテストでの差し替えを想定）。
- DuckDB の executemany 空リスト問題など、実運用でのエッジケースに対応した実装上の注意あり。

Acknowledgements
- この CHANGELOG は提供されたソースコードから機能・設計方針を推測して作成しています。実際の変更履歴やリリース日付はプロジェクトの公式履歴に従ってください。