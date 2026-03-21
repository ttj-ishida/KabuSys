# CHANGELOG

すべての重要な変更点はこのファイルに記録します。本プロジェクトは Keep a Changelog の形式に準拠しています。
リリースバージョンは semver を採用します。

※ この CHANGELOG はソースコードからの推測に基づいて作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-21
初回公開リリース。

### Added
- パッケージ基礎
  - kabusys パッケージ初期実装（__version__ = 0.1.0）。
  - サブパッケージ構成: data, research, strategy, execution, monitoring（execution/monitoring の中身は別途実装予定）。

- 設定管理
  - 環境変数・.env ロード機能を実装（kabusys.config）。
    - パッケージのソース位置（.git または pyproject.toml）を起点にプロジェクトルートを自動検出して .env/.env.local を読み込む。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env のパースは以下をサポート:
      - コメント行（#）と export プレフィックス（export KEY=val）。
      - シングル/ダブルクォートされた値とバックスラッシュによるエスケープ処理。
      - クォートなし値の行内コメントの判定（直前がスペース/タブの場合に # をコメントとして扱う）。
    - Settings クラスにより型付きプロパティを提供（J-Quants トークン、kabu API、Slack、DB パス、環境名、ログレベル等）。
    - env 値・log_level のバリデーション（許容値外は ValueError）。

- データ取得 / 保存（Data layer）
  - J-Quants API クライアント（kabusys.data.jquants_client）
    - rate limiting（120 req/min）を固定間隔スロットリング方式で実装。
    - 冪等性を考慮した保存関数（DuckDB への ON CONFLICT DO UPDATE）を実装:
      - save_daily_quotes -> raw_prices
      - save_financial_statements -> raw_financials
      - save_market_calendar -> market_calendar
    - HTTP 再試行/リトライロジック:
      - 指数バックオフ、最大3回、408/429/5xx を再試行対象に。
      - 429 の場合 Retry-After ヘッダを優先。
    - 401 Unauthorized を受けた際にリフレッシュトークンで id_token を自動更新して 1 回リトライする仕組みを実装。
    - ページネーション対応（pagination_key を使用して繰り返し取得）。
    - レスポンス JSON のデコード失敗や最大リトライ超過時に明示的なエラーを発生。
    - 取得データの型安全な変換ユーティリティ _to_float / _to_int を実装。

  - ニュース収集モジュール（kabusys.data.news_collector）
    - RSS フィードから記事を収集して raw_news へ冪等保存する仕組みを実装。
    - 記事IDは URL 正規化後の SHA-256（先頭 32 文字）で生成し冪等性を確保する方針（実装コメント）。
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ（utm_* 等）除去、フラグメント除去、クエリキーでソート。
    - defusedxml を使った安全な XML パース（XML Bomb 等への耐性）。
    - HTTP 応答サイズ上限（MAX_RESPONSE_BYTES＝10MB）でメモリ DoS を緩和。
    - SSRF 対策や受信ホストの検証（設計方針として記載）。
    - バルク INSERT をチャンク化して DB 側の制約に配慮。

- リサーチ / ファクター計算（Research）
  - ファクター計算モジュール（kabusys.research.factor_research）
    - Momentum ファクター: mom_1m/mom_3m/mom_6m、200日移動平均乖離（ma200_dev）。
    - Volatility / Liquidity ファクター: ATR20（atr_20）、atr_pct、20日平均売買代金（avg_turnover）、volume_ratio。
    - Value ファクター: per（株価 / EPS）、roe（最新の過去財務レコードを参照）。
    - DuckDB 上で効率的に SQL ウィンドウ関数と組み合わせて計算（スキャン範囲のバッファあり）。
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - 将来リターン計算 calc_forward_returns（複数ホライズンを同一クエリで取得）。
    - スピアマン IC（ランク相関）計算 calc_ic とランク関数 rank（同順位は平均ランク）。
    - factor_summary による基本統計量（count/mean/std/min/max/median）。
    - すべて標準ライブラリのみで実装（pandas 等外部依存なし）。

  - research パッケージ外部公開 API のエクスポートを整備（calc_momentum 等を __all__ で公開）。

- 特徴量エンジニアリング（Strategy）
  - build_features（kabusys.strategy.feature_engineering）
    - research で計算した raw factors を読み取り、ユニバースフィルタ（最低株価＝300円、20日平均売買代金 >= 5億円）を適用。
    - 正規化: zscore_normalize を利用して指定カラムを Z スコア正規化し ±3 でクリップ（外れ値抑制）。
    - features テーブルへ日付単位で置換（DELETE + INSERT をトランザクション内で実行し冪等性を確保）。
    - DuckDB での原子的な更新とログ出力。

  - シグナル生成（kabusys.strategy.signal_generator）
    - features と ai_scores を組み合わせて各銘柄の複合スコア final_score を算出。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）を計算するユーティリティを実装。
      - momentum: momentum_20, momentum_60, ma200_dev のシグモイド平均。
      - value: PER を 20 を基準にした 1/(1+per/20) の変換（PER が不正な場合は None）。
      - volatility: atr_pct の Z を反転してシグモイド変換（低ボラ = 高スコア）。
      - liquidity: volume_ratio のシグモイド変換。
      - news: ai_score をシグモイドで変換（未登録は中立補完）。
    - 重み付け（デフォルト weights を定義）、ユーザー渡し weights の検証と再スケーリングを実装。
    - Bear レジーム検知（ai_scores の regime_score 平均が負の場合に Bear とみなす。ただしサンプル数閾値あり）。
    - BUY シグナル: final_score >= threshold（デフォルト 0.60）、Bear 時は BUY を抑制。
    - SELL シグナル（エグジット判定）:
      - ストップロス（終値/avg_price - 1 < -8%）優先判定。
      - final_score が閾値未満のスコア低下によるエグジット。
      - positions テーブルに価格がない場合や価格欠損時の挙動はログで警告・スキップ。
    - signals テーブルへ日付単位で置換（DELETE + INSERT をトランザクションで実行）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- ニュース収集で defusedxml を採用し、XML パースに対する攻撃ベクトルを軽減。
- RSS 受信サイズ上限を設定してメモリ DoS のリスク低減（MAX_RESPONSE_BYTES）。

### Notes / Known limitations / Future work
- signal_generator が参照する一部の SELL 条件（トレーリングストップ、時間決済）は comments にて未実装と明示。positions テーブルに peak_price / entry_date が必要。
- calc_value では PBR・配当利回りは未実装。
- news_collector の記事 ID 生成・紐付け処理・SSRF 検証の詳細は設計記述があるが、実装の残り（news_symbols との紐付け等）がある可能性あり。
- research モジュールは外部ライブラリに依存しない実装を目指すため、最適化や大規模データ処理に関しては将来的に改善の余地あり。
- execution / monitoring モジュールの実装は別途追加予定。

---

以上。リリースノートに漏れや不明点がある場合は、該当ソースのコメントや docstring を参照のうえ修正・追記してください。