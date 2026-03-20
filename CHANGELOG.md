# Changelog

すべての注目すべき変更はこのファイルに記録します。  
この変更履歴は Keep a Changelog の形式に準拠しています。  

※ 内容は提示されたソースコードから推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。

## [Unreleased]

### Added
- ドキュメント文字列と設計方針を各モジュールに追加（コードの目的・処理フロー・設計意図が明記）。
- パッケージ初期エクスポートを定義（kabusys.__init__ の __all__ に "data", "strategy", "execution", "monitoring" を設定）。
- settings を介した環境変数管理機能を追加（kabusys.config.Settings）。
  - .env 自動読み込み機能（プロジェクトルートの検出：.git または pyproject.toml を基準）。
  - .env → .env.local の読み込み順（OS 環境変数を保護する protected 機能）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - 環境変数のパースで export プレフィックス、クォート、インラインコメント、エスケープを考慮するロジックを実装。
  - 必須環境変数取得時に未設定なら ValueError を投げる _require を提供。
  - 有効な実行環境 env 値検証（development / paper_trading / live）とログレベル検証（DEBUG/INFO/...）。
  - 各種設定プロパティ（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、データベースパス等）。

- Data レイヤー（kabusys.data）に外部データ取得・保存の実装（J-Quants クライアント）。
  - J-Quants API クライアント（data/jquants_client.py）
    - 固定間隔スロットリングによるレート制限制御（120 req/min）。
    - リトライ（指数バックオフ、最大 3 回）と 401 時のトークン自動リフレッシュ対応。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB への冪等的な保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装（ON CONFLICT DO UPDATE）。
    - 型変換ユーティリティ（_to_float, _to_int）。
    - 取得時刻を UTC で記録し look-ahead バイアス対策を考慮。

- ニュース収集モジュール（data/news_collector.py）
  - RSS から記事を取得して raw_news へ保存するためのユーティリティ群。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、クエリソート、フラグメント除去）。
  - defusedxml を使った XML パースによる安全対策、受信サイズ制限、SSRF 回避を意識した実装方針。
  - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を担保。
  - バルク INSERT チャンク処理・トランザクションを前提にした性能配慮。

- Research 層（kabusys.research）
  - ファクター計算モジュール（research/factor_research.py）
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - Value（per, roe） — raw_financials と prices_daily を組み合わせて計算
    - DuckDB SQL を多用した実装（ウィンドウ関数等）
  - 解析ユーティリティ（research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns：複数ホライズン対応、入力検証あり）
    - IC（Information Coefficient）計算（calc_ic：Spearman の ρ、最小サンプルチェック）
    - factor_summary（count/mean/std/min/max/median）
    - rank（同順位は平均ランクで処理、丸めで ties を安定化）
  - zscore_normalize の再エクスポートを提供（research/__init__.py 経由）。

- Strategy 層（kabusys.strategy）
  - 特徴量エンジニアリング（strategy/feature_engineering.py）
    - research 層の生ファクターを統合・フィルタ・Zスコア正規化・±3 クリップして features テーブルへ UPSERT（トランザクションで日付単位の置換）。
    - ユニバースフィルタ（最低株価・最低平均売買代金）実装。
    - DuckDB を用いた原子性を意識した DB 操作。
  - シグナル生成（strategy/signal_generator.py）
    - features + ai_scores を統合して final_score を算出（要素：momentum/value/volatility/liquidity/news）。
    - 重みの補完・バリデーション・リスケール処理（デフォルト重みを定義）。
    - Sigmoid 変換、コンポーネント補完（None → 中立 0.5）により欠損銘柄の不当な扱いを回避。
    - Bear レジーム判定（AI の regime_score 平均 < 0 を Bear、として BUY を抑制）。
    - BUY / SELL シグナルの生成ロジック（BUY は閾値超過、SELL はストップロス・スコア低下等）。
    - positions / prices_daily からエグジット判定を行い、signals テーブルへ日付単位で置換（トランザクションで原子性保証）。
    - SELL 優先ポリシーを採用（SELL 対象は BUY から除外、ランク再付与）。
  - strategy/__init__.py で主要関数を公開（build_features, generate_signals）。

- Execution / Monitoring のためのパッケージ構造を準備（execution パッケージ空の __init__ を含む）。

### Security
- news_collector で defusedxml を使用し XML 脆弱性を低減。
- URL 正規化・スキーム制限・受信サイズ制限による SSRF / DoS 対策を想定。

### Documentation
- 各モジュールに詳細な docstring を追加。処理フロー、設計方針、前提（ルックアヘッドバイアス回避、発注層への非依存など）を明示。

---

## [0.1.0] - 2026-03-20

初回リリース想定（コードベースから推測）:

### Added
- パッケージ基盤と主要機能を実装（上記 Unreleased の各機能を含む）。
- 環境設定管理、外部データ取得（J-Quants）、ニュース収集、研究用ファクター計算、特徴量生成、シグナル生成、DuckDB への冪等保存など一連の自動売買システムのコア処理を提供。
- 設計上の安全措置（レートリミット、リトライ、トークン自動リフレッシュ、XML パース防御、DB トランザクション）を導入。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- defusedxml の利用と受信サイズ制限などで外部入力の安全性を強化。

---

注意:
- テーブル名（raw_prices, raw_financials, market_calendar, features, ai_scores, signals, positions など）はコード中の SQL で参照されているため、実運用前にスキーマを整備してください。
- .env の自動ロードはプロジェクトルート検出に依存します。パッケージ配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って制御可能です。
- この CHANGELOG はコードの内容から推測して作成しています。実際のコミットログやリリース日付を基に調整することを推奨します。