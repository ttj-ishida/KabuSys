# CHANGELOG

すべての重要な変更をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。  

なお本リリースはパッケージ初期公開を想定した記述で、コードベースから推測できる機能・設計意図を反映しています。

## [0.1.0] - 2026-03-29

### Added
- パッケージ初期リリース
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - src/kabusys/__init__.py で公開されるトップレベル API: data, strategy, execution, monitoring（パッケージ構成を示唆）

- 環境変数・設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動ロードする仕組みを追加。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサは `export KEY=val` 形式、シングル/ダブルクォート（バックスラッシュエスケープ対応）、およびインラインコメントの扱いをサポート。
  - .env 読み込み時の既存 OS 環境変数保護（protected set）・override 制御を実装。
  - 必須設定を取得する `_require` と Settings クラスを提供。Settings は以下の主要プロパティを持つ:
    - jquants_refresh_token (JQUANTS_REFRESH_TOKEN)
    - kabu_api_password (KABU_API_PASSWORD)
    - kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
    - slack_bot_token (SLACK_BOT_TOKEN)
    - slack_channel_id (SLACK_CHANNEL_ID)
    - duckdb_path (デフォルト data/kabusys.duckdb)
    - sqlite_path (デフォルト data/monitoring.db)
    - env (KABUSYS_ENV: development / paper_trading / live の検証)
    - log_level (LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL の検証)
    - is_live / is_paper / is_dev のユーティリティ判定

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成。
    - OpenAI（gpt-4o-mini, JSON mode）へバッチ送信し、銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルへ書き込み。
    - バッチサイズ、トークン肥大対策（記事数や文字数のトリム）、最大リトライ（429/ネットワーク/タイムアウト/5xx を指数バックオフで再試行）を実装。
    - レスポンスの厳密なバリデーションとクリッピング（±1.0）。
    - DB 書き込みは局所的に DELETE → INSERT の置換方式で冪等性を確保し、部分失敗時に既存スコアを保護。
    - 公開関数: score_news(conn, target_date, api_key=None)
    - タイムウィンドウ計算: calc_news_window(target_date)（JST 基準の前日 15:00 ～ 当日 08:30 を UTC naive datetime で返す）
    - フェイルセーフ: API エラー時は該当チャンクをスキップして処理継続

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で算出。
    - マクロニュース抽出はキーワードベース（複数キーワード定義）でタイトルを取得し、LLM に投げる。LLM には gpt-4o-mini を使用。
    - API 呼び出しはリトライ/バックオフを実装。API 失敗時は macro_sentiment=0.0 にフォールバック（例外を上げず継続）。
    - データベースへの書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に実行。失敗時の ROLLBACK を試みる。
    - 公開関数: score_regime(conn, target_date, api_key=None)

  - AI モジュール共通設計:
    - OpenAI 呼び出し処理はモジュール内で独立実装（モジュール間でプライベート関数を共有しない設計）。
    - テスト容易性のため、API 呼び出し点は unittest.mock.patch による差し替えを想定。

- データプラットフォーム (kabusys.data)
  - ETL パイプライン (kabusys.data.pipeline)
    - 差分取得・保存・品質チェックを行う ETLResult 型とパイプライン基盤を実装。
    - backfill 処理、カレンダー先読み、品質チェック（quality モジュールとの連携）などを実装。
    - DuckDB を前提とした最大日付取得などのユーティリティを実装。
    - ETLResult を再エクスポート (kabusys.data.etl) により公開。

  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを使った営業日判定 API を実装:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - DB 登録値を優先し、未登録日は曜日ベースのフォールバック（週末を非営業日扱い）を行う一貫したロジック。
    - 夜間バッチ更新 job: calendar_update_job(conn, lookahead_days=90)
      - J-Quants API から差分を取得して market_calendar を冪等に保存。バックフィル、健全性チェック（未来日付が異常な場合はスキップ）を実装。
    - 探索最大範囲制限（_MAX_SEARCH_DAYS）で無限ループを防止。
    - 全ての日付は datetime.date を使用し timezone の混入を避ける。

  - jquants_client および quality との連携を想定した設計（実装ファイルは参照されるが本差分内での詳細は省略）

- 研究（Research）モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算（EPS=0/欠損は None）。
    - 全関数は prices_daily / raw_financials のみ参照し、安全にオフライン計算可能。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons のバリデーションあり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。十分なデータがなければ None を返す。
    - rank: 同順位は平均ランクで処理（丸めによる ties 対策あり）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
  - 研究用ユーティリティとして、zscore_normalize を kabusys.data.stats から露出（__init__）している。

### Changed
- 初回リリースのため該当なし

### Fixed
- 初回リリースのため該当なし

### Security
- 環境変数の取り扱いに注意:
  - 必須トークン（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）は Settings で必須チェックを行い、未設定時は ValueError を送出する設計。
  - .env 自動ロードは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）で、テスト環境や CI での誤読込みを防止可能。

### Notes / Implementation details & design choices（重要な設計メモ）
- Blick-ahead バイアス対策:
  - 各 AI / 研究モジュールは内部で datetime.today() / date.today() を直接参照せず、明示的に与えられた target_date に基づき処理を行う設計。
  - DB クエリは target_date 未満（排他）等の条件を用いて未来データ参照を防止。
- フェイルセーフ設計:
  - OpenAI や外部 API の障害時には例外を無闘に上位へ流さず、スコアを 0.0 にフォールバックしたりチャンクをスキップして処理を継続することを優先。
- トランザクションと冪等性:
  - DB 書き込みは DELETE→INSERT の置換やトランザクション（BEGIN/COMMIT/ROLLBACK）で冪等性を担保。
  - DuckDB の executemany の仕様（空リスト不可など）への対策が入っている。
- OpenAI 呼び出し:
  - gpt-4o-mini を想定し JSON Mode（response_format JSON object）でやり取りする実装。
  - SDK の例外（RateLimitError, APIConnectionError, APITimeoutError, APIError）を想定して分岐処理と再試行を実装。
- ロギング:
  - 各主要処理で情報/警告/例外のログ出力を行う（運用での監視に配慮）。

---

今後のリリースで期待される改善点（想定）
- strategy / execution / monitoring サブパッケージの具体的実装と公開 API の整備
- テストカバレッジ・モック用ユーティリティの追加
- AI モデル選択やバッチ設定の外部設定化（Settings 経由での調整）
- jquants_client 等外部クライアントの抽象化・リトライ強化

もし CHANGELOG に含めたい追加の項目（例えばリリース日や特に強調したい注意点）があればお知らせください。