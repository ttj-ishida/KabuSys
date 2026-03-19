# CHANGELOG

すべての変更は Keep a Changelog のガイドラインに準拠して記載しています。  
このファイルはコードベースから推測して作成した変更履歴です。

現在のバージョン: 0.1.0

## [Unreleased]
（今後の変更予定・TODO 等をここに記載）

---

## [0.1.0] - 2026-03-19

初期リリース。日本株の自動売買プラットフォーム「KabuSys」のコア機能を実装しました。主な追加・設計方針・堅牢性対策は以下の通りです。

### Added
- パッケージ構成
  - kabusys パッケージの提供（__version__ = 0.1.0）。公開 API: data, strategy, execution, monitoring を想定。
- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env の行パーサ（クォート、エスケープ、コメント処理、`export KEY=val` 形式対応）を導入。
  - .env と .env.local の読み込み優先度を実装（OS 環境変数を保護する protected 機能、override フラグ）。
  - Settings クラスでアプリケーション設定をラップ（J-Quants トークン、kabu API、Slack、DB パス、環境／ログレベル等）。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD を導入。
- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（株価日足、財務データ、マーケットカレンダー）。
  - 固定間隔の RateLimiter（120 req/min）を実装。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）を実装。
  - 401 Unauthorized 受信時はリフレッシュトークンで自動的に ID トークンを更新してリトライ（1 回のみ）する仕組みを実装し、無限再帰を回避。
  - ページネーション対応（pagination_key の共有）。
  - DuckDB への冪等保存機能を実装（raw_prices / raw_financials / market_calendar への ON CONFLICT DO UPDATE）。
  - レスポンス JSON デコード失敗時のエラーメッセージ強化。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news に冪等保存する処理を実装（記事ID は正規化 URL の SHA-256 で生成）。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）を実装。
  - defusedxml による XML パーシングで XML-Bomb 等の攻撃を防止。
  - SSRF 対策（HTTP/HTTPS 以外のスキーム拒否等）や受信サイズ上限（10 MB）を導入。
  - バルク INSERT のチャンク処理で SQL 長やパラメータ数を抑制。
- 研究用モジュール（kabusys.research）
  - factor_research: calc_momentum, calc_value, calc_volatility を実装（prices_daily / raw_financials を参照）。
  - feature_exploration: calc_forward_returns（複数ホライズン対応）、calc_ic（Spearman の ρ）、factor_summary、rank を実装。
  - zscore_normalize ユーティリティを公開（data.stats 経由）。
- 特徴量生成（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date) を実装。research の生ファクターをマージ後、ユニバースフィルタ適用、Z スコア正規化（±3 クリップ）、features テーブルへ日付単位で置換（トランザクションで原子性確保）。
  - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を導入。
  - 休場日や当日欠損に対応するため target_date 以前の最新価格を参照。
- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold, weights) を実装。features と ai_scores を統合して final_score を計算し、BUY / SELL シグナルを生成して signals テーブルへ日付単位で置換。
  - コンポーネントスコア（momentum, value, volatility, liquidity, news）の計算ロジックを実装（シグモイド変換、PER の逆数スコア、atr 反転等）。
  - AI スコアのレジーム集計で Bear 判定を行い、Bear では BUY を抑制。
  - 欠損コンポーネント値は中立値 0.5 で補完して不当な降格を防止。
  - weights の入力検証とデフォルトへのフォールバック・再スケーリングを実装。
  - 保有ポジションのエグジット判定（ストップロス -8% / スコア低下）を実装。SELL 優先ポリシー（SELL 対象は BUY から除外）。
  - トランザクション + バルク挿入による原子性を保証。
- 汎用ユーティリティ
  - 型安全・堅牢な変換関数（_to_float, _to_int）を実装。小数を含む整数文字列の誤変換回避等に配慮。
  - DuckDB の複数クエリでのパフォーマンス考慮（1 クエリでまとめて取得する実装など）。

### Changed
- DB 操作は可能な箇所でトランザクションを利用し、DELETE→INSERT の日付単位置換による冪等性を確保。
- ログ出力を充実化（情報・警告・デバッグレベルでのメッセージ）。
- .env ロード時に OS 環境変数を保護する protected セットを導入して、意図しない上書きを防止。
- research モジュールは外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。

### Fixed / Robustness
- API リクエストでの 401 リフレッシュ処理は一度だけ実行して無限再帰を防止。
- ページネーション key の二重取得防止（seen_keys で重複チェック）。
- DB 保存時に主キー欠損行をスキップして不正データの挿入を回避（スキップ件数をログ出力）。
- 売却判定で価格が取得できない場合は判定をスキップして誤クローズを防止。
- calc_ic / factor_summary 等で有効レコード不足時に None を返すようにして不正な計算を回避。
- ニュース収集で受信サイズを制限してメモリ DoS を防止。
- rank() の実装で丸め (round(v, 12)) を用いて浮動小数点の ties 検出漏れを抑制。

### Security
- XML パーシングに defusedxml を使用して XML 関連攻撃を防止。
- RSS/URL 処理においてスキーム検証やトラッキングパラメータ削除を行い、SSRF とトラッキング漏洩を低減。
- API クライアントでタイムアウトを設定（urllib）し、リトライで過剰な負荷を抑制。

### Performance
- RateLimiter による固定間隔スロットリングで API レート制限（120 req/min）を順守。
- DuckDB へのクエリはまとめて取得する設計（複数ホライズンを一度のクエリで取得する等）。
- ニュースのバルク挿入はチャンク化して SQL 長やパラメータ数の上限を抑制。

### Documentation / Examples
- 各モジュールにモジュールドックストリングで設計方針・処理フロー・使用例を記載。開発者が利用方法を理解しやすくしています。

### Breaking Changes
- なし（初期リリースのため互換性問題は想定していません）。

---

注記:
- 環境変数や .env の重要項目（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）は Settings から取得する設計です。必須変数が未設定の場合は ValueError を送出します。
- デフォルトの DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring 用): data/monitoring.db
- 将来的な改善案（未実装の仕様・TODO）はコード内 docstring に記載されています（例: トレーリングストップや時間決済等）。

（この CHANGELOG はコード内容から推測して作成しています。実際のリリースノートとして利用する場合は、実際のコミット・チケット情報に基づいて修正してください。）