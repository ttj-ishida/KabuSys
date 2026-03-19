# CHANGELOG

すべての重要な変更をここに記載します。フォーマットは「Keep a Changelog」に準拠しています。

注意: このリポジトリはバージョン 0.1.0 が初回リリース相当の状態です。以下はソースコードから推測して作成した機能一覧・変更点・既知の制限事項です。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-03-19
初回公開リリース

### 追加
- パッケージ基盤
  - kabusys パッケージの基礎構成を追加。__version__ = "0.1.0"、主要サブパッケージ（data, strategy, execution, monitoring）を __all__ に公開。

- 環境変数 / 設定管理
  - kabusys.config モジュールを追加。
    - .env / .env.local をプロジェクトルートから自動ロード（CWDに依存しない探索、.git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env パーサーは export 形式、クォート処理、インラインコメント処理をサポート。
    - Settings クラスを公開し、J-Quants / kabuステーション / Slack / DB パスなどの設定をプロパティ経由で取得。必須キーは未設定時に ValueError を発生させる。
    - 環境（development / paper_trading / live）およびログレベルの妥当性チェックを実装。

- データ収集・保存（data モジュール）
  - J-Quants API クライアント（kabusys.data.jquants_client）
    - API レート制御（120 req/min 固定間隔スロットリング）を実装。
    - リトライ（指数バックオフ、最大 3 回）と HTTP ステータスに基づく再試行ポリシーを実装（408, 429, 5xx を対象）。
    - 401 Unauthorized 時はリフレッシュトークンから id_token を再取得して 1 回だけリトライする処理を実装（トークンキャッシュの仕組みあり）。
    - ページネーション対応（pagination_key を用いたループ）。
    - データ変換ユーティリティ（文字列→float/int の安全な変換）。
    - DuckDB へ冪等的に保存する関数を提供（raw_prices / raw_financials / market_calendar に対して ON CONFLICT DO UPDATE、挿入件数のログ出力）。

  - ニュース収集（kabusys.data.news_collector）
    - RSS フィードから記事を収集し raw_news に冪等保存する処理を実装。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除、小文字化）を実装。
    - defusedxml を使った XML パース（安全対策）、HTTP スキーム検証、受信サイズ上限（10MB）などのセキュリティ対策を実装。
    - 記事IDは正規化 URL の SHA-256 の先頭などで生成する方針（冪等性確保）。
    - バルク挿入のチャンク化等によるパフォーマンス配慮。

- 研究（research モジュール）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）、Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）、Value（per, roe）等の計算関数を実装。
    - DuckDB の window/OVER 句を活用した効率的な SQL ベース計算。
    - データ不足時の None 処理やスキャン範囲バッファ（カレンダー日での余裕）等の設計。

  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターンの計算（calc_forward_returns: 複数ホライズン対応、SQLで一括取得）を実装。
    - IC（Information Coefficient）計算（スピアマンのランク相関）を実装。ties（同順位）は平均ランクで処理。
    - カラム単位の統計サマリー（count/mean/std/min/max/median）を実装。
    - 決定的なランク付けユーティリティ rank を提供。

  - research パッケージの __all__ に主要関数群を公開。

- 戦略（strategy モジュール）
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - 研究環境で計算した生ファクターを取り込み、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - 数値ファクターを Z スコア正規化（kabusys.data.stats の zscore_normalize 利用）し ±3 でクリップ。
    - features テーブルへ日付単位で冪等 upsert（DELETE→INSERT をトランザクションで実施）する build_features を実装。

  - シグナル生成（kabusys.strategy.signal_generator）
    - features と ai_scores を統合しコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出、重み付き合算で final_score を計算。
    - デフォルト重みと閾値（DEFAULT_THRESHOLD=0.60）を実装。ユーザ指定 weights の妥当性チェックと再スケーリングを行う。
    - Bear レジーム判定（AI の regime_score の平均が負かつサンプル数十分）による BUY 抑制。
    - BUY/SELL シグナルの生成と signals テーブルへの日付単位置換（トランザクション＋バルク挿入）を実装。
    - エグジット判定（ストップロス -8% / スコア低下）を実装。価格欠損時の判定スキップや features に存在しない保有銘柄は final_score=0 として扱う等の安全策あり。

- API エクスポート
  - strategy パッケージで build_features, generate_signals を __all__ にて公開。

### セキュリティ（一部は設計方針として明示）
- XML パースに defusedxml を使用して XML Bomb 等を防止。
- RSS URL と HTTP レスポンス処理で SSRF / メモリDoS を想定した対策（スキームチェック、最大受信バイト数）を適用。
- .env 読み込みで OS 環境変数を保護するため protected セットを使用（.env.local は上書き可だが OS 環境は保護）。

### 既知の制限 / 未実装項目
- strategy のエグジット条件における以下は未実装（コードコメントに記載）:
  - トレーリングストップ（peak_price が positions に必要）
  - 時間決済（保有 60 営業日超過）
- execution パッケージは存在するが実装ファイルは本差分には含まれていない（発注層への依存は戦略モジュールで排除する方針）。
- monitoring モジュールは __all__ に含まれているが、実装が未検出（将来追加予定）。
- news_collector の記事 ID 生成やニュース→銘柄紐付けの詳細実装は方針が示されているが、全文実装の有無はソースの残り（ここで提供された断片）による。
- settings.jquants_refresh_token 等の必須環境変数は未設定の場合エラーとなるため、導入時に .env の整備が必要。

### その他の注意事項 / 運用メモ
- J-Quants API クライアントは rate limiter と retry/backoff を含むため、API レートに配慮した運用が可能。
- DuckDB を用いた SQL 主導のデータ処理設計により、ローカル DB ファイル（デフォルト data/kabusys.duckdb）を用いた分析・バッチ処理が想定されている。
- 環境変数の自動ロードはプロジェクトルートの検出に依存するため、配布後やインストール環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して制御可能。

---

翻訳・要約はソースコードのコメントおよび実装から推測して作成しています。リポジトリの他ファイルや将来のコミットにより内容が変わる可能性があります。追加でリリースノート形式の修正や、より詳細な「導入手順」「DB スキーマ要件」「環境変数一覧」を作成することも可能です。必要であれば作成します。