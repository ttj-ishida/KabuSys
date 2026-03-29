# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-29

初期リリース — 日本株自動売買 / 研究プラットフォーム "KabuSys" のコア機能を実装しました。主にデータ取得・カレンダー管理、ファクター計算、ニュース NLP・市場レジーム判定の AI 統合、および環境設定ユーティリティを提供します。

### Added
- パッケージ全体
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` に設定。
  - kabase エクスポートに `data`, `strategy`, `execution`, `monitoring` を登録（パッケージ入口）。

- 環境設定 / 設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - .env パーサーを実装:
    - `export KEY=val` 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、無効行（空行・#始まり）の無視。
    - `.env.local` は `.env` を上書き（OS 環境変数は保護）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能（テスト用途）。
  - Settings クラスを実装し、環境変数から各種設定を取得するプロパティを提供:
    - J-Quants: `JQUANTS_REFRESH_TOKEN`
    - kabu API: `KABU_API_PASSWORD`, `KABU_API_BASE_URL`（デフォルト http://localhost:18080/kabusapi）
    - Slack: `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`
    - DB パス: `DUCKDB_PATH`（デフォルト data/kabusys.duckdb）, `SQLITE_PATH`（デフォルト data/monitoring.db）
    - システム設定: `KABUSYS_ENV`（development/paper_trading/live の検証）、`LOG_LEVEL`（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
  - 必須変数未設定時は明確なエラーメッセージを送出（ValueError）。

- ニュース NLP（AI 統合） (kabusys.ai.news_nlp)
  - target_date に対するニュース収集ウィンドウ計算 (`calc_news_window`) を実装（JST ベース -> UTC 換算）。
  - raw_news と news_symbols から銘柄ごとに記事を集約する `_fetch_articles`（1銘柄最大記事数・最大文字数でトリム）。
  - OpenAI (gpt-4o-mini) を JSON Mode で呼ぶ `_call_openai_api` と、API 呼び出し・レスポンス検証ロジックを実装。
  - バッチ処理（1 API コールあたり最大 20 銘柄）と指数バックオフによるリトライ（429/ネットワーク/タイムアウト/5xx 対応）。
  - レスポンス検証（`results` フォーマット、コード検証、数値変換、有限値チェック）とスコアの ±1.0 クリップ。
  - 書き込み: 成功した銘柄のみ `ai_scores` テーブルへ冪等的（DELETE → INSERT）に保存。DuckDB 互換性のため executemany の空配列対策を実装。
  - フェイルセーフ: API 失敗時は該当チャンクをスキップして処理継続。API キーが未設定の場合は ValueError を送出。
  - 単体テスト用フック: `_call_openai_api` をパッチ可能に実装。

- 市場レジーム判定（AI + テクニカル） (kabusys.ai.regime_detector)
  - ETF 1321（日経225連動）の 200 日移動平均乖離（ma200_ratio）とマクロニュース LLM センチメントを重み付け（70% / 30%）して日次で市場レジームを判定（'bull'/'neutral'/'bear'）。
  - マクロニュースは raw_news からマクロキーワードで抽出し LLM（gpt-4o-mini）で JSON 出力を要求、複数リトライ・フェイルセーフを実装（失敗時 macro_sentiment = 0.0）。
  - スコア合成後、`market_regime` テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
  - API キーが未設定の場合は ValueError を送出。
  - lookahead バイアス防止のため日付取得に datetime.today()/date.today() を使わない設計。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research モジュールを追加:
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離（cnt_200 チェックで不足時は None）。
    - calc_volatility: 20 日 ATR（true_range の NULL 伝播制御）、相対 ATR（atr_pct）、平均売買代金、出来高比率。
    - calc_value: raw_financials から直近の財務を取得し PER（EPS が 0/欠損時は None）と ROE を算出。
    - SQL を主体とした DuckDB 内完結実装。外部 API 不使用。
  - feature_exploration モジュールを追加:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）に対応、LEAD を使った単一クエリ取得、ホライズン上限 252。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装（同順位は平均ランク）。
    - rank: 値のランク化（丸めによる ties 対策）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出。
  - research パッケージの __all__ に主要関数をエクスポート。

- データ管理 (kabusys.data)
  - calendar_management:
    - market_calendar をベースに営業日判定を行うユーティリティ群を実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB 登録がない場合は曜日ベース（週末は非営業日）でフォールバックする一貫したロジック。
    - カレンダー夜間バッチ `calendar_update_job` を実装（J-Quants から差分取得、バックフィル、健全性チェック、保存処理）。
  - pipeline / ETL:
    - ETLResult dataclass を実装（取得数・保存数・品質チェック・エラー集約用）。
    - _table_exists / _get_max_date 等のユーティリティを実装。
    - data.etl モジュールから ETLResult を再エクスポート。

- テスト性・運用性のための配慮
  - OpenAI 呼び出し部はモジュールごとに個別実装し、ユニットテストで差し替え可能な設計。
  - ルックアヘッドバイアス防止: 内部ロジックは日付パラメータを受け、date.today()/datetime.today() への直接依存を避ける。
  - DuckDB のバージョン差異（executemany 空配列問題など）に対するワークアラウンドを導入。
  - 詳細なログ出力・警告を追加し、失敗時にもフェイルセーフで継続するポリシー。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーや各種トークンは Settings 経由で必須チェックを行い、未設定時に明示的エラーを発生させることで誤操作を防止。

### Notes / 運用メモ
- 環境変数（必須）:
  - OPENAI_API_KEY: AI 機能（score_news / score_regime）を利用する場合に必要
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視用): data/monitoring.db
- 自動 .env 読み込みはプロジェクトルートを基準に行われます。CI / テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB を利用するため、ETL / calendar / research 関数は duckdb.PyConnection を引数に取ります。ユニットテストではメモリ DB を利用してテスト可能です。
- OpenAI 呼び出しの挙動はリトライやバックオフなどを含むため、API レート制限や一時的なネットワーク障害に耐性があります。とはいえ API コストに注意してください。

### Known issues
- 本リリースでは一部のサブパッケージ（例: strategy/execution/monitoring）の実装が外部に依存するか、別モジュールとして存在することを前提としています。運用で全機能を利用するにはこれらのモジュールが揃っている必要があります。
- DuckDB のバージョン差異によっては SQL バインドの振る舞いに差が出る可能性があるため、運用環境の DuckDB バージョン確認を推奨します。

---

その他の問い合わせやリリースノートの詳細な分割（例: minor/patch リリース計画）をご希望であればお知らせください。