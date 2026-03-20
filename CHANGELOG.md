# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
この変更履歴は「Keep a Changelog」の形式に従っています。  

現在のパッケージバージョン: 0.1.0

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-20
初回公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0（src/kabusys/__init__.py）。
  - サブモジュールのエクスポートを定義（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env / .env.local を自動ロード（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env パース機能を実装（コメント行・export 形式・クォート・エスケープ・インラインコメント処理対応）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
  - Settings クラスを提供し、以下の設定取得プロパティを実装：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト値あり）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development/paper_trading/live のバリデーション）
    - LOG_LEVEL（DEBUG/INFO/... のバリデーション）
    - is_live / is_paper / is_dev ヘルパープロパティ
  - 必須環境変数未設定時は明示的な ValueError を送出。

- Data: J‑Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 固定間隔スロットリングによるレート制限実装（120 req/min, RateLimiter）。
  - HTTP リクエストユーティリティ：JSON デコード、タイムアウト、ページネーション対応。
  - 再試行（指数バックオフ、最大 3 回）および 408/429/5xx のリトライロジック。
  - 401 応答時の自動トークンリフレッシュ（1 回）とモジュールレベルの ID トークンキャッシュ。
  - 公開 API：
    - get_id_token(refresh_token=None)
    - fetch_daily_quotes(...)
    - fetch_financial_statements(...)
    - fetch_market_calendar(...)
  - DuckDB への保存ユーティリティ（冪等性を考慮した INSERT ... ON CONFLICT 実装）：
    - save_daily_quotes(conn, records)
    - save_financial_statements(conn, records)
    - save_market_calendar(conn, records)
  - 型変換ユーティリティ：_to_float / _to_int（安全な変換処理）

- Data: ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード取得 & 記事抽出機能（デフォルトソース: Yahoo Finance ビジネスカテゴリ）。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
  - セキュリティ配慮: defusedxml の使用、受信サイズ上限（MAX_RESPONSE_BYTES）など。
  - バルク INSERT 用のチャンク処理、記事IDは正規化 URL のハッシュを利用する方針（冪等性）。
  - DB への保存は ON CONFLICT DO NOTHING / トランザクションでまとめて実行（挿入数を正確に把握）。

- Research（研究用ユーティリティ、src/kabusys/research/）
  - factor_research: 株価データからファクターを計算する関数を追加：
    - calc_momentum(conn, target_date)：mom_1m/3m/6m、ma200_dev（200 日のデータ不足時は None）
    - calc_volatility(conn, target_date)：atr_20, atr_pct, avg_turnover, volume_ratio（窓不足時は None）
    - calc_value(conn, target_date)：per, roe（raw_financials と prices_daily を組み合わせ）
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=[1,5,21])：将来リターン取得（営業日ベース）
    - calc_ic(factor_records, forward_records, factor_col, return_col)：Spearman（ランク相関）IC 計算
    - factor_summary(records, columns)：count/mean/std/min/max/median の統計サマリー
    - rank(values)：同順位の平均ランクを使うランク変換（丸め処理で tie の検出精度を向上）
  - いずれも DuckDB を直接使用し、外部依存（pandas 等）を持たない実装。

- Strategy（戦略ロジック、src/kabusys/strategy/）
  - feature_engineering.build_features(conn, target_date)
    - research モジュールから生ファクターを取得してマージ
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ
    - features テーブルへ日付単位で置換（DELETE + bulk INSERT、トランザクションで原子性）
  - signal_generator.generate_signals(conn, target_date, threshold=0.60, weights=None)
    - features と ai_scores を統合し、各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
    - シグモイドや平均化によるスコア変換、欠損コンポーネントは中立 0.5 で補完
    - デフォルト重みを実装（momentum 0.40 等）。与えられた weights は検証・補完・正規化（合計 1.0 に再スケール）される
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）
    - BUY（threshold 以上）・SELL（ストップロスまたはスコア低下）シグナル生成
    - SELL 優先（SELL 対象は BUY から除外）、signals テーブルへ日付単位で置換（トランザクション）
    - 標準の停止損失閾値: -8%（_STOP_LOSS_RATE）

- API エクスポート
  - strategy パッケージの公開関数 build_features / generate_signals を __all__ に追加。
  - research パッケージの代表ユーティリティを __all__ に追加。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュースパーシングで defusedxml を使用して XML による攻撃（XML bomb 等）を軽減。
- news_collector で受信サイズを制限（MAX_RESPONSE_BYTES）し、メモリ DoS を緩和する方針を導入。
- jquants_client の HTTP エラー・ネットワーク障害に対するリトライ実装により一時的なエラー影響を低減。
- .env 読み込みでは OS 環境変数保護や上書き制御（protected set）を採用。

### Known limitations / TODO
- signal_generator._generate_sell_signals の一部のエグジット条件は未実装（コメント記載）:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- calc_value: PBR / 配当利回りは現バージョンでは未実装。
- news_collector の SSRF / IP ブラックリスト等の具体的なネットワーク層チェックはコメント・方針あり（コード断片のため実装箇所は要確認）。
- positions テーブルのスキーマ（peak_price / entry_date 等）に依存する追加ロジックはまだ未着手。
- AI スコア（ai_scores）が欠損している場合、news スコアは中立 0.5 で補完される点に注意。

### Breaking Changes
- （初回リリースのため該当なし）

---

注: 上記はリポジトリ内のコード・コメントから推測して作成した初回リリースの変更履歴です。実際の運用や今後のコミットによって差異が生じる可能性があります。必要であれば各モジュールごとに詳細なリリースノート（例: 入力/出力スキーマ、DB テーブル定義、例外仕様）を追記します。