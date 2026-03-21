Keep a Changelog に準拠した CHANGELOG.md を以下の通り作成しました。リポジトリ内のコード内容から推測して記載しています。

なおバージョンはパッケージの __version__ (src/kabusys/__init__.py) に合わせて 0.1.0 を初版リリースとして扱い、リリース日には現在日時（2026-03-21）を設定しています。必要に応じて日付や表現を調整してください。

----------------------------------------------------------------------
Keep a Changelog
All notable changes to this project will be documented in this file.

The format is based on "Keep a Changelog" and this project adheres to Semantic Versioning.
----------------------------------------------------------------------

## [Unreleased]

## [0.1.0] - 2026-03-21
### Added
- パッケージ基盤
  - 新規パッケージ "kabusys" を追加。モジュール公開 API を __all__ で定義（data, strategy, execution, monitoring）。
  - バージョン番号を src/kabusys/__init__.py にて "0.1.0" として管理。

- 環境設定 / config
  - .env ファイルおよび環境変数を読み込む設定管理モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルート検出: .git または pyproject.toml を基準に自動検出（CWD に依存しない挙動）。
    - .env と .env.local を優先順位付きで自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env のパースを強化:
      - export KEY=val 形式の対応
      - シングル／ダブルクォート内のバックスラッシュエスケープ処理
      - インラインコメント処理（クォート有無での扱いの違い）
    - 上書き制御: override / protected による OS 環境変数保護の仕組み。
    - Settings クラスを提供し、必須環境変数の取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）および検証（KABUSYS_ENV, LOG_LEVEL の許容値）を実装。
    - データベースパスのデフォルト（DUCKDB_PATH, SQLITE_PATH）を Path 型で返すユーティリティを提供。

- データ取得・保存（J-Quants クライアント）
  - J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）。
    - レート制限制御: 固定間隔スロットリング実装（120 req/min を想定する _RateLimiter）。
    - 再試行ロジック: 指数バックオフと最大試行回数（3 回）、HTTP 408/429/5xx 等に対するリトライ。
    - 401 Unauthorized に対する自動トークンリフレッシュ（1 回だけリトライ）とトークンキャッシュを実装。
    - ページネーション対応のフェッチ実装:
      - fetch_daily_quotes（株価日足）、fetch_financial_statements（財務）、fetch_market_calendar（マーケットカレンダー）。
    - DuckDB への冪等保存関数を追加:
      - save_daily_quotes, save_financial_statements, save_market_calendar — ON CONFLICT による更新で重複を排除。
    - データ整形ユーティリティ: _to_float / _to_int（堅牢な変換処理）を提供。
    - fetched_at に UTC 時刻を記録して Look-ahead バイアスの追跡性を確保。

- ニュース収集
  - RSS ベースのニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
    - デフォルト RSS ソースを定義（例: Yahoo Finance のビジネスカテゴリ）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）やバルク挿入用チャンクサイズを設定。
    - URL 正規化ユーティリティを実装（トラッキングパラメータ除去、スキーム/ホストの小文字化、フラグメント削除、クエリのソート）。
    - defusedxml を用いた XML パースを想定し、XML Bomb 等の攻撃緩和を考慮。
    - 設計としては記事 ID を正規化 URL の SHA-256 の一部から生成して冪等性を確保する方針（ドキュメント記載）。
    - DB 保存はバルク/トランザクションを想定し、INSERT の冪等性を重視。

- リサーチ / ファクター計算
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。
    - calc_value: raw_financials から最新財務を取得し PER・ROE を計算（EPS が無い/0 の場合は None）。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみ参照する設計。

  - 特徴量探索（研究用）モジュールを追加（src/kabusys/research/feature_exploration.py）。
    - calc_forward_returns: 各ホライズン（デフォルト 1,5,21 営業日）に対する将来リターン計算を実装。ホライズンのバリデーションあり。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算する実装（同順位は平均ランク処理、サンプル不足時は None）。
    - factor_summary / rank: 基本統計量（count, mean, std, min, max, median）とランク変換ユーティリティを実装。
    - 外部依存を持たない（pandas などを使わない）軽量実装。

- 戦略（特徴量エンジニアリング・シグナル生成）
  - 特徴量作成モジュールを追加（src/kabusys/strategy/feature_engineering.py）。
    - research の calc_* 関数から得た raw ファクターを統合、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）→ ±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE + バルク INSERT をトランザクションで実行し原子性を確保）。
    - 休日や当日欠損を考慮して target_date 以前の最新価格を参照する実装。

  - シグナル生成モジュールを追加（src/kabusys/strategy/signal_generator.py）。
    - features と ai_scores を統合し、複数コンポーネント（momentum / value / volatility / liquidity / news）から final_score を計算（デフォルト重みあり）。
    - シグモイド変換、欠損コンポーネントの中立補完（0.5）、重みの検証・再スケーリングなど堅牢な重み処理。
    - Bear レジーム判定（ai_scores の regime_score 平均が負 -> BUY 抑制、サンプル不足時は抑制しない）。
    - BUY は閾値（デフォルト 0.60）以上、SELL はストップロス（-8%）やスコア低下で判定。
    - positions / prices_daily / ai_scores / features を参照して SELL 判定を行い、BUY と SELL を分離して signals テーブルへ日付単位置換で保存（トランザクション処理、ROLLBACK ハンドリング）。
    - SELL 判定では価格欠損時に判定をスキップする安全ロジックを追加。

### Security / Reliability
- DB 操作や外部 API 呼び出しに対して冪等性・トランザクション制御を多用（ON CONFLICT, DELETE+INSERT, BEGIN/COMMIT/ROLLBACK）。
- ニュースパーサでは defusedxml を利用して XML の脆弱性対策（XML Bomb 等）を考慮。
- J-Quants クライアントでのレート制御と再試行はネットワーク障害や API 制限下での堅牢性を高める設計。
- 環境変数の取り扱い・必須チェックにより起動時の誤設定を早期検出。

### Notes / Requirements (実装から推測)
- DuckDB 上に以下のテーブルを前提として操作する:
  - prices_daily, raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals, raw_news 等。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 設計文書（StrategyModel.md, DataPlatform.md 等）に準拠した仕様をコード上で意図している（コメント・定数名から確認可能）。

### Known limitations / TODO（コード中コメントより）
- 一部のエグジット条件（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等が必要で現状未実装。
- news_collector の記事 ID 生成や URL 検査／SSRF 防止の完全実装は docstring に言及あり（ファイル一部は未出力のため、実装の詳細は残る可能性あり）。
- monitoring / execution パッケージの実装は今回のコード断片では最小または空（将来的な追加を想定）。

----------------------------------------------------------------------
（開発者向け）変更点をより細かく分割したい場合、各モジュールごとにサブセクションを追加することができます。日付・バージョン付けや「Unreleased」セクションの運用方法はプロジェクトのリリースフローに合わせて調整してください。