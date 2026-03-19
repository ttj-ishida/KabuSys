CHANGELOG
=========
All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under Semantic Versioning.

Unreleased
----------
（なし）

0.1.0 - 2026-03-19
------------------
Initial release — 基本機能の実装

Added
- パッケージ基本設定
  - kabusys.__version__ を 0.1.0 に設定。
  - 公開 API: kabusys パッケージが data, strategy, execution, monitoring をエクスポート。

- 環境設定 / 設定管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env パーサの実装: コメント行、export プレフィクス、シングル/ダブルクォート内のエスケープなどに対応。
  - 上書き制御（override）と OS 環境変数保護（protected）をサポート。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - Settings クラス: J-Quants / kabu ステーション / Slack / データベースパス / 実行環境・ログレベル等のプロパティとバリデーション（有効値チェック、必須環境変数チェック）。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアント実装。
  - レートリミッタ（固定スロットル: 120 req/min）。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象。429 の Retry-After を尊重）。
  - 401 受信時のトークン自動リフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ。
  - ページネーション対応の fetch_* 関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
  - DuckDB への保存関数（冪等）: save_daily_quotes, save_financial_statements, save_market_calendar。ON CONFLICT / DO UPDATE を使用して重複更新を防止。
  - データ型変換ユーティリティ: _to_float / _to_int（安全な変換処理）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからの記事収集基盤（デフォルトで Yahoo Finance のビジネス RSS を定義）。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホストの小文字化、フラグメント除去、クエリのソート）。
  - セキュリティ対策：defusedxml による XML パース保護、受信サイズ上限（MAX_RESPONSE_BYTES）など。
  - 冪等保存、バルク挿入のチャンク化、記事 ID をハッシュ化して一意化。

- 研究用ファクター計算 (kabusys.research.factor_research)
  - モメンタム、ボラティリティ（ATR ベース）、バリュー（PER / ROE）などのファクター計算関数: calc_momentum, calc_volatility, calc_value。
  - DuckDB の prices_daily / raw_financials テーブルを使った SQL ベースの実装（ウィンドウ関数活用、欠損制御、スキャン範囲バッファ等）。
  - 仕様に基づく各種ウィンドウ・閾値を定数化（例: MA200, ATR=20 など）。

- 研究支援ユーティリティ (kabusys.research.feature_exploration)
  - 将来リターン計算: calc_forward_returns（複数ホライズン対応、混同を防ぐため horizons バリデーション）。
  - IC（Spearman rank）計算: calc_ic（ランク付け、同順位は平均ランク処理、最小サンプル数制御）。
  - 基本統計サマリ: factor_summary。
  - ランク変換ユーティリティ: rank。
  - 依存を最小化（pandas 等に依存せず、標準ライブラリ + duckdb で実装）。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research で算出した生ファクターを正規化・合成して features テーブルへ保存する build_features 実装。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）適用。
  - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）と ±3 でクリップ。
  - 日付単位の置換（トランザクション + バルク挿入）による冪等な保存処理。
  - 休場日や当日欠損に対応する最新価格参照ロジック。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成する generate_signals 実装。
  - コンポーネントスコア（momentum / value / volatility / liquidity / news）の算出ロジックと既定重み（合計 1.0 に正規化）。
  - シグナル生成フロー: Bear レジーム判定（ai_scores の regime_score 平均が負なら BUY 抑制）、BUY 閾値（デフォルト 0.6）、SELL エグジット判定（ストップロス -8% / スコア低下）。
  - 保有ポジションの判定（positions テーブル参照）、価格欠損時の挙動（判定スキップ）とログ出力。
  - signals テーブルへ日付単位の置換（トランザクション + バルク挿入）。

Changed
- （初版のため過去変更履歴なし）

Fixed
- （初版のため過去修正履歴なし）

Security
- news_collector で defusedxml を利用して XML 関連の脆弱性を軽減。
- news_collector と jquants_client で外部入力のバリデーション・受信サイズ制限や URL 正規化を実装し SSRF / DoS のリスク軽減を図る。

Known issues / Limitations
- execution および monitoring パッケージは公開されているが、今回のリリースでは実装が見られないか最小限です（将来的に発注層・監視機能を追加予定）。
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装で、positions テーブルに peak_price / entry_date が必要になる想定。
- DuckDB のスキーマ（tables: raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar 等）は本パッケージに含まれていないため、利用前にスキーマの作成が必要。
- 外部依存: defusedxml、duckdb が必要（環境によりバージョン互換性を確認してください）。
- テストコードや CI 設定は同梱されていない（別途整備推奨）。

Migration notes
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - DUCKDB_PATH / SQLITE_PATH はデフォルト値を持つが必要に応じて設定可能。
  - KABUSYS_ENV は development | paper_trading | live のいずれかに設定してください。
- .env の自動読み込みはプロジェクトルート検出に依存するため、パッケージ配布後にプロジェクト構成を変える場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動で環境をロードしてください。

Acknowledgements / Contributors
- 本リリースは設計ドキュメント（StrategyModel.md / DataPlatform.md 等）に準拠して実装されています。

If you want, I can:
- CHANGELOG に日付や出典（コミットハッシュ）を追加する、
- 既定の DuckDB スキーマ（CREATE TABLE 文）を草案として作成する、
- 未実装部分（execution / monitoring、エグジット条件など）の実装方針案を作る。