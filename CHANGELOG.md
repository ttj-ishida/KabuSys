# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-03-21
初回リリース。日本株自動売買システム「KabuSys」のコア機能群を追加しました。以下はコードベースから推測できる主要な追加点・設計方針・堅牢化対応の一覧です。

### 追加
- コアパッケージ構成
  - パッケージエントリポイント: `kabusys.__init__`（バージョン 0.1.0 / __all__ に data, strategy, execution, monitoring を公開）。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルまたは OS 環境変数から設定値を自動読込（プロジェクトルートを .git または pyproject.toml から探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パーサ実装（コメント、export 形式、クォート／エスケープ処理に対応）。
  - 環境変数保護：既存 OS 環境変数は `.env` による上書きを抑止。`.env.local` は上書き可能だが保護集合を尊重。
  - Settings クラスを提供（必須変数チェック、Path 型でのデフォルト、env/log_level 値検証、is_live/is_paper/is_dev ユーティリティ）。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（株価日足、財務データ、マーケットカレンダーの取得）。
  - レート制限: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter 実装。
  - 再試行・指数バックオフ: 最大試行回数 3、ネットワーク／一部 HTTP ステータス（408/429/5xx）に対するリトライ処理。429 の場合は Retry-After を優先。
  - 401 発生時の自動トークンリフレッシュ（1 回のみリトライ）とモジュールレベルのトークンキャッシュ共有。
  - ページネーション対応の fetch_* 系関数と DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）。
  - DuckDB 保存時に fetched_at を UTC ISO8601 で記録。INSERT は ON CONFLICT DO UPDATE（冪等性）を採用。

- ニュース収集（kabusys.data.news_collector）
  - RSS から記事収集し raw_news に保存する処理の骨格。デフォルト RSS ソースを定義（例: Yahoo Finance）。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
  - 記事 ID は正規化 URL の SHA-256 を利用（先頭 32 文字）で冪等性確保方針を記載。
  - XML パースに defusedxml を利用して XML Bomb 等の脆弱性低減。
  - 受信サイズの上限（MAX_RESPONSE_BYTES = 10MB）や SSRF・非 HTTP スキーム排除などセキュリティ配慮。
  - バルク INSERT のチャンク処理、ON CONFLICT DO NOTHING による冪等保存。

- リサーチユーティリティ（kabusys.research）
  - ファクター計算モジュール（factor_research）:
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）、Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）、Value（per, roe）を DuckDB の prices_daily / raw_financials を用いて計算。
    - 営業日ベースのラグ・移動平均計算（200日MA 等）や欠損時の None 扱いを明確化。
  - 特徴量探索（feature_exploration）:
    - 将来リターン（calc_forward_returns: デフォルト horizons = [1,5,21]）の計算、IC（スピアマンランク相関: calc_ic）、ランク変換ユーティリティ、factor_summary による基本統計量算出。
    - 計算精度対策（浮動小数丸め、同順位の平均ランク処理など）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research モジュールから得た生ファクターを結合し、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）適用。
  - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 クリップで外れ値抑制。
  - features テーブルへの日付単位置換（DELETE + INSERT をトランザクションで実施し冪等性・原子性を保障）。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合し、複数コンポーネント（momentum/value/volatility/liquidity/news）から final_score を計算。
  - デフォルト重みは momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10。合計が 1.0 でない場合は再スケール。
  - スコア変換: Z スコアをシグモイドで [0,1] に変換、欠損コンポーネントは中立 0.5 で補完。
  - Bear レジーム判定（ai_scores の regime_score 平均が負の場合。ただしサンプル数閾値を導入）。
  - BUY シグナル閾値デフォルト 0.60。SELL 条件にストップロス（-8%）とスコア低下を実装。
  - signals テーブルへの日付単位置換（トランザクション＋バルク挿入、SELL 優先ポリシー、ランク再付与など）。

### 設計上の堅牢化・品質改善
- トランザクション管理: features / signals など書き込み処理で BEGIN/COMMIT/ROLLBACK を適用し、ROLLBACK 失敗時はログ警告を出力。
- 入力検証: weights の検証（非数値・NaN/Inf・負値・未知キーの排除）、horizons の範囲チェック（1..252）など。
- ロギング: 各主要処理で情報・警告・デバッグログを出力（問題発見や運用観測性を考慮）。
- NULL / データ欠損対策: 価格欠損時の SELL 判定スキップや、統計関数での None 除外、ゼロ除算回避等、実運用で想定される欠損ケースに配慮。
- セキュリティ考慮: defusedxml の利用、受信サイズ制限、URL 正規化／トラッキング除去によるデータ整合性向上。

### 未実装 / 将来検討点（コード内コメントより）
- signal_generator のエグジット条件で未実装のトレーリングストップ／時間決済（positions に peak_price / entry_date が必要）。
- news_collector の詳細な RSS パースや銘柄紐付け処理の完全実装（骨格とセキュリティ対策は整備済み）。
- execution 層（発注 API 連携）はパッケージに存在するが、このリリースでは直接の発注依存は排除（戦略層は発注層に依存しない設計）。

### セキュリティ
- ニュース処理で defusedxml を使用し XML 攻撃を防止。
- RSS/URL 関連で非 HTTP(s) スキームを排除する方針、受信サイズ上限を設けることでメモリ DoS を軽減。
- J-Quants クライアントで認証トークン管理と自動リフレッシュを実装（無限再帰防止のため allow_refresh フラグを導入）。

---

セマンティックバージョンや日付はソースコードおよび本日のスナップショット（2026-03-21）に基づき作成しています。さらに細かい変更履歴やマイナー/パッチ単位の更新があれば、今後のリリースで追記してください。