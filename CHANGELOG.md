# Changelog

すべての重要な変更点をここに記録します。This project adheres to "Keep a Changelog" と Semantic Versioning を想定しています。

## [0.1.0] - 2026-03-20

Released 初期リリース。主要な機能群（データ取得・保存、ファクター計算、特徴量作成、シグナル生成、設定管理、ニュース収集）を実装しました。

### Added
- パッケージ基盤
  - kabusys パッケージ初期実装。モジュール構成:
    - kabusys.config: 環境変数 / .env 管理
    - kabusys.data: J-Quants API クライアント、ニュース収集ユーティリティ
    - kabusys.research: ファクター計算・特徴量解析ユーティリティ
    - kabusys.strategy: 特徴量生成・シグナル生成ロジック
    - kabusys.execution: プレースホルダ（将来の発注実装用）
  - パッケージバージョンは `__version__ = "0.1.0"`。

- 設定管理（kabusys.config）
  - プロジェクトルート自動検出（.git または pyproject.toml を探索）に基づく .env 自動読み込みを実装（.env → .env.local の順に読み込み、.env.local は上書き）。  
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - .env パーサーの強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート対応（バックスラッシュエスケープ考慮）
    - インラインコメントの取り扱い（クォート内は無視、クォート外は '#' の前に空白/タブがある場合をコメントとみなす）
    - 読み込み失敗時の警告出力
  - Settings クラスを提供（J-Quants リフレッシュトークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、環境/ログレベル検証、is_live/is_paper/is_dev 等のユーティリティ）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 固定間隔スロットリングによるレート制御（120 req/min を想定する RateLimiter 実装）。
  - 冪等・堅牢な HTTP 実装:
    - 指数バックオフによるリトライ（最大 3 回、408/429/5xx を対象）。
    - 401 Unauthorized 受信時は自動でリフレッシュトークンから ID トークンを更新して 1 回リトライ（トークンキャッシュをモジュール内で保持）。
    - ページネーション対応（pagination_key を用いたループ）。
    - JSON デコード失敗やネットワークエラーに対する例外メッセージ強化。
  - データ取得 API:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存ユーティリティ（冪等）:
    - save_daily_quotes / save_financial_statements / save_market_calendar：ON CONFLICT / DO UPDATE を用いた upsert 実装。
    - データ型変換ユーティリティ (_to_float / _to_int) を提供。
    - PK 欠損行はスキップし、その数を警告ログで通知。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集パイプライン。デフォルトソースに Yahoo Japan ビジネス RSS を設定。
  - セキュリティ・堅牢性強化:
    - defusedxml による XML パース（XML Bomb 対策）。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を軽減。
    - URL 正規化（クエリの追跡パラメータ削除、スキーム/ホスト正規化、フラグメント削除、クエリソート）。
    - 記事ID は URL 正規化後の SHA-256 ハッシュを想定し冪等性を保証（設計ドキュメントに基づく）。
  - DB 保存はバルク INSERT をチャンク化して行い、挿入件数を正確に取得する設計。

- 研究用ユーティリティ（kabusys.research）
  - factor_research: prices_daily / raw_financials を参照する SQL ベースのファクター計算を実装。
    - calc_momentum: mom_1m、mom_3m、mom_6m、ma200_dev（200日移動平均乖離）を算出。ウィンドウ未満は None。
    - calc_volatility: ATR 20 日、相対 ATR (atr_pct)、20日平均売買代金、出来高比率を算出。データ不足は None。
    - calc_value: raw_financials の直近財務情報を結合して PER / ROE を算出（EPS=0 は None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一回の SQL クエリで取得。
    - calc_ic: スピアマンのランク相関（IC）を実装（有効サンプルが 3 未満なら None）。
    - rank: 同順位は平均ランクにする実装（丸め処理で ties 検出を安定化）。
    - factor_summary: count/mean/std/min/max/median を純粋 Python で算出（None を除外）。

- 特徴量生成（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date) を実装:
    - research の calc_* から生ファクターを取得しマージ。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5億円）を適用。
    - 指定カラムを zscore 正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップして外れ値の影響を抑制。
    - DuckDB の features テーブルへ日付単位で置換（BEGIN/DELETE/INSERT/COMMIT でトランザクションを保証、エラー時は ROLLBACK を試行）。
    - アップサート済み銘柄数を返す。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装:
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算。
    - Z スコアはシグモイド変換で [0,1] にマップ。欠損コンポーネントは中立値 0.5 で補完。
    - weights はデフォルト重み（momentum 0.40 等）を持ち、ユーザ指定は検証・補完・正規化して合計を 1.0 に再スケール。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数条件）により BUY を抑制。
    - SELL 条件（ストップロス: -8% 以下、final_score < threshold）を positions と最新価格から判定。価格欠損時は SELL 判定をスキップしてログ出力。
    - signals テーブルへ日付単位で置換（トランザクション処理、ROLLBACK 保護）。
    - BUY と SELL の優先ルール（SELL を優先して BUY から除外）を適用し、最終的なシグナル数を返す。

### Security
- XML パースに defusedxml を採用し、RSS の攻撃ベクタ（XML Bomb 等）を軽減。
- RSS/URL 処理でトラッキングパラメータの除去、スキームチェック等を設計に含め SSRF/トラッキング指標の影響を低減。
- J-Quants クライアントではタイムアウト、リトライ、429 の Retry-After 処理を扱い、API レート制御を実装。

### Internal / Implementation notes
- DuckDB を主要なデータストアとして想定し、SQL（ウィンドウ関数等）でパフォーマンス重視の処理を実装。
- 外部依存を最小化する方針（research の統計処理は標準ライブラリのみで実装）。
- ログ出力（warning/info/debug）を各所で行い、障害時のトレースを容易にしている。
- 一部モジュール（kabusys.execution）はプレースホルダで今後発注層を実装するための準備がある。

### Changed
- 初版のため該当なし。

### Fixed
- 初版のため該当なし。

### Breaking Changes
- 初版のため該当なし。

---

注: 上記はソースコードの実装内容から推測してまとめた CHANGELOG です。実際のリリースノート作成時は、テストの実施状況、既知の制約（例: 未実装のトレーリングストップや時間決済条件）、および運用上の注意事項を追記することを推奨します。