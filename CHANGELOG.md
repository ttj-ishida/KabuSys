CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
（主な機能・設計方針はソースコードのドキュメント文字列および実装から推測して記載しています。）

[Unreleased]: https://example.com/kabusys/compare/HEAD...v0.1.0
[0.1.0]: https://example.com/kabusys/releases/tag/v0.1.0

## [0.1.0] - 2026-03-20

初回リリース — KabuSys: 日本株自動売買システムの基本モジュール群を追加。

### 追加 (Added)
- パッケージ基盤
  - src/kabusys/__init__.py にバージョン（0.1.0）と公開 API を定義（data, strategy, execution, monitoring）。
- 設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数からの自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
    - 複雑な .env パース実装（export プレフィックス対応、シングル/ダブルクォートのエスケープ処理、コメントルール）。
    - .env と .env.local の読み込み優先度実装（OS 環境変数は保護）。自動ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - 設定ラッパークラス Settings を提供（必須パラメータ取得とバリデーション）。
    - 主な設定プロパティ: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV（開発/paper_trading/live 検査）、LOG_LEVEL（許可レベル検査）など。
- データ取得・保存（J-Quants）
  - src/kabusys/data/jquants_client.py
    - レートリミッタ実装（120 req/min、固定間隔スロットリング）。
    - HTTP リクエスト共通処理（_request）にリトライ（指数バックオフ）、429/408/5xx の再試行、401 時のトークン自動リフレッシュ（1 回のみ）を実装。
    - トークン取得 get_id_token（リフレッシュトークンを利用）。
    - ページネーション対応のフェッチ API: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への保存ユーティリティ: save_daily_quotes, save_financial_statements, save_market_calendar（fetched_at を UTC で記録、ON CONFLICT による冪等保存）。
    - 型変換ヘルパー _to_float / _to_int を実装（不正値を安全に None に）。

- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS からのニュース収集フロー（RSS 取得、テキスト前処理、正規化、DB への冪等保存、記事→銘柄紐付け）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去、小文字化）。
    - defusedxml による XML パース（XML Bomb 対策）、受信サイズ上限（MAX_RESPONSE_BYTES）などセーフガード。
    - 記事 ID を URL 正規化後の SHA-256 で生成して冪等性を確保（設計方針）。
    - デフォルト RSS ソースとして Yahoo Finance のカテゴリ RSS を定義。

- リサーチ（研究用）機能
  - src/kabusys/research/factor_research.py
    - モメンタム calc_momentum（1M/3M/6M リターン、MA200 乖離率）、ボラティリティ calc_volatility（ATR20・相対ATR・流動性指標）、バリュー calc_value（PER/ROE）を実装。
    - DuckDB の prices_daily / raw_financials を参照して純粋にテーブル演算で算出する設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン calc_forward_returns（複数ホライズン同時取得）、IC（calc_ic）計算（Spearman ランク相関）、rank 関数、factor_summary（基本統計量）を実装。
    - 外部依存を避けた（pandas 等不使用）実装方針。
  - research パッケージ __init__ にて上記 API を公開。

- 戦略（Strategy）
  - src/kabusys/strategy/feature_engineering.py
    - 研究で算出した raw ファクターのマージ、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）、Z スコア正規化（zscore_normalize を利用）、±3 でクリップ、features テーブルへの日単位置換（トランザクションによる原子性）を実装。
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して最終スコア final_score を計算し、BUY / SELL シグナルを生成して signals テーブルへ保存。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。sigmoid 変換・欠損は中立 0.5 で補完。
    - デフォルト重み（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）を備え、ユーザー重みの検証とリスケール処理を実装。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合）により BUY シグナルを抑制。
    - SELL 判定にストップロス（-8%）とスコア閾値未満を実装。positions / prices を参照し、price 欠損時は SELL 判定をスキップして誤クローズを防止。
    - signals テーブルへの日単位置換（トランザクション）を実装。

- パッケージ公開 API
  - src/kabusys/strategy/__init__.py で build_features / generate_signals を公開。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 既知の制限・未実装 (Known issues / TODO)
- signal_generator のエグジット条件について未実装項目あり（コード中の記載）:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- calc_value では PBR や配当利回りは未実装（ドキュメントコメントに記載）。
- news_collector はデフォルトソースが限定的（現状は Yahoo Finance のカテゴリ RSS）。
- 一部設計は研究/本番分離を前提としており、execution 層や発注 API への直接依存を避けているため、実際の注文執行ロジックは別モジュールでの実装が必要。
- jquants_client のリトライ対象コードは実装上 408/429/5xx を意図して扱うが、運用で追加の調整が必要な場合がありうる。
- .env パーサは多くのケースをカバーするが、極端に特殊な構文は想定外（必要ならさらに拡張）。

### セキュリティ (Security)
- news_collector で defusedxml を使用し XML ベースの攻撃（XML Bomb 等）に対処。
- ニュース収集での URL 正規化・スキームチェックや受信サイズ制限により SSRF / メモリ DoS のリスクを軽減する設計方針を明示。
- jquants_client の _request は allow_refresh フラグでトークン自動リフレッシュの無限再帰を防止。

--- 

注記:
- 上記はコード内の docstring と実装から推測して作成した CHANGELOG です。実際のリリースノート作成時はリリース日や外部参照（リリースタグ、Issue/PR 番号）を適宜追記してください。