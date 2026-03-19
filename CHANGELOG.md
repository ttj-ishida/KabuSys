CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠しています。  
各リリースにはセマンティックバージョニング（MAJOR.MINOR.PATCH）を使用します。

[Unreleased]
-------------

（未リリースの変更はここに記載します）

[0.1.0] - 2026-03-19
-------------------

Added
- 初回公開リリース。
- パッケージ基本情報
  - パッケージ初期化（kabusys.__init__）にて __version__ = "0.1.0" として定義。
  - 公開 API として data, strategy, execution, monitoring をエクスポート。

- 設定 / 環境変数管理（kabusys.config）
  - プロジェクトルート検出機能を導入（.git または pyproject.toml を探索）。
  - .env / .env.local の自動読み込み（優先順位: OS 環境 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - .env の行パーサ実装（コメント・export 形式・クォート／エスケープ対応）。
  - 環境変数取得のラッパー Settings クラスを提供（J-Quants / kabuAPI / Slack / DB パス / 環境判定 / ログレベル検証等）。
  - 必須キー未設定時の明確な例外メッセージ提供。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（ページネーション対応）。
  - API レート制限制御（固定間隔スロットリング、120 req/min）。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）。
  - 401 受信時のトークン自動リフレッシュ（1 回まで）とモジュールレベルのトークンキャッシュ。
  - JSON デコードエラーの明示的なエラーメッセージ化。
  - DuckDB への冪等保存関数を提供:
    - save_daily_quotes -> raw_prices テーブルへ ON CONFLICT DO UPDATE
    - save_financial_statements -> raw_financials テーブルへ ON CONFLICT DO UPDATE
    - save_market_calendar -> market_calendar テーブルへ ON CONFLICT DO UPDATE
  - データ整形ユーティリティ (_to_float, _to_int) により不正値を安全に処理。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集の枠組みを実装（デフォルトに Yahoo Finance の RSS を設定）。
  - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント削除、スキーム/ホスト小文字化）。
  - セキュリティ対策: defusedxml を利用した XML パース、受信サイズ上限（10 MB）設定、SSRF を考慮した URL チェック。
  - 記事ID 生成方針（URL 正規化後のハッシュ）や DB への冪等保存戦略（ON CONFLICT / INSERT チャンク化）を設計に反映。

- リサーチ機能（kabusys.research）
  - factor_research: prices_daily / raw_financials を用いたファクター計算を実装。
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev 計算（200 日分のチェック含む）。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio 計算（true_range の NULL 伝播制御含む）。
    - calc_value: target_date 以前の最新財務データを用いて PER / ROE を計算。
  - feature_exploration:
    - calc_forward_returns: 指定 horizon に対する将来リターンを一括取得（LEAD を使用、スキャン範囲最適化）。
    - calc_ic: Spearman の ρ（ランク相関）計算実装（ties を平均ランクで扱う）。
    - factor_summary / rank: 基本統計量とランク付けユーティリティ。
  - いずれの関数も pandas 等に依存せず、DuckDB SQL と標準ライブラリで実装。

- 戦略レイヤー（kabusys.strategy）
  - feature_engineering.build_features:
    - research で計算した raw ファクターを取り込み、ユニバースフィルタ（最低株価・平均売買代金）適用。
    - Z スコア正規化（kabusys.data.stats の zscore_normalize を使用）および ±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE + バルク INSERT、トランザクションで原子性保証）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - final_score の重み付け（デフォルト重みを定義）と閾値による BUY シグナル生成。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合、一定以上のサンプル数で判定）により BUY を抑制。
    - 保有ポジションに対するエグジット判定（ストップロス、スコア低下）を実装。
    - signals テーブルへ日付単位で置換（トランザクションで原子性保証）。
    - 重み入力の検証と再スケーリング（不正値を警告してスキップ）。

Changed
- 初回リリースのため、過去バージョンからの変更点はなし。

Fixed
- 初回リリースのため、修正点はなし。

Security
- XML パースに defusedxml を利用して XML Bomb 等の攻撃を低減。
- ニュース収集で受信サイズ上限を設定（MAX_RESPONSE_BYTES = 10MB）し、メモリ DoS を軽減。
- ニュースの URL 正規化とトラッキングパラメータ除去により、ID の冗長化やトラッキング漏れを防止。
- J-Quants クライアントで Authorization ヘッダを適切に扱い、トークンの自動更新の際は無限リトライを回避。

Notes / Known limitations
- signal_generator の SELL 条件について、トレーリングストップや時間決済（保有60営業日超過）は未実装（positions テーブルに peak_price / entry_date が必要）。（StrategyModel.md に記載の仕様の一部は未対応）
- DuckDB のテーブル（prices_daily, raw_financials, features, ai_scores, positions, signals, raw_prices, market_calendar 等）が事前に定義されていることを前提とする。
- news_collector の実装はセキュリティを重視した設計を取っていますが、RSS フィードの取得部分でのネットワーク例外処理やテキスト抽出の細部は今後の拡張項目です。
- config の .env パーサは多くのケース（export 形式、クォート、エスケープ、インラインコメント）に対応していますが、特殊な .env フォーマットは追加テストが必要。

参考（主なファイル）
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/data/jquants_client.py
- src/kabusys/data/news_collector.py
- src/kabusys/research/factor_research.py
- src/kabusys/research/feature_exploration.py
- src/kabusys/strategy/feature_engineering.py
- src/kabusys/strategy/signal_generator.py

補足
- 各モジュールの詳細な設計方針・実装ノートはソースの docstring/comment に記載しています。今後のリリースではテストカバレッジ、エラーケースのログ整備、より細かなパラメータチューニングを予定しています。