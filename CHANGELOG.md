# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

最新リリース
------------

### [0.1.0] - 2026-03-19

初回公開リリース。以下の主要機能・モジュールを実装しています。

Added
- パッケージ基盤
  - kabusys パッケージ初期化（バージョン 0.1.0、エクスポート: data, strategy, execution, monitoring）。
- 設定 / 環境変数管理（kabusys.config）
  - .env/.env.local 自動読み込み（プロジェクトルートを .git / pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化。
  - export KEY=val 形式やクォート、インラインコメントなどに対応した .env パーサ実装。
  - 必須設定取得ヘルパーとバリデーション（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）。
  - 環境 (development/paper_trading/live) とログレベルの検証ユーティリティ。
  - デフォルト DB パス設定（DUCKDB_PATH / SQLITE_PATH）。
- データ取り込みクライアント（kabusys.data.jquants_client）
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）。
  - 固定間隔スロットリングによるレート制御（120 req/min, _RateLimiter）。
  - リトライ（指数バックオフ、最大 3 回、408/429/5xx の再試行）、429 の Retry-After 優先。
  - 401 発生時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ。
  - ページネーション対応（pagination_key を用いたループ取得）。
  - DuckDB への冪等保存ユーティリティ（raw_prices / raw_financials / market_calendar に対する ON CONFLICT 更新）。
  - レスポンス → 型変換ユーティリティ（_to_float/_to_int）と入力検査（PK 欠損行のスキップ & ログ）。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集用モジュール（デフォルトソースに Yahoo Finance を設定）。
  - URL 正規化（utm_* 等のトラッキングパラメータ除去、スキーム/ホスト小文字化、クエリソート、フラグメント除去）。
  - セキュリティ対策: defusedxml による XML パース、受信最大バイト数制限（10MB）、HTTP スキーム検証、SSRF/DoS 緩和策。
  - 冪等保存（記事ID を正規化 URL の SHA-256 先頭等で生成、ON CONFLICT / INSERT チャンク化）。
- 研究用ファクター計算（kabusys.research）
  - calc_momentum / calc_volatility / calc_value を実装（prices_daily / raw_financials を参照）。
  - calc_forward_returns（複数ホライズンに対応、営業日近似のスキャン範囲最適化）。
  - calc_ic（Spearman のランク相関による IC 計算）と rank ユーティリティ（同順位は平均ランク）。
  - factor_summary（各ファクター列の基本統計量計算）。
  - 研究モジュールの設計方針は DuckDB のみ参照・本番 API にアクセスしないこと。
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research モジュールで計算した生ファクターをマージ・フィルタリングして features テーブルへ保存する build_features。
  - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を実装。
  - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）と ±3 でクリップ。
  - 日付単位の置換（DELETE→INSERT をトランザクションで実行）により冪等性と原子性を確保。
- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算し BUY/SELL シグナルを生成する generate_signals。
  - コンポーネントスコア: momentum/value/volatility/liquidity/news（シグモイド変換、欠損は中立 0.5 補完）。
  - デフォルト重みと閾値（DEFAULT_WEIGHTS、DEFAULT_THRESHOLD=0.60）を実装。ユーザ指定 weights の検証・正規化を実装。
  - Bear レジーム判定（ai_scores の regime_score 平均が負の場合、サンプル数閾値あり）で BUY を抑制。
  - エグジット（SELL）ロジック: ストップロス（-8%）とスコア低下を実装。価格欠損時は判定をスキップして誤クローズを回避。
  - signals テーブルへの日次置換（トランザクション処理）で冪等性を保証。
- ドキュメント的説明（各モジュールの docstring に設計方針・処理フローを明示）
  - ルックアヘッドバイアス防止、外部発注 API へ直接依存しない設計などを明記。

Security
- news_collector: defusedxml の採用や受信サイズ制限、URL スキーム検証など SSRF / XML Bomb / メモリ DoS に対する対策を実装。
- jquants_client: HTTP エラー・ネットワークエラーの再試行制御により一時的な失敗に対する堅牢性を向上。

Notes / 備考
- 必要な環境変数（未設定時は例外を投げる）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 自動 .env ロードはプロジェクトルートを .git / pyproject.toml で検出するため、配布環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化可能。
- DuckDB 側に想定されるテーブル（本実装で参照／書き込みする主要テーブル）:
  - raw_prices, raw_financials, market_calendar, raw_news, prices_daily, features, ai_scores, positions, signals, etc.
  - 各 SQL クエリ内で参照されるカラム名／主キー仕様に依存するため、既存スキーマとの互換性に注意してください。
- 未実装・今後の拡張余地（コード内コメントより）
  - signal_generator の SELL 条件でトレーリングストップや時間決済は未実装（positions に peak_price / entry_date が必要）。
  - 研究モジュールは外部ライブラリ非依存（標準ライブラリのみ）で実装しているため、大規模データ処理の最適化は今後の課題。

Changed
- 初回リリースのため変更履歴なし。

Fixed
- 初回リリースのため修正履歴なし。

Deprecated / Removed
- 初回リリースのため該当なし。

---

（今後のリリースでは Unreleased セクションを使用して作業中の変更を管理してください。）