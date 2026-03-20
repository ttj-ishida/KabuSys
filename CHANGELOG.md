Keep a Changelog
=================

すべての重要な変更をここに記録します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠します。  

[0.1.0] - 2026-03-20
-------------------

Added
- 初期リリース: kabusys パッケージ (バージョン 0.1.0)
  - パッケージエントリポイント
    - src/kabusys/__init__.py による公開モジュール: data, strategy, execution, monitoring
    - バージョン情報: __version__ = "0.1.0"

- 環境設定 / ロード機能
  - src/kabusys/config.py
    - .env/.env.local からの自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）
    - 自動読み込みの無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - .env パーサ: export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント扱い、無効行スキップ
    - .env の上書き制御: .env は既存 OS 環境変数を保護（protected set）、.env.local は上書き可能
    - Settings クラスでの環境値参照とバリデーション:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須とする _require() ロジック
      - KABUSYS_ENV の許可値 (development, paper_trading, live) 検証
      - LOG_LEVEL の許可値検証 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
      - データベース既定パス: DUCKDB_PATH= data/kabusys.duckdb、SQLITE_PATH= data/monitoring.db
      - 環境フラグ helper: is_live/is_paper/is_dev

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - レート制御: 固定間隔スロットリングで 120 req/min を満たす _RateLimiter
    - リトライ: 指数バックオフ、最大試行回数 _MAX_RETRIES = 3、408/429/5xx を再試行対象に
    - 401 受信時の自動トークンリフレッシュ（1 回だけ）とトークンキャッシュ共有（ページネーション間）
    - 汎用 HTTP ヘルパ _request()（JSON デコード、Retry-After の考慮、ログ出力）
    - ページネーション対応のデータ取得:
      - fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
    - DuckDB 保存ユーティリティ:
      - save_daily_quotes(): raw_prices へ挿入（ON CONFLICT DO UPDATE）／fetched_at を UTC ISO8601 で記録
      - save_financial_statements(): raw_financials へ挿入（ON CONFLICT DO UPDATE）
      - save_market_calendar(): market_calendar へ挿入（ON CONFLICT DO UPDATE）
    - 型変換ユーティリティ: _to_float(), _to_int()（堅牢な変換・空値処理）
    - 設計上の配慮: 冪等性、look-ahead bias トレース用 fetched_at、レート制限の順守

- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィード収集の基礎機能（既定ソースに Yahoo Finance RSS を含む）
    - URL 正規化: トラッキングパラメータ除去（utm_* 等）、クエリのソート、フラグメント削除、小文字化
    - セキュリティ対策:
      - defusedxml による XML パース（XML Bomb 等の防止）
      - HTTP/HTTPS スキーム以外の URL 拒否（SSRF 緩和）
      - 最大受信バイト数制限（MAX_RESPONSE_BYTES = 10 MB）によるメモリ DoS 緩和
    - 記事 ID は正規化後 URL の SHA-256 ハッシュ（先頭 32 文字を利用）で冪等性を確保
    - DB 保存はバルク挿入、チャンク化、トランザクションにまとめる方針（INSERT RETURNING を活用）

- 研究（research）モジュール
  - src/kabusys/research/factor_research.py
    - calc_momentum(): mom_1m/mom_3m/mom_6m と ma200_dev を DuckDB のウィンドウ関数で計算
    - calc_volatility(): ATR（atr_20, atr_pct）、avg_turnover、volume_ratio を計算。true_range の NULL 伝播を明示的に扱う
    - calc_value(): raw_financials と prices_daily を結合して PER/ROE を計算（EPS 欠損時は None）
    - カレンダーバッファや最小データ数チェック等、実運用を意識した設計
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns(): 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得
    - calc_ic(): スピアマンのランク相関（Information Coefficient）を計算。サンプル 3 未満は None を返す
    - factor_summary(): count/mean/std/min/max/median を計算
    - rank(): 同順位は平均ランクを与える方式（round(v, 12) で ties の安定化）
  - research パッケージのエクスポート強化（zscore_normalize などと共に公開）

- 戦略（strategy）モジュール
  - src/kabusys/strategy/feature_engineering.py
    - build_features(conn, target_date):
      - research で計算した raw factors を取得（calc_momentum/calc_volatility/calc_value）
      - 株価・流動性によるユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）
      - 指定カラムの Z スコア正規化（zscore_normalize を使用）と ±3 でクリップ
      - features テーブルへ日付単位で置換（BEGIN/DELETE/INSERT/COMMIT、ロールバック処理）
      - 冪等での上書き（対象日を全消去してから挿入）
  - src/kabusys/strategy/signal_generator.py
    - generate_signals(conn, target_date, threshold=0.60, weights=None):
      - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
      - _sigmoid による Z スコア -> [0,1] 変換、_avg_scores によるコンポーネント合成
      - デフォルト重みの採用と user-supplied weights の検証・正規化（負値・非数値は無視、合計が 1.0 にリスケール）
      - Bear レジーム判定: ai_scores の regime_score の平均が負かつサンプル数 >= 3 の場合、BUY を抑制
      - BUY: final_score >= 0.60 を閾値、SELL: ストップロス（-8%）または final_score < threshold
      - 保有ポジションは positions テーブル参照（最新ポジションのみ）し、価格欠損時は判定スキップ
      - signals テーブルへ日付単位の置換（トランザクション + バルク挿入）
      - ログ出力・警告（features 空時や価格欠損時など）

Changed
- 初回リリースのため "Changed" に該当する過去変更はなし。

Fixed
- 初回リリースのため "Fixed" に該当する既知修正はなし。

Security
- news_collector: defusedxml の採用、HTTP/HTTPS のみ許可、最大受信バイト数制限で外部入力に対する安全性を向上
- jquants_client: トークン管理・自動リフレッシュにより認証失敗時の安全なリトライを実現。レート制御により API 利用制限を順守。

Known limitations / Not implemented
- _generate_sell_signals 内で言及されている未実装のエグジット条件:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- news_collector 実装の一部（例: 記事パース→DB への完全な流れや id ハッシュ生成の詳細）はドキュメントに記載されているが、コード断片は一部省略されているため実装状況は要確認。
- unit tests / CI やパッケージ配布メタ情報はこのリリースには含まれていない（今後の追加予定）。

開発者向け備考
- DuckDB 接続を受け取る設計により、外部 API 呼び出しや発注層への直接依存を避けているため、ローカルテストやリサーチ用途での再利用が容易。
- 多くの関数が「target_date 時点のみを使用」することでルックアヘッドバイアスの軽減を図っている。
- ログは詳細に出力する設計（warning/info/debug）で運用時のトラブルシュートを意識。