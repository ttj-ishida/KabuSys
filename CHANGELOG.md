Keep a Changelog に準拠した CHANGELOG.md

すべての注目すべき変更を記録します。フォーマット: https://keepachangelog.com/ja/ を準拠しています。

# 変更履歴

すべての注目すべき変更を記録します。フォーマット: https://keepachangelog.com/ja/ を準拠しています。

## [0.1.0] - 2026-03-20
初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。以下の主要コンポーネントを提供します。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージの初期化（version = 0.1.0）。モジュール公開: data, strategy, execution, monitoring。

- 設定・環境変数管理 (`kabusys.config`)
  - .env 自動読み込み機能（プロジェクトルートの .git または pyproject.toml を探索）。
  - 読み込み優先順位: OS 環境 > .env > .env.local（.env.local は override=True）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 行パーサ: export 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理をサポート。
  - Settings クラス: J-Quants / kabu API / Slack / データベース / システム設定をプロパティとして提供。
  - 必須値のチェック（_require）と値検証（KABUSYS_ENV, LOG_LEVEL の有効値チェック）。
  - デフォルト値: KABUSYS_ENV=development、KABUSYS_API_BASE_URL、DB パス（duckdb/sqlite）等。

- データ取得・保存 (`kabusys.data.jquants_client`)
  - J-Quants API クライアント実装（認証、ページネーション対応）。
  - レート制限: 固定間隔スロットリングで 120 req/min（RateLimiter）。
  - リトライ: 指数バックオフ付き最大 3 回、408/429/5xx に対するリトライ処理。
  - 401 応答時のトークン自動リフレッシュ（1 回のみ）とキャッシュ化された ID トークン共有。
  - fetch_* 系 API: daily_quotes, financial_statements, market_calendar（ページネーション対応）。
  - DuckDB への保存関数 (save_daily_quotes, save_financial_statements, save_market_calendar) を実装。ON CONFLICT を用いた冪等保存。
  - 入力データの型変換ユーティリティ (_to_float, _to_int) を提供。

- ニュース収集 (`kabusys.data.news_collector`)
  - RSS フィードから記事収集し raw_news へ保存する基礎実装（デフォルトソースに Yahoo Finance）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化、フラグメント除去）。
  - セキュリティ対策: defusedxml による XML パース（XML Bomb 対策）、受信バイト数上限（MAX_RESPONSE_BYTES）、HTTP(S) スキームや SSRF を考慮した検証方針（注釈で明記）。
  - バルク INSERT チャンク処理、記事 ID は正規化 URL の SHA-256 の一部を利用して冪等性を確保。

- 研究（research）モジュール
  - ファクター計算 (`kabusys.research.factor_research`)
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA の利用とデータ不足時の None 処理）。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（true_range の NULL 伝播制御を含む）。
    - calc_value: per, roe（raw_financials の最新レコードを参照）。
  - 特徴量探索 (`kabusys.research.feature_exploration`)
    - calc_forward_returns: 指定ホライズンの将来リターン（デフォルト: 1,5,21 営業日）。
    - calc_ic: Spearman のランク相関（IC）計算（結合・有効サンプルチェック）。
    - factor_summary: 各ファクターの count/mean/std/min/max/median を算出。
    - rank: 同順位は平均ランクとするランク付け関数（round(...,12) による tie 対策）。
  - zscore_normalize を再公開（kabusys.research の __all__ に含める）。

- 戦略モジュール (`kabusys.strategy`)
  - 特徴量エンジニアリング (`feature_engineering.build_features`)
    - research の calc_momentum / calc_volatility / calc_value を組み合わせ、ユニバースフィルタ（最低株価・平均売買代金）を適用。
    - Z スコア正規化、±3 でクリップ、features テーブルへ日付単位で置換（トランザクションで原子性確保）。
    - ユニバース基準値: 最低株価 300 円、最低平均売買代金 5 億円。
  - シグナル生成 (`signal_generator.generate_signals`)
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - final_score を重み付き合算（デフォルト重みを実装）し閾値（デフォルト 0.60）で BUY シグナル生成。
    - Bear レジーム判定（AI の regime_score の平均が負かつサンプル数閾値を満たす場合は BUY を抑制）。
    - 保有ポジションに対するエグジット判定（ストップロス -8%／スコア低下）を実装し SELL シグナルを生成。
    - signals テーブルへ日付単位で置換（トランザクションで原子性確保）。
    - 重み指定時の入力バリデーション・リスケーリング実装（未知キー・負値・NaN/Inf を除外）。

- 一般的な品質・運用上の設計
  - DuckDB を中心に SQL と Python で計算・保存を行う設計（発注 API には依存しないレイヤ分離）。
  - 各保存処理・シグナル処理でトランザクション（BEGIN/COMMIT/ROLLBACK）を用いて原子性を確保。ROLLBACK 失敗時は警告ログを出力。
  - ロギング（logger）を各モジュールで利用。

### 変更 (Changed)
- 初版のため該当なし（新規実装）。

### 修正 (Fixed)
- 初版のため該当なし。

### 既知の制限・未実装 (Known issues / Unimplemented)
- signal_generator のエグジット条件でコメントにある「トレーリングストップ（peak_price 必要）」「時間決済（保有 60 営業日超過）」は未実装。positions テーブルの拡張が必要。
- news_collector の詳細な SSRF/ホスト検証ルールやネットワーク制約は設計で言及しているが、実運用での追加検証・サンドボックス化が望ましい。
- 一部の探索的・研究向け関数は research 環境向けに設計されており、本番発注パイプラインには直接結びつかない意図。

### セキュリティ (Security)
- XML パースに defusedxml を採用し XML Bomb 等の攻撃に対策。
- news_collector で受信サイズ上限、URL 正規化、トラッキングパラメータ除去などを導入。
- J-Quants クライアントで 401 リフレッシュを安全に行い、無限再帰を回避するため allow_refresh フラグで制御。

---

今後の予定（TODO / Roadmap）
- execution 層の実装（kabu ステーション API との注文・約定連携）。
- monitoring モジュールによる監視・アラート（Slack 通知等）。
- テスト整備（ユニットテスト・統合テスト）と CI パイプライン構築。
- news_collector のシンボル紐付け（news_symbols）と NLP/AI スコアリングの実装。
- strategy のパラメータチューニングとバックテストパイプラインの強化。

---

リリースノートに不明点や誤記がある場合は issue を作成してください。