CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に準拠して記載しています。  
このファイルはコードベースの内容から推測して作成した初期リリースの変更履歴です。

注: ここに記載のリリース日はリポジトリ内のコードから推定した「初期リリース」として現在日付（2026-03-21）を使用しています。実際のリリース運用時は適宜調整してください。

Unreleased
----------
- なし（開発中の変更はここに記載）

[0.1.0] - 2026-03-21
--------------------

Added
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__init__）。公開 API: data, strategy, execution, monitoring をエクスポート。
  - バージョンを 0.1.0 に設定。

- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート・エスケープ対応、行内コメント処理など）。
  - 読み込み時の保護キー（OS 環境変数）を考慮した override ロジックを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用）。
  - 必須環境変数取得用 _require と Settings クラスを提供。主な設定キー:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパス設定
  - Settings に利便性プロパティ（is_live / is_paper / is_dev）を実装。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装:
    - 固定間隔スロットリングによるレート制限（120 req/min）。
    - 冪等なページネーション処理。
    - リトライ（指数バックオフ、最大3回）、408/429/5xx に対する再試行、429 の Retry-After 優先処理。
    - 401 受信時の自動トークンリフレッシュ（1回のみ）とトークンキャッシュ共有（モジュールレベル）。
    - JSON デコードエラーハンドリングと詳細ログ。
  - データ保存用ユーティリティを実装（DuckDB への保存）:
    - save_daily_quotes: raw_prices へ INSERT ... ON CONFLICT DO UPDATE（冪等）。
    - save_financial_statements: raw_financials へ INSERT ... ON CONFLICT DO UPDATE（冪等）。
    - save_market_calendar: market_calendar へ INSERT ... ON CONFLICT DO UPDATE（冪等）。
    - PK 欠損行のスキップとスキップ件数ログ出力。
  - 型安全な変換ユーティリティ _to_float / _to_int を実装。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集機能を実装（デフォルトソースに Yahoo Finance を設定）。
  - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ（utm_* 等）削除、フラグメント除去、クエリをキーでソート。
  - defusedxml を用いた XML パース（XML Bomb 等への防御）。
  - 受信バイト数上限（MAX_RESPONSE_BYTES）によるメモリ DoS 対策。
  - 記事ID生成に SHA-256 ハッシュ（正規化 URL ベース）を採用して冪等性を確保。
  - DB へのバルク挿入はチャンク化して実行（パフォーマンスと SQL 長制限対策）。
  - SS R F / 非 HTTP スキームの拒否等、セキュリティ対策を意識した実装方針。

- リサーチ（kabusys.research）
  - ファクター計算モジュールを実装（factor_research）:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）。
    - calc_volatility: 20 日 ATR（atr_20, atr_pct）、20 日平均売買代金、volume_ratio。
    - calc_value: EPS を用いた PER、ROE（raw_financials と prices_daily を組み合わせ）。
    - 各関数は prices_daily / raw_financials のみを参照し、(date, code) をキーとする dict リストを返す。
  - 特徴量探索モジュール（feature_exploration）:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装（最小サンプル数チェック）。
    - factor_summary / rank: 基本統計量とランク付け（同順位は平均ランク）を提供。
  - research パッケージの公開 API を整備。

- 戦略（kabusys.strategy）
  - 特徴量エンジニアリング（feature_engineering.build_features）:
    - research の生ファクターを取得してユニバースフィルタ（最低株価、20 日平均売買代金）を適用。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）と ±3 でのクリップ。
    - 日付単位の置換（DELETE→INSERT をトランザクションで実行）により処理を冪等化。
    - DuckDB を利用した効率的な価格取得ロジック（target_date以前の最新価格を参照）。
  - シグナル生成（signal_generator.generate_signals）:
    - features と ai_scores を統合して各銘柄のコンポーネントスコアを算出（momentum/value/volatility/liquidity/news）。
    - シグモイド変換、欠損コンポーネントは中立 0.5 で補完。
    - デフォルト重み・閾値を実装（weights の検証とリスケール処理を含む）。
    - Bear レジーム検出（ai_scores の regime_score 平均が負かつサンプル閾値到達時に BUY 抑制）。
    - SELL（エグジット）判定: ストップロス（-8%）とスコア低下（threshold 未満）。
    - BUY/SELL の日付単位置換で冪等性を確保。SELL 優先の処理（BUY から SELL 対象を除外）。
    - いくつかの exit 条件（トレーリングストップ、時間決済）は未実装箇所として明示。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- defusedxml の採用、RSS/URL 正規化、受信バイト上限、SSRF 想定対策などセキュリティに配慮した実装。
- J-Quants クライアントでのトークン取り扱いや自動リフレッシュでの無限再帰回避措置（allow_refresh フラグ）を実装。

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Notes / 既知の制約・運用上の注意
- DuckDB テーブルスキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar 等）はリリースに先立って整備する必要があります。各関数はこれらの存在を前提としています。
- 一部戦略ロジック（トレーリングストップ、時間決済）は未実装。positions テーブルに peak_price / entry_date 等の追加を想定。
- news_collector の RSS パースは外部ネットワークに依存するため、タイムアウトや接続エラーのハンドリングを運用で監視してください。
- 環境変数の自動ロードはプロジェクトルート検出に依存します。パッケージ配布後や CWD が異なる環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を用いるか、環境変数を明示的に設定してください。
- J-Quants API レート制限や認証の挙動は外部 API の仕様変更に影響されます。運用時はログとリトライ挙動を監視してください。

必要な環境変数（初期）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（必須）
- KABUSYS_ENV（任意）: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL（任意）: ログレベル（デフォルト: INFO）
- DUCKDB_PATH / SQLITE_PATH（任意）: データベースファイルパス（デフォルト path を使用）

今後の改善候補
- 戦略の追加エグジット条件（トレーリングストップ、時間決済）実装。
- ai_scores の計算 / 収集パイプラインの実装とテスト。
- テストカバレッジ（ユニット / 統合テスト）の整備。
- 並列処理 / 非同期化による J-Quants データ取得パフォーマンス改善（レート制限に注意）。
- パッケージ配布後のプロジェクトルート検出ロジック改善（pip install 後の挙動確認）。

以上。