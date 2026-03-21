# Changelog

すべての重要な変更点をこのファイルに記録します。  
本ファイルは Keep a Changelog の形式に準拠しています。

最新リリース: 0.1.0

## [0.1.0] - 2026-03-21

初回リリース。日本株自動売買システム「KabuSys」の基本モジュール群を追加しました。以下はコードベースから推察される主要機能・設計方針のまとめです。

### 追加 (Added)
- パッケージ基盤
  - pakage: `kabusys`（__version__ = 0.1.0）
  - 公開 API: `kabusys.data`, `kabusys.strategy`, `kabusys.execution`, `kabusys.monitoring` を __all__ に登録。

- 環境設定 / 設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git / pyproject.toml を探索）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用）。
  - .env / .env.local の読み込み順と上書きルール（OS環境変数保護）を実装。
  - 独自の .env パーサ（コメント/引用/エスケープ処理を考慮）。
  - 必須環境変数チェックを行う Settings クラスを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）。
  - 型チェック・値検証（KABUSYS_ENV の許容値, LOG_LEVEL の検証など）。

- データ収集 / 永続化 (`kabusys.data`)
  - J-Quants API クライアント (`jquants_client`)
    - レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を実装。
    - リトライ（指数バックオフ、最大 3 回）、特定ステータスでの再試行ロジック (408, 429, 5xx) を実装。
    - 401 の場合はリフレッシュトークンで自動トークン再取得（1 回のみ）してリトライ。
    - ページネーション対応のデータ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB へ冪等に保存する関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT による更新）。
    - 取得時刻は UTC の fetched_at を記録し、Look-ahead バイアス管理を意識。
    - 型安全な変換ユーティリティ: _to_float / _to_int。
  - ニュース収集モジュール (`news_collector`)
    - RSS フィードから記事収集し raw_news へ冪等保存する処理を実装。
    - URL 正規化（トラッキングパラメータ削除、ソート、フラグメント削除）と記事 ID の一意化（SHA-256 の一部）による冪等性。
    - defusedxml による安全な XML パース、受信サイズ上限（メモリ DoS 対策）、SSRF 防止（スキーム制限等）などのセキュリティ対策を考慮。
    - バルク INSERT のチャンク処理で DB 負荷を抑制。

- リサーチ / ファクター計算 (`kabusys.research`)
  - ファクター計算モジュール (`factor_research`)
    - Momentum: mom_1m, mom_3m, mom_6m、ma200_dev（200日MA乖離）を DuckDB の SQL ウィンドウ関数で計算。
    - Volatility: 20日 ATR、atr_pct（ATR/close）、avg_turnover、volume_ratio を計算（true_range の NULL 伝播を考慮）。
    - Value: raw_financials から最新財務データを結合して PER / ROE を算出（EPS=0 のときは PER を None に）。
    - 実装は prices_daily / raw_financials のみを参照し、本番の発注 API へはアクセスしない設計。
  - 特徴量探索モジュール (`feature_exploration`)
    - 将来リターン計算（horizons デフォルト [1,5,21]、営業日ベース）: calc_forward_returns。
    - IC（Spearman ランク相関）を計算する calc_ic（有効サンプル数が不足する場合は None を返す）。
    - 基本統計（count/mean/std/min/max/median）を計算する factor_summary。
    - ランク変換ユーティリティ rank（同順位は平均ランク、丸めで ties の検出を安定化）。
  - zscore_normalize は data.stats から提供（research パッケージで再公開）。

- 特徴量エンジニアリング / 戦略用特徴量格納 (`kabusys.strategy.feature_engineering`)
  - build_features(conn, target_date)
    - research の各ファクター計算（calc_momentum, calc_volatility, calc_value）を統合し features テーブルへ UPSERT（置換）して保存。
    - ユニバースフィルタ（最低株価 >= 300 円、20日平均売買代金 >= 5億円）を適用。
    - 指定カラムを Z スコア正規化（±3 でクリップ）した上で保存。
    - DuckDB トランザクションによる日付単位の置換（冪等性・原子性確保）。
    - 休場日や欠損に対応して target_date 以前の最新価格を使用。

- シグナル生成 (`kabusys.strategy.signal_generator`)
  - generate_signals(conn, target_date, threshold=0.60, weights=None)
    - features と ai_scores を統合して各銘柄の最終スコア（final_score）を計算。
    - コンポーネント: momentum / value / volatility / liquidity / news（デフォルト重みを提供）。
    - AI スコアの regime_score を用いた Bear 相場判定（サンプル数閾値あり）。Bear 時は BUY シグナル抑制。
    - BUY シグナルは閾値超過銘柄、SELL シグナルはストップロス（終値比 -8%）やスコア低下で判定。
    - positions / prices から保有ポジションを参照してエグジット判定（価格欠損時は判定スキップ）。
    - SELL 優先ポリシー（同一銘柄が SELL 判定なら BUY から除外）。
    - signals テーブルへの日付単位置換（トランザクション＋バルク挿入）。

- ユーティリティ / ロギング
  - ロガーを各モジュールで使用。エラー時にトランザクションの ROLLBACK を試みる実装。
  - 入力検証や警告ログを多用し、不正パラメータや欠損データへの耐性を確保。

### 修正 (Fixed)
- （初回リリースのため特定の修正履歴はなし。コード内にエラーハンドリングや警告ログを多用しており、実行時の堅牢性に配慮。）

### 破壊的変更 (Breaking Changes)
- なし（初回リリース）

### セキュリティ (Security)
- RSS パースに defusedxml を使用して XML 攻撃を軽減。
- ニュース収集時の URL 正規化・トラッキングパラメータ除去、受信サイズ制限、HTTP スキーム制御等で SSRF / DoS 対策を実施。
- J-Quants クライアントは認証トークン管理と自動リフレッシュを実装。API レート制限遵守のための RateLimiter を導入。

### 既知の制限 / TODO
- signal_generator の一部エグジット条件は未実装（コード内コメントに記載）
  - トレーリングストップ（peak_price / entry_date が positions に必要）
  - 時間決済（保有 60 営業日超過）
- 一部のユーティリティ（例: zscore_normalize の実装場所は data.stats に依存）が外部モジュールに委譲されているため、統合テストが必要。
- DB スキーマ（tables: raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar 等）は別途用意する必要あり（スキーマ定義は本リポジトリに含まれていない想定）。

---

今後のリリースでは、以下のような項目を予定・検討しています（コード内コメントや設計方針に基づく想定）:
- execution 層の実装：kabuステーション API を使った発注ロジック（安全な送信/確認/再試行）。
- monitoring 層の充実：Slack 通知や稼働監視、戦略パフォーマンスダッシュボード。
- 戦略の追加チューニング：トレーリングストップ / 時間決済 / ポジションサイジングの実装。
- 単体テスト・統合テストの追加と CI の整備。

（以上）