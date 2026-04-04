KEEP A CHANGELOG 準拠 — CHANGELOG.md

全般
- このプロジェクトは日本株自動売買プラットフォーム「KabuSys」の初期リリースです。
- パッケージバージョン: 0.1.0

[0.1.0] - 2026-04-04
Added
- パッケージ初期実装を追加。
  - src/kabusys/__init__.py にてパッケージ公開 API を定義（data, strategy, execution, monitoring）。
- 環境変数・設定管理 (src/kabusys/config.py)
  - .env ファイル自動読み込み機能（プロジェクトルートは .git または pyproject.toml から探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーで以下に対応:
    - コメント行、`export KEY=val` 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い（クォート有無での挙動差）。
  - 環境設定クラス Settings を追加。主な設定プロパティ:
    - J-Quants / kabu API / LINE / DB パス（duckdb/sqlite）/監視用 PID・kill フラグ・しきい値（CPU/MEM/DISK）/実行環境（development/paper_trading/live）/ログレベル検証等。
  - 必須環境変数未設定時は ValueError を送出するユーティリティ _require。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - news_nlp.score_news: raw_news と news_symbols を集約し、OpenAI (gpt-4o-mini) の JSON モードで銘柄別センチメントを評価して ai_scores テーブルへ書き込む。
    - 集計ウィンドウ: JST 前日 15:00 ～ 当日 08:30（内部は UTC naive に変換）。
    - バッチ処理: 最大 20 銘柄 / API 呼び出し (_BATCH_SIZE = 20)。
    - 1 銘柄あたりの記事数上限・文字数トリム: _MAX_ARTICLES_PER_STOCK = 10、_MAX_CHARS_PER_STOCK = 3000。
    - レスポンスバリデーションと ±1.0 クリップ（_SCORE_CLIP = 1.0）。
    - リトライ方針: 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフ（最大リトライ回数 _MAX_RETRIES）。
    - DB 書き込みは冪等性確保のため DELETE → INSERT の置換方式。部分失敗で既存スコアを消さないようコード絞り込みを行う。
    - OpenAI API キー解決: api_key 引数または環境変数 OPENAI_API_KEY。未設定時は ValueError。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - regime_detector.score_regime: ETF 1321（日経225連動型）の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して市場レジーム（bull / neutral / bear）を日次で判定し market_regime テーブルへ保存。
    - 計算:
      - MA200 乖離重み 70%（_MA_WEIGHT = 0.7）、マクロニュース重み 30%（_MACRO_WEIGHT = 0.3）、MA スケール _MA_SCALE = 10.0。
      - クリッピング: 合成スコアを -1.0〜1.0 に制限。強気閾値 _BULL_THRESHOLD = 0.2、弱気閾値 _BEAR_THRESHOLD = 0.2。
      - マクロキーワードで raw_news をフィルタし最大 20 記事を LLM に渡す（_MAX_MACRO_ARTICLES = 20）。
    - OpenAI 呼び出しは gpt-4o-mini、JSON 出力を期待。API 障害時は macro_sentiment=0.0 にフォールバック（例外を投げず継続）。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の組合せで冪等性を確保。失敗時は ROLLBACK を試行し例外を上位へ伝播。

- データプラットフォーム (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダー管理 API との連携を想定（jquants_client 経由）。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB に値が無い場合は曜日ベースでフォールバック（土日非営業日扱い）。
    - 最大探索日数 _MAX_SEARCH_DAYS = 60、先読み _CALENDAR_LOOKAHEAD_DAYS = 90、バックフィル _BACKFILL_DAYS = 7、健全性チェック _SANITY_MAX_FUTURE_DAYS = 365。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存。バックフィル・健全性チェックを実施。

  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを公開（取得/保存件数、品質問題、エラー等を格納）。
    - 差分更新・バックフィル（デフォルト _DEFAULT_BACKFILL_DAYS = 3）・品質チェック（quality モジュールとの連携）設計を反映。
    - データ開始日の定義 _MIN_DATA_DATE = 2017-01-01。
    - テーブル存在確認や最大日付取得などのユーティリティ関数を実装。

- リサーチ / ファクター (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離 (ma200_dev) を計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR（atr_20）/相対 ATR (atr_pct)、20 日平均売買代金 (avg_turnover)、出来高比 (volume_ratio) を計算。
    - calc_value: raw_financials から直近財務を取得し PER・ROE を計算（EPS が欠損/0 の場合は per=None）。
    - DuckDB ベースの SQL と Python を組み合わせた実装。外部 API に依存しない。

  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。最小有効レコード数は 3。
    - factor_summary: 各ファクターの基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクにするランク関数。丸め (round(v, 12)) を利用して ties の検出安定化。

- その他
  - Pure-Python 実装を重視し、pandas 等の外部ライブラリへの依存を避ける設計方針を多くのモジュールで採用。
  - DuckDB を主要なローカル分析用 DB として利用する想定（関数の引数は DuckDB 接続を受け取る）。

Design / Behavior Notes (設計上の注意点)
- ルックアヘッドバイアス対策: 各スコア/判定関数は datetime.today() / date.today() を内部参照せず、外部から与えられる target_date を起点に処理する。
- OpenAI 呼び出し:
  - gpt-4o-mini + JSON mode を使用する想定。
  - API 障害に対してはログを残してフェイルセーフ（スコアのデフォルト値やスキップ）で継続する方針。
  - テスト容易性のため _call_openai_api をパッチ差し替え可能（unittest.mock.patch を想定）。
- DB 書き込みはできる限り冪等性を保つ（DELETE→INSERT、ON CONFLICT 等）。部分失敗時に他データを削らない配慮あり。
- 品質チェックはエラーを収集して呼び出し側で判断する（Fail-Fast にはしない）。

Known limitations / 今後の改善余地
- PBR・配当利回りなどのバリュー指標は未実装（calc_value 参照）。
- strategy / execution / monitoring パッケージの実装詳細は本リリースの範囲外（パッケージエクスポートは定義済み）。
- OpenAI SDK の将来の仕様変更（例: APIError の属性）を考慮した防御コードはあるが、動作確認は必要。

脚注
- 本 CHANGELOG はコードベースからの仕様・設計の読み取りに基づく初期リリースのまとめです。動作や API との連携は実運用での検証が必要です。