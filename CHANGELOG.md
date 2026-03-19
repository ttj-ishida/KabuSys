# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
リリースバージョンは package の __version__ (= 0.1.0) に合わせています。

## [0.1.0] - 2026-03-19

### 追加 (Added)
- パッケージ初期リリース: 日本株自動売買システム "KabuSys" のコアモジュールを提供。
  - モジュール構成:
    - kabusys.config: 環境変数・設定管理
    - kabusys.data: データ取得・保存（J-Quants クライアント、ニュース収集）
    - kabusys.research: 研究用ファクター計算・探索ユーティリティ
    - kabusys.strategy: 特徴量生成とシグナル生成
    - kabusys.execution, kabusys.monitoring: 名前空間を公開（将来的な拡張用）
  - パッケージ公開 API:
    - build_features(conn, target_date) — 特徴量の構築・features テーブルへの UPSERT（strategy.feature_engineering）
    - generate_signals(conn, target_date, threshold=0.60, weights=None) — signals テーブルへの BUY/SELL シグナル生成（strategy.signal_generator）
    - 研究用 API: calc_momentum / calc_volatility / calc_value / zscore_normalize / calc_forward_returns / calc_ic / factor_summary / rank（kabusys.research）

- 環境設定機能（kabusys.config）
  - .env / .env.local の自動ロード機能を実装（読み込み優先順位: OS 環境変数 > .env.local > .env）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .git または pyproject.toml を基にプロジェクトルートを探索する実装（CWD 非依存）。
  - .env のパース機能強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理
    - インラインコメントの扱い（クォート有無での処理差分）
  - 必須設定取得用ヘルパー _require と Settings クラスを提供。主要環境変数:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live のいずれか、デフォルト: development）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアント実装:
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
    - get_id_token(refresh_token=None)（リフレッシュトークン -> idToken）
    - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存、ON CONFLICT DO UPDATE）
  - レート制限制御: 固定間隔スロットリングで 120 req/min を遵守（_RateLimiter）。
  - 再試行ロジック: 指数バックオフ採用、最大 3 回（対象: 408, 429, 5xx / ネットワークエラー）。429 の場合は Retry-After を優先。
  - 401 Unauthorized 受信時のトークン自動リフレッシュ（1 回のみ）と再試行機構を実装。ページネーション間でのトークンキャッシュを採用。
  - レスポンスの JSON デコード失敗やネットワークエラーに対する明示的な例外処理。
  - レスポンスデータ整形・型変換ユーティリティ: _to_float / _to_int（安全な None 返却・文字列数値ハンドリング）。

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得から raw_news 保存までのワークフローを実装（既定ソースに Yahoo Finance）。
  - セキュリティ・堅牢化:
    - defusedxml を用いた XML パース（XML Bomb 等の防御）
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）
    - HTTP/HTTPS 以外の URL 拒否（SSRF 対策）
    - 受信最大サイズ制限（MAX_RESPONSE_BYTES = 10 MB）でメモリ DoS を防止
    - 記事 ID は正規化 URL の SHA-256 ハッシュ先頭 32 文字で生成し冪等性を確保
    - DB へバルク挿入（チャンクサイズ、トランザクション）で効率化。ON CONFLICT DO NOTHING などの冪等保存を意図

- 研究用ファクター計算（kabusys.research.factor_research）
  - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均乖離）を計算
  - calc_volatility: 20 日 ATR（atr_20）・atr_pct（相対 ATR）・avg_turnover・volume_ratio を計算
  - calc_value: raw_financials の最新報告から PER / ROE を計算（価格は prices_daily）
  - 各関数とも DuckDB の prices_daily / raw_financials のみ参照し、結果は dict リストで返却

