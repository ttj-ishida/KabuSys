# CHANGELOG

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

なお、記載内容はコードベースから推測して記載しています（ドキュメント文字列・実装から機能/設計意図を要約）。

## [Unreleased]

（未リリースの変更はここに記載）

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システム「KabuSys」の基本機能群を収録しています。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージを追加。バージョンは 0.1.0。公開 API として data, strategy, execution, monitoring をエクスポート。

- 環境設定 / 自動 .env ロード
  - kabusys.config: 環境変数管理クラス Settings を追加。
  - プロジェクトルートの自動検出（.git または pyproject.toml を基準）による .env/.env.local の自動ロード機能を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - .env パーサーを実装。export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理などの堅牢な解析を実装。
  - 必須環境変数取得時に未設定で ValueError を投げる _require を提供。
  - Settings に J-Quants / kabuステーション / Slack / DB パス /環境・ログレベル検証プロパティを追加（値検証・デフォルト値含む）。

- データ取得クライアント（J-Quants）
  - kabusys.data.jquants_client を追加。
  - レート制限（120 req/min）の固定間隔スロットリング実装（内部 RateLimiter）。
  - HTTP リクエストの共通処理 _request を実装。指数バックオフを用いたリトライ（最大 3 回）、429 の Retry-After 尊重、408/429/5xx 切り分け、401 発生時のトークン自動リフレッシュ（1回のみ）をサポート。
  - トークン取得 get_id_token（リフレッシュトークン経由）を実装。
  - ページネーション対応のデータ取得: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
  - DuckDB への冪等保存ユーティリティ: save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT DO UPDATE を利用）。フェッチ時刻（fetched_at）を UTC で記録。
  - 型変換ユーティリティ _to_float / _to_int を実装（堅牢な欠損・不正値処理）。

- ニュース収集
  - kabusys.data.news_collector を追加。
  - RSS フィード収集のワークフローを実装（ソース一覧・最大受信バイト制限・XML 防御・URL 正規化等）。
  - 記事ID を URL 正規化後の SHA-256 ハッシュで生成し冪等性を確保。トラッキングパラメータ排除やスキーム/ホスト小文字化などの正規化処理を実装。
  - defusedxml を用いた XML 攻撃防御、受信サイズ制限によるメモリ DoS 対策、SSRF 対策に配慮した実装方針を採用。
  - バルク INSERT のチャンク化・トランザクション最適化を想定（INSERT チャンクサイズ定義）。

- 研究用ファクター計算 / 探索
  - kabusys.research.factor_research を追加。prices_daily / raw_financials を参照して以下を算出:
    - モメンタム（mom_1m / mom_3m / mom_6m、ma200_dev）
    - ボラティリティ / 流動性（atr_20, atr_pct, avg_turnover, volume_ratio）
    - バリュー（per, roe）
  - kabusys.research.feature_exploration を追加:
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、1/5/21 営業日をデフォルト）
    - IC（Spearman）を計算する calc_ic（ランク付け実装、最小サンプル制約）
    - factor_summary（count/mean/std/min/max/median）および rank ユーティリティを実装。
  - research パッケージのエクスポートを整備（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- 特徴量生成（Feature Engineering）
  - kabusys.strategy.feature_engineering を追加。
  - 研究環境で算出した生ファクターを統合・正規化して features テーブルへ UPSERT する build_features を実装。
  - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を実装。
  - Z スコア正規化（zscore_normalize の利用）、±3 でのクリップ、日付単位の置換（トランザクション＋バルク挿入）で冪等性を保証。

- シグナル生成（Signal Generation）
  - kabusys.strategy.signal_generator を追加。
  - features と ai_scores を統合して最終スコア final_score を算出し、BUY/SELL シグナルを生成する generate_signals を実装。
  - コンポーネントスコアの計算（momentum/value/volatility/liquidity/news）、シグモイド変換、欠損値の中立補完（0.5）、重みの検証・再スケーリング機能を実装。
  - Bear レジーム判定（ai_scores の regime_score 平均が負でかつサンプル数閾値以上）による BUY 抑制を実装。
  - エグジット判定の実装（停止損失 -8%、final_score が閾値未満など）。保有ポジションの価格欠損時は SELL 判定をスキップする安全策あり。
  - signals テーブルへの日付単位置換で冪等性を保証。

- 公開 API の統合
  - kabusys.strategy.__init__ で build_features / generate_signals をエクスポート。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- XML パースに defusedxml を利用（news_collector）。  
- ニュース収集で受信サイズ上限を設定しメモリ DoS を緩和。  
- RSS URL 正規化・トラッキング削除、SSRF を意識した入力検証の方針を導入。  
- J-Quants クライアントで 401 発生時に安全にトークンリフレッシュし、無限再帰を防止（allow_refresh フラグ）。

### Notes / Implementation details
- 多くのデータ保存処理は DuckDB を前提とし、トランザクション + バルク挿入 / ON CONFLICT を用いて冪等性と原子性を確保しています。
- research モジュールは標準ライブラリのみで実装する設計（pandas 等に依存しない）。
- 一部の機能（strategy のトレーリングストップや時間決済など）はコード内コメントで未実装として注記されています。
- ロギングが各モジュールに導入されており、警告・情報出力により運用時の可観測性を考慮しています。

（今後のリリース候補）
- execution / monitoring モジュールの具体実装（発注 API 統合、監視 / アラート処理）
- テスト・CI 用のモック/依存分離
- ドキュメント（使用例、DB スキーマ定義、StrategyModel.md 等の外部参照ファイルの整備）

------------------------------
履歴は可能な限り実装から推測して作成しています。詳細な変更履歴や日付・担当者等は実際のコミット履歴に基づき補完してください。