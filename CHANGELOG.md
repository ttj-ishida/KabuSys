# CHANGELOG

すべての重要な変更をここに記録します。  
このファイルは「Keep a Changelog」の形式に準拠しています。  

なお、本 CHANGELOG はリポジトリ内のソースコードから機能・設計意図を推測して作成しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-20
初回リリース。日本株自動売買システムのコアライブラリを提供します。主な追加点は以下のとおりです。

### 追加 (Added)
- 全体
  - パッケージ初期化 (kabusys.__init__) とバージョン定義を追加（version = 0.1.0）。
  - モジュール構成: data, strategy, execution, monitoring を公開（execution は現時点で空のパッケージとして存在）。

- 設定 / 環境管理 (kabusys.config)
  - .env ファイルおよび環境変数を読み込む自動ロード機能を実装。優先順位は OS 環境変数 > .env.local > .env。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準）。パッケージ配布後でも動作するよう設計。
  - .env パーサ実装（export 形式、クォート処理、インラインコメント対応、無効行スキップ）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑止機能。
  - Settings クラスを追加し、J-Quants / kabuステーション / Slack / DB パス / 環境種別・ログレベルなどをプロパティ経由で取得。KABUSYS_ENV と LOG_LEVEL の値検証を実装。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - 固定間隔のレートリミッタ (120 req/min) を実装。
    - リトライ（指数バックオフ、最大 3 回）と HTTP ステータスに基づく再試行ポリシーを実装（408, 429, 5xx 等を対象）。
    - 401 受信時にリフレッシュトークンから ID トークンを再取得して 1 回リトライするトークン自動再取得ロジックを実装。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を実装。
    - データ保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装し、DuckDB への保存は冪等性のため ON CONFLICT ... DO UPDATE を使用。
    - データ型変換ユーティリティ (_to_float, _to_int) を提供。
    - 取得時刻を UTC で記録（fetched_at）し、look-ahead バイアスのトレースを可能に。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからのニュース収集モジュールを実装（デフォルトソースに Yahoo Finance を設定）。
  - XML パースに defusedxml を使用して XML Bomb 等を防御。
  - 受信サイズ制限（MAX_RESPONSE_BYTES）や URL 正規化（トラッキングパラメータ除去、スキーム/ホストの小文字化、フラグメント削除、クエリソート）を実装。
  - 記事の前処理（URL 除去・空白正規化）や冪等保存（ON CONFLICT / DO NOTHING 想定）・バルク挿入チャンク化を考慮。
  - SSRF やメモリ DoS を考慮した設計コメントを含む。

- 研究用ファクター計算 (kabusys.research.factor_research)
  - Momentum / Volatility / Value に関するファクター計算関数を実装:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日ウィンドウのチェック含む）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（true_range の NULL 伝播制御を含む）
    - calc_value: per, roe（raw_financials の最新レコード取得ロジックを実装）
  - DuckDB を用いた SQL＋Python のハイブリッド実装で、prices_daily / raw_financials テーブルのみを参照する設計。

- 研究用分析ツール (kabusys.research.feature_exploration)
  - 将来リターン計算: calc_forward_returns（複数ホライズンを一括取得、日付範囲緩衝）。
  - IC 計算: calc_ic（Spearman の ρ、同順位は平均ランクで処理）。
  - 統計サマリー: factor_summary（count/mean/std/min/max/median）。
  - ランク付けユーティリティ: rank（同順位は平均ランク、丸めによる ties 対策あり）。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features を実装。research モジュールから raw ファクターを取得し、
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用、
    - 指定列を Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、
    - ±3 でクリップ、
    - features テーブルへ日付単位の置換（DELETE + INSERT をトランザクションで実行）して冪等性を確保。
  - ルックアヘッドバイアスを避ける設計（target_date 時点のデータのみ参照）。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals を実装。features と ai_scores を統合し最終スコア final_score を算出。
    - モメンタム/バリュー/ボラティリティ/流動性/ニュース（AI）をコンポーネントスコアとして計算。
    - コンポーネントスコアの欠損は中立値 0.5 で補完。
    - 重み（デフォルト値を持ち、ユーザ指定は正当性チェック・再スケーリング）による重み付け合算で final_score を算出。
    - Bear レジーム判定（ai_scores の regime_score 平均が負であれば Bear。ただしサンプル数閾値あり）により BUY シグナルを抑制。
    - BUY（閾値 default=0.60）と SELL（エグジット）を生成。SELL 判定条件にストップロス（-8%）とスコア低下を実装。
    - 保有ポジションの価格欠損時には SELL 判定をスキップし警告を出力。
    - signals テーブルへ日付単位の置換で書き込み（トランザクション + バルク挿入）。

### セキュリティ関連 (Security)
- news_collector で defusedxml を利用し XML ベースの攻撃を防止。
- news_collector にて受信サイズ制限や URL 正規化により SSRF・メモリ DoS を低減する設計を採用。
- J-Quants クライアントはトークンの自動リフレッシュを実装し、認証エラー時の安全な再試行を行う。

### 既知の制限 / 未実装 (Known issues / Notes)
- strategy.signal_generator のエグジット条件について、トレーリングストップや時間決済（保有 60 営業日超過）は未実装（positions テーブルに peak_price / entry_date が必要とのコメントあり）。
- execution パッケージは空で、発注 API との接続層は実装されていない（戦略層は発注層に依存しない設計）。
- news_collector の記事 ID 生成や DB 保存の詳細（ON CONFLICT の正確な実装など）はドキュメントで言及されているが、ソースの一部は抜粋のため実装の全体像が見えない場合がある。
- 外部依存を抑えた実装を目指しているが、実稼働前には DuckDB スキーマ整備・実データでの検証が必要。

### 変更 (Changed)
- 該当なし（初回リリース）。

### 修正 (Fixed)
- 該当なし（初回リリース）。

### 削除 (Removed)
- 該当なし（初回リリース）。

もし詳細（各関数のシグネチャ、期待スキーマ、テーブル定義、またはリリース日変更など）を反映させたい場合は、追加情報を提供してください。