- 研究支援ツール（kabusys.research.feature_exploration）
  - calc_forward_returns(conn, target_date, horizons=[1,5,21])：複数ホライズンの将来リターンを一度に取得
  - calc_ic(factor_records, forward_records, factor_col, return_col)：Spearman の ρ（ランク相関）を実装（有効レコードが 3 未満の場合は None）
  - factor_summary(records, columns)：count/mean/std/min/max/median を計算
  - rank(values)：同順位は平均ランクで処理（浮動小数丸めで ties の検出漏れを防止）

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date)
    - research 側の calc_momentum / calc_volatility / calc_value を統合
    - ユニバースフィルタ: 株価 >= 300 円、20 日平均売買代金 >= 5億円
    - 正規化: zscore_normalize を利用、対象カラムを Z スコア正規化し ±3 でクリップ
    - features テーブルへ日付単位で置換（BEGIN / DELETE / INSERT / COMMIT による原子性）

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None)
    - features と ai_scores を統合して final_score を算出（component: momentum/value/volatility/liquidity/news）
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10（合計 1.0 に正規化）
    - スコア変換: 各ファクターは Z スコア（±3 クリップ済み）をシグモイド変換して [0,1] にマッピング
    - AI スコアが無い銘柄に対しては中立値 0.5 で補完
    - Bear レジーム判定: ai_scores の regime_score 平均が負 ⇒ BUY シグナルを抑制（サンプル数閾値あり）
    - SELL（エグジット）判定:
      - ストップロス: 終値 / avg_price - 1 <= -0.08（-8%）
      - final_score < threshold
      - positions テーブルの価格欠損時には SELL 判定をスキップして誤クローズを回避
    - signals テーブルへ日付単位で置換（トランザクション + バルク挿入）
    - BUY と SELL の同一銘柄は SELL を優先し BUY から除外、BUY はランク再付与

### 仕様メモ / 注意点 (Notes)
- DB スキーマ期待:
  - prices_daily, raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals, raw_news 等のテーブルが前提。
  - 特に positions テーブルは avg_price / position_size が必要（エグジット判定に利用）。将来的に peak_price / entry_date を追加すればトレーリングストップ等を実装可能。
- 環境変数の必須項目を満たしていない場合は Settings のプロパティアクセス時に ValueError が発生します（例: JQUANTS_REFRESH_TOKEN 等）。
- generate_signals の weights 引数:
  - 未知キー・非数値・負値・NaN/Inf は無視され、既知キーに対してのみ反映される。
  - 合計が 1.0 でなければ自動的に再スケールまたは _DEFAULT_WEIGHTS にフォールバックする。
- jquants_client のレート制限は固定間隔スロットリング (120 req/min) を採用しているため、高頻度の並列呼び出しでは全体のスループットを考慮してください。
- news_collector はトラッキングパラメータの除去や URL 正規化を行いますが、外部 RSS の形式差異や不正なフィードに対してはログ出力を行いスキップします。

### セキュリティ関連 (Security)
- RSS パースに defusedxml を使用（XML ベースの攻撃緩和）。
- ニュースニュースや外部 URL の処理において、受信サイズ制限・スキーム制限・トラッキング除去等の安全策を講じています。
- J-Quants API 呼び出しにおける認証トークン管理はモジュール内でキャッシュ・自動更新を行い、トークン漏洩リスクを低減するための工夫（ただし運用時は環境変数管理に注意してください）。

### 既知の未実装・制限 (Known limitations)
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は positions に peak_price / entry_date 等の情報が追加されるまで未実装。
- 一部の統計系関数は外部依存（pandas 等）を避けるため純粋 Python 実装となっており、大規模データでのパフォーマンス調整が今後の課題。
- news_collector の記事 ID は正規化 URL のハッシュを利用しますが、同一記事の多様なURL表現や微妙な差異を完全に吸収できない場合があります。

---

今後の予定（例）
- execution 層の実装（kabu API との接続・注文送信）
- モジュール単体テストと CI/CD の整備
- モニタリング / Slack 通知機能の追加（Settings に Slack 設定あり、今後連携予定）