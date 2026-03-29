Keep a Changelog
=================

すべての注目すべき変更をこのファイルで管理します。  
フォーマットは Keep a Changelog に準拠しています。  

履歴
----

### Unreleased
（なし）

### [0.1.0] - 2026-03-29
初回公開リリース。日本株自動売買プラットフォーム "KabuSys" のデータ取得・ETL・研究・AI スコアリング・カレンダー管理などのコア機能を実装しました。

主な追加点
- 全体
  - パッケージ初期バージョンを 0.1.0 として公開。
  - パッケージエントリポイントに data, strategy, execution, monitoring を公開。

- 環境設定（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - .env 自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env の詳細なパース実装を追加：
    - export KEY=val 形式をサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープを考慮したパース。
    - クォートなしの行でのインラインコメント処理（'#' の直前が空白/タブ時にコメント扱い）。
  - OS 側の既存環境変数を保護するための protected 上書き制御、override フラグを実装。
  - 自動読み込み無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト等で使用）。
  - 必須環境変数未設定時に ValueError を投げる _require ヘルパー。
  - env, log_level の検証（允許値チェック）や便利プロパティ（is_live/is_paper/is_dev）を提供。
  - デフォルト DB パス（DUCKDB_PATH, SQLITE_PATH）と kabu API, Slack 関連設定を定義。

- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini）へ送信してセンチメント（ai_score）を算出。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供（UTC naive datetime）。
    - 1銘柄あたりの記事数上限 (_MAX_ARTICLES_PER_STOCK) と文字数上限 (_MAX_CHARS_PER_STOCK) を実装し、トークン肥大化対策。
    - バッチ送信（最大 _BATCH_SIZE=20 銘柄）、JSON Mode での応答処理、レスポンスの厳密なバリデーションを実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ。
    - レスポンス整形（前後余分テキストが混ざる場合の {} 抽出）や数値チェック、未知コードの無視、スコアの ±1.0 クリップを実装。
    - DuckDB の executemany 空パラメータ制約を考慮した安全な DB 書き込み（DELETE → INSERT、対象コードのみ置換）。
    - テスト容易性のため _call_openai_api をモック差し替え可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を組み合わせて日次で市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算（target_date 未満のデータのみを使用してルックアヘッドバイアスを回避）。
    - マクロ記事はキーワードフィルタ（_MACRO_KEYWORDS）で抽出、最大件数制限を実装。
    - OpenAI 呼び出しでのリトライ/バックオフ、API 失敗時は macro_sentiment=0.0 でフェイルセーフ継続。
    - レジームスコア合成と閾値判定、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - テスト用に _call_openai_api を分離しているためモジュール結合を低減。

- データ（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた JPX カレンダー（祝日／半日／SQ日）の管理ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB 未取得時は曜日ベース（土日非営業）でフォールバックする堅牢な実装。
    - next/prev_trading_day は最大探索日数制限（_MAX_SEARCH_DAYS）を設定して無限ループを防止。
    - calendar_update_job を実装（J-Quants クライアントから差分取得、バックフィル、健全性チェック、冪等保存）。外部 jquants_client を使用。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラー管理を含む）。
    - 差分更新、バックフィル、品質チェック連携の設計方針に基づいたユーティリティ群を実装。
    - DuckDB のテーブル存在チェックや最大日付取得ヘルパーなどを提供。
    - デフォルト backfill、カレンダー先読み等の定義を加え、J-Quants データ取り込みの土台を実装。
  - data パッケージから ETLResult を再エクスポート（kabusys.data.etl）。

- リサーチ（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M）、200日 MA 乖離、ATR/ボラティリティ、出来高・売買代金指標、PER/ROE（raw_financials から）を DuckDB 上の SQL と Python で計算する関数群を実装。
    - データ不足時は None を返す方針。全関数は prices_daily / raw_financials のみ参照する点を保証。
  - feature_exploration
    - 将来リターン calc_forward_returns（任意ホライズン）、IC（スピアマンランク相関）calc_ic、ランク変換 rank、統計サマリー factor_summary を実装。
    - ランクの ties は平均ランクで処理。浮動小数丸めでの ties 検出漏れ対策（round を使用）。
  - research パッケージの __init__ で主要関数を再公開。

改良点 / 設計方針の明示
- ルックアヘッドバイアス回避
  - AI スコアリングやファクター計算において datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計。
- フェイルセーフ設計
  - 外部 API 失敗時に処理を停止させない（デフォルト値で継続、ログ出力）。部分失敗が他データを破壊しないよう DB 書き込み設計を行っている。
- テスト容易性
  - OpenAI 呼び出し箇所を内部関数化し、unittest.mock.patch による差し替えを想定。
- DuckDB 互換性
  - executemany の空リスト問題や日付型の取り扱い（_to_date）など、DuckDB の実装差分を考慮した実装。

既知の制限 / 注意点
- OpenAI クライアント（gpt-4o-mini）への依存があるため API キー（OPENAI_API_KEY）が必要。各 API 呼び出し関数は api_key 引数で上書き可能。
- データベーススキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）に依存するため、初回利用時はスキーマ準備が必要。
- 一部の計算は十分な過去データがない場合に None や中立値（例: ma200_ratio=1.0, macro_sentiment=0.0）を返すため、運用側での後続処理はこれらを考慮すること。
- .env 自動ロードはプロジェクトルート検出に依存する（.git または pyproject.toml）。配布後や特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

破壊的変更
- なし（初回リリース）

セキュリティ
- なし

貢献
- このリリース以降の機能追加・不具合修正は CHANGELOG.md に追記してください。