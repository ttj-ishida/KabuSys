# CHANGELOG

すべての重要な変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-21

初回リリース。以下の主要機能・モジュールを追加しました。

### Added
- 基本パッケージ構成を追加
  - ファイル: src/kabusys/__init__.py
  - 内容: バージョン定義（__version__ = "0.1.0"）と公開サブパッケージ宣言（data, strategy, execution, monitoring）。

- 環境設定管理
  - ファイル: src/kabusys/config.py
  - 内容: .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動読み込み（.env → .env.local の優先度）。
    - 高度な .env パーサ（コメント、export 形式、シングル/ダブルクォート、エスケープ処理をサポート）。
    - 上書き制御（override/protected）および KABUSYS_DISABLE_AUTO_ENV_LOAD フラグで自動ロード無効化可能。
    - 必須項目検査（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_* 等）と値検証（KABUSYS_ENV, LOG_LEVEL）。
    - SQLite / DuckDB ファイルパスプロパティ。

- J-Quants API クライアント
  - ファイル: src/kabusys/data/jquants_client.py
  - 内容:
    - レートリミッタ（120 req/min）を実装し固定間隔スロットリングで制御。
    - HTTP retry（指数バックオフ、最大3回）。408/429/5xx をリトライ対象。429 の場合は Retry-After を尊重。
    - 401 受信時にリフレッシュトークンから自動で id_token を再取得して 1 回リトライ。
    - ページネーション対応の fetch_* API（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT を用いた更新。
    - 型変換ユーティリティ (_to_float, _to_int)、UTC タイムスタンプ記録（fetched_at）。
    - モジュールレベルの id_token キャッシュを実装（ページ間共有）。

- ニュース収集モジュール（RSS）
  - ファイル: src/kabusys/data/news_collector.py
  - 内容:
    - RSS 取得→正規化→raw_news へ冪等保存するワークフローの実装。
    - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント除去、小文字化）と記事 ID のハッシュ化で冪等性を確保。
    - defusedxml を用いた安全な XML パース、受信サイズ制限（MAX_RESPONSE_BYTES=10MB）、挿入のチャンク化で DoS やメモリ負荷を軽減。
    - デフォルト RSS ソースの定義（例: Yahoo Finance）。

- 研究（Research）モジュール
  - ファイル: src/kabusys/research/factor_research.py, src/kabusys/research/feature_exploration.py, src/kabusys/research/__init__.py
  - 内容:
    - factor_research: モメンタム / ボラティリティ / バリューを計算する calc_momentum, calc_volatility, calc_value を実装。DuckDB の SQL ウィンドウ関数を活用。
    - feature_exploration: 将来リターン計算(calc_forward_returns)、IC（Spearman の ρ）計算(calc_ic)、ファクター統計要約(factor_summary)、ランク付け(rank)を提供。
    - 研究向けに外部依存を避け標準ライブラリと DuckDB のみで実装。

- 特徴量エンジニアリング（本番側）
  - ファイル: src/kabusys/strategy/feature_engineering.py
  - 内容:
    - research モジュールで算出した生ファクターを結合し、ユニバースフィルタ（最低株価・20日平均売買代金）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへの日付単位の置換（DELETE + bulk INSERT）で冪等性と原子性を保証。

- シグナル生成（戦略）
  - ファイル: src/kabusys/strategy/signal_generator.py
  - 内容:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum, value, volatility, liquidity, news）を計算。
    - コンポーネントを重み付け合算して final_score を算出（デフォルト重みを定義）。weights の検証・正規化処理を実装。
    - Bear レジーム検知（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）により BUY を抑制。
    - BUY（threshold デフォルト 0.60）と SELL（ストップロス -8% / スコア低下）を生成。
    - positions / prices の参照により売却判定を行い、signals テーブルへ日付単位の置換で保存。
    - トランザクションとロールバック処理を実装し、例外時に注意のログ出力。

- 公開 API のエクスポート
  - ファイル: src/kabusys/strategy/__init__.py, src/kabusys/research/__init__.py
  - 内容: build_features, generate_signals, calc_momentum/volatility/value 等をパッケージ外から簡単に利用できるようにエクスポート。

### Fixed
- データ欠損時の堅牢性向上
  - feature_engineering や signal_generator の各処理で、価格やファクターが欠損する場合のスキップ・警告ログを追加。価格欠損時は SELL 判定をスキップして誤クローズを防止。
  - DB トランザクション内での例外発生時に ROLLBACK を試行し、ROLLBACK 自体の失敗をログに出力。

### Security
- 入力/外部データの安全性を強化
  - news_collector: defusedxml を利用し XML 攻撃を防止、受信サイズ制限を設けてメモリ DoS を緩和。
  - jquants_client: 認証トークンの取り扱いをキャッシュで安全に管理し、401 発生時に安全にトークン再取得。

### Notes / Known limitations
- signal_generator のエグジット条件について、コメントの通り以下は未実装:
  - トレーリングストップ（peak_price に基づく -10%）
  - 時間決済（保有 60 営業日超過）
  これらは positions テーブルに peak_price / entry_date 等の情報が必要です。
- news_collector 内でインポートされている ipaddress / socket などは今後の SSRF/IP検証処理に備えた準備で、現バージョンでは一部未使用箇所があります。
- execution と monitoring パッケージは空のプレースホルダ（今後の実装予定）。

---

もし CHANGELOG に追記したいリリース日や細かい差分（例: 具体的な SQL スキーマ、外部 API の仕様変更、互換性に関する注意点など）があれば教えてください。必要に応じて各変更項目をより詳細に分割して記載します。