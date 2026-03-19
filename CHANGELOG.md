# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠し、セマンティックバージョニングを採用します。

なお、本ファイルはコードベースから推測して作成した初期リリース用の CHANGELOG です。

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - YYYY-MM-DD
最初の公開リリース。

### Added
- パッケージの基礎構成を追加
  - kabusys パッケージエントリ（src/kabusys/__init__.py、バージョン: 0.1.0）。
  - サブパッケージの公開 API: data, strategy, execution, monitoring（execution は空パッケージとして追加）。

- 環境・設定管理 (src/kabusys/config.py)
  - .env / .env.local 自動ロード機能（プロジェクトルートを .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パーサ実装（export 形式対応、クォート・エスケープ、インラインコメント処理）。
  - Settings クラス（環境変数の取得ラッパー、必須チェック、デフォルト値、列挙検証）。
  - 必須環境変数例（使用箇所）:
    - JQUANTS_REFRESH_TOKEN（J-Quants API）
    - KABU_API_PASSWORD（kabuステーション API）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（Slack 通知）
    - DB パス: DUCKDB_PATH, SQLITE_PATH
    - 実行環境: KABUSYS_ENV（development, paper_trading, live）
    - ログレベル: LOG_LEVEL（DEBUG/INFO/...）

- Data 層（src/kabusys/data）
  - J-Quants クライアント (jquants_client.py)
    - API 呼び出しユーティリティ（ページネーション対応）。
    - レート制限制御（固定間隔スロットリング、デフォルト 120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行対象）。
    - 401 時の自動トークンリフレッシュ（1 回だけ再試行）。
    - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()。
    - DuckDB へ冪等保存関数: save_daily_quotes(), save_financial_statements(), save_market_calendar()（ON CONFLICT で重複更新）。
    - データ変換ユーティリティ: _to_float(), _to_int()（堅牢な型変換）。
    - UTC の fetched_at 記録（Look-ahead バイアスのトレーサビリティ確保）。
  - ニュース収集モジュール (news_collector.py)
    - RSS フィードからの記事収集と raw_news への冪等保存（ON CONFLICT DO NOTHING を想定）。
    - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除、小文字化）。
    - 記事 ID を SHA-256（正規化 URL のハッシュ）で生成して冪等性を担保。
    - defusedxml を用いた安全な XML パース（XML Bomb などの防御）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES, デフォルト 10MB）によるメモリ DoS 対策。
    - HTTP スキームチェック / SSRF 回避、挿入のチャンク分割（_INSERT_CHUNK_SIZE）。
    - デフォルト RSS ソース: Yahoo Finance（news.yahoo.co.jp のビジネスカテゴリ）。

- Research 層（src/kabusys/research）
  - ファクター計算 (factor_research.py)
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）計算。
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）計算。
    - Value（per, roe）計算（raw_financials と prices_daily を組合せ）。
    - DuckDB SQL ベースで営業日欠損やウィンドウ不備を考慮した実装。
  - 特徴量探索・評価ユーティリティ (feature_exploration.py)
    - 将来リターン計算（calc_forward_returns: 任意ホライズン、デフォルト [1,5,21]）。
    - IC（Spearman の ρ）計算（calc_ic）とランク化ユーティリティ（rank）。
    - ファクター統計サマリー（factor_summary: count/mean/std/min/max/median）。
  - zscore_normalize は kabusys.data.stats から利用（モジュール公開を前提）。

- Strategy 層（src/kabusys/strategy）
  - 特徴量エンジニアリング (feature_engineering.py)
    - 研究結果の生ファクターをマージ、ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円）を適用。
    - Z スコア正規化（対象カラム指定）および ±3 でのクリッピング。
    - DuckDB の features テーブルに対して日付単位で置換（トランザクション + バルク挿入で原子性を保証）。
    - 冪等設計（対象日を削除してから挿入）。
  - シグナル生成 (signal_generator.py)
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - シグモイド変換、欠損コンポーネントは中立 0.5 で補完。
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）を提供、ユーザー重みは検証・正規化してマージ。
    - BUY 閾値デフォルト 0.60、Bear レジーム検知（ai_scores の regime_score 平均が負かつサンプル数条件）による BUY 抑制。
    - エグジット（SELL）判定: ストップロス（-8%）とスコア低下。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）、signals テーブルへ日付単位で置換（トランザクション保証）。
    - 生成関数は generate_signals(conn, target_date, threshold, weights) で総シグナル数を返す。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- ニュース収集で defusedxml を使用し XML の脅威を低減。
- RSS パース・URL 正規化でトラッキングパラメータ除去やスキーム検証を実施、SSRF やトラッキング由来の情報漏洩リスクを軽減。
- J-Quants クライアントはトークン管理・自動リフレッシュを実装し、認証エラーに対して誤動作しないよう対処。

### Known limitations / Notes / TODO
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price / entry_date 等が必要）。
- features テーブル等のスキーマ定義（DDL ファイル）は本チェンジログ作成時点のコードに含まれていないため、DB マイグレーションは別途必要。
- kabusys.data.stats の実装（zscore_normalize 等）は本スナップショットには含まれていないが、research/strategy から利用される前提。
- news_collector の実際の HTTP フェッチ処理と DB への紐付けロジック（news_symbols など）は、実装の詳細により追加の検証が必要。
- テストや運用時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードを無効化できる（テストの隔離に便利）。

---

作成者注:
- 日付（YYYY-MM-DD）は実際のリリース日に合わせて更新してください。
- 本 CHANGELOG は提供されたコード内容から推測して記載しています。実際のリポジトリ履歴やコミットメッセージに基づく正確な履歴が必要な場合は、Git のコミットログから正式な CHANGELOG を生成してください。