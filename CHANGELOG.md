# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
現在のバージョンは pkg 内の __version__ に合わせて 0.1.0 としています。

## [0.1.0] - 2026-03-21

### 追加
- パッケージ初期リリース。日本株の自動売買・データ基盤・研究用ユーティリティ群を提供。
- 基本パッケージ構成
  - kabusys.config: 環境変数 / .env 管理（自動ロード機能・検証付き Settings クラス）
    - .git または pyproject.toml を基準にプロジェクトルートを探索して .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
    - 必須変数取得時の _require() により未設定時は ValueError を送出。
    - Settings にて各種設定プロパティを提供（J-Quants トークン、kabu API パスワード、Slack トークン・チャンネル、DB パス、環境・ログレベルの検証等）。
  - kabusys.data.jquants_client: J-Quants API クライアント
    - レート制限（120 req/min）を固定間隔スロットリングで制御する RateLimiter を実装。
    - リトライロジック（指数バックオフ、最大 3 回）を実装。HTTP 408/429/5xx を対象にリトライ。
    - 401 Unauthorized を検知した場合、自動でリフレッシュして 1 回再試行する仕組み（トークンキャッシュを保持）。
    - ページネーション対応の fetch_* 系関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）は冪等（ON CONFLICT DO UPDATE）で挿入・更新を行う。
    - 文字列→数値変換ユーティリティ (_to_float, _to_int) を提供し、不正データを安全に扱う。
  - kabusys.data.news_collector: RSS ニュース収集の骨子
    - RSS 取得・記事構築・テキスト前処理・DB 保存（raw_news, news_symbols 想定）のフロー設計を実装。
    - defusedxml を利用して XML 攻撃を防止、受信バイト上限（10MB）など DoS 対策、URL 正規化（トラッキングパラメータ除去）等を実装。
    - 記事ID は URL 正規化後の SHA-256 の先頭（設計）で冪等性を確保する方針（実装の骨子を含む）。
  - kabusys.research: 研究用ユーティリティ
    - factor_research: prices_daily / raw_financials を用いたファクター計算を実装
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均乖離）
      - calc_volatility: 20 日 ATR（atr_20 / atr_pct）、avg_turnover、volume_ratio
      - calc_value: per, roe（target_date 以前の最新財務データを参照）
    - feature_exploration: 研究用分析ユーティリティ
      - calc_forward_returns: 1/5/21 日等の将来リターンを一括取得（LEAD を利用した SQL 実装）
      - calc_ic: Spearman ランク相関（IC）計算
      - rank: 同順位を平均ランクで処理するランク変換ユーティリティ
      - factor_summary: 基本統計量（count/mean/std/min/max/median）
    - zscore_normalize は kabusys.data.stats から利用可能（研究モジュール共通）。
  - kabusys.strategy: 戦略層
    - feature_engineering.build_features
      - research で計算した生ファクターを取り込み、ユニバースフィルタを適用、Z スコア正規化（指定列）して ±3 でクリップし、features テーブルへ日付単位で置換保存（トランザクションで原子性を保証）。
      - ユニバース定義: 株価 >= 300 円、20 日平均売買代金 >= 5 億円。
    - signal_generator.generate_signals
      - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、重み付きで final_score を算出。
      - デフォルト重み・閾値を持ち、ユーザ指定 weights は検証・補完・リスケールして使用。
      - Bear レジーム検知（ai_scores の regime_score 平均が負かつサンプル数 >= 3）により BUY を抑制。
      - BUY 生成（閾値デフォルト 0.60）、SELL（エグジット）生成（ストップロス -8% および final_score < threshold）。
      - positions / prices_daily を参照して SELL 判定を行い、SELL 優先で BUY から除外、signals テーブルへ日付単位で置換保存（トランザクションで原子性を保証）。

### 仕様注記（実装上の重要ポイント）
- 環境変数自動ロード
  - 読み込み優先度: OS 環境 > .env.local > .env
  - OS 環境は保護され、.env/.env.local で上書かれない（ただし .env.local は override=True で読み込まれるが protected により OS 環境キーは上書きされない）。
- J-Quants クライアント
  - レート制限は固定間隔（スロットリング）で保証しており、burst を想定しない仕様。
  - 401 発生時はトークン再取得を1回試みる挙動（再取得に失敗すると例外）。
  - ページネーションは pagination_key を利用し、同一キーの無限ループ防止を行う。
- Signal / Feature の設計方針
  - ルックアヘッドバイアス防止のため、常に target_date 時点のデータのみを参照する方針。
  - 欠損コンポーネントは中立値（0.5）で補完し、欠損銘柄の不当な降格を防止。
  - Z スコアは ±3 でクリップし極端な外れ値の影響を抑制。
- DB 操作は可能な限りトランザクション + バルク挿入で原子性・効率を確保している。

### 修正 / 既知の制約
- news_collector はセキュリティ対策（defusedxml, バイト上限, URL 正規化等）の骨子を含むが、外部接続時の詳細な SSRF 防止（IP 除外ルール等）や完全な記事→銘柄紐付けロジックは今後の実装で整備予定。
- signal_generator の未実装事項（設計メモ）
  - positions テーブルに peak_price / entry_date があればトレーリングストップや時間決済ロジックを追加可能（現状は未実装）。
- 一部のユーティリティ（例: news_collector の挿入時の INSERT RETURNING による正確な挿入数返却等）は設計文言を含むが、環境依存（DuckDB のバージョン差など）により動作差異が生じる可能性がある。運用時には DuckDB スキーマ・バージョン確認を推奨。

### セキュリティ
- defusedxml を採用して XML 注入攻撃を軽減。
- news_collector で受信サイズ制限を設けてメモリ DoS を低減。
- J-Quants トークンはモジュール内でキャッシュするが、KABUSYS 側では環境変数管理を想定（Settings 経由で必須取得）。

---

今後のリリースに向けては以下を予定しています（例）:
- news_collector の完全実装（記事→銘柄マッチング、SSRF 制御の強化）
- execution 層（kabu ステーション連携）の実装とエンドツーエンドテスト
- モニタリング・運用用ツール（Slack 通知等）の追加

もし CHANGELOG に別の形式（英語での併記、日付変更、より詳細なモジュール単位の差分等）が必要であれば指示ください。