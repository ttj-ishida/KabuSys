# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
この CHANGELOG は「Keep a Changelog」仕様に準拠しており、セマンティックバージョニングを使用します。

現在の日付: 2026-03-20

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-20
初回リリース。日本株の自動売買・データ基盤向けに以下の主要コンポーネントを実装しました。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージ初期化 (バージョン 0.1.0)。公開 API: data, strategy, execution, monitoring を __all__ に定義。

- 設定 / 環境読み込み
  - 環境変数／.env 管理モジュールを実装（kabusys.config）。
  - プロジェクトルートを .git または pyproject.toml から自動検出して .env / .env.local を自動読み込み（優先順位: OS 環境 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応（テスト用途）。
  - .env パーサ実装: export 句、クォート（シングル／ダブル）、エスケープ、インラインコメントなどに対応。
  - Settings クラスで必須環境変数取得（_require）と検証を提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - 環境値検証: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）の検証ロジック。

- データ取得・保存（J-Quants クライアント）
  - J-Quants API クライアントを実装（kabusys.data.jquants_client）。
  - レート制限対応: 固定間隔スロットリングで 120 req/min を守る RateLimiter 実装。
  - 再試行ロジック（指数バックオフ、最大 3 回）と HTTP ステータスに基づく挙動（408/429/>=500 をリトライ対象）。
  - 401 応答時の自動トークンリフレッシュ（1 回のみ）を実装。モジュールレベルで ID トークンをキャッシュ。
  - ページネーション対応（fetch_daily_quotes / fetch_financial_statements）。
  - DuckDB への冪等保存ユーティリティを実装（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT を使った更新を行う。
  - データ整形ユーティリティ: safe な数値変換関数 _to_float, _to_int。
  - 取得時に fetched_at を UTC ISO8601 (Z) で記録（Look-ahead バイアスの可視化に配慮）。

- ニュース収集
  - RSS ニュース収集モジュール（kabusys.data.news_collector）を実装。
  - URL 正規化: トラッキングパラメータ（utm_*, fbclid 等）除去、クエリソート、フラグメント除去、小文字化。
  - 記事 ID は正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を確保。
  - defusedxml を使った安全な XML パース、受信最大サイズ制限（MAX_RESPONSE_BYTES = 10MB）、HTTP スキーム検証等によりセキュリティを意識した実装。
  - DB 挿入はバルク＆チャンク化（_INSERT_CHUNK_SIZE=1000）で効率化。raw_news / news_symbols 等への保存を想定。

- 研究（research）モジュール
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - Value（per, roe）: raw_financials と prices_daily を組み合わせて計算
    - 各関数は DuckDB 接続を受け取り SQL を駆使して高効率に計算（外部ライブラリに依存しない）
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、ホライズン検証あり）
    - IC（Information Coefficient）計算 calc_ic（Spearman の ρ、最小サンプル数チェック）
    - 基本統計量を返す factor_summary、順位付け用の rank ユーティリティ
  - zscore_normalize を利用するための公開エクスポートを整備（kabusys.research.__init__）。

- 特徴量エンジニアリング（strategy）
  - build_features 実装（kabusys.strategy.feature_engineering）
    - research モジュールから生ファクターを取得し、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 指定カラムに対する Z スコア正規化、±3 でクリップ。
    - features テーブルへの日次単位の置換（削除→挿入）で冪等性と原子性を確保（トランザクション使用）。
    - DuckDB を前提にした SQL クエリで直近の終値参照や bulk insert を実行。

- シグナル生成（strategy）
  - generate_signals 実装（kabusys.strategy.signal_generator）
    - features と ai_scores を統合して銘柄ごとに final_score を計算（momentum/value/volatility/liquidity/news の重み付け）。
    - デフォルト重みと閾値（デフォルト閾値 0.60）を提供。ユーザー指定の weights は検証／正規化して合計が 1.0 になるようスケーリング。
    - SIGMOID / Z スコアの扱い、コンポーネントが欠損した場合は中立値 0.5 で補完するポリシー。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合に BUY を抑制、サンプル閾値あり）。
    - エグジット（SELL）判定: ストップロス（損益率 <= -8%）および final_score の閾値割れ。
    - SELL を優先して BUY から除外、signals テーブルへ日次単位で置換して保存（トランザクションを使用）。
    - signals / positions / prices_daily / ai_scores を参照。

### 変更 (Changed)
- （初回リリースのため過去からの変更はなし。設計上の注意点やポリシーを明記。）

### 修正 (Fixed)
- （初回リリースのためなし）

### セキュリティ (Security)
- XML パースに defusedxml を採用し XML Bomb 等のリスクを軽減。
- ニュース収集で SSRF 対策（HTTP/HTTPS スキームのみ許可）や受信サイズ上限を設け、メモリ DoS を防止。
- J-Quants クライアントはトークンの自動リフレッシュとリトライ制御を取り入れ、認証失敗時の安全な再試行を行う。

### 既知の制約 / 注意点 (Notes)
- execution パッケージは空の初期プレースホルダ（発注レイヤーはまだ実装されていない）。
- データベースは DuckDB を前提とした SQL を多用（DuckDBPyConnection が必要）。
- research モジュールは pandas 等の外部データ解析ライブラリに依存しない設計のため、配列処理は純粋 Python / SQL ベースで実装されている。
- features / signals 等のテーブルスキーマはコードの期待に合わせて事前に用意しておく必要がある（raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals, raw_news 等）。
- 一部の SELL 条件（トレーリングストップ、時間決済）は未実装で、positions テーブルに peak_price / entry_date 等の情報が必要。

---

開発者向け補足:
- ログ出力は各モジュールで logger を使用しており、Settings.log_level による制御を想定しています。
- J-Quants API のレート制限やリトライの挙動は _MIN_INTERVAL_SEC / _MAX_RETRIES / _RETRY_BACKOFF_BASE 等の定数で調整可能です。
- テスト時に環境自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

（以上）