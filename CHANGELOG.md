# Changelog

すべての注目すべき変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、すべてのバージョンを時系列で記載します。

なお、このリポジトリの初期リリースはバージョン 0.1.0（パッケージ __version__）です。

## [Unreleased]
（現在未リリースの変更はここに記載）

---

## [0.1.0] - 2026-03-19

初回公開リリース。日本株自動売買システム（KabuSys）のコアライブラリを提供します。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py
    - パッケージ名とバージョンを定義（__version__ = "0.1.0"）。
    - 公開 API として data, strategy, execution, monitoring を __all__ に設定。

- 設定・環境変数管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数からの設定自動ロード機能（プロジェクトルートを .git / pyproject.toml により検出）。
    - .env と .env.local の優先順位（OS 環境変数 > .env.local > .env）。OS 環境変数を保護する protected 機能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（主にテスト用途）。
    - export KEY=val 形式、クォートやインラインコメントの取り扱いをサポートするパーサ実装（_parse_env_line）。
    - Settings クラスにアプリ設定プロパティを集約：
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須として取得（未設定時は ValueError）。
      - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値/解決。
      - KABUSYS_ENV（development/paper_trading/live）の検証、LOG_LEVEL の検証、便宜的な is_live / is_paper / is_dev プロパティ。

- データ取得・保存（J-Quants）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアント実装（fetch/save 系関数）：
      - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
      - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存、ON CONFLICT による更新）
    - レート制限のための固定間隔スロットリング実装（_RateLimiter、120 req/min を想定）。
    - 再試行ロジック（指数バックオフ、最大リトライ回数、特定ステータスコードでの再試行、Retry-After の考慮）。
    - 401 が返った場合のトークン自動リフレッシュ機構（get_id_token とキャッシュ化）。
    - Look-ahead bias 対策として fetched_at を UTC で記録。
    - 入力値の安全に配慮したユーティリティ関数（_to_float / _to_int）。
    - エラー時のログ出力と警告。

- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィードから記事を収集し raw_news に保存する処理を提供。
    - 記事 ID を URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を確保。
    - defusedxml を使用して XML の脆弱性（XML Bomb 等）を回避。
    - URL 正規化実装（トラッキングパラメータ除去・クエリソート・フラグメント削除・スキーム/ホスト小文字化）。
    - HTTP 応答サイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策。
    - HTTP/HTTPS 以外のスキーム拒否や SSRF を想定した入力チェック（実装方針として明記）。
    - バルク INSERT のチャンク処理（_INSERT_CHUNK_SIZE）によりDB負荷を抑制。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - calc_momentum, calc_volatility, calc_value を実装：
      - momentum: 約1/3/6ヶ月のリターン、200日移動平均乖離（MA200）を計算。
      - volatility: 20日 ATR（true_range の取り扱いに注意）、相対ATR(atr_pct)、20日平均売買代金、出来高比率を算出。
      - value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（EPS が無効な場合は None）。
    - DuckDB のウィンドウ関数を活用した効率的な実装（LAG, AVG, COUNT, LEAD 等）。
    - データ欠損時の None 帰却方針（ルックアヘッドバイアス回避、欠損銘柄の処理）。

  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）での将来リターンを計算（範囲制限のためカレンダーバッファを採用）。
    - calc_ic: Spearman（ランク）相関による IC 計算（同順位は平均ランク処理、サンプル不足時は None）。
    - rank: 値→ランク変換（同順位は平均ランク、round(v,12) による ties 対策）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を返す。

  - research パッケージの __all__ を整備（外から利用しやすくエクスポート）。

- 戦略（Feature エンジニアリング & シグナル生成）
  - src/kabusys/strategy/feature_engineering.py
    - build_features(conn, target_date): research モジュールの生ファクターを取得し正規化・合成して features テーブルへ UPSERT（置換）する処理を実装。
    - ユニバースフィルタを実装（最低株価 300 円、20日平均売買代金 5 億円）。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）および ±3 でのクリップ。
    - トランザクション + バルク挿入による日付単位の原子性保持。

  - src/kabusys/strategy/signal_generator.py
    - generate_signals(conn, target_date, threshold=0.6, weights=None): features と ai_scores を統合して final_score を算出、BUY/SELL シグナルを生成して signals テーブルへ置換。
    - デフォルト重み _DEFAULT_WEIGHTS を定義し、ユーザ指定 weights の検証・合成・正規化を実装（未知キーや無効値はスキップ）。
    - コンポーネントスコア（momentum, value, volatility, liquidity, news）の算出処理を実装（シグモイド変換、None は中立値 0.5 で補完）。
    - Bear レジーム判定（ai_scores の regime_score を集計、サンプル数閾値あり）により BUY シグナルを抑制。
    - 保有ポジションに対するエグジット判定（ストップロス -8% / スコア低下）を実装（_generate_sell_signals）。
    - SELL を優先して BUY から除外するポリシー、および signals の日付単位置換をトランザクションで実現。

- パッケージエクスポート調整
  - src/kabusys/strategy/__init__.py で build_features / generate_signals を公開。

### Changed
- （新規リリースのため無し）

### Fixed
- （現時点で特定のバグ修正は無し）

### Security
- ニュース処理に defusedxml を採用して XML 関連の攻撃に対処。
- news_collector にて受信バイト数制限と URL 正規化を導入し、メモリ DoS とトラッキングパラメータ由来の不整合を低減。
- J-Quants クライアントでトークン管理とリフレッシュ時の無限再帰防止（allow_refresh フラグ）を実装。

### Performance / Reliability
- J-Quants クライアントで固定間隔のレートリミッタ実装（120 req/min 想定）。
- API 呼び出しに対する堅牢な再試行と指数バックオフ。
- DuckDB へのバルク挿入とトランザクション（BEGIN/COMMIT/ROLLBACK）による原子性保証。
- news_collector でのチャンク挿入により SQL・パラメータ量制限に対応。

### Internal / Notes
- ルックアヘッドバイアス防止の観点から、すべての集計・シグナル生成処理は target_date 時点までに利用可能なデータのみを参照する設計になっています（fetched_at を用いたトレーサビリティ、raw に対する日付選定等）。
- 外部ライブラリへの依存を最小限にする方針（標準ライブラリ + duckdb + defusedxml のみを使用する設計方針がコメントで明記）。
- 一部の仕様はコメントとして未実装箇所を明示：
  - signal_generator._generate_sell_signals 内にトレーリングストップや時間決済など未実装の条件がコメントで記載（positions テーブルに peak_price / entry_date が必要）。
- data.stats.zscore_normalize を前提にした設計（当該ユーティリティは別モジュールで提供される想定）。

### Known issues / Limitations
- SELL の追加条件（トレーリングストップ、時間決済）は未実装。将来的に positions テーブルの拡張（peak_price, entry_date 等）が必要。
- 一部の入力検証やエッジケース処理はログ出力で警告してスキップする実装（例: PK 欠損行のスキップ、無効な weights のスキップ）。運用に応じてより厳格なエラー処理を検討してください。
- 外部 API の仕様変更（J-Quants 側）やネットワーク環境によっては追加のエラーハンドリングが必要となる場合があります。

---

出典 / 参考:
- Keep a Changelog: https://keepachangelog.com/ja/1.0.0/
- 各モジュールの docstring とコードコメントに基づき要約・整理しています。