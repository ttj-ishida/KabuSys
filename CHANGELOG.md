# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  

## [0.1.0] - 初期リリース
最初の公開バージョン。日本株自動売買システム「KabuSys」のコア機能を実装しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0。
  - モジュール構成: data, research, strategy, execution（プレースホルダ）等の基礎モジュールを追加。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする仕組みを実装。
  - .env のパーサを実装（コメント、export プレフィックス、引用符内のバックスラッシュエスケープ、インラインコメントの扱い等に対応）。
  - 自動ロードの無効化オプション: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数取得ヘルパー _require と Settings クラスを提供。主な環境変数:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- データ取得 / 保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装（ページネーション対応）。
  - レート制限を尊重する固定間隔スロットリング（120 req/min）を実装。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）を実装。429 の場合は Retry-After を尊重。
  - 401 受信時にリフレッシュトークンから自動で ID トークンを更新して 1 回リトライする機能を実装。
  - ページネーション間で使うモジュールレベルのトークンキャッシュを実装。
  - DuckDB への保存関数を実装（raw_prices / raw_financials / market_calendar）。挿入は冪等（ON CONFLICT DO UPDATE）で行う。
  - データ変換ユーティリティ: _to_float / _to_int を提供（不正データを None に変換）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード取得と raw_news へ冪等保存するモジュールを追加（デフォルトソースに Yahoo Finance を設定）。
  - セキュリティ対策: defusedxml を使用して XML 攻撃を緩和、HTTP スキーム以外の URL を拒否する方針、受信サイズ上限（10MB）を導入。
  - 記事 ID は URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を確保。トラッキングパラメータ除去、クエリソート等の正規化を実施。
  - バルク INSERT のチャンク処理とトランザクションで効率的かつ安全に保存。

- 研究・ファクター計算 (kabusys.research)
  - ファクター計算モジュールを実装（prices_daily / raw_financials を使用）。
  - calc_momentum: 約1ヶ月/3ヶ月/6ヶ月リターン、200日移動平均乖離率の計算を実装（データ不足時は None を返す）。
  - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
  - calc_value: target_date 以前の最新財務データと価格を用いて PER / ROE を計算。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（任意ホライズン）を高速に一括取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装（ties を平均ランクで扱う）。
    - factor_summary: 各ファクター列の統計サマリ（count/mean/std/min/max/median）を提供。
    - rank: 同順位は平均ランクにするランク関数を提供。
  - 研究モジュールは外部ライブラリ（pandas 等）に依存しない設計。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research モジュールで計算された生ファクターを結合し、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
  - 指定カラムに対する Z スコア正規化（kabusys.data.stats のユーティリティを利用）と ±3 のクリップを実施。
  - features テーブルへ日付単位での置換（DELETE + bulk INSERT）により冪等性を保証。トランザクションで原子性を確保。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して最終スコア（final_score）を計算し、BUY/SELL シグナルを生成。
  - コンポーネントスコア:
    - momentum / value / volatility / liquidity / news を計算するユーティリティを実装（シグモイド変換、逆転など）。
  - デフォルト重みと閾値を実装（デフォルト threshold=0.60、weights の検証と正規化を行う）。
  - Bear レジーム判定（AI の regime_score 平均が負の場合、かつサンプルが十分あることを条件）により BUY を抑制。
  - エグジット条件（ストップロス -8% / final_score の閾値割れ）で SELL シグナルを生成。SELL を優先して BUY を除外。
  - signals テーブルへ日付単位の置換（冪等）、トランザクション処理を実装。
  - 欠損値の扱い: コンポーネントが None の場合は中立値 0.5 で補完し、不当な降格を防止。

### 変更 (Changed)
- ー（初回リリースにつき変更履歴はありません）

### 修正 (Fixed)
- ー（初回リリースにつき修正履歴はありません）

### セキュリティ (Security)
- RSS パーサに defusedxml を使用し XML 攻撃対策を実施。
- news_collector で受信バイト上限を設定しメモリ DoS を抑制。
- jquants_client の HTTP リトライ/トークン刷新で安全に認証・再試行を実施。

### 既知の制限・未実装 (Known issues / Not implemented)
- signal_generator のトレーリングストップや時間決済は未実装（positions テーブルに peak_price / entry_date が必要）。
- news_collector の SSRF 対策や URL ホスト検証は設計に言及があるが、実運用での追加制約が必要な場合がある。
- execution（発注）モジュールは空のパッケージとして存在。実際の発注ロジックは別途実装が必要。
- 一部の処理（Z スコア正規化等）は kabusys.data.stats に依存しているため、そちらの実装が必要。

### マイグレーション / 利用上の注意
- 環境変数を用いて設定を行うこと（必須環境変数が未設定の場合は ValueError を送出）。
- 自動で .env/.env.local を読み込むため、テスト等で自動ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB / SQLite のデフォルトパスは設定で上書き可能（DUCKDB_PATH / SQLITE_PATH）。
- J-Quants API の利用には JQUANTS_REFRESH_TOKEN を設定すること。トークンは自動リフレッシュされる。

---

今後の予定（例）
- execution 層の実装（kabu ステーション等との連携）。
- モニタリング・アラート機能の充実（Slack 通知等）。
- ニュースの銘柄紐付け（news_symbols の自動付与）や NLP によるスコアリング強化。