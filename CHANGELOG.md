# CHANGELOG

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

履歴:
- Unreleased
- [0.1.0] - 2026-03-19

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装しました。以下の主要機能・設計方針・注意点を含みます。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージを導入（version = 0.1.0）。
  - public API として data / strategy / execution / monitoring を公開。

- 環境設定管理
  - settings オブジェクト経由で環境変数を取得する Settings クラスを実装。
  - .env / .env.local の自動読み込み機能を導入（プロジェクトルート検出: .git または pyproject.toml）。
  - .env パーサーは以下に対応:
    - 空行・コメント行の無視
    - export プレフィックス（export KEY=val）のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしのインラインコメント処理（直前が空白/タブの '#' をコメントとみなす）
  - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - 必須環境変数未設定時は ValueError を送出（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - KABUSYS_ENV と LOG_LEVEL の妥当性チェック（許容値セットを検証）。

- データ取得・保存（J-Quants クライアント）
  - J-Quants API クライアントを実装（認証トークン取得・自動リフレッシュ含む）。
  - レート制限（120 req/min）を満たす固定間隔の _RateLimiter を実装。
  - HTTP リクエストのリトライ（指数バックオフ、最大 3 回、408/429/5xx の再試行、429 の Retry-After 優先）。
  - 401 受信時はトークン自動リフレッシュを1回行ってリトライ。
  - ページネーションに対応した fetch_* 関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への永続化ユーティリティ（冪等保存）:
    - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
    - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
    - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
  - saved レコードに fetched_at を UTC ISO8601 で記録。

- ニュース収集モジュール
  - RSS フィードからの記事収集ロジックを実装（デフォルトに Yahoo Finance を含む）。
  - 安全対策:
    - defusedxml を用いた XML パース（XML Bomb 対策）
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）設定
    - 記事 ID を URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を確保
    - トラッキングパラメータ（utm_*, fbclid 等）の除去とクエリソートによる URL 正規化（フラグメント削除）
    - HTTP/HTTPS スキームの想定（SSRF に関する注意を設計に記載）
  - raw_news へのバルク挿入をチャンク化して性能配慮。

- 研究向けファクター・探索モジュール（research）
  - ファクター計算（factor_research）:
    - モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（20 日 ATR / atr_pct）、流動性（20日平均売買代金、出来高比率）、バリュー（PER / ROE）を DuckDB の prices_daily / raw_financials から計算。
    - データ不足時の None 返却やウィンドウ不足時の扱いを明示。
  - 特徴量探索（feature_exploration）:
    - 将来リターン計算（calc_forward_returns、horizons デフォルト [1,5,21]）
    - IC（Information Coefficient）計算（calc_ic: スピアマンの ρ、サンプル不足時は None）
    - factor_summary（基本統計量: count/mean/std/min/max/median）
    - rank 関数（同順位は平均ランク、round(...,12) による ties 対応）
  - 外部依存（pandas 等）を用いず、標準ライブラリ＋DuckDB のみで実装。

- 戦略層（strategy）
  - feature_engineering.build_features:
    - research モジュールの生ファクターを取得してマージ、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5億円）適用。
    - 指定カラムを Z スコア正規化（zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性・冪等性を保証）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントを重み付きで合算し final_score を算出（デフォルト重みは StrategyModel に準拠）。
    - Bear レジーム判定（AI の regime_score 平均が負なら Bear。ただしサンプル数が閾値未満なら Bear と見なさない）。
    - BUY シグナル閾値（デフォルト 0.60）。Bear レジームでは BUY を抑制。
    - エグジット判定（SELL）: ストップロス（-8%）とスコア低下（threshold 未満）。保有価格や現在価格が取得できない場合の挙動はログ出力してスキップ等の安全措置を採用。
    - signals テーブルへ日付単位で置換（トランザクションで原子性を確保）。
    - weights の入力検証（未知キー・非数値・NaN/Inf・負値を除外）と合計が 1.0 でない場合のリスケール/フォールバック。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）
- 各保存関数は PK 欠損行をスキップし、その件数を警告ログ出力するように実装し、データ整合性の安全性を向上。

### セキュリティ (Security)
- RSS XML パースに defusedxml を使用して潜在的な XML 攻撃を防止。
- ニュース URL 正規化でトラッキング系クエリを除去し、ID 生成で冪等性を確保（外部参照の取り扱いを明示）。
- HTTP クライアントはタイムアウトやエラーハンドリング、リトライポリシーを備え、レート制限をモジュール内で厳守。

### 注意事項 / 既知の制限 (Notes)
- DuckDB テーブル構造（テーブル名・カラム）はコード側の期待に依存します。データベーススキーマが未整備の場合はエラーになります。
- news_collector 側での SSRF 等の完全防御は実装方針として示されていますが、実運用では追加のネットワーク制約（アウトバウンドフィルタリング等）を推奨します。
- signal_generator の未実装項目（トレーリングストップ、時間決済）はコード中に注記あり。positions テーブルに peak_price / entry_date を追加すれば対応可能です。
- 環境変数自動読み込みはプロジェクトルート検出に基づくため、パッケージ配布後や特殊なディレクトリ構成では .env の自動読み込みがスキップされる場合があります（その場合は明示的に環境変数を設定してください）。

---

このリリースでは、データ取得→保存→研究/特徴量生成→シグナル生成までの一連のコアパイプラインを整備しています。今後のリリースでは execution（発注）層、monitoring（監視）機能、追加のファクター・AI 統合、耐障害性・性能改善を予定しています。