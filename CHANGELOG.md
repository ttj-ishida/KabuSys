# Changelog

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

最新リリース: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-19
初回公開リリース。以下の機能群を実装しています。

### Added
- コアパッケージ
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に登録。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - プロジェクトルートの探索は __file__ を起点に .git または pyproject.toml を検出する方式を採用（CWD に依存しない）。
  - .env パーサ (_parse_env_line) は以下に対応:
    - 空行・コメント行（#）のスキップ
    - export KEY=val 形式
    - シングル/ダブルクォート内のエスケープ処理
    - クォートなしの場合のインラインコメント取り扱い
  - .env の上書き制御（override）と保護キー(protected)の仕組みを提供。
  - Settings クラスを実装し、環境変数をプロパティ経由で取得:
    - 必須環境変数の検査: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DBパスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - 環境（KABUSYS_ENV）のバリデーション（development|paper_trading|live）
    - ログレベル（LOG_LEVEL）のバリデーション
    - is_live/is_paper/is_dev のユーティリティプロパティ

- データ取得・保存（J-Quants クライアント） (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装:
    - ページネーション対応の fetch_* 系関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）
    - API レート制限（120 req/min）を守る固定間隔スロットリングの RateLimiter 実装
    - 再試行ロジック（指数バックオフ、最大3回）・リトライ対象ステータス（408, 429, 5xx）
    - 401 受信時にリフレッシュトークンで id_token を自動更新して 1 回再試行
    - id_token のモジュールレベルキャッシュによる共有
    - JSON デコードエラーやネットワーク障害への適切なエラーハンドリング
  - DuckDB への冪等保存関数を提供:
    - save_daily_quotes: raw_prices に ON CONFLICT DO UPDATE で保存
    - save_financial_statements: raw_financials に ON CONFLICT DO UPDATE で保存
    - save_market_calendar: market_calendar に ON CONFLICT DO UPDATE で保存
  - データ変換ユーティリティ: _to_float / _to_int（安全な変換、空値処理、"1.0" の扱い等）

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集し raw_news に冪等保存する機能を実装。
    - デフォルト RSS ソース（Yahoo Finance）を提供
    - 記事 ID は URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を確保
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ除去（utm_* 等）、フラグメント削除、クエリソート
    - defusedxml を使った安全な XML パース（XML Bomb 対策）
    - HTTP スキーム制限・受信サイズ上限（MAX_RESPONSE_BYTES=10MB）などの安全対策
    - DB へのバルク挿入はチャンク化してパフォーマンスを考慮
    - 挿入結果を正確に返す（挿入件数の計測）
  - ログ・警告を通じて不正データやスキップされた行を通知

- 研究（Research）モジュール (kabusys.research)
  - ファクター計算のための関数群を提供:
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200日分がなければ None）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（20日ウィンドウ）
    - calc_value: per, roe（raw_financials と prices_daily を結合して計算）
  - 特徴量探索ユーティリティ:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて取得
    - calc_ic: スピアマンランク相関（IC）計算
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー
    - rank: 同順位は平均ランクを割り当てるランク関数（丸めによる ties 対応）
  - 実装方針: DuckDB の prices_daily/raw_financials のみ参照、外部ライブラリ非依存

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date) を実装:
    - research.factor_research の生ファクターを取得して統合
    - ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5 億円）を適用
    - 指定の数値カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）、±3 でクリップ
    - features テーブルへ日付単位で置換（DELETE + bulk INSERT）し冪等性・原子性を保証
    - target_date 以前の最新終値を参照してフィルタを適用（ルックアヘッドバイアス対策）

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装:
    - features と ai_scores を結合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - コンポーネントごとの計算ロジック（シグモイド変換、PER の扱い、欠損時は中立 0.5 で補完）
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）と外部からの weights の検証・正規化
    - Bear レジーム判定（ai_scores の regime_score 平均が負のとき、サンプル数が十分ある場合）により BUY を抑制
    - BUY シグナル: final_score >= threshold（Bear 時は抑制）
    - SELL シグナル（エグジット判定）:
      - ストップロス（終値/avg_price - 1 < -8%）を最優先
      - final_score が閾値を下回った場合
      - positions / prices_daily を参照して欠損データ時は適切にログ出力して処理をスキップまたは安全側へフォールバック
    - SELL 優先ポリシー: SELL 対象は BUY リストから除外し、BUY のランクを再付与
    - signals テーブルへ日付単位の置換（トランザクション + bulk INSERT）で原子性を確保
    - ロギングで重要な判断（Bear 検知、空データなど）を通知

- その他
  - duckdb を前提とした設計で、各処理は DuckDB 接続を引数に取り SQL と Python を組合せて処理を完結
  - ルックアヘッドバイアス防止の設計思想（target_date 時点のデータのみ使用、fetched_at の記録など）
  - 多くの DB 操作を冪等（ON CONFLICT / 日付単位の DELETE→INSERT）にして再実行可能性を担保
  - 詳細なログ出力と警告で異常ケースを検出しやすく設計

### Security
- XML パースに defusedxml を使用し XML ベースの攻撃を軽減
- RSS URL 正規化・スキーム検査による SSRF 対策、受信サイズ上限の導入

### Notes / Requirements
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルト DB パスは settings.duckdb_path / settings.sqlite_path を参照
- 実行環境は DuckDB を利用可能であること

### Changed
- （なし）

### Fixed
- （なし）

### Removed
- （なし）