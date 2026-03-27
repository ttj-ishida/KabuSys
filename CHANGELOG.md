# Keep a Changelog

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。

全てのバージョンはセマンティック バージョニングに従います。

## [0.1.0] - 2026-03-27

追加:
- パッケージ初回リリース: kabusys (バージョン 0.1.0)
  - パッケージメタ:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。

- 環境設定 / ロード機構 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
  - プロジェクトルート検出: __file__ を起点に .git または pyproject.toml を探索してプロジェクトルートを特定（CWD 非依存）。
  - .env パーサ実装:
    - コメント行、空行を無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく処理。
    - クォートなしの値中のインラインコメント認識（直前が空白/タブの場合のみ）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - Settings クラス提供:
    - J-Quants / kabuAPI / Slack / DB パス / 環境 (development|paper_trading|live) / ログレベル のプロパティ。
    - 必須変数未設定時は ValueError を送出（明確なメッセージ）。
    - duckdb/sqlite のパスはデフォルト値を持ち expanduser を適用。
    - env / log_level は許容値の検証を実施。
    - ユーティリティプロパティ: is_live / is_paper / is_dev。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成。
    - スコアリングは OpenAI Chat Completion (gpt-4o-mini, JSON mode) を利用し、銘柄ごとに -1.0〜1.0 のセンチメントを算出して ai_scores テーブルへ書き込む。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 変換で前日 06:00 ～ 23:30）。
    - バッチ処理: 最大 20 銘柄/回、各銘柄は最大 10 記事・最大 3000 文字でトリム。
    - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ（最大 _MAX_RETRIES）。
    - レスポンス検証: JSON パース、"results" キー、コード整合性、数値検証。無効なレスポンスはスキップ（例外は伝播させずフェイルセーフ）。
    - DB 書き込みは部分置換（対象コードのみ DELETE → INSERT）で部分失敗時の既存データ保護。
    - テスト用フック: _call_openai_api をモック可能。
    - API キー解決: api_key 引数優先、その後 OPENAI_API_KEY 環境変数。未設定時は ValueError。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算は target_date 未満のデータのみを使用（ルックアヘッド防止）。データ不足時は中立値を使用。
    - マクロ記事は raw_news からマクロキーワードで抽出（最大 _MAX_MACRO_ARTICLES 件）。
    - OpenAI 呼び出し (gpt-4o-mini) によるセンチメント評価。API 失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - スコア合成・クリッピング・閾値判定の実装。
    - market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - テスト用フック: _call_openai_api は差し替え可能。
    - API キーは api_key 引数または OPENAI_API_KEY 環境変数で解決。未設定時は ValueError。

- データプラットフォーム関連 (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar を使った営業日判定ユーティリティ:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar がない場合は曜日ベース（週末=非営業日）でフォールバック。
    - next/prev では DB 登録値を優先し、未登録日は曜日フォールバックで一貫した結果を返す。
    - calendar_update_job により J-Quants から差分取得・バックフィル・保存を実装（lookahead/backfill/健全性チェックを含む）。
    - 最大探索日数の上限 (_MAX_SEARCH_DAYS) を設け無限ループを防止。

  - ETL / パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを公開（etl.py から再エクスポート）。
    - 差分取得／保存／品質チェックの設計方針を実装するためのユーティリティを提供（テーブル存在チェック、最大日付取得、カレンダーヘルパー等）。
    - ETLResult は品質問題・エラーの集約・シリアライズをサポート(has_errors / has_quality_errors / to_dict)。

  - jquants_client 連携の想定（モジュール参照箇所を含む）。API 呼び出し失敗時のログとフェイルセーフ動作を備える。

- リサーチ / ファクター計算 (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum: 約1M/3M/6M リターン、200 日 MA 乖離率を計算（データ不足時は None）。
    - Volatility / Liquidity: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率などを計算。
    - Value: raw_financials から EPS/ROE を取得して PER/ROE を算出（EPS が 0/欠損時は None）。
    - すべて DuckDB の prices_daily / raw_financials を参照、外部 API へはアクセスしない。
    - 結果は (date, code) を含む辞書のリストで返却。

  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン (calc_forward_returns): 指定ホライズン（デフォルト [1,5,21]）までの将来終値を LEAD で取得してリターンを計算。
    - IC 計算 (calc_ic): Spearman ランク相関を実装（3 件未満は None）。
    - rank: 同順位は平均ランクにする実装（浮動小数の丸めで ties を安定化）。
    - factor_summary: count/mean/std/min/max/median の基本統計量を計算。
    - pandas 等の外部ライブラリに依存せず純粋に標準ライブラリ + DuckDB で実装。

- テスト・デバッグ支援
  - OpenAI API 呼び出し箇所は内部関数（_call_openai_api）を介しており、unittest.mock.patch による差し替えを意図的にサポート。これにより単体テストで外部呼び出しをモック可能。

設計上の注記（主な意図とフェイルセーフ方針）:
- ルックアヘッドバイアス回避: 各種処理は datetime.today()/date.today() を直接参照せず、外部から target_date を受け取る設計。
- DuckDB を主要なローカル DB として利用。DB 書き込みは冪等性を重視（DELETE→INSERT や ON CONFLICT パターン）。
- 外部 API（OpenAI / J-Quants 等）失敗時は基本的に処理を継続し、既定値やスキップでフォールバックする（例: macro_sentiment=0.0、スコア未取得はスキップ）。
- 一部機能は将来的拡張（PBR／配当利回りなど）を想定して未実装の旨を明記。

既知の制約 / 注意点:
- AI 機能を使うには OpenAI API キー（api_key または OPENAI_API_KEY 環境変数）が必要。未設定時は ValueError を送出する。
- ai_scores 書き込み時は DuckDB の executemany に関する制約を考慮して空パラメータでの実行を避ける実装になっている。
- raw_financials のデータが不足すると一部バリュー指標は None になる。
- calendar_update_job は J-Quants クライアント（jquants_client）の実装に依存する。外部 API のエラーはログ出力のうえフェイルセーフで 0 を返す。

変更履歴の初期リリースに含まれる主要機能の概要は以上です。

（将来的な改善・バグ修正はここに追記します）