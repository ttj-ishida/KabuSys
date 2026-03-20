# Changelog

すべての重要な変更点はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

全般:
- バージョン番号はパッケージ top-level の __version__ に従います（現行: 0.1.0）。

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システムのコアライブラリを実装しました。主な追加点は以下のとおりです。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys、トップレベルで data / strategy / execution / monitoring を公開。
  - バージョン: 0.1.0

- 環境設定 (kabusys.config)
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env 解析器を実装（export 形式、シングル/ダブルクォート、インラインコメント、エスケープ処理対応）。
  - 自動ロードを無効にするための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス等の設定取得を統一。
  - 必須設定は _require() により未設定時に明確な例外を発生させる。
  - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証ロジックを実装。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装（トークン取得、ページネーション対応の fetch 関数群）。
  - API レート制限対応（固定間隔スロットリング、デフォルト 120 req/min）。
  - リトライ（指数バックオフ、最大 3 回）および 401 時の自動トークンリフレッシュ（1 回限定）。
  - ページネーションの間でトークンキャッシュを共有。
  - DuckDB へ保存する save_* 関数を追加（raw_prices / raw_financials / market_calendar）。
    - ON CONFLICT（重複キー）での UPDATE により冪等性を担保。
    - fetched_at を UTC で記録（Look-ahead バイアス追跡目的）。
    - 型変換ユーティリティ _to_float / _to_int を提供し不正データを安全に扱う。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集用モジュールを追加（デフォルトソース: Yahoo Finance のビジネス RSS）。
  - 記事の正規化（URL トラッキングパラメータ除去、フラグメント除去、クエリソート）、記事 ID を正規化 URL の SHA-256 ハッシュで生成して冪等性を担保。
  - defusedxml を用いた XML パースで XML 攻撃に対する安全性を強化。
  - 受信サイズ上限（10MB）や URL 正規化など、メモリ・SSRF・トラッキング対策を考慮した実装。
  - DB へのバルク挿入をチャンク処理で行うなどパフォーマンスも配慮。

- リサーチ（研究）ツール群 (kabusys.research)
  - calc_momentum / calc_volatility / calc_value（ファクター計算）を実装（prices_daily / raw_financials を参照）。
  - calc_forward_returns（各ホライズンの将来リターン）、calc_ic（Spearman ランク相関による IC）、factor_summary、rank を実装。
  - 外部依存を増やさず DuckDB + 標準ライブラリのみで動作する設計。

- 特徴量生成 (kabusys.strategy.feature_engineering)
  - research の生ファクターを統合して features テーブルを作成・更新する build_features を実装。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
  - 指標の Z スコア正規化（zscore_normalize を使用）・±3 でクリップ。
  - 日付単位で削除→挿入するトランザクション処理により冪等性と原子性を保証。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して final_score を算出し、BUY/SELL シグナルを生成する generate_signals を実装。
  - 各コンポーネントスコア（momentum/value/volatility/liquidity/news）の算出ロジックを実装（シグモイド変換や欠損値は中立 0.5 で補完）。
  - ユーザー指定の weights は検証・補完・再スケールされる（負値・NaN 等は無視）。
  - Bear レジーム判定（AI の regime_score の平均が負かつ十分なサンプル数がある場合）により BUY シグナルを抑制。
  - SELL ロジックはストップロス（-8%）とスコア低下を実装。保有銘柄の価格欠損時は判定をスキップして誤クローズを防止。
  - signals テーブルへの書き込みは日付単位で置換し原子性を保証。

### 変更 (Changed)
- 初版のため過去リリースからの「変更」はありません（新規追加のみ）。

### 修正 (Fixed)
- 初版のため「修正」はありません。

### 削除 (Removed)
- 初版のため「削除」はありません。

### 非推奨 (Deprecated)
- なし。

### セキュリティ (Security)
- RSS の XML 解析に defusedxml を利用して XML ベースの攻撃を軽減。
- ニュース URL の正規化によりトラッキングパラメータを除去し、ID 生成の一貫性を確保。
- J-Quants クライアントはレート制御とリトライ戦略を実装し、外部 API の異常時に過剰な再試行を抑制。

### 既知の制限 / 未実装の機能
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等の情報が追加されない限り未実装。
- news_collector の詳細な SSRF/IP フィルタリング実装は意図されているが、本リリースのコード断片から完全な網羅は要確認（将来強化予定）。
- calc_forward_returns はホライズンに対して営業日上限チェック（<=252 日）を行うが、カレンダー/営業日の差異はバッファで吸収する設計。

---

今後のリリースでは、テスト用フックの追加、ドキュメント整備、追加のエグジット条件（トレーリングストップ等）、Monitoring / Execution 層の接続（発注 API 統合）を予定しています。