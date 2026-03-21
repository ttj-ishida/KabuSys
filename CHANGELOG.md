# Changelog

すべての注目すべき変更はこのファイルに記録します。  
形式は「Keep a Changelog」に準拠しています。  

現在のバージョン: 0.1.0

## [Unreleased]
- なし

## [0.1.0] - 2026-03-21
初回リリース。日本株自動売買システム (KabuSys) のコア機能群を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージ識別子と公開 API を定義（kabusys/__init__.py, __version__ = "0.1.0"）。
  - strategy、execution、data、monitoring の名前空間を公開。

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動的に読み込む仕組みを追加。
    - プロジェクトルートを .git または pyproject.toml から特定し、.env → .env.local の順で読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
  - .env パーサは export プレフィックス、クォート／エスケープ、インラインコメント処理などをサポート。
  - 既存 OS 環境変数を保護する protected 機能（上書き禁止）を導入。
  - 必須環境変数の取得時に未設定だと ValueError を送出する _require を実装。
  - 設定項目（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_*、データベースパス等）をプロパティ経由で提供。
  - KABUSYS_ENV / LOG_LEVEL の入力検証（有効値チェック）を追加。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔のレート制限（120 req/min）を守る RateLimiter。
    - リトライ（指数バックオフ、最大 3 回）と 408/429/5xx ハンドリング。
    - 401 受信時はリフレッシュトークンから自動で ID トークンを更新して 1 回リトライ。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB へ冪等に保存する save_* 関数（raw_prices/raw_financials/market_calendar）を実装。ON CONFLICT を利用した更新処理。
    - 日時は UTC で fetched_at を記録し、look-ahead bias のトレースを可能に。
    - 型変換ユーティリティ（_to_float/_to_int）で不正なデータを安全に扱う。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードベースのニュース収集モジュールを追加。
    - デフォルト RSS ソース（例: Yahoo Finance）の定義。
    - URL の正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）を実装。
    - defusedxml を用いた安全な XML パース（XML Bomb 等への対策）。
    - 最大受信バイト数制限（10 MB）によるメモリ DoS 緩和。
    - DB への冪等保存（ON CONFLICT / INSERT DO NOTHING を想定）とバルク挿入チャンク処理。
    - 記事 ID は正規化 URL 等からのハッシュを用いる設計（冪等性向上）。
    - セキュリティ対策（URL スキーム制限や SSRF 防止を意識した実装方針）。

- 研究（research）関連
  - ファクター計算モジュール（kabusys.research.factor_research）
    - Momentum（mom_1m, mom_3m, mom_6m）、ma200_dev、Volatility（atr_20, atr_pct）、Liquidity（avg_turnover, volume_ratio）、Value（per, roe）を DuckDB の prices_daily / raw_financials から計算する関数を実装。
    - 各計算は営業日ベースの窓を想定し、データ不足時は None を返す仕様。
  - 特徴量探索モジュール（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（Spearman rho）計算（calc_ic）、統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を実装。
    - pandas 等の外部ライブラリに依存せず実装。
  - research パッケージの公開 API を整備。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research 側で計算された生ファクターを統合し features テーブルへ保存する build_features を実装。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）後 ±3 でクリップ。
    - date 単位で DELETE → bulk INSERT（トランザクション）による冪等な置換を行う。
    - 欠損や価格欠損に配慮した実装。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成する generate_signals を実装。
    - コンポーネントスコア（momentum, value, volatility, liquidity, news）を計算するユーティリティを実装（シグモイド変換等）。
    - デフォルト重みと閾値（DEFAULT_THRESHOLD=0.60）を提供。ユーザー重みは検証・補完・リスケール。
    - Bear レジーム判定（ai_scores の regime_score 平均が負なら Bear。ただしサンプル数閾値あり）。
    - BUY: threshold を超えた銘柄をランク付けして登録（Bear 時は抑制）。
    - SELL: 保有ポジションに対してストップロス（-8%）やスコア低下でエグジット判定。
    - signals テーブルへ日付単位の置換（トランザクション）で保存。
    - SELL を優先し、BUY から該当銘柄を除去してランクを再付与するポリシーを採用。
    - 欠損コンポーネントは中立値 0.5 で補完するロバストな合算処理。

- その他
  - research/strategy 層は発注 API / execution 層へ直接依存しない設計（ルックアヘッドバイアス防止）。
  - DuckDB を想定した SQL 実装とトランザクション / ロールバック処理（失敗時に警告ログ）を導入。
  - execution パッケージのプレースホルダを追加（実装は別途）。

### Security
- external input（RSS/XML/HTTP）に対する複数の安全策を設計に盛り込んでいます（defusedxml、受信サイズ制限、URL 正規化／トラッキング除去、スキーム制限、SSRF 回避方針など）。

### Known limitations / Notes
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装。positions テーブルに peak_price / entry_date といった追加情報が必要。
- news_collector の実装は RSS の収集・正規化を中心に設計されており、全文抽出や NLP の連携は今後の拡張点。
- monitoring パッケージは __all__ に含まれるが、実体が未実装（プレースホルダ）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

---

今後のリリースでは以下を検討しています（例）:
- execution 層の実装（kabu ステーション連携、注文制御、リスク管理）
- モニタリング / アラート機能（Slack 通知等）
- news_collector の記事→銘柄マッチング、AI スコアリング統合
- 性能改善（DuckDB クエリ最適化、並列フェッチ）
- より細かいユニットテスト・統合テストの追加

（本 CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴がある場合はコミット単位での差分記述を推奨します。）