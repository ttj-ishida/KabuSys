CHANGELOG
=========

すべての重要な変更は Keep a Changelog の慣例に従って記載しています。
このファイルは人間向けの要約であり、コードベースから推測した機能追加・設計方針・既知の注意点を含みます。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

[0.1.0] - 2026-03-31
--------------------

Added
- パッケージ初版を公開。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境変数・設定管理 (kabusys.config)
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込みする仕組みを実装。  
    - 読み込み優先順位: OS 環境 > .env.local > .env
    - 環境変数による自動読み込み無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - .env パーサは export 形式、クォート・エスケープ、インラインコメント等に対応
  - Settings クラスを提供し、以下の設定をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV (development, paper_trading, live), LOG_LEVEL
    - is_live / is_paper / is_dev のユーティリティプロパティ
  - 未設定必須値は _require で ValueError を送出

- データプラットフォーム関連 (kabusys.data)
  - ETL インターフェース: ETLResult データクラスを公開（kabusys.data.etl / pipeline）
    - ETL 実行結果（取得件数、保存件数、品質問題、エラー一覧）を格納
  - ETL パイプラインユーティリティ (kabusys.data.pipeline)
    - 差分取得・バックフィル・品質チェックを考慮した設計方針を実装（DuckDB ベース）
    - DuckDB 上の最大日付取得等のユーティリティを提供
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダー（market_calendar）を扱うユーティリティ群を実装:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - calendar_update_job により J-Quants から差分取得して冪等保存する処理を実装
    - DB 未取得日の曜日フォールバック、探索上限、バックフィル、健全性チェック等を実装

- 研究（Research）モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離（ma200_dev）を計算
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算
    - calc_value: raw_financials と当日の株価から PER / ROE を計算
    - DuckDB SQL を主体にした実装で、結果は (date, code) をキーとする dict のリストで返す
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 複数ホライズンの将来リターンを一度のクエリで計算
    - calc_ic: スピアマンランク相関（IC）を実装（不足データ時は None を返す）
    - rank: 同順位は平均ランクで処理（丸めで ties の検出誤差を抑制）
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー

- AI / NLP 統合 (kabusys.ai)
  - ニュース NLU/NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを評価して ai_scores テーブルへ書き込み
    - ニュース時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を提供
    - バッチサイズ、記事数上限、文字数トリム、レスポンスバリデーション、スコアクリップ等の安全対策を実装
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライを実装
    - API レスポンスの JSON 復元ロジックを実装（余分な前後テキストが混入する場合の保護）
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（Nikkei 225 連動型）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で regime_score/label（bull/neutral/bear）を計算し market_regime テーブルへ冪等書き込み
    - prices_daily（target_date 未満のデータのみ使用）や raw_news の集計、OpenAI 呼び出しのリトライ/フォールバック（API 失敗時は macro_sentiment=0.0）などを実装
    - OpenAI クライアントは api_key 引数または環境変数 OPENAI_API_KEY で解決
  - 共通設計方針:
    - datetime.today()/date.today() を直接参照せず、外から target_date を与えることでルックアヘッドバイアスを排除
    - テスト容易性のため、OpenAI 呼び出し箇所を差し替え可能（テストで patch する想定）

- パッケージ初期化
  - kabusys/__init__.py: __version__ = "0.1.0", __all__ で主要サブパッケージを公開

Changed
- 初版のため該当なし（新規実装が中心）

Fixed
- 初版のため該当なし

Removed
- 初版のため該当なし

Security
- 環境変数の自動ロードに際して OS 環境変数を保護するため、.env 読み込み時に既存の os.environ キーを protected として上書き抑止する実装を導入
- OpenAI API キーは引数で注入可能かつ環境変数 OPENAI_API_KEY を利用。未設定時は明示的にエラーを送出（誤操作を早期検出）

Notes / 既知の制約・挙動
- DuckDB に依存する設計（関数は DuckDBPyConnection を引数として受け取る）。実行前に必要なテーブルスキーマとデータを用意する必要があります（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など）。
- OpenAI（gpt-4o-mini）を JSON mode で利用する前提の実装。API 仕様変更やモデル変更時はパースロジックの調整が必要です。
- AI 呼び出しは外部 API に依存するため、API 障害時は（多くの箇所で）フェイルセーフとしてスコア 0.0 を用いるか、該当銘柄をスキップする設計になっています。部分的な失敗時も既存データ保護のために書き込み対象コードを限定して置換する実装です。
- .env パーサは多くのケースを想定した実装ですが、非常に特殊な .env 形式がある場合は想定外のパース結果になる可能性があります。
- calendar_update_job 等は J-Quants クライアント（kabusys.data.jquants_client）へ依存。該当クライアントの設定（API トークン等）を事前に用意してください。

作者注
- 本 CHANGELOG は提供されたソースコードから機能と設計方針を推測して作成したものであり、実際のリリースノートや運用ドキュメントと差異がある可能性があります。必要に応じて実際の運用要件に合わせて追記・修正してください。