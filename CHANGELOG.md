Keep a Changelog に準拠した CHANGELOG.md

全ての変更はコードベースから推測して記載しています。初回リリースとしてまとめています。

Unreleased
----------
- なし

0.1.0 - 2026-03-20
------------------
Added
- パッケージ初期リリース。
- パッケージルート: kabusys.__init__ にバージョン情報と公開モジュール一覧を追加。
- 設定管理:
  - kabusys.config.Settings クラスを追加。環境変数経由で設定を取得するプロパティ群（J-Quants / kabuステーション / Slack / DB パス / 実行環境フラグ等）を提供。
  - .env 自動ロード機能を実装（.env, .env.local の優先順位、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
  - .env の行パーサ（_parse_env_line）を実装。コメント・export 形式・シングル/ダブルクォートおよびエスケープを適切に処理。
  - 必須環境変数未設定時にわかりやすいエラーメッセージを投げる _require 実装。
  - 設定値の検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）。
- Data 層:
  - kabusys.data.jquants_client: J-Quants API クライアントを実装。
    - 固定間隔のレート制御（_RateLimiter）、ページネーション対応、最大 3 回のリトライ（指数バックオフ）、HTTP 429 の Retry-After 尊重、401 の自動トークンリフレッシュ（get_id_token）を備えた堅牢なリクエスト処理。
    - ID トークンのモジュールレベルキャッシュ（_ID_TOKEN_CACHE）。
    - fetch_* 系関数: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）。
    - DuckDB への保存用関数: save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT による冪等保存）。
    - 型変換ユーティリティ（_to_float, _to_int）。
  - kabusys.data.news_collector: RSS ニュース収集モジュールを追加。
    - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント除去）、記事ID を正規化 URL のハッシュで生成する設計を採用。
    - XML パースに defusedxml を使用、受信サイズ制限（MAX_RESPONSE_BYTES）、バルク挿入チャンク処理、INSERT の冪等性を考慮した実装方針。
- Research 層:
  - kabusys.research.factor_research: モメンタム / ボラティリティ / バリューのファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB のウィンドウ関数を活用した高効率な計算。
    - データ不足時の None 処理、スキャン範囲のバッファ設計。
  - kabusys.research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク付けユーティリティ（rank）を実装。
  - kabusys.research.__init__: 主要な研究ユーティリティを再エクスポート。
- Strategy 層:
  - kabusys.strategy.feature_engineering: 研究で得た生ファクターを正規化・統合して features テーブルへ書き込む build_features を実装。
    - ユニバースフィルタ（最低株価 / 20日平均売買代金）、Z スコア正規化（zscore_normalize を利用）、±3 でのクリップ、日付単位での置換（トランザクション）を実装し冪等性を確保。
  - kabusys.strategy.signal_generator: features と ai_scores を用いて最終スコアを計算し BUY/SELL シグナルを生成する generate_signals を実装。
    - コンポーネントスコア（momentum / value / volatility / liquidity / news）の計算（シグモイド変換、欠損補完ルール）。
    - 重みのマージ・検証・正規化（デフォルト重みのフォールバック、無効入力の無視、合計が 1 でない場合の再スケール）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値以上で判定）による BUY 抑制。
    - エグジット判定（_generate_sell_signals）におけるストップロス（-8%）とスコア低下による SELL 判定、保有銘柄の価格欠損時の安全処理。
    - signals テーブルへの日付単位置換（トランザクション＋バルク挿入）による冪等性。
- 共通/設計:
  - DuckDB を前提とした SQL と Python の組み合わせで高パフォーマンス処理を実装。
  - ログ出力（logger）を各モジュールで利用し、計算件数や警告を記録。
  - ドキュメンテーション文字列に設計方針・期待動作を明記（ルックアヘッドバイアス回避、外部 API への不要な依存の排除 等）。
- その他:
  - kabusys.strategy.__init__ で build_features / generate_signals を再エクスポート。
  - execution パッケージのプレースホルダ（空の __init__.py）を追加（将来的な発注層の区分けを想定）。
  - 安全性に関する考慮点を各所に記載（XML パーサに defusedxml、受信上限、URL 正規化、トークンリフレッシュの無限再帰防止など）。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

Security
- RSS XML 処理に defusedxml を採用して XML BOM 等の攻撃を考慮。
- ニュースの URL 正規化・トラッキングパラメータ除去・受信サイズ制限により SSRF/DoS 対策方針を明示。
- J-Quants API クライアントでトークン自動リフレッシュ時の無限再帰を防止（allow_refresh フラグの導入）。

Notes / 今後の課題（コード内コメントより推測）
- signal_generator のエグジット条件にトレーリングストップや時間決済（保有日数）など未実装の条件があることを明記。
- news_collector における SSRF / IP 検査や実際の挿入処理の実装詳細はファイル内方針に依存（現状は設計方針が記載されている）。
- テスト容易性のために KABUSYS_DISABLE_AUTO_ENV_LOAD を利用できる点を提供。

貢献・バグ報告
- 本 CHANGELOG はコードベースから推測して作成しています。実際の変更履歴やリリースノートは開発者提供の情報で更新してください。