# CHANGELOG

すべての重要な変更点を記録します。このプロジェクトは Keep a Changelog の形式に準拠します。  
リリースはセマンティックバージョニングを使用します。

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-03-21
初回公開リリース。

### 追加
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージの公開 API に data, strategy, execution, monitoring を定義。

- 環境設定 / 設定管理 (kabusys.config)
  - .env / .env.local ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に __file__ から探索（CWD 非依存）。
  - .env パーサを実装（コメント、export プレフィックス、クォート文字列、エスケープ対応、インラインコメント処理など）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - OS 環境変数を保護するための protected キー概念による .env.local の上書き制御。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルなどをプロパティ経由で取得。
  - 不正値や未設定時は明確な ValueError を発生させるバリデーションを実装。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制限対応（固定間隔スロットリングで 120 req/min を遵守）。
  - 再試行（指数バックオフ、最大 3 回）と HTTP ステータスに基づくリトライロジック（408/429/5xx を対象）。
  - 401 受信時はリフレッシュ用エンドポイントを叩いてトークンを自動更新し 1 回だけ再試行する処理を実装。
  - ページネーション対応（pagination_key の扱い）。
  - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を提供。
  - DuckDB への保存関数: save_daily_quotes, save_financial_statements, save_market_calendar を提供。いずれも冪等（ON CONFLICT DO UPDATE / DO NOTHING）で挿入・更新を行う。
  - 取得時刻は UTC で fetched_at を記録（Look-ahead バイアスのトレース可能性確保）。
  - 型変換ユーティリティ _to_float / _to_int を実装（空値・不正値を安全に None として扱う）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を取得して raw_news に保存する処理を実装。
  - デフォルト RSS ソース（例: Yahoo Finance）を定義。
  - セキュリティ対策: defusedxml による XML パース、受信サイズ上限（MAX_RESPONSE_BYTES）、HTTP スキーム検証など。
  - 記事 ID は URL 正規化後の SHA-256（先頭 32 文字）で生成して冪等性を確保。クエリのトラッキングパラメータ（utm_* 等）を除去して正規化。
  - URL 正規化、本文正規化（URL 除去・空白正規化）、バルク INSERT のチャンク化などを実装。

- 研究用モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）、Value（PER, ROE）を DuckDB の prices_daily / raw_financials を参照して計算する関数を実装: calc_momentum, calc_volatility, calc_value。
    - 欠測条件やウィンドウ不足時の None ハンドリングを明確に実装。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算: calc_forward_returns（複数ホライズン対応、horizons の検証）。
    - IC（Information Coefficient）計算: calc_ic（スピアマンのρ、同順位の平均ランク処理を含む）。
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）とランク変換 util rank を実装。
  - research パッケージの公開 API に主要関数を追加。

- 戦略・特徴量パイプライン (kabusys.strategy)
  - 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
    - 研究で算出した生ファクターをマージ、ユニバースフィルタ（最低株価: 300 円、20 日平均売買代金: 5 億円）を適用。
    - 数値ファクターを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位での置換（DELETE + バルク INSERT）をトランザクションで行い原子性を保証。
    - build_features(conn, target_date) を実装。
  - シグナル生成 (kabusys.strategy.signal_generator)
    - features と ai_scores を統合し、各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントを重み付けして final_score を算出（デフォルト重みを定義、外部から重みを渡せるがバリデーション・再スケーリングを実施）。
    - Bear レジーム検知（ai_scores の regime_score 平均が負の場合、サンプル数閾値あり）で BUY シグナルを抑制。
    - BUY 生成閾値デフォルト 0.60、SELL 条件にストップロス（-8%）およびスコア低下を実装。エグジット判定は保有ポジションを参照。
    - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入）を行い冪等性を確保。
    - generate_signals(conn, target_date, threshold, weights) を実装。

### 変更
- （初回リリースのため過去バージョンからの変更はなし）

### 修正
- （初回リリースのため過去バージョンからの修正はなし）

### セキュリティ
- news_collector で defusedxml を使用し XML-based 攻撃を緩和。
- ニュース取得時の受信サイズ制限によりメモリ DoS を軽減。
- jquants_client は外部呼び出し時の例外ハンドリングとリトライを実装し、致命的失敗の影響を低減。

### 既知の制限 / TODO
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装（positions に peak_price / entry_date が必要）。
- news_collector の外部 HTTP セキュリティ（プロキシ/SSRF の更なる強化）や RSS ソースの追加は今後の課題。
- execution / monitoring パッケージは存在するが本コードベースでは実装が薄く、発注ロジックや運用監視との統合は今後実装予定。

### 互換性の破壊（Breaking Changes）
- なし（初回リリース）

---

注: 実装の細部（関数名、パラメータ、デフォルト値、閾値等）はコードベースから推測して記載しています。運用やテスト環境で利用する前に、各設定（環境変数、DB スキーマ、Slack 設定など）を確認してください。