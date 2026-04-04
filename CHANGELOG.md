Keep a Changelog
すべての重要な変更をこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。
このプロジェクトは互換性のあるセマンティックバージョニングを使用します。

[Unreleased]
（今後の変更をここに記載）

[0.1.0] - 2026-04-04
Added
- 基本パッケージ初期リリース: kabusys v0.1.0
  - src/kabusys/__init__.py によるパッケージ公開とバージョン定義。
- 環境変数・設定管理（kabusys.config）
  - .env および .env.local ファイル、環境変数から設定を自動読み込みする仕組みを実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env/.env.local 読み込み時の挙動:
    - .env を先に読み込み、.env.local で上書き。OS 環境変数は保護される（上書きされない）。
    - export KEY=val 形式、シングル/ダブルクォート、インラインコメントを考慮したパーサを実装。
  - Settings クラスを提供（J-Quants / kabu API / LINE / データベース / 監視 / システム設定等のプロパティ）。
  - 設定値の検証: KABUSYS_ENV, LOG_LEVEL などの許容値チェック。必須値未設定時は ValueError を送出。
  - Path を返すプロパティは expanduser() を適用。

- AI モジュール（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode でセンチメントスコアを取得して ai_scores テーブルへ書き込む。
    - 処理の特徴: JST ベースのニュースウィンドウ（前日15:00〜当日08:30）、1銘柄あたりの記事数・文字数のトリム、最大バッチサイズ制限（20銘柄/回）。
    - 再試行戦略: 429/ネットワーク断/タイムアウト/5xx を指数バックオフでリトライ。部分失敗時にも既存スコアを保護する（対象コードのみ DELETE → INSERT）。
    - レスポンス検証: JSON 解析（前後ノイズが混入した場合の復元）、results 配列と code/score 検証、スコアは ±1.0 にクリップ。
    - テスト容易性を考慮し、OpenAI 呼び出し部分は差し替え可能（内部 _call_openai_api）。
  - regime_detector:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出はマクロキーワードでフィルタ（複数キーワードリスト）し、最大記事数制限あり。
    - OpenAI 呼び出しは gpt-4o-mini を使用。API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフ実装。
    - API キーは関数引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError。

- Data モジュール（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理（market_calendar）とそれに基づく営業日判定ロジックを実装。
    - 提供関数: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB の market_calendar がない場合は曜日ベースのフォールバック（土日を非営業日扱い）。
    - next/prev_trading_day は最大探索範囲を設け（_MAX_SEARCH_DAYS）無限ループを防止。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新。バックフィルと健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.etl に再エクスポート）。
    - pipeline モジュール（ETL の設計）: 差分更新、保存（idempotent）、品質チェック（quality モジュール）を行うパイプライン基盤。
    - ETLResult は取得数／保存数／品質問題／エラー一覧などを保持し、監査ログ用に to_dict() を提供。

- Research モジュール（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR, ATR 比率）、流動性（20 日平均売買代金, 出来高比率）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials を参照して計算する関数を実装。
    - 関数は (date, code) キーを持つ dict のリストを返す。データ不足時は None を返す設計。
  - feature_exploration:
    - 将来リターン calc_forward_returns（任意ホライズン、入力検証あり）、IC 計算 calc_ic（Spearmanランク相関）、rank、factor_summary（統計サマリー）を実装。
    - pandas 等に依存せず標準ライブラリで実装。ランクは同順位を平均ランクで処理。

Changed
- （新規リリースのため無し）

Fixed
- （新規リリースのため無し）

Security
- OpenAI API キーの扱い: 関数引数または環境変数 OPENAI_API_KEY を利用。鍵未設定時は明確な例外を送出して誤動作を防止。

Notes / 設計上の重要点
- ルックアヘッドバイアス対策: 各種処理（ニュースウィンドウ計算、ファクター計算、レジーム判定等）で datetime.today() / date.today() を直接参照せず、呼び出し側が target_date を渡す設計。
- フェイルセーフ: AI API 呼び出しに失敗した場合は例外ではなく安全なデフォルト（スコア 0.0 や処理スキップ）へフォールバックし、ETL やスコア保存の整合性を保つ方針。
- DuckDB 互換性への配慮: executemany の空リスト回避、list 型バインドの不安定性回避などの実装上の工夫あり。

今後
- ai のレスポンス形式やモデル切り替え、追加の品質チェックルール、ETL の細かなスケジューリング等を拡張予定。

署名
- 初回公開（内部設計・主要機能セット）: kabusys チーム（自動生成ドキュメントに基づく）