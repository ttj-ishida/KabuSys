# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 初回リリース
初版リリース。以下の主要コンポーネントと機能を追加しました。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョンを 0.1.0 として設定。
  - __all__ に主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出は .git または pyproject.toml を基準にし、CWD に依存しない探索を実現。
    - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD オプションを提供。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - .env パーサを実装（コメント行 / export 句 / クォート内エスケープ / 行末コメント処理 等に対応）。
  - Settings クラスを提供し、必須設定の取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_* 等）、デフォルト値（API ベース URL、DB パス等）、KABUSYS_ENV / LOG_LEVEL のバリデーション、環境判定ユーティリティ（is_live/is_paper/is_dev）を実装。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API レート制御（120 req/min）を行う固定間隔スロットリング RateLimiter を実装。
  - HTTP リクエストユーティリティを実装。ページネーション対応。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）を実装。
  - 401 Unauthorized を検出した場合の自動トークンリフレッシュ（1 回のみ）を実装。
  - get_id_token（リフレッシュトークンから idToken を取得）を実装。
  - データ取得関数を実装:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（マーケットカレンダー）
  - DuckDB への永続化ユーティリティを実装（冪等性確保のため ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes → raw_prices
    - save_financial_statements → raw_financials
    - save_market_calendar → market_calendar
  - 入力値パースユーティリティ（_to_float / _to_int）を実装し、不正データを安全に扱う。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を取得し raw_news に冪等保存する仕組みを追加。
  - URL 正規化機能（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）を実装。
  - セキュリティ対策: defusedxml を用いた XML パーシング、レスポンスサイズ上限（10MB）などの保護方針を導入。
  - 記事 ID を URL の正規化後ハッシュで生成して冪等性を担保。
  - バルク INSERT のチャンク化による DB 負荷軽減、INSERT RETURNING による実挿入件数把握（設計）。

- 研究用ファクター計算（kabusys.research.factor_research）
  - モメンタムファクター calc_momentum（1M/3M/6M リターン、MA200 乖離）を実装。
  - ボラティリティ/流動性ファクター calc_volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）を実装。
  - バリューファクター calc_value（直近財務データから PER / ROE）を実装。
  - prices_daily / raw_financials のみを参照する形で実装し、ルックアヘッドバイアスを避ける設計。

- 研究支援ユーティリティ（kabusys.research.feature_exploration）
  - calc_forward_returns（指定ホライズン先の将来リターン計算、複数ホライズン対応）。
  - calc_ic（ファクターと将来リターンの Spearman ランク相関（IC）計算）。
  - factor_summary（各ファクター列の基本統計量計算）。
  - rank（同順位は平均ランクを与えるランク変換ユーティリティ）。
  - 外部依存を抑え、DuckDB を想定した実装。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research の生ファクターを取得して統合・正規化し、features テーブルへ日付単位で安全に置換（トランザクション＋バルク挿入）する build_features を実装。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を実装。
  - Z スコア正規化（外部 zscore_normalize を利用）と ±3 でのクリッピングを適用。
  - 冪等性（対象日分を削除してから挿入）を担保。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出し、重み付け合算で final_score を計算する generate_signals を実装。
  - スコア変換にシグモイド関数を使用、欠損コンポーネントは中立値 0.5 で補完。
  - 重みのユーザ指定を許容し、妥当性チェックと合計スケーリングを実装（デフォルト重みは StrategyModel.md に準拠）。
  - Bear レジーム判定（ai_scores の regime_score の平均が負 → BUY を抑制）を実装。
  - エグジット判定（SELL）を実装:
    - ストップロス（終値/avg_price - 1 < -8%）
    - スコア低下（final_score が閾値未満）
    - 保有銘柄の価格欠損時の処理（判定スキップ）や features に存在しない場合の扱いを定義。
  - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）して冪等性を担保。

### Security
- XML パースに defusedxml を使用（ニュース収集）。
- ニュース取得での受信サイズ上限や URL 正規化により SSRF / DoS のリスクを低減。
- J-Quants クライアントはトークン管理・自動リフレッシュ・レート制御・リトライを組み合わせ、外部 API 呼び出しの堅牢性を確保。

### Known limitations / Not implemented
- signal_generator 内で言及されている一部のエグジット条件は未実装（トレーリングストップ、時間決済等は positions に peak_price / entry_date 等の情報が必要）。
- 一部ユーティリティ（例: data.stats の実装詳細）は本リリースで依存として参照されており、別モジュールで提供されることを前提としています。

### Changed
- 初版のため該当なし。

### Fixed
- 初版のため該当なし。

### Removed
- 初版のため該当なし。

### Deprecated
- 初版のため該当なし。

### Notes
- 各 DB 操作は DuckDB 接続を引数に取り、トランザクションとバルク操作で原子性・効率性を担保する設計になっています。
- ドキュメント（モジュール内 docstring）に StrategyModel.md / DataPlatform.md 等外部設計書へ言及があり、実装はこれらの仕様に従っています。