# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
フォーマット: 変更はセクションごとに分類（Added / Changed / Fixed / Security / Removed / Notes）。  
バージョンはパッケージ内の __version__ に合わせて "0.1.0" を初回リリースとして記載しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-20
最初の公開リリース。日本株自動売買システムのコアライブラリを実装しました。主要な機能群（データ収集・保存、ファクター計算、特徴量エンジニアリング、シグナル生成、リサーチユーティリティ、および環境設定管理）を含みます。

### Added
- パッケージ情報
  - パッケージ初期化: `kabusys.__version__ = "0.1.0"`
  - エクスポート: data, strategy, execution, monitoring を公開。

- 環境設定/ロード (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルート判定: .git または pyproject.toml）。
  - .env / .env.local の優先順位実装 (.env.local は上書き、OS 環境変数は保護)。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグ。
  - .env 行パーサの実装:
    - コメント・空行スキップ
    - export KEY=val 形式をサポート
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理
    - クォートなしのインラインコメント処理
  - Settings クラスで必須設定取得メソッド（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）と検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）を提供。
  - データベースパス（DUCKDB_PATH, SQLITE_PATH）を Path 型で取得。

- データ取得・保存（J-Quants クライアント） (`kabusys.data.jquants_client`)
  - J-Quants API クライアント実装（取得対象: 日足、財務、マーケットカレンダー）。
  - レート制限対策: 固定間隔スロットリングによる _RateLimiter（120 req/min）。
  - リトライロジック: 指数バックオフ・最大 3 回、408/429/5xx を再試行対象。
  - 401 応答時のトークン自動リフレッシュ（1 回のみ）を実装。
  - ページネーション対応（pagination_key を用いたループ取得）。
  - DuckDB への保存関数:
    - save_daily_quotes (raw_prices) / save_financial_statements (raw_financials) / save_market_calendar (market_calendar)
    - 冪等性を確保するため ON CONFLICT DO UPDATE を使用
    - fetched_at を UTC ISO8601 形式で記録
    - 型変換ユーティリティ（_to_float, _to_int）を実装
    - PK 欠損レコードのスキップとログ警告

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィード収集の基盤実装（デフォルトに Yahoo Finance の RSS を設定）。
  - テキスト前処理（URL 除去・空白正規化）と URL 正規化処理の実装:
    - トラッキングパラメータ（utm_, fbclid, gclid 等）除去
    - スキーム/ホスト小文字化、フラグメント除去、クエリソート
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等への防御）
    - 最大受信バイト数制限（MAX_RESPONSE_BYTES = 10MB）
    - SSRF を避けるために非 http/https スキーム拒否（設計方針）
  - 記事 ID の生成は URL 正規化後の SHA-256（先頭 32 文字）を想定（冪等性を確保）。
  - バルク挿入のチャンク処理、トランザクションまとめ、INSERT RETURNING を活用する設計（実装方針・性能配慮）。

- リサーチユーティリティ (`kabusys.research`)
  - 特徴量探索機能:
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト 1,5,21 営業日）で将来リターンを計算。1 クエリでリード（LEAD）を使用して取得。
    - calc_ic: スピアマンのランク相関（IC）を計算（結合・欠損除外・サンプル不足時 None）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 同順位（ties）を平均ランクとして扱うランク変換ユーティリティ（浮動小数の丸め対策あり）。
  - 研究モジュールをまとめてエクスポート。

- ファクター計算 (`kabusys.research.factor_research`)
  - Momentum ファクター: mom_1m, mom_3m, mom_6m, ma200_dev（200 日移動平均乖離）。ウィンドウ不足時は None。
  - Volatility / Liquidity ファクター: atr_20, atr_pct, avg_turnover, volume_ratio（ATR の NULL 伝播制御、ウィンドウ不足時 None）。
  - Value ファクター: per, roe（raw_financials の target_date 以前の最新財務データを参照）。
  - SQL ベースで DuckDB のウィンドウ関数を活用し、営業日欠損（祝日・週末）に対応するバッファを確保。

- 特徴量エンジニアリング (`kabusys.strategy.feature_engineering`)
  - research モジュールで計算した生ファクターを取得し、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
  - 数値ファクターを zscore_normalize で正規化し ±3 でクリップ。
  - features テーブルへ日付単位で置換（DELETE + INSERT をトランザクションで実行し原子性を保証）。
  - ルックアヘッドバイアスを避ける設計（target_date 時点のデータのみ使用）。

- シグナル生成 (`kabusys.strategy.signal_generator`)
  - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
  - s_news は AI スコアのシグモイド、未登録時は中立値を補完。
  - final_score は重み付き和（デフォルト重みを実装）を計算。weights 入力は検証・正規化され、合計が 1.0 になるよう再スケーリング。
  - Bear レジーム判定（ai_scores の regime_score 平均が負且つサンプル数閾値以上で Bear と判定）による BUY 抑制。
  - BUY シグナルの閾値（デフォルト 0.60）を超える銘柄に BUY を生成（Bear 時は抑制）。
  - SELL（エグジット）判定:
    - ストップロス（終値 / avg_price - 1 < -8%）
    - スコア低下（final_score < threshold）
    - 保有銘柄の価格欠損時は SELL 判定をスキップ（安全策）
    - features に存在しない保有銘柄は final_score = 0.0 と見なす
  - BUY/SELL を signals テーブルへ日付単位置換（トランザクション処理）。
  - SELL 優先ポリシー（SELL 対象は BUY から除外、BUY は再ランク付け）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュース収集で defusedxml を使用し XML パース攻撃を軽減。
- RSS 応答の最大受信サイズ制限（メモリ DoS 対策）。
- ニュース URL 正規化でトラッキングパラメータ削除・フラグメント削除を実施。
- J-Quants クライアントでネットワークエラーや HTTP エラーに対して安全な再試行制御を実装。

### Removed
- （初回リリースのため該当なし）

### Notes / Known limitations
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済など）は設計に記載されているが、現行コードでは未実装。positions テーブルに peak_price / entry_date 等が必要。
- news_collector の DB 保存の具体的 SQL 実装や記事→銘柄紐付けロジックは設計で述べられているが、一部は将来的な拡張想定。
- calc_forward_returns はホライズンを営業日ベースで扱う前提だが、入力の営業日データが不完全な場合は期待通りに動作しない可能性がある（DuckDB の prices_daily テーブルの整備が前提）。
- 本パッケージは DuckDB と J-Quants API の利用を想定しています。外部環境（API トークン、DB ファイルパス、Slack 設定など）は Settings により環境変数で指定してください。

---

メンテナンスや追加機能の計画、バグ修正・セキュリティ修正は今後リリースノートで逐次公開します。必要であれば、各モジュールの詳細設計・使用例を CHANGELOG に付加することも可能です。