CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-20
--------------------

Added
- 初回リリース。日本株自動売買システム「KabuSys」の基本モジュールを導入。
- パッケージ構成（kabusys）とバージョン管理（__version__ = "0.1.0"）。
- 環境設定管理（kabusys.config.Settings）
  - .env/.env.local ファイルの自動読み込み（プロジェクトルート検出: .git または pyproject.toml 基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パース機能: export プレフィックス対応、クォート処理、インラインコメント処理。
  - 環境変数必須チェック（_require）と各種プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）。
  - KABUSYS_ENV / LOG_LEVEL の入力検証と is_live / is_paper / is_dev ヘルパー。
- データ取得/保存（kabusys.data）
  - J-Quants クライアント（jquants_client）
    - API 呼び出しユーティリティ（_request）：ページネーション対応、JSON デコードエラーハンドリング。
    - レート制限（_RateLimiter）: 120 req/min 固定間隔スロットリング。
    - リトライ実装（指数バックオフ、最大3回、408/429/5xx 対応）、429 の場合 Retry-After 優先。
    - 401 受信時にリフレッシュトークンで自動更新（get_id_token）して1回リトライ。
    - ID トークンのモジュールレベルキャッシュ(_ID_TOKEN_CACHE) と共有。
    - データ取得関数: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）：冪等性のため ON CONFLICT DO UPDATE を使用、PK 欠損行のスキップとログ出力、fetched_at を UTC で記録。
    - 型変換ユーティリティ _to_float / _to_int（厳格な変換ルール）。
  - ニュース収集（news_collector）
    - RSS 取得から raw_news へ冪等保存の基盤。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリパラメータソート）。
    - defusedxml による XML パースで XML-Bomb 等を防御。
    - HTTP/HTTPS 以外のスキームを拒否するなど SSRF 対策の設計方針。
    - 受信サイズ上限（MAX_RESPONSE_BYTES）設定によるメモリDoS対策。
    - バルク挿入チャンク化による性能対策。
- リサーチ機能（kabusys.research）
  - ファクター計算（factor_research）
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）、Value（PER、ROE）を DuckDB の prices_daily / raw_financials から計算。
    - データ不足時の None 扱い、営業日ベースのラグ処理、スキャン窓のバッファ設計。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応）と IC（calc_ic：Spearman ρ）計算、factor_summary（統計サマリー）、rank ユーティリティ。
    - rank は同順位を平均ランクで処理（丸めで ties を検出）。
  - zscore_normalize を再エクスポート（kabusys.data.stats 依存）。
- 戦略ロジック（kabusys.strategy）
  - 特徴量生成（feature_engineering.build_features）
    - research モジュールから生ファクターを取得（momentum / volatility / value）。
    - ユニバースフィルタ実装（最低株価300円、20日平均売買代金5億円）。
    - Z スコア正規化（指定カラム）、±3 でクリップ、features テーブルへ日付単位の置換（トランザクション + バルク挿入で原子性）。
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - 重み付けによる final_score 計算（デフォルト重みを提供）、ユーザ提供 weights の検証と正規化（合計を再スケール）。
    - Bear レジーム判定（AI の regime_score 平均が負かつサンプル数閾値を満たす場合）により BUY を抑制。
    - BUY閾値デフォルト 0.60、STOP-LOSS -8% 実装。
    - SELL 条件（ストップロス、スコア低下）実装。SELL 優先で BUY から除外しランク再付与。
    - signals テーブルへ日付単位の置換（トランザクション + バルク挿入で原子性）。
    - 欠損コンポーネントは中立値 0.5 で補完して不当な降格を防止。
- ロギングとエラーハンドリング
  - 各モジュールでログ出力を適切に実装（info/warning/debug）。
  - トランザクション失敗時のロールバック試行と警告ログ。

Security
- XML パースに defusedxml を採用（news_collector）。
- RSS/URL 正規化とスキームチェックで SSRF およびトラッキング除去を考慮。
- .env 読み込みで OS 環境変数を保護する protected 引数の導入（上書き禁止）。

Performance / Reliability
- J-Quants API クライアントで固定間隔の RateLimiter を導入しレート制限を厳守。
- 再試行（指数バックオフ、Retry-After 優先）および 401 の自動リフレッシュで堅牢性を向上。
- DuckDB への保存は一括実行・ON CONFLICT で冪等性を確保。DB 書き込みをトランザクションでまとめて原子性を担保。
- ニュースのバルク挿入でチャンク化し SQL パラメータ制限対策。

Fixed
- .env パーサーで以下を考慮:
  - export プレフィックス対応、クォート文字列中のバックスラッシュエスケープ対応、クォートなしでのコメント判定（直前が空白/タブ時のみ）。
  - 空行・コメント行を無視。
- データ保存処理で PK 欠損行をスキップし警告ログを出力するよう改善。
- 型変換ユーティリティで不正な数値表現を安全に None に変換（_to_float/_to_int）。

Notes / Known limitations
- signal_generator の一部のエグジット条件（トレーリングストップ、時間決済）は未実装（positions テーブルの追加情報が必要）。
- research モジュールは外部ライブラリ（pandas 等）に依存しない代わりに純 Python / DuckDB SQL により実装されているため、大規模データでの拡張は今後要検討。
- news_collector の具体的な RSS パーサ/紐付けロジック（news_symbols など）は追加実装が必要。

---

注: 上記はソースコード内の docstring・実装から推測してまとめた変更履歴（初期リリースの機能一覧）です。README やリリースノートと合わせて利用してください。