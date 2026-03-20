# CHANGELOG

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠します。  
フォーマット: https://keepachangelog.com/（日本語意訳）

最新リリース
- [0.1.0] - 2026-03-20

## [Unreleased]
（現状なし）

## [0.1.0] - 2026-03-20
初回リリース。日本株自動売買システム "KabuSys" のコア機能を実装しました。主な追加点・設計方針・既知の制約は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）。公開モジュール: data, strategy, execution, monitoring。
- 設定管理 (kabusys.config)
  - .env / .env.local 自動ロード（プロジェクトルート判定: .git または pyproject.toml）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パーサーの堅牢化（コメント・export プレフィックス・シングル/ダブルクォート、エスケープ対応）。
  - Settings クラスを提供。J-Quants リフレッシュトークン、kabu API 設定、Slack トークン/チャンネル、DB パス（DuckDB/SQLite）、環境（development/paper_trading/live）・ログレベルの検証付きプロパティを実装。
- データ取得 / 保存 (kabusys.data.jquants_client)
  - J-Quants API クライアント実装。
  - レート制限（固定間隔スロットリング: 120 req/min）を内蔵する RateLimiter。
  - 再試行（指数バックオフ、最大 3 回）、HTTP 408/429/5xx のリトライ処理。
  - 401 受信時は ID トークン自動リフレッシュ（1 回のみ）してリトライ。無限再帰防止の allow_refresh フラグあり。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）。冪等性確保のため ON CONFLICT DO UPDATE を使用、fetched_at を UTC で記録。
  - 型変換ユーティリティ (_to_float/_to_int) を実装。
- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード取得・前処理・DB 保存の実装方針を反映。
  - defusedxml を用いた XML パース（XML Bomb 等の防御）。
  - URL 正規化機能（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
  - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）、SSRF を意識したスキーム制限等の安全設計。
  - バルク挿入のチャンク処理。
- 研究用モジュール (kabusys.research)
  - ファクター計算モジュール（factor_research）を実装:
    - Momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日MA乖離率）。データ不足時は None。
    - Volatility: 20日ATR、相対ATR(atr_pct)、20日平均売買代金、volume_ratio。
    - Value: PER、ROE（raw_financials の最新財務データを使用）。
  - 特徴量探索 (feature_exploration):
    - 将来リターン計算（calc_forward_returns）：複数ホライズン対応（デフォルト [1,5,21]）、営業日不足時の取り扱い。
    - IC（Information Coefficient）計算（Spearman の ρ）: calc_ic。
    - 統計サマリー（factor_summary）とランク変換ユーティリティ（rank）。
  - research パッケージのエクスポート設定を提供。
- 戦略モジュール (kabusys.strategy)
  - 特徴量生成 (feature_engineering.build_features):
    - research で計算した生ファクターをマージ、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 指定カラムの Z スコア正規化（外部 zscore_normalize を利用）と ±3 でクリップ。
    - features テーブルへの日付単位の置換（DELETE→INSERT をトランザクションで実行し冪等性と原子性を確保）。
  - シグナル生成 (signal_generator.generate_signals):
    - features と ai_scores を統合し、複数コンポーネント（momentum/value/volatility/liquidity/news）を重み付き合算して final_score を算出。
    - デフォルト重みと閾値（デフォルト閾値 0.60）をサポート。ユーザ渡し weights は検証・正規化される（不適切な値はスキップ、合計が 1.0 にリスケール）。
    - AI によるレジームスコア集計で Bear レジーム判定を行い、Bear の場合は BUY シグナルを抑制。
    - エグジット判定（SELL）にストップロス（-8%）・スコア低下を実装。
    - signals テーブルへの日付単位置換で冪等性を保持。
- ロギング・メッセージ
  - 各モジュールにデバッグ/警告/情報ログが挿入され、運用時のトラブルシュートに寄与。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- RSS パースに defusedxml を使用して XML 攻撃対策。
- ニュース URL 正規化で既知トラッキングパラメータを削除し、一貫した ID 生成（冪等性）を想定。
- HTTP トークンの自動リフレッシュ時、無限ループを避ける仕組み（allow_refresh フラグ）を実装。

### 既知の制約 / TODO
- signal_generator 内での未実装条件:
  - トレーリングストップ（ピーク価格が positions テーブルに必要: peak_price / entry_date が未実装） — コード内に TODO コメントあり。
  - 時間決済（保有 60 営業日超過）の未実装。
- execution パッケージは空（発注層は別途実装予定）。strategy 層は発注 API に直接依存しない設計。
- data.stats.zscore_normalize の実装は別モジュール（kabusys.data.stats）に依存。リポジトリ内で提供されていることを前提としている。
- news_collector の「記事ID を URL 正規化後の SHA-256（先頭32文字）で生成」等の詳細実装は設計に含まれているが、リポジトリの該当箇所（ID 生成／news_symbols の紐付け）の実装状況に依存。
- DuckDB スキーマ定義・マイグレーションは本リリースに含まれていないため、運用前に適切なテーブル定義を準備する必要あり。

### マイグレーション / 注意事項
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。パッケージ配布後にテスト実行等で自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- settings.env / LOG_LEVEL の値は検証され、不正な値は ValueError を発生させます。
- J-Quants API の利用には JQUANTS_REFRESH_TOKEN の設定が必須です。settings.jquants_refresh_token プロパティは未設定時に ValueError を送出します。
- DuckDB への保存は ON CONFLICT により既存行を更新しますが、テーブルの主キー／インデックスが想定通りに定義されていることを確認してください。

---

この CHANGELOG はコード内の docstring・コメント・関数実装から推測して作成しています。実際の運用リリースでは付随するテスト、DB スキーマ、運用ドキュメント（StrategyModel.md / DataPlatform.md 等）の整備を推奨します。