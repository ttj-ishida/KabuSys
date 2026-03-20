CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-03-20
--------------------

Added
- 基本パッケージ初期実装（kabusys v0.1.0）
  - パッケージメタ情報: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ローダ実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env/.env.local の読み込み優先度（OS 環境変数 > .env.local > .env）を実装し、OS 環境変数を保護する protected キーセットを導入。
  - .env パーサ実装（コメント、export 形式、クォート/エスケープ処理、インラインコメント考慮）。
  - 必須環境変数取得用 _require()、および Settings クラスを提供。J-Quants / kabu / Slack / DB パス / 環境種別・ログレベル検証などのプロパティを公開（値検証・既定値あり）。
  - 有効な環境値検証: KABUSYS_ENV（development, paper_trading, live）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

- データ取得・保存（src/kabusys/data）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - レートリミッタ（120 req/min）を固定間隔スロットリングで実装。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）を実装。
    - 401 受信時にリフレッシュトークンから自動で ID トークンを再取得して 1 回リトライ。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB へ冪等保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT による更新、PK 欠損行のスキップとログ警告、fetched_at（UTC）記録など。
    - 安全で堅牢な型変換ユーティリティ _to_float / _to_int。
  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィード収集の骨子を実装（デフォルトソース: Yahoo Finance ビジネスRSS）。
    - セキュリティ対策: defusedxml を用いた XML パース、受信サイズ上限（MAX_RESPONSE_BYTES）、HTTP/HTTPS スキームチェック等。
    - URL 正規化処理（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリ整列）。
    - 挿入はバルクチャンク処理（_INSERT_CHUNK_SIZE）で行う想定、記事ID は正規化 URL のハッシュで冪等性を確保する方針。
    - DB 保存時に ON CONFLICT / DO NOTHING を想定した設計。

- 研究（research）モジュール（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA乖離）を DuckDB 上の SQL＋ウィンドウ関数で計算。
    - calc_volatility: 20日 ATR（true range の平均）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、volume_ratio を計算。true_range の NULL 伝播制御やウィンドウ内サンプルチェックを実装。
    - calc_value: raw_financials から最新の財務データを取得して PER / ROE を計算（EPS が 0 または欠損のときは None）。
    - 各関数は prices_daily / raw_financials のみ参照し、本番 API にはアクセスしない設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定日から指定ホライズン（デフォルト [1,5,21]）先までの将来リターンを一括取得。ホライズン検証（1〜252営業日）やパフォーマンス考慮（スキャン範囲バッファ）あり。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算。データ不足（有効サンプル < 3）の場合は None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を標準ライブラリのみで実装。
  - research パッケージの公開 API を整理（__all__ に主要関数をエクスポート）。

- 戦略（strategy）モジュール（src/kabusys/strategy）
  - 特徴量作成（src/kabusys/strategy/feature_engineering.py）
    - research の生ファクターを取得して統合、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 指定列の Z スコア正規化（zscore_normalize を使用）、±3 でクリップして外れ値影響を低減。
    - 日付単位で features テーブルをトランザクション + DELETE/INSERT により置換（冪等性と原子性を確保）。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合して各種コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算、重み付きで final_score を算出（既定重みを提供）。
    - 重みの検証・補完（未知キー無視、非数値や負値の除外、合計が 1.0 でない場合の再スケール）。
    - AI レジームスコアを用いた Bear 判定（サンプル数閾値あり）。Bear 時は BUY シグナルを抑制。
    - BUY シグナルは閾値（デフォルト 0.60）を超えた銘柄に付与。SELL シグナルはストップロス（-8%）やスコア低下で判定。
    - positions テーブル・価格欠損時の安全策（価格欠損があれば SELL 判定をスキップ）や、features に存在しない保有銘柄は final_score=0 として扱う警告ログを出力。
    - signals テーブルへ日付単位で置換（トランザクションで原子性）。BUY と SELL の優先ルール（SELL 優先で BUY から除外）を実装。
    - 未実装だが設計に言及されているエグジット条件: トレーリングストップ、時間決済（TODO）。

- パッケージ API 整理
  - strategy と research の __init__ で主要関数をエクスポート（build_features, generate_signals, calc_* 等）。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Security
- RSS パーサに defusedxml を採用して XML ベースの攻撃（XML bomb 等）を軽減。
- ニュース収集で受信サイズ上限を設定しメモリ消費攻撃を緩和。
- URL 正規化時にトラッキングパラメータを除去、スキーム検証（HTTP/HTTPS）設計。SSRF リスク軽減の設計方針を明記。
- J-Quants クライアントはトークン管理と再試行に注意を払った設計（401 自動リフレッシュ、Retry-After を考慮した待機等）。

Known Issues / Notes
- execution パッケージは空の初期プレースホルダ（src/kabusys/execution/__init__.py）。実運用の注文送信ロジックは未実装。
- signals/positions テーブルのスキーマ依存:
  - 一部エグジット条件（トレーリングストップ、保有日数判定）は positions に peak_price / entry_date 等の拡張が必要とコメントに記載。
- news_collector の完全な RSS 取得・DB 挿入の細部（チャンク挿入や記事ID生成）の実装継続が想定される（現状はユーティリティや設計を実装済み）。
- DB テーブル（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar 等）はこのコードと合わせて正しいスキーマを用意する必要あり。
- エラー時のロールバック処理を多数実装しているが、運用環境での統合テストを推奨。

その他
- ログ出力を各処理に埋め込み、運用時の可観測性を確保（info/warning/debug レベル）。
- 全体設計はルックアヘッドバイアスを避ける方針（target_date 以前のデータのみ利用、fetched_at による取得時刻記録）を一貫して採用。

------------

今後の予定（例）
- execution 層の発注実装（kabu ステーション連携）と安全なサンドボックス（paper_trading）導入。
- news_collector の完全動作実装と記事→銘柄紐付けロジックの追加。
- 単体テスト・統合テストの追加（特に DB とのトランザクション周りや API リトライ/レートリミット挙動）。