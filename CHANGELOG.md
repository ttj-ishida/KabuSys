# Keep a Changelog
すべての重要な変更をここに記録します。  
フォーマットは Keep a Changelog に準拠し、Semantic Versioning を採用します。

- リリース日付は ISO 形式 (YYYY-MM-DD) です。
- ここに記載の内容は、与えられたコードベースから推測して作成した CHANGELOG です。

## [Unreleased]

## [0.1.0] - 2026-03-21
初回公開リリース。以下の主要機能・設計方針を実装しています。

### Added
- パッケージ初期化
  - kabusys パッケージを追加。バージョンは 0.1.0。モジュール公開 API: data, strategy, execution, monitoring をエクスポート（execution は空のパッケージとして用意）。

- 環境設定 / 自動 .env ロード
  - kabusys.config モジュールを追加。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索）。
  - .env / .env.local の自動読み込み（OS 環境変数を保護する protected 機構、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート）。
  - ユーザーフレンドリーな .env 行パーサ（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理）。
  - Settings クラスを提供（J-Quants トークン、kabu API 設定、Slack 設定、DB パス、環境 / ログレベル検証、is_live / is_paper / is_dev ヘルパー）。

- データ取得・保存
  - kabusys.data.jquants_client を追加:
    - J-Quants API クライアント（価格/財務/マーケットカレンダー取得）。
    - 固定間隔レートリミッタ（120 req/min）を実装。
    - リトライ（指数バックオフ、最大 3 回）、HTTP 429 の Retry-After 優先処理、ネットワーク例外の再試行。
    - 401 受信時にリフレッシュトークンから id_token を自動再取得する仕組み（1 回のみリフレッシュしてリトライ）。
    - ページネーション対応 API 呼び出し。
    - DuckDB への保存ユーティリティ（raw_prices / raw_financials / market_calendar）を冪等に保存（ON CONFLICT DO UPDATE / DO NOTHING を利用）。
    - 型変換ユーティリティ（_to_float / _to_int）を実装し不正データを安全に扱う。

  - kabusys.data.news_collector を追加:
    - RSS フィード収集ロジック（デフォルトに Yahoo Finance を含む）。
    - XML の安全パース（defusedxml）による脆弱性緩和。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
    - レスポンスサイズ上限（10MB）や SSRF 対策などの安全対策。
    - 挿入チャンク / トランザクションによる効率的かつ正確な DB 登録。

- 研究（Research）モジュール
  - kabusys.research.factor_research を追加:
    - Momentum, Volatility, Value（および一部 Liquidity）ファクター計算関数を実装。
    - DuckDB 上の SQL ウィンドウ関数を活用した効率的な計算（移動平均、LAG/LEAD、ATR の算出など）。
    - データ不足（ウィンドウが未満）に対する None ハンドリング。
  - kabusys.research.feature_exploration を追加:
    - 将来リターン計算（任意ホライズン、単一クエリで取得）。
    - IC（Spearman ランク相関）計算、rank ユーティリティ（同順位は平均ランク）。
    - ファクター統計サマリ（count/mean/std/min/max/median）。
  - research パッケージの __all__ を整備し zscore_normalize などを公開。

- 戦略（Strategy）モジュール
  - kabusys.strategy.feature_engineering を追加:
    - research モジュールが出す生ファクターをマージ、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）適用、Z スコア正規化、±3 でクリップして features テーブルへ日付単位置換（冪等）。
    - DuckDB トランザクション + バルク挿入で原子性を保証。ロールバック時の警告ログを実装。
    - ルックアヘッドバイアス回避方針の明記（target_date のみ参照）。
  - kabusys.strategy.signal_generator を追加:
    - features と ai_scores を統合し final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ日付単位置換（冪等）。
    - コンポーネントスコア（momentum / value / volatility / liquidity / news）の計算ロジックを実装（シグモイド変換、欠損は中立 0.5 補完）。
    - 重みのマージと再スケール（ユーザー重みは検証して不正値をスキップ）。
    - Bear レジーム判定（AI の regime_score 平均が負かつサンプル数閾値を満たす場合）による BUY 抑制。
    - SELL 判定ロジック（ストップロス -8% / スコア低下）。保有銘柄の価格欠損時は判定をスキップして安全策を講じる。
    - signals テーブルへトランザクションで書き込み、ROLLBACK に対するログ処理。

- 汎用ユーティリティ
  - zscore_normalize 等のスコア正規化ユーティリティを data.stats（別モジュールとして存在）から利用する設計。

### Changed
- （初版のため「変更」はなし。設計上の注意点やデフォルト値をコード内ドキュメントで明記）
  - 各モジュールに詳細な docstring と設計方針を追加しており、実運用・テストの前提条件（テーブル構成・環境変数）を明確化。

### Fixed
- （初版リリースのため該当なし。各関数に不正入力・例外発生時の防御ロジックを実装）

### Security
- news_collector で defusedxml を用いて XML 関連の攻撃を軽減。
- news_collector の URL 正規化とトラッキング除去で情報漏洩の低減。
- jquants_client の HTTP レスポンス処理で JSON デコードエラー時に明確な例外を送出。
- .env ロード時に OS 環境変数を保護する設計（override/protected）。

### Notes / Known limitations
- execution 層（kabu ステーションとの実際の発注処理）はこのコードベースでは実装されていない（パッケージは空で用意）。実際のオーダー送信は別モジュールで実装する想定。
- 一部機能（例: positions テーブルに peak_price / entry_date が必要なトレーリングストップや時間決済）は未実装で、コードにて未実装である旨コメントが残されている。
- DuckDB のスキーマ（tables: raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals など）は事前に作成されている前提。
- 外部依存は最小限に抑えているが、defusedxml と duckdb は必要。

---

（今後のリリースでは機能追加・バグ修正・パフォーマンス改善・execution 層の組み込みなどを記載予定）