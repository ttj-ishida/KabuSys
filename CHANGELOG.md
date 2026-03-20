# CHANGELOG

すべての変更は Keep a Changelog の仕様に準拠して記載しています。  
互換性のあるバージョニングは SemVer に従います。

## [0.1.0] - 2026-03-20

Initial release — 日本株自動売買システムのコア機能を実装しました。

### Added
- パッケージ基礎
  - パッケージエントリポイントを定義（kabusys.__version__ = 0.1.0、公開モジュール: data, strategy, execution, monitoring）。
- 環境設定管理（kabusys.config）
  - .env ファイルと環境変数の自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を起点に探索して特定（CWD 非依存）。
  - 読み込み優先度を OS 環境変数 > .env.local > .env とし、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサ実装（export 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの扱い等）。
  - .env 読み込み時に既存 OS 環境変数を保護する protected セットを導入。
  - Settings クラスを実装し、J-Quants / kabu API / Slack / DB パス / 環境種別（development/paper_trading/live）/ログレベルの取得とバリデーションを提供。
- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。ページネーション対応の fetch_* 系関数（株価、財務、マーケットカレンダー）を提供。
  - API レート制御のため固定間隔スロットリング RateLimiter を実装（デフォルト 120 req/min）。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx 対象）と 401 受信時のトークン自動リフレッシュ（1 回まで）を実装。
  - ID トークンのモジュールレベルキャッシュを導入し、ページネーションや複数呼び出しでの再利用を最適化。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。冪等性を考慮した ON CONFLICT DO UPDATE を使用。
  - 受け渡しデータの型安全な変換ユーティリティ _to_float / _to_int を提供。
  - 取得時刻（fetched_at）を UTC ISO8601 形式で保存してルックアヘッドバイアスをトレース可能に。
- ニュース収集（kabusys.data.news_collector）
  - RSS からの記事収集の骨格を実装。デフォルト RSS ソース（Yahoo Finance）を定義。
  - セキュリティ対策として defusedxml を想定した XML パース、受信最大バイト数制限（10MB）、SSRF 対策を明記。
  - URL 正規化機能を実装（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
  - 記事ID の冪等性を想定した SHA-256 ベースの生成（コメントに記載）。
  - DB 挿入をバルク化しチャンク処理で SQL 長を抑制する仕組み（チャンクサイズ定義）。
- 研究（research）モジュール
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）を DuckDB SQL で計算。
    - Volatility / Liquidity（atr_20, atr_pct, avg_turnover, volume_ratio）を実装。
    - Value（per, roe）を raw_financials と prices_daily を結合して計算。
    - データ不足時の None ハンドリングやスキャン範囲のバッファ設計を反映。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算 calc_forward_returns（デフォルトホライズン: 1,5,21 日、入力バリデーションあり）。
    - IC（Spearman の ρ）計算 calc_ic、ランク化ユーティリティ rank（同順位は平均ランク）。
    - factor_summary による基本統計量集計（count / mean / std / min / max / median）。
  - research パッケージの public API を __all__ で整理。
- 戦略（strategy）モジュール
  - 特徴量加工（kabusys.strategy.feature_engineering）
    - 研究側で算出した raw factor を収集して統合、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 正規化は zscore_normalize を利用し、指定カラムを ±3 でクリップして外れ値の影響を低減。
    - features テーブルへ日付単位で置換（BEGIN/DELETE/INSERT/COMMIT）することで冪等性と原子性を保証。
  - シグナル生成（kabusys.strategy.signal_generator）
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出、重み付け合算で final_score を計算。
    - デフォルト重みと閾値（default threshold = 0.60）を実装。ユーザー指定 weights は検証して正規化（合計を 1 に再スケール）。
    - Sigmoid マッピング、欠損値は中立 0.5 で補完する保守的な扱いで欠損銘柄の不当降格を防止。
    - Bear レジーム判定（ai_scores の regime_score の平均が負かつ十分なサンプル数の場合）で BUY シグナルを抑制。
    - SELL 判定ロジックにストップロス（-8%）とスコア低下を実装。保有ポジションに関する価格欠損時の警告と判定スキップを追加。
    - signals テーブルへの日付単位の置換（トランザクション）で冪等性を保証。
- ロギング
  - 各モジュールにて重要箇所での警告・情報ログを追加（IO/DB/HTTP エラー、ROLLBACK 失敗時の警告など）。

### Security
- news_collector で defusedxml を想定した XML パース方式を採用（XML Bomb 等の防御）。
- ニュース URL の正規化とトラッキングパラメータ除去により情報漏洩やトラッキング影響を軽減。
- ネットワーク関連は受信サイズ上限や SSRF 制限を設計文として明記。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

補足:
- 本 CHANGELOG はコードに記載されているドキュメント文字列と実装から推測して作成しています。将来的に API 仕様や DB スキーマが変更された場合は該当セクションを更新してください。