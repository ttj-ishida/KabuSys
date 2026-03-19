# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-19
初回公開リリース。日本株自動売買システムの基本機能を実装しています。以下はコードベースから推測される主要な追加点・設計方針の要約です。

### Added
- パッケージ基盤
  - kabusys パッケージの初期実装。トップレベルで data / strategy / execution / monitoring をエクスポート。
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 設定・環境変数管理（src/kabusys/config.py）
  - .env/.env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサの実装: export 構文、クォート、エスケープ、インラインコメント処理に対応。
  - OS 環境変数を保護する protected ロジック（.env.local は override=True）。
  - Settings クラスを提供し、アプリケーションで利用する必須設定をプロパティとして取得（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
  - 環境チェック（KABUSYS_ENV の有効値検証、LOG_LEVEL 検証）とユーティリティプロパティ（is_live / is_paper / is_dev）。

- データ取得・保存（src/kabusys/data/）
  - J-Quants クライアント（src/kabusys/data/jquants_client.py）
    - API 呼び出しラッパー: 固定間隔レートリミッタ（120 req/min）、最大リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ（1 回）。
    - ページネーション対応 fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - DuckDB へ冪等で保存する save_* 関数（raw_prices / raw_financials / market_calendar）— ON CONFLICT / DO UPDATE による重複排除。
    - レスポンスの JSON デコード例外処理・ログ出力、型変換ユーティリティ (_to_float / _to_int)。
    - fetched_at を UTC で記録し、look-ahead bias 対策を考慮。

  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS 取得→前処理→raw_news 登録のフローを実装。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホストの小文字化、フラグメント削除、クエリソート）。
    - セキュリティ対策: defusedxml による XML Bomb 防止、HTTP スキームチェック、受信サイズ上限（MAX_RESPONSE_BYTES）によるメモリ DoS 対策、SSRF 対策を意識した実装。
    - 冪等性を考慮した ID 生成（正規化 URL のハッシュ等を想定）とバルク挿入のチャンク処理。

- リサーチ用モジュール（src/kabusys/research/）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、MA200 乖離率）、Volatility（20日 ATR、相対ATR、出来高比率、平均売買代金）、Value（PER、ROE）を DuckDB の prices_daily / raw_financials を参照して計算。
    - 営業日ベースの窓処理を SQL で実装、データ不足時は None を返す設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（複数ホライズン、範囲チェック）、IC（Spearman の ρ）計算、統計サマリー、ランク付けユーティリティを実装。
    - 外部ライブラリに依存せず標準ライブラリ + duckdb を想定した実装。
  - モジュールレベルで便利関数を再エクスポート（zscore_normalize 等）。

- 戦略モジュール（src/kabusys/strategy/）
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research モジュールの生ファクターを取り込み、ユニバースフィルタ（最低株価、平均売買代金）を適用、数値ファクターを Z スコア正規化して ±3 でクリッピング、features テーブルへ日付単位で UPSERT（トランザクションで原子性確保）。
    - ユニバースフィルタの閾値はコード内定数（最低価格 300 円、平均売買代金 5 億円 等）。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - シグナル生成ロジック: final_score（重み付き合算、デフォルト重みを定義）、Bear レジーム抑制（ai_scores の regime_score 平均で判定）、BUY（閾値 0.60）／SELL（ストップロス -8% / スコア低下）を生成。
    - positions / prices_daily を参照したエグジット判定、SELL を優先して signals テーブルへ日付単位で置換（トランザクション実行）。
    - 重みの入力検証・正規化ロジック（負値/非数は無視、合計が 1 でない場合はスケール補正）。

- 公開 API の整理
  - strategy.__init__ で build_features / generate_signals をエクスポート。
  - research.__init__ に主要関数をエクスポート。

### Changed
- （初版につき該当なし）

### Fixed
- （初版につき該当なし）

### Security
- news_collector: defusedxml の使用、応答サイズ制限、スキームチェックなどで XML Bomb / SSRF / メモリ DoS 対策を実装。
- jquants_client: トークンリフレッシュ周りで無限再帰を防ぐ設計（allow_refresh フラグ）。

### Notes / Design decisions
- DuckDB をデータ層に採用し、クエリ中心の処理（SQL + 必要な Python ロジック）でファクター計算・集約を実施。多くの処理は SQL ウィンドウ関数で実装されているため大量データの一括処理に適する設計。
- Look-ahead bias を避けるため、各処理は target_date 時点までのデータのみを参照し、fetched_at を UTC で記録する等の配慮がある。
- 冪等性を重視（DB への INSERT は ON CONFLICT、signals/features は日付単位で DELETE→INSERT のトランザクション置換）。
- 外部依存は最小化（標準ライブラリ + duckdb、defusedxml を使用）。Pandas 等の大型依存は避ける設計。
- 環境変数周りはテストしやすいように KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。

### Known / TODO (コード内コメントより推測)
- signal_generator の SELL 条件で未実装の一部（トレーリングストップ・時間決済）は positions テーブルに peak_price / entry_date 等の追加が必要。
- 一部レコード欠損時の扱い（features に存在しない保有銘柄は final_score=0.0 として扱う等）はログ出力とともに保守運用での検討を推奨。

---

今後のリリースでは、execution（発注実装）および monitoring（監視・アラート）周りの実装、テストカバレッジの拡充、ドキュメント（StrategyModel.md / DataPlatform.md 等）の反映・整備が想定されます。