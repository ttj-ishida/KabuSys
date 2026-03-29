Keep a Changelog
================

すべての重要な変更はこのファイルに記録します。  
このプロジェクトでは "Keep a Changelog" のフォーマットに従います。

[Unreleased]
------------

なし

[0.1.0] - 2026-03-29
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ識別子: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
  - パブリックサブパッケージとして data, strategy, execution, monitoring をエクスポート。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサーの強化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理（クォート無の # は前が空白/タブの場合のみコメントとみなす）。
    - ファイル読み込み失敗時は警告を出力して継続。
    - override / protected オプションにより既存 OS 環境変数を保護しつつ .env.local で上書き可能。
  - Settings クラスを提供（settings オブジェクトをエクスポート）。
    - J-Quants, kabuステーション, Slack, DB パスなどのプロパティを提供。
    - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - KABUSYS_ENV の検証（development / paper_trading / live）および LOG_LEVEL の検証。
    - ユーティリティプロパティ: is_live / is_paper / is_dev。
  
- AI モジュール (kabusys.ai)
  - news_nlp.score_news
    - raw_news / news_symbols を用いて銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - ニュースウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 変換された半開区間で処理）。
    - バッチ処理: 最大 20 銘柄／API コール、1 銘柄あたり最大 10 記事・3000 文字にトリム。
    - JSON Mode を使用し、レスポンスのバリデーションを厳格に行う（results キー、型チェック、既知コードのみ採用、スコアは ±1.0 にクリップ）。
    - リトライ戦略: 429、ネットワーク断、タイムアウト、5xx に対して指数バックオフでリトライ。その他のエラーはスキップ。
    - DB 書き込みは部分失敗耐性あり（取得成功コードのみ DELETE → INSERT にて置換）。DuckDB の executemany 空リスト制約に対応。
    - テスト用フック: _call_openai_api を patch して差し替え可能。
  - regime_detector.score_regime
    - ETF 1321（Nikkei 225 連動ETF）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - ma200_ratio の計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを排除。
    - マクロニュース抽出はキーワードベース（複数の日本/米国キーワードを定義）でタイトルを最大 20 件取得。
    - OpenAI 呼び出しは gpt-4o-mini（JSON 出力）を用い、API エラー時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
    - レジームスコアは合成後にクリップし、market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書込み失敗時はロールバックして例外を伝播。

- Data モジュール (kabusys.data)
  - calendar_management
    - JPX カレンダー（market_calendar）操作と営業日判定ロジックを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - market_calendar が未取得のときは曜日ベース（平日=営業日）でフォールバック。
    - next/prev_trading_day は DB 登録値を優先し、未登録日は曜日フォールバック、一致しない場合の最大探索日数を設定して無限ループ回避。
    - calendar_update_job: J-Quants クライアント経由で差分取得→保存（fetch_market_calendar / save_market_calendar）を実装。バックフィルと健全性チェック（将来日付過剰はスキップ）をサポート。
  - pipeline / etl
    - ETLResult データクラスを定義して ETL 実行結果（取得数、保存数、品質問題、エラー要約）を格納。
    - 差分更新・バックフィル・品質チェック統合を想定したユーティリティ関数と内部ヘルパー（テーブル存在チェック、最大日付取得等）を実装。  
    - デフォルトのバックフィル日数、カレンダー先読み等の定義を追加。
    - DataPlatform.md の設計方針に基づく idempotent 保存と品質チェックの取り扱い方針を反映。

- Research モジュール (kabusys.research)
  - factor_research
    - モメンタム、ボラティリティ、バリュー等のファクター計算関数を実装：
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA 乖離）を計算。データ不足時は None を返す。
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。データ不足時は None を返す。
      - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS が 0/欠損のときは None）。
    - すべて DuckDB 上の prices_daily / raw_financials テーブルのみ参照（外部 API にはアクセスしない設計）。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）における将来リターンを一括で計算。horizons の検証あり。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（Information Coefficient）を計算。3 件未満は None を返す。
    - rank: 同順位は平均ランクにするランク化実装（round による丸めで ties の安定化）。
    - factor_summary: count, mean, std, min, max, median を各列について算出。None 値は除外。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

Changed
- 設計方針（全体）
  - ルックアヘッドバイアス防止: 各 AI / リサーチ関数は datetime.today() / date.today() を内部参照しない設計（呼び出し側が target_date を渡す前提）。
  - OpenAI 呼び出しは JSON Mode を使用し、レスポンス検証を厳格に行うことで LLM 出力の不確実性に対処。
  - API エラーに対してはフェイルセーフの方針（エラー時にスコアを 0.0 にフォールバック、処理継続）を採用。

Fixed
- なし（初回リリース）

Security
- 環境変数保護: .env ロード時に既存 OS 環境変数を protected として扱い、.env からの上書きを防止可能（.env.local は override=True だが protected により OS 環境変数は保護）。

Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings により必須チェックが行われます（必要に応じて .env を用意してください）。
  - OpenAI を利用する機能(news_nlp.score_news, regime_detector.score_regime) を呼ぶ際は api_key 引数または環境変数 OPENAI_API_KEY の設定が必要です。
- DuckDB を用いたローカル DB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_calendar, market_regime 等）が前提です。ETL / calendar ジョブを実行する前にスキーマ準備を行ってください。
- テスト・モック: OpenAI 呼び出しはモジュール内の _call_openai_api を patch して差し替えることを想定しています（ユニットテスト容易化のため）。

Acknowledgements
- 初期実装では OpenAI SDK（OpenAI）と DuckDB を利用しています。API の将来的な変更や SDK の挙動差異に備え、例外処理や getattr を用いた安全なステータスコード参照などを実装しています。