# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/) の形式に従います。

注: 本 CHANGELOG はソースコードから推測して作成したもので、実際のコミット履歴ではありません。

## [Unreleased]

---

## [0.1.0] - 2026-03-21

初回公開リリース。日本株自動売買システムのコアライブラリを実装・公開。

### Added
- パッケージ基盤
  - パッケージ名: kabusys（バージョン 0.1.0）
  - パブリック API エクスポート: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする機能を実装。
  - .env パーサを実装（コメント行、export プレフィックス、クォート・エスケープ、インラインコメントの扱いに対応）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - OS 環境変数を保護する protected ロジック（.env.local での上書き時に考慮）。
  - 必須環境変数取得用の _require ユーティリティと Settings クラスを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を扱うプロパティを提供。
    - DB パス（DUCKDB_PATH, SQLITE_PATH）、ログレベル（LOG_LEVEL）、環境（KABUSYS_ENV）の検証を実装。
    - is_live / is_paper / is_dev のヘルパーを追加。

- データ収集・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制限 (120 req/min) に従う固定間隔スロットリング RateLimiter を実装。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）を追加。
  - 401 発生時のリフレッシュトークン自動更新を実装（1 回のみリトライ）。
  - ページネーション対応の fetch_* 関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を実装。
  - DuckDB へ冪等に保存する save_* 関数を実装:
    - save_daily_quotes: raw_prices テーブルへの ON CONFLICT DO UPDATE を実装。
    - save_financial_statements: raw_financials への保存と重複排除。
    - save_market_calendar: market_calendar テーブルへの保存と重複排除。
  - 型安全な変換ユーティリティ _to_float / _to_int を追加。
  - fetched_at を UTC ISO8601 で記録し、Look-ahead バイアス回避のため取得時刻を追跡。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集モジュールを実装（デフォルトで Yahoo Finance のビジネス RSS を設定）。
  - defusedxml を用いた XML パース（XML Bomb 等に対する防御）。
  - URL 正規化ロジック（トラッキングパラメータ除去、スキーム/ホスト小文字化、クエリソート、フラグメント除去）。
  - レスポンス最大サイズ制限（MAX_RESPONSE_BYTES = 10MB）、SSRF 対策、トラッキングパラメータリストの除去等を実装。
  - バルク INSERT のチャンク化（INSERT_CHUNK_SIZE）と冪等保存の方針を明記。

- リサーチ（kabusys.research）
  - ファクター計算を行う factor_research を実装:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離）を計算。
    - calc_volatility: 20 日 ATR、atr_pct、avg_turnover、volume_ratio を計算。
    - calc_value: 最新の財務データ（eps/roe）と当日株価から PER/ROE を計算。
  - 特徴量探索モジュール feature_exploration を実装:
    - calc_forward_returns: 将来リターン（デフォルト: 1,5,21 営業日）を一括取得。
    - calc_ic: スピアマンランク相関（IC）計算。
    - factor_summary: 各ファクターの基本統計量（count/mean/std/min/max/median）。
    - rank: 同順位を平均ランクで扱うランク関数。
  - DuckDB の prices_daily / raw_financials テーブルのみ参照し、本番 API へアクセスしない設計を強調。

- 戦略（kabusys.strategy）
  - 特徴量エンジニアリング（strategy.feature_engineering.build_features）
    - research の生ファクターを統合して正規化済み特徴量を features テーブルへ日付単位で置換（冪等）。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を実装。
    - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）と ±3 でのクリップを実装。
    - トランザクション + バルク挿入で原子性を保証。
  - シグナル生成（strategy.signal_generator.generate_signals）
    - features と ai_scores を統合して各銘柄の最終スコア（final_score）を計算。
    - コンポーネントスコア: momentum, value, volatility, liquidity, news を計算するユーティリティを実装（シグモイド変換等）。
    - デフォルト重みと閾値を実装（デフォルト閾値: 0.60）。
    - Bear レジーム検知（ai_scores の regime_score 平均が負である場合。サンプル数閾値あり）に基づく BUY 抑制。
    - エグジット判定（売りシグナル）を実装:
      - ストップロス（終値/avg_price - 1 < -8%）優先。
      - スコア低下（final_score < threshold）。
      - 価格欠損時の SELL 判定スキップとログ出力。
    - BUY/SELL を signals テーブルへ日付単位で置換（冪等）。
    - ユーザー指定 weights の検証・正規化ロジックを実装（未知キーや不正値は無視、合計が 1 に再スケール）。

### Changed
- n/a（初回リリースのため履歴変更はなし）

### Fixed
- n/a（初回リリースのためバグ修正履歴はなし）

### Known limitations / Notes
- signal_generator の未実装部分（将来的に追加予定）
  - トレーリングストップ（positions テーブルに peak_price / entry_date が必要）
  - 時間決済（保有 60 営業日超過）等は未実装としてコメントに記載。
- news_collector は記事 ID を SHA-256 ハッシュ（先頭 32 文字）で生成する設計がコメントにあるが、現状のファイル断片では全実装が確認できない部分がある（この CHANGELOG はソースからの推測に基づく）。
- jquants_client は urllib ベースの実装であり、外部 HTTP クライアントの選定や非同期化は今後の検討事項。
- research モジュールは pandas 等に依存せず標準ライブラリと DuckDB の SQL を重視した実装方針。

### Dependencies (言及)
- 必須: duckdb
- ニュースパース時: defusedxml
- （環境変数により J-Quants / Slack / kabu API の設定が必要）

---

（今後は機能追加・バグ修正ごとにこのファイルを更新してください）