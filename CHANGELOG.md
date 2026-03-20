# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の方針に従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-20
初回リリース。主な追加機能・実装内容は以下のとおりです。

### Added
- パッケージ基盤
  - パッケージメタ情報: kabusys/__init__.py にバージョン "0.1.0" を追加。公開 API として data, strategy, execution, monitoring をエクスポート。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート検出: .git または pyproject.toml を起点にルートを自動検出（カレントディレクトリ非依存）。
  - .env 解析器を実装し、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの処理に対応。
  - 自動ロード優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化が可能。
  - Settings クラスで主要設定をプロパティとして提供（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、環境・ログレベル検証など）。
  - 環境値の検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）と必須項目未設定時のエラー報告。

- データ取得・保存: J-Quants クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装（認証、ページネーション対応のfetch、保存関数）。
  - レート制限 (120 req/min) を固定間隔スロットリングで制御する RateLimiter を導入。
  - 冪等性のため DuckDB への保存は ON CONFLICT を用いた upsert を利用（raw_prices / raw_financials / market_calendar）。
  - リトライ戦略を実装（最大3回、指数バックオフ、408/429/5xx を対象）。429 の場合は Retry-After ヘッダを優先。
  - 401 を検知した場合の自動トークンリフレッシュ（1 回のみ）と ID トークンのモジュールレベルキャッシュ。
  - データ変換ユーティリティ（_to_float, _to_int）を追加。PK 欠損レコードはスキップし警告を出力。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集モジュールを実装（デフォルトに Yahoo Finance のカテゴリRSSを含む）。
  - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ除去（utm_*, fbclid 等）、フラグメント削除、クエリ並べ替え。
  - セキュリティ対策: defusedxml を使用した XML パース、受信サイズ上限(MAX_RESPONSE_BYTES)、HTTP/HTTPS 以外のスキーム拒否や SSRF 緩和の設計方針を採用。
  - 記事ID を URL 正規化後の SHA-256 によるハッシュ（先頭32文字など）で生成して冪等性を確保。
  - DB 保存はバルク挿入をチャンク化して効率化、ON CONFLICT DO NOTHING により重複を排除。

- リサーチ（factor 計算・探索） (kabusys.research)
  - factor_research モジュールでモメンタム（1/3/6M、MA200乖離）、ボラティリティ（ATR20/相対ATR/出来高関連）、バリュー（PER/ROE）等のファクター計算を実装。すべて DuckDB の prices_daily / raw_financials を参照。
  - feature_exploration にて将来リターン計算（複数ホライズン対応）、IC（Spearman のρ）計算、ファクター統計サマリー、ランク変換ユーティリティを実装。外部依存を避け、標準ライブラリ + DuckDB で実装。
  - 計算窓・スキャン日数などの定数（MA200 等）を定義し、営業日ベースやカレンダー日バッファを考慮した実装。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - 研究モジュールで算出した生ファクターを結合・ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円）を適用。
  - 指定カラムに対して Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
  - features テーブルへの日付単位アップサート（トランザクションで原子性を保証）を実装。冪等。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。シグモイド変換や平均化ロジックを実装。
  - デフォルト重み・閾値を実装（デフォルト final_score 閾値 = 0.60）。ユーザー定義 weights の入力検証（キー制限、非数値/負値の排除、正規化）を実装。
  - Bear レジーム検知（ai_scores の regime_score 平均が負かつサンプル数閾値以上）に基づく BUY 抑制。
  - SELL シグナル（エグジット）判定を実装: ストップロス（終値/avg_price - 1 < -8%）、スコア低下（final_score < threshold）。保有銘柄の価格欠損時には SELL 判定をスキップして安全性を確保。
  - BUY / SELL の signals テーブルへの日付単位置換（トランザクションで原子性）を実装。SELL が BUY より優先されるポリシーを適用。
  - 欠損コンポーネントは中立値（0.5）で補完し、欠損による不当な評価低下を防止。

### Security
- news_collector で defusedxml を用いた安全な XML パースを採用。
- RSS 取得時の受信上限や URL 正規化で SSRF / メモリ DoS リスクを軽減。
- J-Quants クライアントでレート制御・リトライロジック・トークンリフレッシュを実装し、過負荷・認証エラーに対処。

### Notes (既知の制限 / TODO)
- signal_generator の追加エグジット条件（トレーリングストップ、時間決済）は comments に未実装として記載。positions テーブルに peak_price / entry_date が必要。
- research モジュールは外部ライブラリ（pandas 等）に依存せず実装されているため、大規模データでのパフォーマンスは今後の改善余地あり。
- news_collector の記事 ID はコメントに設計意図あり（SHA-256 の先頭など） — 実運用での詳細は確認が必要。

### Breaking Changes
- 初回リリースのため該当なし。

---

注: 各モジュールには詳細な docstring とログ出力が含まれており、関数単位での使用方法（引数・返値）や設計方針が明記されています。必要であれば、各モジュール別の CHANGELOG（機能追加・バグ修正の粒度を細かくしたもの）を追記できます。