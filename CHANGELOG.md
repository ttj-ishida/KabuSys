# CHANGELOG

すべての重要な変更をここに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

全般:
- このリポジトリは日本株自動売買システム「KabuSys」の初期リリースを表します。
- 主要な目的はデータ収集（J-Quants / RSS）、ファクター計算、特徴量生成、シグナル生成、および設定管理を提供することです。
- 実際の発注（execution）や外部モニタリング（monitoring）はパッケージのエクスポート対象に含まれますが、発注層はこの段階ではプレースホルダ / 初期実装です。

## [0.1.0] - 2026-03-20

### Added
- パッケージ構成
  - `kabusys` パッケージの初期実装。公開 API として `data`, `strategy`, `execution`, `monitoring` をエクスポート（`execution` は現時点でモジュール初期化のみ）。
  - パッケージバージョンは `0.1.0` に設定。

- 環境設定管理 (`kabusys.config`)
  - `.env` / `.env.local` をプロジェクトルート（`.git` または `pyproject.toml`）から自動ロードする仕組みを実装。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能。
  - `.env` パーサーは以下に対応:
    - コメント行・空行の無視、`export KEY=val` 形式の対応
    - シングル／ダブルクォート内のエスケープ処理
    - クォートなし値のインラインコメント取り扱い（直前が空白/タブの `#` をコメントと判定）
  - アプリケーション設定 (`Settings`) を提供。主要な必須環境変数をプロパティで取得（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`）。
  - `KABUSYS_ENV` と `LOG_LEVEL` の値検証（許容値チェック）・ユーティリティプロパティ（`is_live`, `is_paper`, `is_dev`）。
  - デフォルト DB パス設定 (`DUCKDB_PATH`, `SQLITE_PATH`) をプロパティ経由で提供。

- データ取得 / 保存（J-Quants クライアント） (`kabusys.data.jquants_client`)
  - J-Quants API クライアントを実装:
    - 固定間隔スロットリングによるレート制限（120 req/min）を守る `_RateLimiter`。
    - 再試行ロジック（指数バックオフ、最大 3 回、対象ステータスコード 408/429/5xx）。
    - 401 発生時の ID トークン自動リフレッシュ（1 回のみ）とトークンキャッシュ共有。
    - ページネーション対応のフェッチ関数:
      - `fetch_daily_quotes`（日足 OHLCV）
      - `fetch_financial_statements`（四半期財務）
      - `fetch_market_calendar`（JPX カレンダー）
    - DuckDB への保存関数（冪等化、ON CONFLICT を用いた更新）:
      - `save_daily_quotes` → `raw_prices`
      - `save_financial_statements` → `raw_financials`
      - `save_market_calendar` → `market_calendar`
    - データ変換ユーティリティ `_to_float`, `_to_int`（厳密な変換ルールを定義）。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードから記事を取得して `raw_news` テーブルへ保存するためのユーティリティを実装。
  - セキュリティ／堅牢性設計:
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - 受信サイズ上限（`MAX_RESPONSE_BYTES = 10 MB`）によるメモリ DoS 緩和。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を確保。
    - バルク INSERT のチャンク化（`_INSERT_CHUNK_SIZE`）を導入。
  - デフォルト RSS ソース（例: Yahoo Finance のビジネスカテゴリ）を定義。

- 研究用 / データ処理ユーティリティ (`kabusys.research`, `kabusys.data.stats` を期待)
  - ファクター計算モジュール (`kabusys.research.factor_research`):
    - Momentum ファクター（1M/3M/6M リターン、MA200 乖離）。
    - Volatility / Liquidity ファクター（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）。
    - Value ファクター（PER, ROE：`raw_financials` と `prices_daily` の組合せ）。
    - DuckDB のウィンドウ関数を活用した実装。データ不足時の None ハンドリング。
  - 特徴量探索ユーティリティ (`kabusys.research.feature_exploration`):
    - 将来リターン計算（horizons デフォルト [1,5,21]、単一クエリで取得）。
    - IC（Spearman のランク相関）計算 `calc_ic`。
    - 基本統計量サマリー `factor_summary`。
    - ランキング `rank`（同順位は平均ランク、丸め誤差対策あり）。
  - これらは外部ライブラリに依存せず標準ライブラリ + DuckDB で実装。

- 特徴量生成 / 戦略 (`kabusys.strategy`)
  - 特徴量エンジニアリング (`feature_engineering.build_features`):
    - `research` モジュールの生ファクター（momentum / volatility / value）を取得しマージ。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 数値ファクターを Z スコア正規化後 ±3 でクリップ（外れ値抑制）。
    - `features` テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性）。
  - シグナル生成 (`signal_generator.generate_signals`):
    - `features` と `ai_scores` を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換や欠損コンポーネントの中立値（0.5）補完を実施。
    - デフォルト重み・閾値を提供（デフォルト閾値 0.60）。
    - Bear レジーム判定（AI の regime_score 平均が負の場合、サンプル数要件あり）で BUY を抑制。
    - エグジット判定（ストップロス -8% / スコア低下）を実装し SELL シグナルを生成。
    - `signals` テーブルへ日付単位で置換（トランザクション + バルク挿入）。
    - 重みはユーザ入力で部分的上書き可能で、合計が 1.0 になるよう正規化される。無効値は警告してスキップ。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- RSS パースに defusedxml を使用して XML 関連の攻撃リスクを低減。
- ニュース URL 正規化とトラッキングパラメータ除去、受信サイズ制限により情報の一貫性・資源消費攻撃に配慮。
- J-Quants クライアントでトークン自動リフレッシュと厳格なリトライ制御を実装。

### Notes / Known limitations
- execution（発注）層はパッケージのエクスポート対象に含まれるが、実装は初期段階（プレースホルダ）です。実際の発注ロジック・API 統合は今後の作業。
- 戦略の SELL 条件の一部（トレーリングストップ、時間決済）はコメントで未実装と明記されています。これらは `positions` テーブルに `peak_price` / `entry_date` 等の情報が追加され次第実装予定です。
- news_collector のドキュメントでは「INSERT RETURNING を用いて挿入数を正確に返す」とありますが、実装はチャンク化した executemany を使用する方式です（将来の最適化候補）。
- 外部依存をできるだけ排した設計（pandas など非依存）だが、実運用ではデータ量や性能要件に応じて最適化が必要。

### Migration / Upgrade notes
- なし（初回リリース）

Contributors:
- 初期実装（リポジトリ作成者）による開発。