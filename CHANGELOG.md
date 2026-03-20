# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」準拠です。

全般ルール:
- バージョンは semver に準拠します。
- 各リリースにはカテゴリ（Added / Changed / Fixed / Security / Deprecated / Removed / Performance / Known limitations 等）を付与します。

## [Unreleased]
（未リリースの変更はここに記載）

## [0.1.0] - 2026-03-20
初回公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージ初期構成を追加。公開 API を定義（data, strategy, execution, monitoring を __all__ に含む）。
  - バージョン番号を `__version__ = "0.1.0"` に設定。

- 設定/環境変数管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env 文字列パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - Settings クラスを提供し、各種必須/任意設定に対するプロパティを追加（J-Quants トークン、kabu API 設定、Slack トークン/チャンネル、DB パス、環境・ログレベル判定ユーティリティ等）。
  - env／log_level の許容値チェックと is_live/is_paper/is_dev の簡易判定を実装。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント実装。
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - HTTP リトライ（指数バックオフ、最大 3 回、408/429/5xx のリトライ対象）、429 の Retry-After を尊重。
    - 401 受信時は ID トークンを自動リフレッシュして再試行（再帰防止）。
    - ページネーション対応の fetch_* 関数（株価 / 財務 / マーケットカレンダー）。
    - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装（ON CONFLICT DO UPDATE で重複を回避）。
    - データ変換ユーティリティ (_to_float / _to_int) により堅牢に数値を扱う。
    - fetched_at を UTC ISO8601 形式で格納し、データ取得時点をトレース可能に。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集モジュールを追加。
    - デフォルト RSS ソースを定義（例: Yahoo Finance）。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
    - 受信サイズ上限（10MB）や XML パースに対する defusedxml 使用などメモリ/セキュリティ対策を実装。
    - 記事ID を正規化 URL の SHA-256 ハッシュで生成して冪等性を確保。
    - バルク INSERT チャンク化・トランザクション集約により DB 書き込みを高速化。

- 研究用ファクタ計算（kabusys.research）
  - ファクター計算モジュールを追加（calc_momentum / calc_volatility / calc_value）。
    - prices_daily, raw_financials テーブルを参照し、モメンタム／ボラティリティ／バリュー系ファクターを算出。
    - 各関数は (date, code) ベースの dict リストを返す設計。
  - 特徴量探索ユーティリティ（feature_exploration）を追加。
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応、範囲チェック）。
    - IC（Spearman のランク相関）計算（calc_ic）およびランク変換（rank）。
    - ファクター統計サマリー（factor_summary）。
  - zscore_normalize をデータユーティリティとして公開（kabusys.data.stats から再エクスポート）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - 研究で計算した raw ファクター群を結合・ユニバースフィルタ・Z スコア正規化・クリッピング（±3）して features テーブルへ UPSERT（トランザクションで日付単位の置換）する build_features を実装。
  - ユニバースフィルタ: 最低株価（300円）・20日平均売買代金（5億円）を適用。
  - 正規化対象カラムやクリップ範囲などの定数を定義。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して最終スコア（final_score）を計算し、BUY / SELL シグナルを生成して signals テーブルへ書き込む generate_signals を実装。
    - 統合スコアのデフォルト重みを定義（momentum/value/volatility/liquidity/news）。
    - 重みのバリデーションと正規化（不正値は無視、合計が 1.0 に再スケール）。
    - スコア計算: 各コンポーネント（モメンタム、バリュー、ボラティリティ、流動性、ニュース）を個別に計算。欠損コンポーネントは中立 0.5 で補完。
    - スコア変換にシグモイド関数を利用。Z スコア（±3 クリップ）を [0,1] に変換。
    - Bear レジーム判定（ai_scores の regime_score の平均が負かつ十分なサンプル数がある場合に BUY を抑制）。
    - SELL シグナル（エグジット判定）: ストップロス（終値が avg_price に対して -8% 以下）や final_score が閾値未満の場合に判定。
    - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入）を保証。
  - ログ出力や警告により欠損データや異常重みを明示。

### Performance
- DuckDB クエリは集約/ウィンドウ関数を多用しており、必要データ範囲をカレンダーバッファで制限することでスキャン負荷を抑制。
- DB への一括挿入を executemany + トランザクションでまとめて実行。

### Security
- RSS の XML パースに defusedxml を使用して XML Bomb 等の攻撃に対処。
- URL 正規化時にトラッキングパラメータを除去し、SSRF のリスク低減のためスキーム・ホストに注意する実装思想（実装済みの検証/拒否の詳細はモジュール内に記載）。
- J-Quants クライアントではネットワークエラー時のリトライ、429 の Retry-After 尊重、トークン自動リフレッシュによる堅牢性向上。

### Known limitations / TODO
- signal_generator にて一部エグジット条件は未実装（コメントあり）:
  - トレーリングストップ（peak_price を参照する実装）
  - 時間決済（保有日数をベースとしたエグジット）
  これらは positions テーブルに追加のメタ情報（peak_price / entry_date 等）が必要。
- news_collector の銘柄コード紐付け（news_symbols への確実な連携）は設計書に記載の通りで、現状コードベースの一部のみが含まれている箇所があります（今後の拡張想定）。
- execution パッケージは初期化ファイルのみ（実際の発注ロジックは別途実装予定）。

### Developer notes
- 設定は環境変数に依存するため、テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動読み込みを抑制してください。
- DuckDB のテーブルスキーマ（prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals / market_calendar 等）は本パッケージの動作に必須です。スキーマの定義とマイグレーションは別途管理してください。

---

今後のリリースでは、以下を優先して対応予定です:
- execution 層（kabu ステーション連携、注文マネジメント）の実装
- 評価用ユニットテストの充実と CI の導入
- news_collector のシンボル自動紐付け強化、言語処理（簡易 NLP）導入
- トレーリングストップ・時間決済等のエグジットルール追加

（必要であれば CHANGELOG を英語版に翻訳します）