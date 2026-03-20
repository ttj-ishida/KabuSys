# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングに基づいて記載しています。

全般的な注意:
- 本リリースはコードベースから推測して作成した初期の変更履歴です。実際のコミット履歴とは異なる可能性があります。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-03-20

### Added
- 基本パッケージ初期実装を追加
  - src/kabusys/__init__.py にパッケージ名・バージョン情報（0.1.0）と公開モジュール一覧を追加。

- 環境設定・読み込み機能を追加（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能（プロジェクトルート検出：.git または pyproject.toml を基準）。
  - .env 行パーサー実装（コメント、export プレフィックス、クォート・エスケープ、インラインコメント処理対応）。
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 環境変数取得ユーティリティ _require と Settings クラスを提供（J-Quants / kabu / Slack / DB パス / 実行環境 / ログレベル等のプロパティを実装）。
  - KABUSYS_ENV と LOG_LEVEL の値検証を実装。

- データ収集クライアント（J-Quants）を追加（src/kabusys/data/jquants_client.py）
  - API 呼び出しラッパー _request を実装（JSON デコード検査、ページネーション対応）。
  - レート制御（_RateLimiter）により 120 req/min の制限を守る実装。
  - リトライロジック（指数バックオフ、最大試行回数、408/429/5xx の再試行、429 の Retry-After 優先）。
  - 401 発生時のリフレッシュトークン処理（自動トークン更新を 1 回のみ行う）。
  - fetch_* 系 API（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を実装（ページネーション対応）。
  - DuckDB への保存ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT ベースで冪等性を確保。
  - CSV 等からの型変換ユーティリティ（_to_float, _to_int）を実装し、不正値を安全に扱う。

- ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）
  - RSS フィード取得と記事の正規化処理を実装（URL 正規化、トラッキングパラメータ除去、テキスト前処理）。
  - 安全対策を考慮：defusedxml を利用して XML 関連の脆弱性を低減、受信最大サイズ制限（MAX_RESPONSE_BYTES）、HTTP スキーム制約、SSRF 緩和の考慮。
  - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等保存を容易にする設計。
  - バルク INSERT のチャンク処理・トランザクション化により DB 書き込みの効率を向上。

- 研究系モジュールを追加（src/kabusys/research/*）
  - ファクター計算（factor_research.py）:
    - モメンタム（mom_1m / mom_3m / mom_6m / ma200_dev）、ボラティリティ（ATR・atr_pct・avg_turnover・volume_ratio）、バリュー（per, roe）を DuckDB の prices_daily / raw_financials を用いて計算。
    - 営業日ベースのウィンドウ処理とデータ不足時の None ハンドリング。
  - 特徴量探索（feature_exploration.py）:
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応、取得範囲を最小化するスキャン戦略）。
    - IC（Spearman の ρ）計算（calc_ic）とランク関数 rank、統計サマリー（factor_summary）。
    - 外部ライブラリに依存せず標準ライブラリのみで実装する方針。
  - research パッケージの公開 API を __init__ でまとめてエクスポート。

- 戦略（strategy）モジュールを追加（src/kabusys/strategy/*）
  - 特徴量エンジニアリング（feature_engineering.py）
    - research モジュールの生ファクターを統合、ユニバースフィルタ（最低株価・最低平均売買代金）適用、Zスコア正規化、±3 クリップ、features テーブルへ日付単位での置換（トランザクション）で冪等保存。
    - 正規化対象カラムの指定と欠損値処理。
  - シグナル生成（signal_generator.py）
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアから重み付け合算で final_score を算出。
    - デフォルト重み、閾値（デフォルト BUY=0.60）、Bear レジーム検知（ai_scores の regime_score 平均が負）、エグジット判定（ストップロス -8% など）、BUY/SELL シグナルの生成と signals テーブルへの日付単位置換（トランザクション）。
    - 重みのユーザ指定時のバリデーション（負値/NaN/Inf/未知キーの除外、合計スケーリング）を実装。
  - strategy パッケージの公開 API を __init__ でまとめてエクスポート。

- execution と monitoring のパッケージ構成を用意（空の __init__ ファイル等）。

### Changed
- （初期リリースのため過去からの変更は無し。設計上の決定点をドキュメントに反映）
  - Look-ahead bias を避けるため、各集計・計算は target_date 時点までのデータのみを使用する方針を各モジュールで統一して実装。
  - DuckDB に対する書き込みはトランザクション + バルク挿入で原子性・効率性を担保する実装方針を適用。

### Fixed
- （該当なし）

### Security
- ニュース収集で XML パーシングに defusedxml を利用して XML BOM/XXE 等の攻撃を防止。
- RSS/URL 正規化でトラッキングパラメータ除去、スキーム確認、応答サイズ制限を導入し SSRF や DoS のリスクを軽減。
- J-Quants API クライアントでトークン自動リフレッシュとリトライ戦略を整備し、不正/一時的エラーに対する堅牢性を向上。

### Known limitations / Notes
- 実行・監視（execution / monitoring）層の実装はまだ薄い／未実装の機能がある：
  - 実際の発注 API 呼び出しは戦略層から分離されているが、execution 層の具体的な発注ロジック・接続処理は未実装（現状は signals テーブルへの出力まで）。
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装で、positions テーブルに peak_price / entry_date 等の追加カラムが必要。
- news_collector の一部（RSS フィード一覧の拡充、記事→銘柄紐付けロジック）は今後の改良対象。
- research の処理は外部ライブラリ（pandas 等）に依存しない代わりに、数値計算やデータ操作の柔軟性で制約がある可能性あり。パフォーマンス上の最適化は今後検討。

--- 

注: 実際のリリース時にはコミットハッシュや差分が残るため、CHANGELOG は実コミット履歴に合わせて更新してください。