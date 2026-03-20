# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

最新リリース
- 0.1.0 / 2026-03-20

## [0.1.0] - 2026-03-20

### 追加 (Added)
- パッケージ基盤
  - 初期パッケージ公開。トップレベルパッケージ `kabusys`（バージョン 0.1.0）。
  - __all__ により public API を整理（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理 (`kabusys.config`)
  - .env 自動ロード機構を実装（プロジェクトルートは `.git` または `pyproject.toml` を基準に探索）。  
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト向け）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - .env ファイルの堅牢なパーサ `_parse_env_line` を実装：
    - `export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い、コメント行の無視などに対応。
  - `.env` 読み込み時に OS 側の既存環境変数を保護する `protected` 機能を実装。`override` フラグで上書き制御可能。
  - 必須環境変数検査 `_require` と `Settings` クラスを提供：
    - J-Quants / kabu ステーション / Slack / DB パス等の設定プロパティ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH）。
    - `KABUSYS_ENV` / `LOG_LEVEL` の検証ロジック（許容値チェック）、環境判定用プロパティ (`is_live`, `is_paper`, `is_dev`)。

- Data 層: J-Quants クライアント (`kabusys.data.jquants_client`)
  - J-Quants API クライアント実装（ページネーション対応）。
  - レート制御（固定間隔スロットリング）実装 `_RateLimiter`。デフォルト 120 req/min を守る。
  - 再試行ロジック（指数バックオフ、最大 3 回）とステータスベースの再試行判定（408/429/5xx）。429 の場合 `Retry-After` を尊重。
  - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライするロジックを実装（無限再帰防止）。
  - fetch 系関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を提供（ページネーション対応）。
  - DuckDB への保存（冪等）ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar は ON CONFLICT DO UPDATE を使用して重複を排除。
    - PK 欠損行のスキップとスキップ件数のログ出力。
  - 型変換ユーティリティ `_to_float` / `_to_int` を実装（安全変換、空値・不正値の扱い）。

- Data 層: ニュース収集 (`kabusys.data.news_collector`)
  - RSS フィード収集モジュールを追加（デフォルトで Yahoo Finance Business RSS を含む）。
  - セキュリティと堅牢性のための実装:
    - defusedxml を使用して XML Bomb 等の攻撃を防止。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を抑止。
    - URL 正規化（クエリのトラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）を実装。トラッキングパラメータのプレフィックス定義（utm_ 等）。
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を担保。
    - SSRF 等を防ぐため HTTP/HTTPS スキームの検証を想定（設計方針）。
  - DB 保存はバルク挿入・チャンク化（_INSERT_CHUNK_SIZE）とトランザクションで実行し、挿入件数の正確な取得を想定。

- Research 層 (`kabusys.research`)
  - ファクター計算と解析ユーティリティを追加:
    - factor_research: calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を使用）。
      - Momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200日MA 要件チェック）。
      - Volatility: 20日 ATR（atr_20, atr_pct）、avg_turnover、volume_ratio。true_range の NULL 伝播を明示的に制御。
      - Value: PER / ROE（最新の raw_financials を target_date 以前の最新レコードから結合）。
    - feature_exploration: calc_forward_returns（複数ホライズン対応、営業日バッファで範囲限定）、calc_ic（Spearman ランク相関）、factor_summary（count/mean/std/min/max/median）、rank（同順位は平均ランク）。
  - pandas 等の外部ライブラリに依存せず標準ライブラリ + DuckDB のみで実装。

- Strategy 層
  - 特徴量生成 (`kabusys.strategy.feature_engineering`)
    - research モジュールから得た raw ファクターをマージし、ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 正規化: 指定カラムを zscore_normalize（kabusys.data.stats より）で正規化、±3 でクリップして外れ値影響を低減。
    - features テーブルへ日付単位で置換（DELETE + バルク INSERT、トランザクションで原子性保証）。冪等性を確保。
  - シグナル生成 (`kabusys.strategy.signal_generator`)
    - features と ai_scores を統合して各種コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - component の変換に sigmoid を用い、欠損コンポーネントは中立 0.5 で補完。
    - デフォルト重みとしきい値: momentum 0.40 / value 0.20 / volatility 0.15 / liquidity 0.15 / news 0.10、BUY 閾値 0.60。ユーザー渡しの weights は検証・補完（負値や非数を無視）し合計が 1.0 でない場合は再スケール。
    - Bear レジーム判定: ai_scores の regime_score 平均が負で、十分なサンプル数（>=3）がある場合に BUY を抑制。
    - SELL（エグジット）判定実装:
      - ストップロス: 現在価格が平均取得価格に対して -8% 以下で即時 SELL（最優先）。
      - スコア低下: final_score が閾値未満の場合 SELL。
      - 価格欠損時は SELL 判定をスキップして誤クローズを回避（ログ警告）。
    - signals テーブルへの日付単位置換（DELETE + INSERT、トランザクションで原子性保証）。
    - SELL が確定した銘柄は BUY 候補から除外（SELL 優先ポリシー）。BUY はスコア降順でランク番号を振り直す。

### 変更 (Changed)
- 初期リリースのため過去リリースとの互換性対応はなし。

### 修正 (Fixed)
- 初期リリースのためなし（新規実装）。

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- ニュース XML のパースに defusedxml を採用し、XML 関連攻撃のリスク低減を行った。
- ニュース取得時の受信サイズ制限、URL 正規化、トラッキングパラメータ除去により情報漏洩や DoS リスクを低減。
- J-Quants クライアントは HTTP レスポンスの JSON デコード失敗やネットワーク例外時の安全なエラー処理、トークンの自動リフレッシュ処理を導入。

### 備考 / 使用上の注意
- DuckDB スキーマ（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar など）を事前に用意することを想定しています。  
- 自動 .env ロードはプロジェクトルートの検出に依存するため、配布パッケージ利用時は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定するか、適切に環境変数を設定してください。  
- AI スコアやポジションの一部ロジック（例: トレーリングストップ、時間決済、positions テーブルの peak_price/entry_date 利用）は将来的な拡張余地を残しています（注釈あり）。

---

今後のリリースでは、実運用向けの execution 層（kabu api 連携・注文実行）、監視/アラート機能（monitoring）、および追加のファクター・バックテスト機能を段階的に追加する予定です。