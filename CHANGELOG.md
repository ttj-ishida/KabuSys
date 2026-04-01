CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。
タグ付けやリリース管理はセマンティックバージョニングに従います。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （なし）

0.1.0 - 初回リリース (YYYY-MM-DD)
--------------------------------

Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - 公開サブパッケージ: data, strategy, execution, monitoring を __all__ で定義。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート自動検出ロジック（.git または pyproject.toml を起点）を実装し、
    それを基に .env/.env.local を自動ロード（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env ファイルの堅牢なパーサ実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどへの対応）。
  - 必須設定取得用の _require() と各種プロパティを実装（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
  - 環境設定のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）、デフォルト DB パス・監視しきい値等のプロパティを提供。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）でセンチメントスコアを取得して ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window() で提供。
    - API 呼び出しのバッチ処理（最大 20 銘柄/チャンク）、トークン肥大化対策（記事数・文字数制限）、レスポンスの厳密バリデーションとクリッピング（±1.0）を備える。
    - リトライ/バックオフ戦略（429・ネットワーク断・タイムアウト・5xx を対象）とフェイルセーフ動作（失敗時は該当チャンクをスキップして処理継続）。
    - テスト容易性のため _call_openai_api を patch して差し替え可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出して market_regime テーブルに冪等書き込みを行う score_regime() を実装。
    - MA 計算はルックアヘッドバイアスを避けるよう target_date 未満のデータのみを使用。ニュースは calc_news_window と組み合わせて取得。
    - OpenAI 呼び出し部分は独立実装（news_nlp の内部関数と共有しない）で、再試行・エラー分類（5xx とそれ以外）を考慮した堅牢な実装。
    - API キー注入可能（引数または環境変数 OPENAI_API_KEY）。失敗時は macro_sentiment=0.0 として処理継続。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーを扱うユーティリティ（is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day）を実装。
    - market_calendar が未登録または一部しかない場合には曜日ベース（土日除外）でフォールバックする一貫性ある判定ロジック。
    - 夜間バッチ更新 job（calendar_update_job）を実装。J-Quants から差分取得→冪等保存（ON CONFLICT 相当）・バックフィル・健全性チェックをサポート。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスにより ETL 実行結果を集約（取得数・保存数・品質問題・エラーメッセージ等）。
    - 差分取得・バックフィル・品質チェック（kabusys.data.quality と連携想定）の設計に基づく基盤を実装。
    - DuckDB を前提としたテーブル存在チェックや最大日付取得ユーティリティを提供（DuckDB 互換性を考慮）。
    - kabusys.data.etl で ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR、相対 ATR）、流動性（20 日平均売買代金・出来高変化率）、バリュー（PER、ROE）を DuckDB の prices_daily / raw_financials を用いて計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時は None を返す等、欠損に配慮。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（スピアマンランク相関）計算（calc_ic）、ランク変換ユーティリティ（rank）、およびファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリ＋DuckDB SQL のみで実装。

Changed
- 設計上の注意・方針をコード内ドキュメントに明示
  - ルックアヘッドバイアス回避のため date.today()/datetime.today() を直接参照しない設計方針を各 AI/研究モジュールで明記。
  - DuckDB のバージョン差異（executemany の空リスト等）に配慮した実装を行い互換性を重視。

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーなど機密情報は環境変数で扱うことを想定。.env 自動ロードはテスト等で環境変数からの上書きをコントロールするための protected/override ロジックを備える。

Notes / 今後の注意点
- 環境変数の必須項目（例）
  - OPENAI_API_KEY（AI モジュールを使う場合）
  - JQUANTS_REFRESH_TOKEN（J-Quants クライアント使用時）
  - KABU_API_PASSWORD（kabu API 連携時）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（通知機能使用時）
- デフォルトのデータベースパスや PID パス等は設定プロパティで定義されており、必要に応じて環境変数で上書き可能。
- テストしやすさを考慮し、OpenAI 呼び出し箇所は patch/mocking できるように分離済み。
- 一部ファイル（pipeline の最後など）に未完のコード断片がある（開発中の注意点として残す）。本リリースは主要機能の初期実装を含む。

バックワード互換性
- 初回リリースのため破壊的変更なし。

貢献
- このリリースは内部設計方針と主要機能の実装に焦点を当てています。バグ報告・改善提案は issue を通じて受け付けます。

----- End of CHANGELOG -----