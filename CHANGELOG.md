CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注意: 下記はコードベース（src/kabusys/）の内容から推測して作成した初期リリースの変更履歴です。

[Unreleased]

0.1.0 - 2026-03-21
------------------

Added
- 初回リリース。日本株自動売買システム「KabuSys」のコア機能群を追加。
- パッケージ構成:
  - kabusys.config: 環境変数 / .env 管理
    - .git または pyproject.toml を基準にプロジェクトルートを自動検出して .env/.env.local を読み込む自動ロード機能（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env パーサは export 付き形式、シングル/ダブルクォート、エスケープ、行末コメント等に対応。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス等の設定プロパティを取得。KABUSYS_ENV / LOG_LEVEL の妥当性検査を実装。
  - kabusys.data.jquants_client: J-Quants API クライアント
    - 固定間隔のレートリミッタ（120 req/min）。
    - HTTP リトライ（指数バックオフ、最大3回）、408/429/5xx を考慮。429 の場合は Retry-After を優先。
    - 401 受信時のトークン自動リフレッシュ（1 回のみ）とモジュール内トークンキャッシュ。
    - ページネーション対応の fetch_* 関数（daily quotes / financial statements / market calendar）。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等（ON CONFLICT DO UPDATE）で実装。
    - データ変換ユーティリティ：_to_float / _to_int。
    - データ取得日時（fetched_at）を UTC で記録し、Look-ahead バイアス対策を考慮。
  - kabusys.data.news_collector: ニュース収集（RSS）モジュール
    - RSS フィードから記事収集、テキスト前処理、URL 正規化（utm_* 等のトラッキングパラメータ除去）を実装。
    - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
    - defusedxml を用いた XML パース（XML Bomb 対策）、受信サイズ上限（10MB）、HTTP/HTTPS スキーム以外拒否などのセキュリティ対策を実装。
    - DB へのバルク挿入（チャンク化）を行い、実際に挿入されたレコード数を返却。
  - kabusys.research:
    - factor_research: Momentum / Volatility / Value（per, roe 等）を DuckDB の prices_daily / raw_financials テーブルから計算する関数群（calc_momentum, calc_volatility, calc_value）。
      - 各ファクターは target_date 時点のデータのみを使用（ルックアヘッド防止）。
      - 移動平均や ATR 等、必要サンプル数チェックを実装（データ不足なら None を返す）。
    - feature_exploration: 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic, Spearman ρ）、ファクター統計サマリ（factor_summary）、ランク関数（rank）。
      - pandas に依存せず標準ライブラリと DuckDB のみで実装。
    - 研究用ユーティリティ（zscore_normalize は data.stats から再利用）。
  - kabusys.strategy:
    - feature_engineering.build_features:
      - research モジュールの生ファクターを統合し、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
      - 指定カラムを Z スコア正規化し ±3 でクリップ、features テーブルへ日付単位で置換保存（トランザクションによる原子性）。
    - signal_generator.generate_signals:
      - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算。
      - 標準重みを持ち、ユーザ指定の weights を受け入れつつバリデーション・再スケーリングを実施（既知キーのみ許容）。
      - final_score を算出し、閾値 (default 0.60) 超の銘柄を BUY、保有ポジションに対してはストップロス（-8%）やスコア低下で SELL を生成。
      - Bear レジーム判定（ai_scores の regime_score 平均が負の場合）により BUY を抑制。
      - signals テーブルへ日付単位で置換保存（トランザクション＋バルク挿入で原子性）。
- トランザクションと冪等性:
  - features / signals / raw_* / raw_financials / market_calendar への DB 操作は日付単位DELETE→バルクINSERT、あるいは ON CONFLICT により冪等性を保証。
- ロギングと安全策:
  - 不整合データや欠損に対する警告ログ出力（例: PK 欠損スキップ、価格欠損時の SELL 判定スキップ等）を多用し、誤判定やデータ不整合への耐性を強化。
- 定数・デフォルト値（戦略設計に明示）:
  - Z スコアクリップ ±3、ユニバース最小株価 300 円、最小平均売買代金 5e8 円
  - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10
  - BUY 閾値 0.60、STOP_LOSS -8%、Bear 判定の最小サンプル数 3 など。

Changed
- n/a（初回リリースのため変更履歴なし）

Fixed
- n/a（初回リリースのため修正履歴なし）

Security
- XML パースに defusedxml を使用（XML Bomb 対策）。
- ニュース収集で受信サイズ上限・スキーム検証等の SSRF / DoS 緩和策を導入。
- J-Quants クライアントで HTTP エラーに応じたリトライ・トークンリフレッシュを実装し、認証失敗時の安全な復旧手段を提供。

Known Issues / Limitations
- signal_generator のトレーリングストップや保有期間ベースの自動エグジットは未実装（positions テーブルに peak_price / entry_date 等の情報が必要）。
- news_collector の SSRF 周りの厳密な接続フィルタ（IP ブロック等）は実装の余地あり（コードに意図はあるが詳細実装は限定的）。
- research モジュールは DuckDB の prices_daily / raw_financials の良質な履歴データを前提としている。データ不足時は多くの値が None になる。
- J-Quants API 関連はネットワーク環境・API レートに依存するため、実行環境での設定と監視が必要。

Notes
- 設計方針として「ルックアヘッドバイアスを防ぐ」「発注レイヤー（execution）への直接依存を持たない」「冪等性とトランザクションによる原子性確保」を明確にしているため、研究（research）→特徴量生成→シグナル生成→（別途）発注のワークフローで安全に利用可能。
- 実運用時は Settings の必須環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）を適切に設定してください。

もし CHANGELOG に追記したい項目（リリース日を別にする、より細かい分類など）があれば指示してください。