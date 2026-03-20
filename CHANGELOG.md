KEEP A CHANGELOG に準拠した形式で、コードベースから推測して作成した CHANGELOG.md（日本語）を以下に示します。

CHANGELOG.md

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project adheres to Semantic Versioning.

Unreleased
---------

（現在差分なし）

0.1.0 - 2026-03-20
-----------------

Added
- 初回リリース。以下の主要機能を実装。
  - パッケージ基盤
    - パッケージ初期化情報（kabusys.__version__ = "0.1.0"）。
    - public API を定義（strategy.build_features, strategy.generate_signals 等を __all__ に登録）。
  - 設定/環境変数管理（kabusys.config）
    - .env / .env.local 自動読み込み機構を実装（プロジェクトルートは .git または pyproject.toml を探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理、インラインコメント処理などに対応）。
    - 環境変数の必須チェックと型/値検証を実装（KABUSYS_ENV, LOG_LEVEL の許容値チェック等）。
    - 設定アクセス用の Settings クラスを提供（J-Quants / kabu / Slack / DB パス等をプロパティで取得）。
  - データ取得・保存（kabusys.data.jquants_client）
    - J-Quants API クライアントを実装。
      - 固定間隔のレートリミッタ（120 req/min）を実装。
      - リトライロジック（指数バックオフ、最大3回、408/429/5xx 対象）を備える。
      - 401 エラー時はトークンを自動リフレッシュして1回リトライする仕組みを実装（id_token キャッシュ）。
      - ページネーション対応の fetch_* API（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
      - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装（ON CONFLICT / DO UPDATE を使用）。
      - 型変換ユーティリティ（_to_float, _to_int）を実装して不正入力を安全に扱う。
  - ニュース収集（kabusys.data.news_collector）
    - RSS フィード取得・正規化処理を実装（デフォルトに Yahoo Finance ビジネス RSS を設定）。
    - URL 正規化（トラッキングパラメータ除去、フラグメント削除、クエリソート）を実装。
    - XML パースに defusedxml を使用して XML Bomb などへの対策を実施。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES）や受信スキーム制限などで DoS / SSRF 対策を考慮。
    - バルク挿入のチャンク処理で DB オーバーヘッドを低減。
    - 記事 ID 生成（URL 正規化後の SHA-256 ハッシュ先頭）による冪等性を設計に反映。
  - リサーチ（kabusys.research）
    - ファクター計算（kabusys.research.factor_research）
      - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）計算。
      - Volatility / Liquidity（atr_20, atr_pct, avg_turnover, volume_ratio）計算。
      - Value（per, roe）計算（raw_financials から最新の財務データを取得して prices_daily と結合）。
      - 各関数は DuckDB の prices_daily / raw_financials テーブルのみを参照する設計。
    - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
      - 将来リターン計算（calc_forward_returns、horizons の検証と一括取得クエリ）。
      - IC（Information Coefficient）計算（Spearman の ρ 相当、rank 関数を含む）。
      - ファクター統計要約（factor_summary）。
    - zscore 正規化ユーティリティを公開（kabusys.research を通じて data.stats の zscore_normalize を再エクスポート）。
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - research モジュールが出力する生ファクターをマージしてユニバースフィルタを適用。
    - ユニバース条件：最低株価 300 円、20 日平均売買代金 5 億円。
    - 指定カラムを Z スコア正規化・±3 でクリップし features テーブルへ日付単位で置換（トランザクションで原子性を担保）。
    - 欠損や非有限値の扱いを明示。
  - シグナル生成（kabusys.strategy.signal_generator）
    - features と ai_scores を組み合わせて各銘柄のコンポーネントスコア（momentum, value, volatility, liquidity, news）を計算。
    - コンポーネントの合成は重み付け（デフォルト重みを実装）とスケーリングを行い final_score を生成。
    - Sigmoid 変換・欠損補完（中立値 0.5）により欠損耐性を確保。
    - Bear レジーム判定（ai_scores の regime_score 平均が負でサンプル数閾値以上の場合）により BUY を抑制。
    - BUY/SELL ルールを実装：
      - BUY: final_score >= デフォルト閾値 0.60（Bear 時は抑制）。
      - SELL: ストップロス（終値/avg_price - 1 < -8%）およびスコア低下（final_score < threshold）。SELL は BUY より優先。
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入で原子性）。
  - トランザクション性・冪等性
    - DuckDB への更新は基本的にトランザクション + bulk insert / ON CONFLICT を用いて冪等性・原子性を担保。

Security
- ニュース XML パースで defusedxml を採用、RSS パース時の脆弱性緩和を実施。
- ニュースの URL 正規化・スキーム検証・受信サイズ制限などで SSRF / DoS を配慮。
- J-Quants クライアントは 401 時に自動トークン更新を行うものの、allow_refresh フラグで無限再帰を防止。

Known limitations / Notes
- 戦略の一部ルールは未実装（TODO として明示）。
  - トレーリングストップ（直近最高値からの −10%）は未実装（positions テーブルに peak_price / entry_date が必要）。
  - 時間決済（保有 60 営業日超過）も未実装。
- news_collector の実装は記事の抽出 / マッピング（news_symbols 等）を前提としているが、外部的な紐付け処理の詳細は別途必要。
- calc_forward_returns は最大ホライズンに対してカレンダーバッファを用いるが、極端に不足したデータに対する挙動は利用環境に依存。
- settings.env の許容値は "development", "paper_trading", "live" のみ。LOG_LEVEL も限定値のみ許容。
- .env パーサは多くのケースに対応しているが、極端な複雑ケース（複数行にまたがるクォート等）は想定外。

Breaking Changes
- 初回リリースのため既存バージョンとの互換性問題はなし。

その他
- 外部依存は最小限（duckdb, defusedxml）に留める設計。
- ドメイン知識（StrategyModel.md, DataPlatform.md 等）に基づく実装注記を多数含む（内部ドキュメント参照推奨）。

もし、より詳細な項目（例えばモジュール別の変更ログや設計上の判断理由、将来の TODO リスト）を含めたい場合は指示してください。