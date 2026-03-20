CHANGELOG
=========

すべての公開リリースは「Keep a Changelog」形式に準拠しています。  
日付は本コードベース解析日（2026-03-20）を用いています。

## [0.1.0] - 2026-03-20

Added
-----
- パッケージ初期公開（kabusys v0.1.0）。
- 基本パッケージ構成：
  - kabusys.data: データ取得・保存ユーティリティ群
  - kabusys.strategy: 特徴量作成・シグナル生成
  - kabusys.research: 研究用ファクター計算・解析ユーティリティ
  - kabusys.execution / kabusys.monitoring: 名前空間を確保（実装は分割可能）
- 環境設定 / 自動 .env ロード（src/kabusys/config.py）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込み。
  - 読み込み優先順位: OS 環境 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、インラインコメント等に対応。
  - Settings クラスを提供し、J-Quants トークン・kabu API パスワード・Slack 設定・DB パスなどの取得を行う。入力検証（KABUSYS_ENV / LOG_LEVEL）あり。
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - fetch_* 系関数: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）。
  - save_* 系関数: save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存、ON CONFLICT を使用）。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter 実装。
  - 再試行ロジック: 指数バックオフ（最大リトライ3回）、408/429/5xx を対象。429 の Retry-After ヘッダを考慮。
  - 認証: リフレッシュトークンからの id_token 取得（自動リフレッシュ処理、401 時に1回リトライ）。
  - データの fetched_at を UTC ISO 形式で記録（Look-ahead バイアス追跡用）。
  - レスポンス JSON デコードとエラーハンドリングを備えた安全な HTTP ユーティリティ。
  - 型変換ユーティリティ (_to_float / _to_int) による堅牢なデータ整形。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS からの記事収集フローの実装（既定ソースに Yahoo Finance を設定）。
  - 安全対策: defusedxml を利用した XML パース（XML Bomb 対策）、受信サイズ上限（10 MB）、HTTP/HTTPS のみ許可、SSRF を意識した検証を実装方針として記載。
  - URL 正規化: トラッキングパラメータ除去（utm_* 等）、スキーム/ホスト小文字化、フラグメント除去、クエリソート化。
  - 記事 ID は正規化 URL の SHA-256 の先頭を用いる方針（冪等性）。
  - DB 保存はバルク・チャンク化してトランザクションで実行、ON CONFLICT DO NOTHING による冪等保存。
- 研究用ファクター計算（src/kabusys/research/factor_research.py）
  - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を計算。データ不足時は None を返す。
  - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。
  - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新の報告日を使用）。
  - 全関数は DuckDB の prices_daily / raw_financials のみを参照し、外部 API へはアクセスしない設計。
- 研究用解析ユーティリティ（src/kabusys/research/feature_exploration.py）
  - calc_forward_returns: 指定日から各ホライズン（デフォルト [1,5,21] 営業日）の将来リターンを一括取得（LEAD を使用）。
  - calc_ic: ファクター値と将来リターンの Spearman（ランク相関）を計算。サンプル不足（<3）→ None。
  - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - rank: 同順位は平均ランクにするランク付けユーティリティ（浮動小数丸めを考慮）。
- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features: research モジュールの calc_* を組み合わせて features テーブルを作成。
  - ユニバースフィルタ実装: 最低株価（300 円）、20 日平均売買代金 >= 5億円。
  - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）→ ±3 でクリップ。
  - DuckDB トランザクションで日付単位の置換（冪等性）。
  - ルックアヘッドバイアス防止のため target_date 時点のデータのみを使用。
- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals: features / ai_scores / positions を参照し BUY/SELL シグナルを生成して signals テーブルへ保存（冪等）。
  - スコア算出: momentum/value/volatility/liquidity/news の各コンポーネントを計算し、重み付けで final_score を作成。デフォルト重みを実装（momentum 0.40 等）。ユーザー重みのバリデーション・再スケーリングを実装。
  - Sigmoid 変換・欠損値補完（中立 0.5）を採用して欠損時の不当な降格を防止。
  - Bear レジーム検知: ai_scores の regime_score 平均が負かつサンプル数閾値（3）以上で BUY を抑制。
  - エグジット判定（_generate_sell_signals）: ストップロス（-8%）とスコア低下による SELL。価格欠損時の安全処理（判定スキップ）。
  - BUY と SELL の優先ルール（SELL 優先、BUY のランク再付与）を実装。
  - DuckDB トランザクションで日付単位の置換（冪等性）。
- パッケージ API エクスポート
  - kabusys.strategy に build_features / generate_signals を __all__ で公開。
  - kabusys.research に主要関数群（calc_* / zscore_normalize / calc_forward_returns / calc_ic / factor_summary / rank）を公開。

Security
--------
- defusedxml の使用や受信サイズ制限、HTTP スキームチェック等、外部入力に対するセキュリティ対策がニュース収集モジュールで取られています。
- J-Quants クライアントでトークン自動リフレッシュは 1 回までに制限し、無限再帰を回避する実装。

Known limitations / Notes
-------------------------
- 実行層（execution）や監視（monitoring）は名前空間を用意しているが、発注ロジックや外部注文 API への接続等の実装はこの初期版では含まれていません。
- features / signals / raw_* / raw_financials / market_calendar 等の DuckDB テーブル定義は本リリースに含まれないため、導入時はスキーマ定義（DDL）を作成する必要があります。
- ニュース記事の銘柄紐付け（news_symbols への関連付け）や一部戦略の追加条件（トレーリングストップ、時間決済）は未実装で TODO として言及されています。
- calc_forward_returns の horizons は営業日ベース（連続レコード数）を前提としており、最大 252 日の制限があります。
- 設定値は環境変数ベース（.env/.env.local）で提供される設計です。.env.example を参考にセットアップしてください。

Breaking Changes
----------------
- 初回リリースのため既存ユーザー向けの破壊的変更はありません。

Migration / Upgrade notes
-------------------------
- 新規導入時は以下を確認してください：
  - 必要環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を設定すること。
  - DuckDB / SQLite を格納するファイルパス（DUCKDB_PATH, SQLITE_PATH）を適切にセットすること。
  - プロジェクトルートに .env/.env.local を配置すると自動読み込みされる。CI / テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化可能。
  - raw_prices/raw_financials/features/signals/ai_scores/positions/market_calendar 等のテーブルスキーマを用意すること（DDL は別途提供想定）。

Contact / Contribution
----------------------
- バグ報告、機能要望、改善 PR はプロジェクトの issue / PR で受け付けてください。README / ドキュメントに従って環境構築を行ってください。

----  
（この CHANGELOG は配布されたコードの内容から推測して作成しています。実際のリリースノート作成時はテスト・リリース事実・DDL・マイグレーション手順等をあわせて更新してください。）