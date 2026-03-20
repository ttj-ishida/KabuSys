# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
このプロジェクトの初期リリースを記録しています。

## [Unreleased]
- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-20
初回リリース

### 追加
- パッケージ基盤
  - kabusys パッケージを導入。公開 API として data / strategy / execution / monitoring を __all__ に登録（execution は空のパッケージとしてプレースホルダを用意）。
  - バージョン情報: 0.1.0

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートの探索は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き許可）。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス等の設定取得とバリデーションを実装（未設定時は例外を送出）。
  - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG/INFO/...）の検証ロジックを追加。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装:
    - レート制限 (120 req/min) を固定間隔スロットリングで制御する RateLimiter を実装。
    - 指数バックオフを用いたリトライ処理（最大 3 回、408/429/5xx を再試行）。
    - 401 はトークン自動リフレッシュを行い 1 回リトライ（トークン取得ロジックを組み込み）。
    - ページネーションに対応した fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB への永続化関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装し、ON CONFLICT DO UPDATE で冪等性を確保。
    - データ変換ユーティリティ (_to_float/_to_int) を実装し、安全に数値変換を行う。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集し raw_news に保存するロジックを実装。
  - 記事 ID は正規化された URL の SHA-256（先頭 32 文字）を利用して冪等性を確保。
  - URL 正規化機能を実装（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
  - defusedxml を用いた XML の安全パースや、受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）等、セキュリティ上の配慮を導入。
  - バルク挿入のチャンク化による DB 負荷低減。

- リサーチ / ファクター計算 (kabusys.research)
  - ファクター計算モジュールを実装（prices_daily / raw_financials を参照）:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算。
    - calc_value: per, roe を計算（target_date 以前の最新財務データを参照）。
  - feature_exploration: 将来リターン計算 (calc_forward_returns)、IC（Spearman ρ）計算 (calc_ic)、統計サマリー (factor_summary)、ランク化ユーティリティ (rank) を提供。
  - 外部依存を避け、DuckDB と標準ライブラリのみで完結する設計。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - 研究環境で算出した生ファクターを正規化・合成し、features テーブルへ日付単位の置換（冪等）で保存する build_features を実装。
  - 主な処理:
    - calc_momentum / calc_volatility / calc_value の結果統合
    - ユニバースフィルタ（最小株価 300 円、20 日平均売買代金 5 億円）
    - 指定列の Z スコア正規化と ±3 のクリップ
    - DuckDB トランザクションを使った日付単位置換（DELETE→INSERT、COMMIT/ROLLBACK 処理）
  - Z スコア正規化ユーティリティは kabusys.data.stats の zscore_normalize を利用。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合し final_score を算出、BUY / SELL シグナルを生成して signals テーブルへ日付単位置換で保存する generate_signals を実装。
  - 実装のポイント:
    - コンポーネントスコア: momentum / value / volatility / liquidity / news の算出ロジック
    - デフォルト重みと閾値（weights、threshold）を定義し、ユーザ指定は検証・正規化して適用
    - AI レジームスコアに基づく Bear 判定（サンプル閾値あり）で BUY を抑制
    - エグジット判定（ストップロス -8% / スコア低下）に基づく SELL 生成
    - SELL 優先ポリシー（SELL 対象を BUY から除外）
    - DuckDB トランザクションによる原子性確保とロールバックハンドリング
  - デフォルトの運用パラメータ（例: BUY 閾値 0.60、ストップロス -8%、Z スコアクリップ ±3）を設定。

- パブリックエクスポート
  - strategy パッケージは build_features / generate_signals をトップレベルで公開。
  - research パッケージは calc_momentum / calc_volatility / calc_value / zscore_normalize / calc_forward_returns / calc_ic / factor_summary / rank を公開。

### セキュリティ・信頼性に関する配慮
- J-Quants クライアント:
  - API レート制限遵守、リトライ、トークン自動更新を実装し、ネットワーク障害や一時的なエラーに耐性を持たせる設計。
  - JSON デコードエラーや HTTP エラーの適切なログと例外報告を実装。
- ニュース収集:
  - defusedxml を利用して XML パース関連の攻撃を防止。
  - 受信サイズ制限や URL 正規化（トラッキングパラメータ削除）で DoS/トラッキング対策を実施。
- DB 操作:
  - INSERT の冪等化（ON CONFLICT DO UPDATE / DO NOTHING）とトランザクション（BEGIN/COMMIT/ROLLBACK）で整合性を確保。
  - PK 欠損データはスキップし、スキップ件数をログに出力。

### ドキュメンテーション・ログ
- 各モジュールに詳細な docstring を導入。設計方針、処理フロー、想定テーブル（例: prices_daily, raw_financials, features, ai_scores, positions）や制約条件が記載されているため、実装の意図や使い方が分かりやすい構成。

### 既知の未実装 / 今後の予定（実装ノート）
- signal_generator のエグジット条件の一部（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等の追加情報が必要であり未実装。
- news_collector の SSRF / IP 検査などの追加検証は設計書に言及があるが、現状のコードには一部ユーティリティしか含まれていない箇所がある（今後強化予定）。

---

注: 本 CHANGELOG はソースコードからの推測に基づいて作成しています。実際のリリースノートに含めるべき詳細（ユーザー向けの導入手順、互換性注意点、マイグレーション手順など）はプロジェクト方針に応じて追加してください。