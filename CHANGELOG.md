# Changelog

すべての注目すべき変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システムのコアライブラリを提供します。主な機能は以下の通りです。

### Added
- パッケージ基礎
  - kabusys パッケージ初版を追加。サブパッケージ: data, strategy, execution, monitoring（execution は初期は空）。
  - パッケージバージョンを 0.1.0 に設定。

- 設定／環境変数管理（kabusys.config）
  - .env ファイル自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォートのエスケープ処理、行内コメントの扱い等を考慮）。
  - 環境変数必須チェック用のヘルパー _require と Settings クラスを提供。主なプロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパス）
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント実装:
    - 固定間隔スロットリングによるレート制御（120 req/min, _RateLimiter）。
    - 再試行ロジック（最大 3 回、指数バックオフ、408/429/5xx を対象）。
    - 401 受信時はリフレッシュトークンで id_token を自動更新して 1 回リトライ。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - レスポンス JSON のデコード検査とエラーハンドリング。
  - DuckDB への保存ユーティリティ:
    - raw_prices / raw_financials / market_calendar への冪等保存（ON CONFLICT DO UPDATE / DO NOTHING を使用）。
    - 型安全な変換ユーティリティ _to_float / _to_int を提供。
    - 市場カレンダー保存時に is_trading_day / is_half_day / is_sq_day を判定して保存。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集と前処理機能（デフォルトソース: Yahoo Finance ビジネス RSS を含む）。
  - 記事 ID を URL 正規化後の SHA-256 ハッシュで生成（冪等性確保）。
  - URL 正規化でトラッキングパラメータ（utm_*, fbclid, gclid 等）やフラグメントを除去、クエリをソート。
  - defusedxml を利用した XML パース（XML Bomb 等の防御）。
  - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）や SSRF／不正スキームの防止を考慮した実装。
  - バルク INSERT チャンク処理・トランザクション最適化を想定（INSERT RETURNING 等の利用を想定）。

- 研究（research）
  - factor_research: モメンタム／ボラティリティ／バリュー計算を実装。
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離）を算出。
    - calc_volatility: 20 日 ATR、atr_pct、avg_turnover、volume_ratio を算出。
    - calc_value: target_date 以前の最新財務データと株価から PER/ROE を算出。
    - 各関数は DuckDB の prices_daily / raw_financials を参照し、欠損やデータ不足時に None を返す扱いを採用。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト 1,5,21 営業日）で将来リターンを一括取得。
    - calc_ic: スピアマンのランク相関（IC）を計算する実装（ties は平均ランク）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
    - rank ユーティリティ（同順位は平均ランク）。
  - research パッケージ初期エクスポートを追加。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features を実装:
    - research 側の calc_momentum/calc_volatility/calc_value を統合。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定カラムについて Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）し ±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE + INSERT をトランザクションで行い冪等を確保）。
    - ロギングで処理件数を報告。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals を実装:
    - features / ai_scores / positions を参照して銘柄ごとのコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換・欠損補完（欠損コンポーネントは中立 0.5）を採用。
    - デフォルト重みとユーザー指定重みのマージ（不正値は無視、合計が 1 でない場合は再スケール）。
    - Bear レジーム判定（ai_scores の regime_score の平均が負でサンプル数閾値以上の場合）により BUY を抑制。
    - BUY 生成閾値（デフォルト 0.60）を超えた銘柄を BUY、保有ポジションに対してストップロス（-8%）／スコア低下で SELL を生成。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）と日付単位の置換をトランザクションで実施（冪等性）。
    - ロギングで BUY/SELL 件数を報告。

### Fixed
- （初回リリースのため過去のバグ修正履歴はなし。実装内で想定されるエッジケース（JSON デコード失敗、PK 欠損レコードのスキップ、価格欠損時の SELL 判定スキップなど）に対する注意喚起とログ出力を多数追加。）

### Security
- news_collector で defusedxml を使用し XML による攻撃（XML Bomb 等）対策を実施。
- RSS URL 正規化時に HTTP/HTTPS スキームのみを許可することを想定し、SSRF のリスクを軽減する設計（コメント・実装上の注記あり）。
- J-Quants クライアントで認証トークンの扱いに注意し、トークンリフレッシュ／失敗時の安全な挙動を実装。

### Notes / Migration
- 本ライブラリは DuckDB の特定テーブル（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar 等）を参照／更新します。利用前にスキーマが存在することを確認してください。
- Settings に定義された必須環境変数（JQUANTS_REFRESH_TOKEN 等）未設定時は起動時に ValueError を送出します。`.env.example` を参考に .env を準備してください。
- news_collector の RSS 処理や jquants_client の外部 API 呼び出しはネットワーク IO を伴うため、実行環境のネットワーク設定やレート制限に注意してください。

---

（この CHANGELOG はコードベースの内容から推測して作成しています。実運用では実際のコミット履歴・リリース日・既知のバグ修正履歴を基に更新してください。）