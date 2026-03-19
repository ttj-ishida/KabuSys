CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは「Keep a Changelog」に準拠します。  
このリポジトリの初回リリースを記録しています。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-19
-------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - src/kabusys/__init__.py
    - パッケージメタ情報を追加。公開 API（data, strategy, execution, monitoring）を __all__ で定義。

- 環境変数 / 設定管理
  - src/kabusys/config.py
    - .env/.env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env パーサー実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応、インラインコメント処理等）。
    - .env の読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - OS 環境変数を保護する protected オプションを導入。
    - Settings クラスを実装（必須変数チェック、既定値、検証ロジック）。
      - J-Quants リフレッシュトークン、Kabu API パスワード、Slack トークン/チャンネル、DB パス等の設定取得。
      - KABUSYS_ENV, LOG_LEVEL の検証（許容値チェック）とユーティリティプロパティ（is_live/is_paper/is_dev）。

- Data 層: J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - J-Quants API との通信クライアントを実装。
    - 固定間隔レートリミッタ (_RateLimiter) 実装（120 req/min 想定）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）。
    - 401 受信時はトークン自動リフレッシュを 1 回行い再試行（無限再帰を回避）。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - DuckDB への保存ユーティリティ（冪等）
      - save_daily_quotes, save_financial_statements, save_market_calendar
    - データ型変換ユーティリティ _to_float / _to_int、fetch 時刻を UTC で記録（fetched_at）。
    - 設計上の注意: Look-ahead バイアス防止のため取得時刻を記録、ON CONFLICT を使った冪等性。

- Data 層: ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィードから記事を収集する骨格を実装。
    - URL 正規化（トラッキングパラメータ削除、クエリソート、小文字正規化、フラグメント除去等）。
    - セキュリティ対策:
      - defusedxml を利用して XML 攻撃を軽減。
      - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止。
      - トラッキングパラメータの除去や HTTP(S) スキームの検査（SSRF 対策の方針記載）。
    - 記事 ID は正規化後 URL の SHA-256 ハッシュ（一意化／冪等化の方針）。
    - raw_news テーブルへの冪等保存（ON CONFLICT DO NOTHING を予定）、news_symbols での銘柄紐付け設計。

- Research 層
  - src/kabusys/research/factor_research.py
    - ファクター計算モジュールを実装:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA の条件付き計算等）
      - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（true_range の NULL 伝播制御）
      - calc_value: per / roe（raw_financials の最新レコード参照）
    - DuckDB を用いた SQL ベース実装。prices_daily / raw_financials のみ参照。

  - src/kabusys/research/feature_exploration.py
    - 研究用ユーティリティを実装:
      - calc_forward_returns: 複数ホライズンの将来リターンを一括取得（LEAD を利用、ホライズン検証）
      - calc_ic: Spearman の ρ（ランク相関）を計算（同順位は平均ランク）
      - factor_summary: count/mean/std/min/max/median の基本統計
      - rank: 平均ランク方式によるランク付け（丸めによる ties 対応）
    - 標準ライブラリのみを用いる方針を記載。

  - src/kabusys/research/__init__.py
    - 公開 API をエクスポート（calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize）。

- Strategy 層
  - src/kabusys/strategy/feature_engineering.py
    - 研究で算出した raw ファクターの正規化・合成処理を実装:
      - calc_momentum / calc_volatility / calc_value を呼び出してマージ
      - ユニバースフィルタ（最低株価 _MIN_PRICE=300, 平均売買代金 _MIN_TURNOVER=5e8）適用
      - 指定カラムの Z スコア正規化（zscore_normalize を使用）、±3 でクリップ
      - features テーブルへ日付単位で置換（トランザクション＋バルク挿入で原子性確保）
    - ルックアヘッドバイアス回避（target_date 時点のみのデータ利用）を明示。

  - src/kabusys/strategy/signal_generator.py
    - 正規化済み features と ai_scores を統合して最終スコアを計算しシグナルを生成:
      - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）
      - スコア変換ヘルパ: _sigmoid, _avg_scores 等
      - final_score は重み付き合算（デフォルト weights を実装、与えられた weights のバリデーションと正規化を実施）
      - Bear レジーム判定（ai_scores の regime_score 平均が負の場合。ただしサンプル数閾値あり）
      - BUY: threshold（デフォルト 0.60）超過で生成（Bear レジームでは BUY を抑制）
      - SELL: エグジット条件（ストップロス -8% 優先、score_drop）を実装
      - positions / prices_daily を参照してエグジット判定、signals テーブルへ日付単位で置換（トランザクション）
      - SELL 優先ポリシー（SELL 対象は BUY から除外してランク再付与）
    - 未実装機能を明記（トレーリングストップ、時間決済は positions に peak_price / entry_date が必要）。

- strategy パッケージエクスポート
  - src/kabusys/strategy/__init__.py
    - build_features, generate_signals を公開 API としてエクスポート。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- News collector で defusedxml を利用、受信サイズ制限、URL 正規化等の対策を導入。
- J-Quants クライアントでトークン取り扱いと自動リフレッシュ時の無限再帰回避を実装。

Notes / 設計上の重要点
- 冪等性
  - DB への保存処理は原則冪等（ON CONFLICT / 日付単位の DELETE→INSERT トランザクション）としているため、再実行に耐える設計。  
- Look-ahead バイアス対策
  - 研究/戦略/データ取得の各層で「target_date 時点で利用可能なデータのみ」を使う方針を明示。J-Quants の fetched_at を UTC で記録。
- 環境変数の自動読み込み
  - デフォルトでプロジェクトルートの .env を自動で読み込む実装。CI/テスト等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定。
- 設定の検証
  - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL を Settings にて検証し、不正値は例外を投げる。
- 制限事項 / 未実装事項
  - signal_generator 内の一部エグジット条件（トレーリングストップ、時間決済）は未実装。positions テーブルの拡張が必要。
  - news_collector の銘柄紐付け（news_symbols）の具体ロジックや RSS パースの例外ハンドリングの詳細は今後拡張予定。

Acknowledgements / References
- 各モジュールには内部設計方針（StrategyModel.md, DataPlatform.md 等）への言及があり、実装はそれらに沿っている旨をコメントで記載。

ライセンスや公開方法、マイグレーション手順等は別途ドキュメント化を予定しています。