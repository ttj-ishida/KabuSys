# Changelog

すべての重要な変更をここに記録します。本ファイルは Keep a Changelog の形式に準拠します。  
バージョン番号は semver に従います。

## [Unreleased]

## [0.1.0] - 2026-03-19
初回公開リリース

### Added
- パッケージ基盤
  - パッケージエントリポイント `kabusys` を追加（__version__ = 0.1.0）。モジュール公開: data, strategy, execution, monitoring。
- 環境設定
  - `kabusys.config.Settings` を実装。環境変数からアプリ設定（J-Quants トークン、kabu API パスワード、Slack トークン・チャンネル、DB パス、環境種別、ログレベル等）を取得。
  - .env 自動読み込み機能を追加（プロジェクトルート検出: `.git` または `pyproject.toml`）。読み込み順は OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パーサーは `export KEY=val` 形式、クォート対応、インラインコメント処理などに対応。
  - 必須環境変数が未設定の場合に `ValueError` を投げる `_require` 実装。
- データ収集（J-Quants）
  - `kabusys.data.jquants_client` を実装。
  - RateLimiter による固定間隔スロットリング（デフォルト 120 req/min）を実装。
  - HTTP リトライ（指数バックオフ）、最大 3 回、408/429/5xx を考慮。429 の場合は `Retry-After` を優先。
  - 401 受信時はリフレッシュトークンで自動的に ID トークンを再取得して 1 回リトライ。
  - ページネーション対応の取得関数を実装:
    - fetch_daily_quotes (日足)
    - fetch_financial_statements (財務データ)
    - fetch_market_calendar (取引カレンダー)
  - DuckDB へ冪等的に保存する関数を実装:
    - save_daily_quotes (raw_prices テーブルへの ON CONFLICT DO UPDATE)
    - save_financial_statements (raw_financials)
    - save_market_calendar (market_calendar)
  - データ変換ユーティリティ `_to_float`, `_to_int` を実装し、入力の堅牢なパースを実現。
- ニュース収集
  - `kabusys.data.news_collector` を実装（RSS からのニュース収集基盤）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）およびテキスト前処理の基礎を実装。
  - defusedxml を使った XML パースを想定し、受信バイト数制限や SQL バルク挿入のチャンク化など DoS 対策を考慮。
  - デフォルト RSS ソースとして Yahoo Finance のビジネスカテゴリを登録。
- リサーチ（研究用ユーティリティ）
  - `kabusys.research.factor_research` を実装。prices_daily / raw_financials を参照して以下のファクターを計算:
    - Momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日移動平均乖離）
    - Volatility / Liquidity: atr_20, atr_pct, avg_turnover, volume_ratio
    - Value: per, roe（最新の財務データを結合）
  - `kabusys.research.feature_exploration` を実装:
    - calc_forward_returns: 将来リターン（horizons のバリデーションあり）
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算
    - factor_summary: 各ファクター列の統計サマリ（count, mean, std, min, max, median）
    - rank: 平均ランク処理（同順位は平均ランク）
  - `kabusys.research.__init__` で上記ユーティリティを公開。
- 戦略
  - `kabusys.strategy.feature_engineering` を実装:
    - 研究モジュール（calc_momentum / calc_volatility / calc_value）から得た生ファクターをマージ、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 数値ファクターを z-score 正規化し ±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE + INSERT トランザクション）し冪等性を担保。
  - `kabusys.strategy.signal_generator` を実装:
    - features と ai_scores を統合し各コンポーネントスコア（momentum / value / volatility / liquidity / news）を計算。
    - コンポーネントはシグモイド変換や PER の逆数変換等で [0,1] にマップし、重み付け和で final_score を算出（デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。
    - BUY シグナル閾値のデフォルトは 0.60。weights はユーザ指定を許容し、妥当性検査後に合計が 1.0 になるよう再スケーリングする。
    - Bear レジーム判定（AI の regime_score 平均が負の場合でサンプル数閾値以上のとき）を導入し、Bear では BUY シグナルを抑制。
    - エグジット（SELL）判定を実装（ストップロス: -8% を優先、score の低下でのクローズなど）。positions テーブルの欠如や価格欠損時の安全対策あり。
    - signals テーブルへ日付単位の置換で保存（冪等）。
  - `kabusys.strategy.__init__` で build_features / generate_signals を公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュース収集で defusedxml を使用して XML ベースの攻撃を軽減する設計。
- ニュース URL の正規化・トラッキングパラメータ除去、受信サイズ上限（10MB）やホスト/IP の検証（SSRF 対策を予定）などを考慮した実装方針。
- J-Quants クライアントはトークン管理と自動リフレッシュの実装により 401 が発生した際の安全な再認証を実現。

### Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は未設定だと実行時に例外が発生します。
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring 用): data/monitoring.db
  - 必要に応じて環境変数（DUCKDB_PATH, SQLITE_PATH）で変更してください。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CI/テスト環境等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB 側で想定されるテーブルスキーマ（少なくとも以下のテーブルが必要）:
  - raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news 等
  - 各関数の docstring に挙げられているカラム/PK 制約に準拠すること。
- signal_generator の weights パラメータは不正値（未知キー、負値、NaN/Inf、bool 等）をスキップし、残りをデフォルト重みにマージして合計が 1 に再スケールされます。カスタム重みを渡す際は注意してください。
- sell 判定や未実装の条件（トレーリングストップ、時間決済）はコードコメントで言及されています。これらは将来的な拡張ポイントです。

### Known limitations / TODO
- news_collector の記事 ID 生成（URL 正規化後の SHA-256 ハッシュ等）や記事パースの詳細ロジックは設計方針に記載されているが、個別の結合ロジックは環境に依存しているため実装拡張が必要。
- positions テーブルに peak_price / entry_date 等の情報がないとトレーリングストップ・時間決済の判定は未実装。
- research モジュールは外部ライブラリ（pandas 等）に依存しない設計だが、大規模データでの性能チューニングやインデックス設計は運用段階での調整が必要。

---

作成者: kabusys コードベース（自動生成された CHANGELOG）。ドキュメントや API の仕様、DB スキーマについては各モジュールの docstring を参照してください。