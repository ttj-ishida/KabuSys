# CHANGELOG

すべての重要な変更は Keep a Changelog のフォーマットに従って記載します。  
このファイルはプロジェクトのリリース履歴を分かりやすくまとめるためのものです。

すべての変更はセマンティックバージョニングに従います（https://semver.org/）。

## [Unreleased]

## [0.1.0] - 2026-03-21
初回公開リリース。日本株自動売買システム "KabuSys" の基本機能群を実装。

### 追加 (Added)
- パッケージ基礎
  - src/kabusys/__init__.py を追加し、パッケージ名・バージョン (__version__ = "0.1.0") と主要サブモジュール（data, strategy, execution, monitoring）をエクスポート。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルと環境変数から設定を自動で読み込む機能を実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - .env のパースを堅牢化（export プレフィックス対応、クォート・エスケープ処理、インラインコメントの扱い）。
  - .env 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / システム環境などのプロパティを提供。必須キーは未設定時に ValueError を送出。
  - 環境（KABUSYS_ENV）やログレベル（LOG_LEVEL）の妥当性検証を実装。

- データ取得・保存 (src/kabusys/data/)
  - J-Quants クライアント (jquants_client.py)
    - API 呼び出し用の低レベル HTTP ラッパーと共通ロジックを実装。
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - リトライ（指数バックオフ、最大3回）と HTTP ステータスに応じた挙動（408/429/5xx の再試行、429 の Retry-After 優先）。
    - 401 受信時にリフレッシュトークンを使用して ID トークンを自動更新して再試行。
    - ページネーション対応の fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar を実装。
    - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装（ON CONFLICT DO UPDATE）。
    - 値変換ユーティリティ (_to_float, _to_int) を実装して不正値に対処。
    - データ取得時に fetched_at を UTC ISO8601 で記録し、look-ahead バイアス追跡を可能に。

  - ニュース収集モジュール (news_collector.py)
    - RSS フィードから記事を収集して raw_news テーブルへ冪等に保存する基本実装を追加。
    - URL 正規化 (トラッキングパラメータ除去、クエリソート、フラグメント除去、小文字化) を実装。
    - defusedxml を使った XML パース（XML Bomb 対策）、受信サイズ制限（MAX_RESPONSE_BYTES = 10 MB）、HTTP スキーム検証などセキュリティ対策を実装。
    - 挿入はチャンク化して一括保存（_INSERT_CHUNK_SIZE）し、挿入件数を正確に返す方針を採用。
    - デフォルト RSS ソースを追加（例: Yahoo Finance のビジネスカテゴリ）。

- リサーチ機能 (src/kabusys/research/)
  - factor_research.py
    - モメンタム（1M/3M/6M）、MA200乖離 (ma200_dev)、ATR（20日）、相対ATR (atr_pct)、20日平均売買代金、出来高比率、PER/ROE 等のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB の prices_daily / raw_financials テーブルを用いて SQL とウィンドウ関数で効率的に算出。
    - データ不足時の None 処理やウィンドウカウント検査を実装。

  - feature_exploration.py
    - 将来リターン計算 (calc_forward_returns) を実装（複数ホライズン対応、1/5/21 日がデフォルト）。
    - ランク相関（Spearman の ρ）による IC 計算 (calc_ic) とランク変換ユーティリティ (rank) を実装（同順位は平均ランク）。
    - factor_summary により各ファクター列の count/mean/std/min/max/median を算出する統計サマリ機能を追加。
    - pandas に依存せず、標準ライブラリ + duckdb で実装。

  - research パッケージ __init__ で主要 API を再エクスポート。

- 戦略層 (src/kabusys/strategy/)
  - 特徴量エンジニアリング (feature_engineering.py)
    - research 側で計算した raw ファクターを取り込み、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 正規化（z-score）・±3 のクリップ処理を行い、features テーブルへ日付単位で置換（トランザクション + バルク挿入で冪等）。
    - build_features API を提供。

  - シグナル生成 (signal_generator.py)
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news コンポーネントから final_score を計算するロジックを実装。
    - コンポーネントスコア計算（シグモイド変換や PER に基づく値スコア等）、欠損コンポーネントは中立値 0.5 で補完。
    - 重み（デフォルトは momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）を受け付け、検証・再スケールを実施。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値）で BUY を抑制。
    - BUY シグナル閾値デフォルト 0.60、ストップロス -8% を実装。
    - 保有ポジションに対するエグジット判定を行い SELL シグナルを生成（_generate_sell_signals）。
    - signals テーブルへ日付単位で置換して保存する API (generate_signals) を実装。

- その他
  - strategy パッケージ __init__ で build_features と generate_signals をエクスポート。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 既知の制限 / TODO / 未実装 (Notes)
- signal_generator._generate_sell_signals 内の一部条件（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date の情報が必要であり、未実装のまま注記あり。
- calc_value では PBR・配当利回りは現バージョンで未実装。
- news_collector の外部フェッチ処理の細かなエラーハンドリングや RSS ソースの拡張は今後追加予定。
- execution, monitoring パッケージ（__all__ に含まれているが今回コードベースでは実装の痕跡が薄い）は今後の実装対象。

### セキュリティ (Security)
- RSS パースに defusedxml を使用、受信バイト上限や URL スキーム検証、SSRF 対策などを導入。
- J-Quants クライアントでトークン管理とリトライ制御、レート制限を導入して API 利用の安全性・堅牢性を高める。

---

今後のリリースでは以下を優先的に見込んでいます（例）:
- execution 層の注文発行ロジック（kabuステーション連携）の実装とテスト
- monitoring（監視・アラート）および Slack 通知の統合
- 単体テスト・統合テストの整備と CI パイプラインの導入
- ドキュメント（StrategyModel.md, DataPlatform.md 等）の整備とサンプルワークフロー

（注）この CHANGELOG はコードベースの実装内容から推測して作成した初回の変更履歴です。実際のリリースノートに合わせて必要に応じて修正してください。