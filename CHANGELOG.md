# Changelog

すべての注目すべき変更点を記録します。フォーマットは Keep a Changelog に準拠しています。  

現在のパッケージバージョン: 0.1.0

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システム「KabuSys」の基本機能群を実装しました。
主な提供機能は以下の通りです。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py: パッケージ名とバージョン指定（__version__ = "0.1.0"）、公開モジュール指定（data, strategy, execution, monitoring）。

- 設定 / 環境読み込み
  - src/kabusys/config.py:
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動で読み込む自動環境読み込み機能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env のパース実装（コメント・export 形式・クォート・エスケープを考慮）。
    - .env.local は .env の後に上書き（override=True）されるが、OS 環境変数は保護（protected）。
    - Settings クラスを提供し、JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID など必須設定をプロパティで取得。
    - DUCKDB_PATH / SQLITE_PATH の既定値指定、KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）および is_live / is_paper / is_dev の便宜プロパティ。

- データ取得・保存（J-Quants クライアント）
  - src/kabusys/data/jquants_client.py:
    - J-Quants API クライアント実装（ページネーション対応）。
    - レートリミッタ（120 req/min 固定間隔スロットリング）実装。
    - 再試行ロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx 対応）。
    - 401 発生時の自動トークンリフレッシュ（1回のみ）とモジュールレベルのトークンキャッシュ共有。
    - fetch_* 系関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への冪等保存関数: save_daily_quotes、save_financial_statements、save_market_calendar（ON CONFLICT による更新）。
    - データ変換ユーティリティ _to_float / _to_int。

- ニュース収集
  - src/kabusys/data/news_collector.py:
    - RSS フィードからの記事収集の基盤実装（デフォルトに Yahoo Finance RSS を含む）。
    - URL 正規化（tracking パラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
    - セキュリティ対策: defusedxml による XML パース、受信サイズ上限（MAX_RESPONSE_BYTES）、HTTP/HTTPS スキーム制限、SSRF や XML Bomb などへの配慮。
    - 記事 ID は正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で作成し冪等保存を支援。
    - バルク INSERT のチャンク化による効率化。

- リサーチ（ファクター計算・探索）
  - src/kabusys/research/factor_research.py:
    - モメンタム（calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev）、ボラティリティ（calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio）、バリュー（calc_value: per, roe）を DuckDB 上で計算する関数群。
    - 営業日ベース・ウィンドウの扱い、データ不足時の None ハンドリング。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算 calc_forward_returns（指定ホライズン、ページ範囲最適化）。
    - IC 計算（Spearman の ρ） calc_ic、ランク変換ユーティリティ rank、統計サマリー factor_summary。
    - 外部依存なしで標準ライブラリのみで実装。

- 戦略（特徴量生成・シグナル生成）
  - src/kabusys/strategy/feature_engineering.py:
    - research モジュールで算出された生ファクターを統合、ユニバースフィルタ（最低株価、平均売買代金）適用、Z スコア正規化（zscore_normalize を利用）、±3 クリップ、features テーブルへの日付単位での置換（トランザクションで原子性）。
    - ルックアヘッドバイアス防止の設計（target_date 時点のみ使用）。
  - src/kabusys/strategy/signal_generator.py:
    - features と ai_scores を統合して final_score を計算し、BUY / SELL シグナルを生成して signals テーブルへ保存。
    - 重みのフォールバック・正規化、無効な重みのフィルタリング。
    - Bear レジーム判定（ai_scores の regime_score 平均）、Bear 時の BUY 抑制。
    - SELL 判定ロジック（ストップロス、スコア低下）を実装。トレーリング／時間決済は未実装だが注記あり。
    - 日付単位の置換（DELETE → INSERT）で冪等性を確保。

- モジュールエクスポート
  - src/kabusys/strategy/__init__.py と src/kabusys/research/__init__.py で主要 API を公開（build_features, generate_signals, calc_momentum, calc_value, calc_volatility, zscore_normalize 等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector において defusedxml を利用、受信サイズ制限、URL 正規化・ホワイトリスト的な扱いなど、外部入力に対する複数の保護を実装。
- jquants_client の HTTP エラー処理でトークン漏洩や無限再帰を防ぐ設計（allow_refresh フラグの採用など）。

### Notes / Migration
- 必要な環境変数（少なくともリリース時に必須なもの）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - (任意) DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL
- 自動 .env 読み込みの挙動:
  - OS 環境変数 > .env.local > .env の優先順位。
  - OS 環境変数は .env による上書きを防ぐ（protected）。
  - テスト等で自動ロードをオフにするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB 側に期待するテーブル（実行時に存在する前提）
  - raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals
  - 各関数は上記テーブルの特定カラムを参照・更新するため、既存スキーマが必要です（関数内 SQL を参照してマイグレーションしてください）。
- signal_generator のデフォルト重みは StrategyModel.md の仕様（momentum 0.40 等）を反映。外部から weights を与えるとスケール調整される。
- 未実装の戦略要素: トレーリングストップ、時間決済（注釈あり）。必要に応じて positions テーブルへ peak_price / entry_date の追加が必要。

### Breaking Changes
- （初回リリースのため該当なし）

---

今後のリリースでは、ポジション管理の拡張（トレーリングストップ等）、発注（execution 層）との統合、より詳細なログ / メトリクス、テストカバレッジ強化などを予定しています。必要であれば、CHANGELOG に追記する優先事項や詳細説明の追加を行います。