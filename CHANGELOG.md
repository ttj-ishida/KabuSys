# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

なお、この CHANGELOG は与えられたコードベースの内容（ソースコード内のドキュメント文字列や実装）から推測して作成しています。

## [Unreleased]

（無し）

## [0.1.0] - 2026-03-21

初回リリース。日本株自動売買システム「KabuSys」のコアライブラリを公開します。  
主な目的はデータ取得・前処理・ファクター計算・特徴量作成・シグナル生成の基礎実装を提供することです。実運用（発注実行・監視周り）は別モジュールでの実装を想定しています。

### Added
- パッケージ基盤
  - パッケージメタ情報（kabusys.__init__）および初期バージョン `0.1.0` を定義。
  - パッケージ公開 API に `data`, `strategy`, `execution`, `monitoring` を含める構成（execution は空パッケージ、monitoring は現コードベースでは未実装）。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイル（.env, .env.local）および環境変数から設定値を自動ロードする仕組み（プロジェクトルート検出: .git または pyproject.toml を探索）。
  - .env パーサー（export プレフィックス対応、クォート／エスケープ処理、インラインコメント処理）。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` サポート。
  - 必須環境変数取得時の検証（_require）。
  - Settings クラスによるプロパティアクセス:
    - J-Quants / kabuAPI / Slack / DB パス（DuckDB/SQLite）/実行環境（development/paper_trading/live）/ログレベル等の取得とバリデーション。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント実装（urllib ベース）。
  - レート制限（120 req/min）を守る固定インターバル RateLimiter 実装。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）。
  - 401 受信時の自動トークンリフレッシュ（1 回）とトークンキャッシュ。
  - ページネーション処理（pagination_key を利用）。
  - DuckDB への冪等保存ユーティリティ:
    - save_daily_quotes（raw_prices、ON CONFLICT DO UPDATE）
    - save_financial_statements（raw_financials、ON CONFLICT DO UPDATE）
    - save_market_calendar（market_calendar、ON CONFLICT DO UPDATE）
  - 型安全な変換ユーティリティ（_to_float、_to_int）と fetched_at の UTC 記録（look-ahead バイアス対策）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからのニュース収集方針とユーティリティ実装（URL 正規化、トラッキングパラメータ除去、受信サイズ制限、defusedxml による安全な XML パース、記事ID の SHA-256 ハッシュ化等）。
  - デフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）。
  - 生データ raw_news への冪等保存（ON CONFLICT DO NOTHING を想定）、news とシンボル紐付けのための設計方針。
  - 大量挿入に配慮したチャンク処理やメモリ保護（MAX_RESPONSE_BYTES）。

- 研究（research）モジュール
  - ファクター計算（kabusys.research.factor_research）:
    - モメンタム（mom_1m, mom_3m, mom_6m, ma200_dev）
    - ボラティリティ / 流動性（atr_20, atr_pct, avg_turnover, volume_ratio）
    - バリュー（per, roe） — raw_financials と prices_daily を組み合わせて計算
    - DuckDB SQL を用いた効率的なウィンドウ集計と欠損制御
  - 特徴量探索（kabusys.research.feature_exploration）:
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応、入力チェック）
    - ランク相関（IC）計算（calc_ic、Spearman の ρ 相当を実装）
    - ランク化補助（rank: 同順位は平均ランク）
    - 統計サマリー（factor_summary: count/mean/std/min/max/median）
  - 研究向けユーティリティのエクスポートを提供。

- 戦略（strategy）モジュール
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - research の raw ファクターを統合し、ユニバースフィルタ（最小株価・最小売買代金）を適用。
    - 指定カラムを Z スコア正規化（zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへトランザクションを用いた日付単位の置換（冪等性）。
  - シグナル生成（kabusys.strategy.signal_generator）
    - features と ai_scores を統合して最終スコア final_score を計算（モメンタム/バリュー/ボラティリティ/流動性/ニュースの加重和）。
    - デフォルト重みとしきい値（デフォルト閾値 0.60）を採用、カスタム重みの検証と再スケール処理を実装。
    - Bear レジーム検出による BUY 抑制（ai_scores の regime_score 平均が負なら Bear）。
    - BUY 条件（threshold 超過）および SELL 条件（ストップロス -8% / スコア低下）を実装。
    - positions / prices_daily を参照してエグジット判定を実行。
    - signals テーブルへトランザクションで日付単位置換（冪等性）。
    - BUY と SELL の優先順位（SELL 優先で BUY から除外）に基づくランク再付与。

- ロギングおよびエラーハンドリング
  - 各モジュールで詳細なログ出力（info/warning/debug）とトランザクションロールバック対応。

### Changed
- （初版のため過去変更なし）

### Fixed
- （初版のため過去修正なし）

### Removed
- （なし）

### Known issues / TODO
- execution パッケージは空（実運用での発注処理は別実装が必要）。
- monitoring はパッケージ __all__ に含まれるが、現コードベースでは未実装。
- signal_generator の一部エグジット条件は未実装（ドキュメントに記載）：  
  - トレーリングストップ（peak_price / entry_date を positions に持たせる必要あり）
  - 時間決済（保有 60 営業日超過）
- feature_engineering / research 側で参照する zscore_normalize は kabusys.data.stats に依存するが、該当ファイルは与えられたコード断片に含まれていない（実装場所は data.stats を想定）。
- news_collector の RSS 取得部分（ネットワーク取得・パースの統合処理）はコード断片が途中で切れているため、実運用前に完全なフェッチ・正規化・DB 保存フローの確認が必要。
- J-Quants クライアントは urllib ベース（requests を用いていない）：運用上の要件に応じて TLS/プロキシ/接続設定の追加検討が必要。
- 一部 SQL は DuckDB に依存（機能／バージョン差異に注意）。
- 単体テスト・統合テストは本コードに含まれないため、CI/テストの整備が必要。

### Notes for Upgrading
- 環境変数名・設定キー（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）に依存するため、.env または実行環境に必要なキーを設定してください。
- DuckDB スキーマ（raw_prices / raw_financials / prices_daily / features / ai_scores / positions / signals / market_calendar / raw_news 等）が前提となるため、初期スキーマ作成スクリプトを適用してください（スキーマはコードの SQL と docstring を参照）。
- strategy の重みや閾値は generate_signals の引数で上書き可能。運用環境では paper_trading 環境での検証を推奨します。

---

参考: 各モジュールの docstring に StrategyModel.md / DataPlatform.md 等の参照が記載されています。実運用に移す際はそれらの設計書・仕様書に従って追加実装・検証を行ってください。