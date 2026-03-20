# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに従います。  

※バージョン番号はパッケージ内の __version__ に合わせています。

## [Unreleased]

（現在のコードベースでは 0.1.0 が最初のリリースです。今後の変更はここに記載します）

---

## [0.1.0] - 2026-03-20

最初の公開リリース。日本株自動売買システムの基礎機能を実装しました。主な追加内容は以下の通りです。

### Added
- パッケージ基盤
  - パッケージのエントリポイントとバージョン管理を追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。
  - 公開 API: strategy.build_features / strategy.generate_signals をエクスポート。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込み（優先順位: OS 環境変数 > .env.local > .env）。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により CWD に依存しない読み込み。
  - .env 解析器の実装（コメント、export プレフィックス、引用符内エスケープ、インラインコメント等に対応）。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須設定取得ヘルパー _require と Settings クラスを提供。JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等のプロパティを実装。
  - DUCKDB_PATH / SQLITE_PATH 等のデフォルトパス、KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）を実装。

- データ取得・保存（src/kabusys/data）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - レート制御（120 req/min 固定間隔スロットリング）を実装する RateLimiter。
    - HTTP リクエストの共通処理を実装（ページネーション対応、JSON パース、最大リトライ回数、指数バックオフ）。
    - 401 受信時のトークン自動リフレッシュ（1回のみ）とモジュールレベルの ID トークンキャッシュ。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar の取得関数（ページネーション処理を含む）。
    - DuckDB 保存用ユーティリティ: save_daily_quotes, save_financial_statements, save_market_calendar（冪等性のため ON CONFLICT DO UPDATE を使用）。
    - 入力値変換ユーティリティ _to_float / _to_int を提供（堅牢な型変換処理）。

  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィードからのニュース収集基盤を実装。デフォルトソースに Yahoo Finance のビジネス RSS を含む。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除、小文字化）と記事ID生成（正規化 URL の SHA-256 ハッシュ）。
    - defusedxml による XML パースで XML Bomb 等の攻撃緩和、受信サイズ上限（10MB）やバルク INSERT チャンク等の保護策を導入。
    - raw_news / news_symbols 等への冪等保存を想定（ON CONFLICT DO NOTHING / トランザクション運用を想定）。

- リサーチ（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日移動平均乖離 ma200_dev）を計算する calc_momentum を実装。
    - Volatility（20日 ATR と相対 ATR(atr_pct)、20日平均売買代金・出来高変化率）を計算する calc_volatility を実装。
    - Value（PER, ROE）を計算する calc_value を実装（raw_financials の最新レコードを参照）。
    - DuckDB の window 関数を活用し、営業日不連続やデータ欠損を考慮した実装。

  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 calc_forward_returns（複数ホライズンに対応、営業日ベースのリードを使用）。
    - IC（Spearman のランク相関）計算の calc_ic、ランク変換 rank、カラム統計量 factor_summary を実装。
    - 外部ライブラリに依存せず純粋な Python および DuckDB SQL で実装。

  - research パッケージの __all__ を整備し、zscore_normalize 等のユーティリティを再輸出。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research の生ファクターを統合し、正規化・クリップして features テーブルに保存する build_features を実装。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を実装。
  - Z スコア正規化（kabusys.data.stats の zscore_normalize を使用）、±3 でクリップ。
  - 日付単位での置換（DELETE → INSERT）をトランザクションで行い冪等性を保証。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合して final_score を算出し、BUY/SELL シグナルを生成する generate_signals を実装。
  - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI スコア）を算出し、デフォルト重みで加重平均。
  - 重みはユーザ指定で上書き可能だが検証（非数値、負値を無視）および再スケール処理を実装。
  - Sigmoid 変換・欠損値は中立値 0.5 で補完するポリシーを採用。
  - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数 >= 3 で BUY を抑制）。
  - SELL シグナル生成（ストップロス -8%、final_score が閾値未満）。
  - signals テーブルへの日付単位置換をトランザクションで実行し冪等性を保証。
  - デフォルト閾値: BUY = 0.60、ストップロス = -8%。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- news_collector で defusedxml を使用し XML 攻撃を緩和。
- RSS URL 正規化でトラッキングパラメータ除去を実施。
- J-Quants クライアントでタイムアウト・リトライ・トークンリフレッシュなどネットワーク/認証の耐障害性を強化。

### Notes / Known limitations / TODO
- シグナル生成の SELL 判定において、トレーリングストップや時間決済（保有日数に基づく決済）は未実装。positions テーブルに peak_price / entry_date 等のカラムが必要。
- news_collector 内で IP/SSRF 関連の追加保護（ipaddress, socket を用いたホワイトリスト/ブロック検査）は将来の実装候補だが、現状は URL 正規化・スキーマチェック・サイズ制限などの基本対策に留まる。
- データ保存は DuckDB を前提（raw_prices, raw_financials, features, ai_scores, signals, positions, market_calendar, raw_news 等のテーブル構成を想定）。
- J-Quants クライアントのリトライ対象は 408 / 429 / 5xx としている。429 の場合は Retry-After ヘッダを優先。
- 環境変数の自動ロードはプロジェクトルートが見つからない場合スキップされる。テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

過去リリースや将来の変更はこのファイルの上部（Unreleased）に追記してください。