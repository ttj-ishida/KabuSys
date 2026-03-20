# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

なお本リポジトリの現在のパッケージバージョンは src/kabusys/__init__.py の __version__ に合わせています。

## [Unreleased]

### Added
- 開発中・今後実装予定の項目を記載しています。
  - ポジション管理におけるトレーリングストップおよび時間決済（60 営業日超過）のエグジット条件：strategy/signal_generator.py 内に未実装コメントとして残しています。
  - 追加ファクター（PBR・配当利回りなど）のサポート（research/factor_research.py に TODO 記載）。

### Changed
- （今後のリリースで検討）AI スコアの取扱いや重み付けのチューニング、外部データ取得のエラー処理強化など。

---

## [0.1.0] - 2026-03-20

### Added
- 基本パッケージ構成
  - kabusys パッケージの初期公開（src/kabusys/__init__.py: __version__ = 0.1.0）。
  - strategy、execution、data、monitoring などの公開モジュールを __all__ で定義。

- 環境変数 / 設定管理（src/kabusys/config.py）
  - .env / .env.local ファイルからの自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - export KEY=val 形式やクォート付き値、行内コメントなどに対応した .env パーサ実装。
  - OS 環境変数を保護する protected 機構（.env.local による上書きを制御）。
  - 必須設定取得用の _require と Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベルなど）。
  - KABUSYS_ENV と LOG_LEVEL の許容値検証を実装（不正値で ValueError 発生）。

- データ取得クライアント：J-Quants API（src/kabusys/data/jquants_client.py）
  - 基本 API クライアントを実装（トークン取得、ページネーション対応の fetch_* 関数）。
  - レート制限（120 req/min）対応の固定間隔レートリミッタ実装。
  - リトライ（指数バックオフ、最大 3 回）対応、HTTP 429 の Retry-After 優先、408/429/5xx の再試行ロジック。
  - 401 受信時の ID トークン自動リフレッシュ（1 回のみ）とモジュールレベルのトークンキャッシュ。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）：ON CONFLICT（重複更新）による冪等保存を実装。
  - 型変換ユーティリティ _to_float / _to_int を提供（不正値は None にフォールバック）。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集と前処理機能を実装（デフォルトソースに Yahoo Finance）。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）。
  - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を担保。
  - defusedxml を使用して XML 攻撃を防御、HTTP(S) スキーム以外拒否、最大受信サイズ制限（10 MB）、DB へのバルク挿入最適化。
  - raw_news 保存時に ON CONFLICT DO NOTHING を使用。

- 研究（research）モジュール（src/kabusys/research/*.py）
  - ファクター計算（factor_research.py）
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）、Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）、Value（per, roe）を DuckDB の prices_daily / raw_financials を用いて計算。
    - ウィンドウ不足時は None を返す設計。
  - 特徴量探索（feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）のリターンを一括取得。
    - IC（Spearman 相関）計算（calc_ic）: ランク計算を行う rank 関数を提供。
    - ファクター統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。
  - research パッケージの公開 API を __init__ で整理（calc_momentum 等を再エクスポート）。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research モジュールから原始ファクターを取得し、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
  - 指定列の Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 のクリッピングを実施。
  - DuckDB に対する日付単位の置換（DELETE → INSERT のトランザクション）で features テーブルへ冪等に保存。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合し final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ冪等で保存。
  - final_score は momentum/value/volatility/liquidity/news の重み付き和（デフォルト重みを実装、合計が 1.0 になるよう正規化）。ユーザー重みの検証（無効値のスキップ、合計 0 の場合はデフォルトにフォールバック）。
  - シグモイド変換や欠損コンポーネントの中立補完（0.5）を採用。
  - Bear レジーム検知（ai_scores の regime_score 平均が負かつサンプル >= 3 の場合）により BUY を抑制。
  - エグジット条件（ストップロス: -8% 以下、スコア低下）を実装。保有銘柄の価格欠損時は SELL 判定をスキップして誤クローズを防止。
  - signals テーブルへの書き込みもトランザクションで日付単位置換。

### Changed
- なし（初回公開）。

### Fixed
- なし（初回公開）。

### Security
- RSS パースに defusedxml を使用、受信サイズ上限や URL スキームチェック等で外部入力に対する安全策を導入。
- J-Quants API のトークン処理 / リフレッシュは allow_refresh フラグで再帰を防止。

### Notes / Design decisions
- DuckDB を中心とした設計で、prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals 等のテーブルを前提としている（DDL は別途）。
- ルックアヘッドバイアス防止のため、すべての計算は target_date 以前のデータのみを参照するよう意図されている。
- 外部ライブラリへの依存を最小化（research.feature_exploration は pandas 等を使わず標準ライブラリで実装）。
- 一部機能（トレーリングストップ、時間決済、追加ファクター）は将来のリリースでの実装を想定。

---

※ この CHANGELOG は、ソースコードとその docstring / コメントからの推測に基づいて作成しています。実際のリリースノートとして利用する場合は、変更内容の確認および必要に応じた編集をお願いします。