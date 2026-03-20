# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースから推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-20

### Added
- パッケージ初期リリース "KabuSys"（src/kabusys）。パッケージメタ情報として `__version__ = "0.1.0"` を設定し、public API として data / strategy / execution / monitoring をエクスポート。
- 環境変数・設定管理モジュール（src/kabusys/config.py）
  - .env / .env.local から設定を自動ロード（OS 環境変数が優先）。プロジェクトルート検出は `.git` または `pyproject.toml` を基準に行うため、カレントディレクトリに依存しない動作。
  - `.env` の行パーサを実装（コメント・export プレフィックス・シングル/ダブルクォート・エスケープ対応、インラインコメントの扱いなどを考慮）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途想定）。
  - Settings クラスを提供。必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）取得用プロパティ、デフォルト値（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等）、環境値検証（KABUSYS_ENV, LOG_LEVEL）を含む。
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - レート制限対応（120 req/min）用の固定間隔スロットリング RateLimiter を実装。
  - リトライロジック（指数バックオフ、最大 3 回）および 408/429/5xx などへの再試行処理を実装。429 の場合は Retry-After ヘッダを優先。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュを実装。
  - ページネーション対応の fetch 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）を実装。
  - DuckDB への保存用ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。insert の冪等性を保証するため ON CONFLICT（アップサート）を使用。
  - データ変換ユーティリティ `_to_float` / `_to_int` を実装し、入力の堅牢なパースを提供。取得時刻（fetched_at）は UTC で記録。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を取得し raw_news に保存するための実装。既定の RSS ソースに Yahoo Finance を含む。
  - セキュリティとデータ品質の対策を導入：defusedxml を利用した XML パース、受信サイズ制限（MAX_RESPONSE_BYTES=10MB）、記事 ID を正規化 URL の SHA-256 ハッシュで生成する方針、トラッキングパラメータ（utm_* 等）の除去、URL 正規化、バルク INSERT チャンク分割、ON CONFLICT DO NOTHING による冪等性確保。
  - HTTP/HTTPS スキームの扱い・トラッキング除去・テキスト前処理（URL 除去・空白正規化）等のユーティリティを含む。
- リサーチ機能（src/kabusys/research/）
  - ファクター計算モジュール（factor_research.py）：momentum / volatility / value を計算する関数（calc_momentum / calc_volatility / calc_value）を実装。複数のウィンドウ長（例: 1M/3M/6M, MA200, ATR20, 20日平均売買代金 等）と欠損処理を考慮。
  - 特徴量探索モジュール（feature_exploration.py）：将来リターン計算（calc_forward_returns）、IC（スピアマンランク相関）計算（calc_ic）、統計サマリー（factor_summary）、ランク関数（rank）を提供。外部依存を避け、標準ライブラリ/SQL ベースで実装。
  - 研究用 API を kabusys.research パッケージで再公開。
- 戦略モジュール（src/kabusys/strategy/）
  - 特徴量エンジニアリング（feature_engineering.build_features）
    - research モジュールの生ファクターを取得し、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - Z スコア正規化（外部 zscore_normalize を利用）、±3 でクリップ、features テーブルへ日付単位で置換（トランザクション＋バルク挿入による原子性）して冪等性を確保。
  - シグナル生成（signal_generator.generate_signals）
    - features / ai_scores / positions を参照して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を計算し、重み付き合算で final_score を算出（デフォルト重みを備える）。
    - AI スコアの regime_score による Bear レジーム判定（市場平均が負なら Bear と判定、ただしサンプル数が閾値未満なら判定を行わない）。
    - Bear レジーム時は BUY シグナルを抑制、BUY は閾値（デフォルト 0.60）以上で生成。エグジット（SELL）はストップロス（-8%）およびスコア低下で判定。
    - 欠損コンポーネントは中立値 0.5 で補完、ユーザー指定重みは検証・正規化（合計が 1 になるよう再スケール）して採用。
    - signals テーブルへ日付単位で置換して保存（原子性保証）。
- execution / monitoring 用の名前空間を用意（src/kabusys/execution/__init__.py が存在）。実装は今後追加予定。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- ニュース収集における XML パースに defusedxml を採用し、XML BOM や潜在的攻撃を軽減。
- RSS URL の正規化とトラッキングパラメータの除去、受信サイズ制限などでメモリ DoS /トラッキングの影響を低減する設計。

### Notes / Known limitations
- signal_generator のエグジット条件について、ドキュメントで言及されている「トレーリングストップ（直近最高値から -10%）」および「時間決済（60 営業日超過）」は未実装（positions テーブルに peak_price / entry_date 情報が必要）。
- value ファクターでは PBR や配当利回りは未実装（docstring に明記）。
- news_collector の一部セキュリティ（例: SSRF/IP ブロック等）の追加対策は意図されているが、表示されたコード断片では実装詳細が限定的な箇所があるため、運用前に総合的なレビューを推奨。
- DuckDB スキーマ（raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals 等）は本リリースで前提となるため、マイグレーション / スキーマ定義が別途必要。

### Internal / Implementation notes
- 多くの処理で「ルックアヘッドバイアスを防ぐ」方針を採用（target_date 時点のみのデータ参照、fetched_at を UTC 記録等）。
- DB 書き込み操作はトランザクションとバルク挿入を基本として原子性と性能を考慮。
- ロギング（logger）を各モジュールで使用し、警告・情報を出力する設計。

---

貢献・バグ報告・機能要望はリポジトリの Issue を通じて受け付けてください。