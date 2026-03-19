# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-19
初回リリース。

### Added
- パッケージ基礎
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ で定義。

- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルートは __file__ を基点に .git または pyproject.toml を探索して特定。特定できない場合は自動ロードをスキップ。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
  - .env パーサーの実装:
    - コメント行・空行無視、export KEY=val 形式対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理。
    - クォートなしの値では '#' の直前が空白/タブの場合のみコメント扱い。
  - Settings クラスを提供し、アプリケーション設定へプロパティ経由でアクセス可能:
    - J-Quants / kabuステーション / Slack / DB（DuckDB/SQLite） / システム設定（env, log_level, is_live 等）。
    - 必須変数未設定時は明確な ValueError を送出。
    - env/log_level の値検証（許容値セットあり）。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - RateLimiter（固定間隔スロットリング）による 120 req/min 制限の遵守。
    - リトライロジック（指数バックオフ、最大3回）。408/429/5xx に対する再試行、429 の Retry-After を尊重。
    - 401 レスポンス時はリフレッシュトークンを使ったトークン更新を 1 回行い再試行。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes: 株価日足（OHLCV）取得。
      - fetch_financial_statements: 財務データ取得。
      - fetch_market_calendar: JPX カレンダー取得。
    - get_id_token: リフレッシュトークンから ID トークンを取得する POST 呼び出し。
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes: raw_prices へ ON CONFLICT DO UPDATE で保存。fetched_at を UTC ISO8601 で記録。
    - save_financial_statements: raw_financials へ ON CONFLICT DO UPDATE で保存。
    - save_market_calendar: market_calendar へ ON CONFLICT DO UPDATE で保存。
  - 入出力の堅牢化ユーティリティ:
    - _to_float / _to_int により安全な型変換と不正値扱いを実装。
    - ペイロードの妥当性チェックで PK 欠損行をスキップし警告ログ出力。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード収集の骨組みを実装。
    - デフォルト RSS ソース（例: Yahoo Finance の business カテゴリ）。
    - RSS 解析に defusedxml を使用して XML による攻撃（XML bomb 等）に対処。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を設定しメモリ DoS を抑止。
    - URL 正規化ユーティリティ:
      - トラッキングパラメータ（utm_* など）の除去、スキーム/ホスト小文字化、フラグメント除去。
    - 記事ID の生成方針（コメントに仕様）：URL 正規化後の SHA-256 ハッシュ（先頭32文字）等で冪等性確保。
    - DB 保存はバルク挿入・チャンク化（_INSERT_CHUNK_SIZE）で性能を考慮。
    - HTTP/HTTPS 以外のスキーム拒否など SSRF を意識した設計（コメントとして明記）。

- 研究（research）モジュール
  - factor_research: prices_daily / raw_financials を用いたファクター計算の実装
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200日移動平均乖離）を計算。データ不足時は None。
    - calc_volatility: 20日 ATR（atr_20）, atr_pct（相対 ATR）, avg_turnover（20日平均売買代金）, volume_ratio（当日/20日平均）を計算。true_range の NULL 伝播を厳密に扱う。
    - calc_value: target_date 以前の最新 raw_financials と当日の株価を組み合わせて PER / ROE を計算（EPS=0/欠損時は None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを効率的に一括取得。horizons の入力検証（正の整数かつ <=252）。
    - calc_ic: ファクター値と将来リターンの Spearman（ランク相関）を計算。3 サンプル未満では None を返す。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
    - rank: 同順位は平均ランクとするランク変換を実装（round(..., 12) による丸めで ties 検出を安定化）。
  - research パッケージ公開 API を整備（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- 戦略（strategy）モジュール
  - feature_engineering.build_features:
    - research 側で計算した生ファクターをマージし、ユニバースフィルタ（最低株価 _MIN_PRICE=300 円、20日平均売買代金 _MIN_TURNOVER=5e8）を適用。
    - 正規化は zscore_normalize に委譲し、正規化対象カラムを定義（mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）。
    - Z スコアを ±3 でクリップして外れ値影響を抑制。
    - 日付単位で DELETE → INSERT（トランザクション）により冪等に features テーブルへ保存。
  - signal_generator.generate_signals:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントはシグモイド変換や PER の逆数スケーリング等で 0〜1 に変換。
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）を持ち、外部から与えられた weights は検証・正規化して使用（不正値は無視）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負）で BUY シグナルを抑制。
    - BUY 閾値のデフォルトは 0.60。
    - SELL（エグジット）判定を実装:
      - ストップロス: 終値 / avg_price - 1 < -0.08（-8%）。
      - スコア低下: final_score が threshold 未満。
      - 保有銘柄で価格欠損の場合は判定をスキップして警告ログ。
      - SELL は BUY より優先し、signals テーブルへ日付単位の置換で保存。
    - 最終的に BUY/SELL 合計件数を返す。

### Changed
- なし（初回リリースのため）。

### Fixed
- なし（初回リリースのため）。

### Known limitations / Notes
- signal_generator のエグジットロジックではトレーリングストップ（peak_price ベース）や時間決済（保有 60 営業日超）などは未実装（コメントで明記）。追加には positions テーブルの拡張が必要。
- news_collector の一部セキュリティ関連実装（IP/ホスト検査等）は設計コメントで言及されているが、提供されたコード断片では処理全体が未完（引き続き実装が必要な箇所あり）。
- data.stats.zscore_normalize は外部モジュール（kabusys.data.stats）として利用される前提だが、本リリースでその実装の完全性を確認する必要がある（インポート箇所は存在）。
- 一部のユーティリティは外部環境（DuckDB スキーマやテーブル定義、外部 API トークン等）依存のため、実運用前にスキーマ定義・環境変数の整備が必要。

### Security
- J-Quants API クライアントはトークンリフレッシュと HTTP ヘッダ制御を実装しているが、トークン管理（保存場所・権限）は運用者で適切に行ってください。
- RSS 解析は defusedxml を使用し XML 系攻撃への対策を講じています。HTTP レスポンスサイズ制限やスキーム検査などの防御も設計に含まれます。

---

貢献・改善案や不具合を見つけた場合は Issue を立ててください（実装の意図や安全性に関わる点は特に歓迎します）。