CHANGELOG
=========
すべての変更は Keep a Changelog の形式に準拠します。
リリース日付はコードベースの最終更新を元に記載しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティに関する重要事項
- Notes: 実装上の注意点 / 未実装の機能

Unreleased
----------
（なし）

[0.1.0] - 2026-03-20
-------------------

Added
- パッケージ基礎
  - kabusys パッケージ初版を追加。モジュール公開シンボルを __all__ で定義（data, strategy, execution, monitoring）。
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 環境設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする仕組みを追加。
  - 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーを強化:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応
    - インラインコメント処理（クォート外かつ直前が空白の # をコメントと認識）
    - 無効行やキー欠損時の安全なスキップ
  - .env 読み込み時の上書きポリシー:
    - OS 環境変数を保護する protected セットを用意し .env.local の上書き挙動を制御
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 実行環境（development/paper_trading/live）などの設定をプロパティ経由で取得。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装:
    - 固定間隔のスロットリングによる RateLimiter（120 req/min）を実装。
    - HTTP リトライ（指数バックオフ、最大3回）と 408/429/5xx ハンドリングを実装。
    - 401 応答時にリフレッシュトークンで自動的に ID トークンを再取得して 1 回再試行する機能を追加。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）を実装。
  - DuckDB への冪等保存関数を追加:
    - save_daily_quotes / save_financial_statements / save_market_calendar: ON CONFLICT DO UPDATE で重複を排除して保存。
    - 取得日時（fetched_at）を UTC ISO 形式で記録し、データがいつ取得されたかを追跡可能に。
    - 型安全な変換ユーティリティ (_to_float, _to_int) を実装し、不正な値は None として扱う。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news に保存するモジュールを追加。
  - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント削除、小文字化）を実装。
  - 記事IDは正規化後 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
  - defusedxml を用いた XML パースで XML Bomb 等を軽減。
  - 受信サイズ上限（MAX_RESPONSE_BYTES=10MB）、バルク INSERT チャンク化（_INSERT_CHUNK_SIZE）などリソース保護の実装。

- リサーチ / ファクター計算 (kabusys.research)
  - 研究用ユーティリティ群を追加:
    - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照してファクターを計算）。
    - zscore_normalize を再利用可能 API として公開（data.stats からインポート）。
    - calc_forward_returns（将来リターン: デフォルト [1,5,21]）、calc_ic（Spearman IC）、factor_summary、rank を実装。
  - 実装方針として pandas 等の外部依存を持たず、DuckDB クエリ + 標準ライブラリで完結する実装。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - 研究で計算された生ファクターを正規化・合成して features テーブルへ保存する build_features を実装。
  - ユニバースフィルタ:
    - 最低株価 _MIN_PRICE = 300 円
    - 20日平均売買代金 _MIN_TURNOVER = 5e8（5 億円）
  - 正規化: 指定カラムを Z スコアで正規化し ±3 でクリップ。
  - 書き込みは日付単位の置換（DELETE + bulk INSERT）をトランザクションで実行して原子性を保証。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成する generate_signals を実装。
  - スコア計算:
    - momentum/value/volatility/liquidity/news の重み付け集約（デフォルト重みを定義）。
    - 重みのバリデーション（未知キーの無視、NaN/Inf/負値のスキップ、合計が 1.0 でなければ再スケール）。
    - コンポーネント欠損は中立値 0.5 で補完（欠損銘柄の不当な降格を防止）。
  - Bear レジーム判定: ai_scores の regime_score の平均が負でかつ十分なサンプル数がある場合に BUY を抑制。
  - SELL 条件（実装済み）:
    - ストップロス（終値 / avg_price - 1 < -8%）
    - final_score が閾値未満（score_drop）
  - SELL 優先ポリシー: SELL 対象は BUY から除外し、BUY のランクを再付与。
  - signals テーブルへの日付単位置換をトランザクションで実行。

Changed
- なし（初版リリース）

Fixed
- なし（初版リリース）

Security
- 環境変数読み込み時:
  - OS 環境変数を保護する仕組みを導入。意図しない上書きを防止。
- news_collector:
  - defusedxml による安全な XML パースを採用。
  - 最大受信バイト数の上限設定でメモリ DoS を緩和。
  - URL 正規化とトラッキングパラメータ除去を実装（追跡パラメータによる誤検知・重複を低減）。
- jquants_client:
  - レートリミット、リトライ、トークン自動リフレッシュを実装し API エラー・レート制限に対する堅牢性を向上。

Notes (設計上の注意 / 未実装事項)
- generate_signals のエグジット条件について、トレーリングストップ（peak_price に基づく -10%）と時間決済（保有 60 営業日超過）は未実装（positions テーブルへ peak_price / entry_date の保存が必要）。
- 一部モジュールは DuckDB 上の特定テーブル（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar 等）の存在を前提にしています。テーブルスキーマの準備が必要です。
- news_collector モジュール内で SSRF / IP 検査やソケットレベルの追加検証を行うためのインポート（ipaddress, socket 等）がある一方で、抜粋コードでは全ての検査処理が示されていないため、運用時は外部入力に対する追加的なバリデーションを検討してください。
- .env 自動読み込みはプロジェクトルート検出に依存するため、パッケージ配布後や非標準配置では KABUSYS_DISABLE_AUTO_ENV_LOAD の設定や明示的な環境注入を行ってください。

References
- パッケージバージョンは src/kabusys/__init__.py の __version__ に一致します（0.1.0）。
- 実装上の仕様・設計方針は各モジュールの docstring に記載されています。