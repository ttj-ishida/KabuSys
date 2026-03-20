Keep a Changelog
=================

すべての重要な変更をここに記録します。  
このプロジェクトはセマンティックバージョニングに従います。  

## [Unreleased]

（現在の開発中の変更はここに記載）

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システムのコアライブラリを導入します。主な機能、設計方針、公開 API を以下に列挙します。

### Added

- パッケージ・エントリポイント
  - src/kabusys/__init__.py
    - __version__ = "0.1.0"
    - パブリック API として data, strategy, execution, monitoring をエクスポート（execution はプレースホルダ）。  

- 環境変数・設定管理
  - src/kabusys/config.py
    - .env ファイル（.env, .env.local）と OS 環境変数を統合してロードする自動ロード機能を実装。
    - プロジェクトルート検出（.git または pyproject.toml）によりカレントワーキングディレクトリに依存しないロードを実現。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env パーサーは export プレフィックス、シングル/ダブルクォートやバックスラッシュエスケープ、インラインコメント等を考慮して堅牢にパース。
    - Settings クラスを追加し、J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等のプロパティを提供。必須変数未設定時は ValueError を発生させる。

- Data 層（J-Quants クライアント・データ保存）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装（ページネーション、レート制限、リトライ、トークンリフレッシュを含む）。
    - 固定間隔スロットリングによるレート制限（120 req/min）を _RateLimiter で実装。
    - リトライロジック（指数バックオフ、最大 3 回）。HTTP 401 受信時はトークン自動更新を一度行い再試行。
    - fetch_* 系（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）はページネーション処理を実装。
    - DuckDB へ保存する save_* 系（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等性を考慮し、ON CONFLICT DO UPDATE を用いて重複を回避。
    - データ取得時の fetched_at を UTC ISO8601 で記録し、ルックアヘッドバイアスのトレースを可能に。
    - 型変換ユーティリティ（_to_float / _to_int）を実装し、不正な形式を安全に扱う。

- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィードからの記事収集モジュールを追加（既定の RSS ソースを含む）。
    - セキュリティ対策: defusedxml の使用による XML 攻撃防御、HTTP(S) スキーム検証、受信サイズ上限(MAX_RESPONSE_BYTES) によるメモリ DoS 緩和等を設計に反映。
    - URL 正規化（トラッキングパラメータの除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）を実装予定・文書化（記事ID は正規化後の SHA-256 部分を利用する方針）。
    - raw_news への冪等保存、news と銘柄コードの紐付け方針を設計に明示。
    - バルク INSERT のチャンク化による性能・安全性配慮。

- Research 層（ファクター計算・探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（calc_momentum）、ボラティリティ（calc_volatility）、バリュー（calc_value）を実装。
    - prices_daily / raw_financials のみを参照する設計（本番APIや発注層に依存しない）。
    - 各関数は (date, code) キーの dict リストを返し、データ不足時は None を返す仕様。
    - ATR/MA 等の計算はウィンドウサイズやデータ不足時の取り扱いを明確化。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリー（factor_summary）、rank ユーティリティを実装。
    - 外部依存を避け、標準ライブラリと DuckDB のみで実装。

- Strategy 層（特徴量生成・シグナル生成）
  - src/kabusys/strategy/feature_engineering.py
    - build_features(conn, target_date) を実装。
    - research モジュールの生ファクターを取得し、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムを z スコア正規化（zscore_normalize を利用）し ±3 でクリップ、features テーブルへ日付単位で置換（トランザクションによる原子性保証、冪等）。
    - ルックアヘッドバイアス防止の方針を明記（target_date 時点のデータのみを使用）。
  - src/kabusys/strategy/signal_generator.py
    - generate_signals(conn, target_date, threshold, weights) を実装。
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news の各コンポーネントスコアを算出、重み付け合算で final_score を算出（デフォルト重みを採用）。
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完。
    - Bear レジーム判定（AI の regime_score 平均が負）、Bear 時は BUY シグナルを抑制。
    - エグジット条件（ストップロス -8%、スコア低下）を実装。SELL は BUY より優先して排除。
    - signals テーブルへ日付単位で置換（トランザクションによる原子性保証、冪等）。
    - 重みの入力検証（未知キー/負値/NaN を無視、合計でリスケール）。

- 公開 API の整理
  - src/kabusys/strategy/__init__.py, src/kabusys/research/__init__.py で主要関数を再エクスポートし、使いやすいモジュール API を提供。

### Security / Robustness

- API クライアントでの堅牢性
  - レート制限遵守、再試行ロジック、401 時のトークン自動更新、タイムアウト設定などを実装。
- CSV/JSON/HTTP など外部入力に対して安全に処理するためのチェックを各所に実装（例: PK 欠損行のスキップ、受信サイズ制限、XML パーサの安全化）。
- DB 書き込みは冪等性を重視（ON CONFLICT / 日付単位の DELETE+INSERT トランザクションパターン）。

### Notes / Implementation details

- DuckDB を中心に設計されており、prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals / market_calendar 等のテーブルを想定。
- 多くの DB 書き込みは BEGIN/COMMIT/ROLLBACK を使った明示的トランザクションで原子性を確保。
- 一部機能（news_collector の完全な記事ID生成ロジック、execution 層、monitoring モジュール）はこのバージョンでは設計・骨組みが整っているが、今後の実装・拡張を想定。
- ドキュメント（関数 docstring）で StrategyModel.md / DataPlatform.md / Research の外部仕様への準拠を明記しているため、仕様追従が容易。

### Breaking Changes

- 初回リリースのため該当なし。

### Migration Notes

- 設定: 必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を .env または OS 環境変数で提供してください。未設定時は Settings のプロパティが ValueError を投げます。
- 自動 .env ロードを無効化したいテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

以上が initial release (0.1.0) の変更点要約です。追加のリリースノートや日付・詳細が必要であればお知らせください。