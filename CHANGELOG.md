# Keep a Changelog
すべての変更は https://keepachangelog.com/ja/ に準拠して記録しています。

全般方針:
- バージョニングは SemVer に準拠します。
- 各リリースには主な追加機能、変更点、修正点を記載します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-27
初回リリース。以下の主要機能・モジュールを実装・公開します。

### Added
- パッケージ基盤
  - パッケージメタ情報と公開 API: kabusys.__init__ により主要サブパッケージ（data, research, ai, ...）を公開。
  - バージョン: 0.1.0。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を起点に探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
  - .env パースの詳細:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート対応（バックスラッシュによるエスケープ処理を考慮）。
    - クォート無し時は '#' が直前にスペース/タブある場合をコメント扱いにする等、実運用での柔軟な挙動。
  - 必須値取得ヘルパー _require と Settings クラスを提供。主な環境変数:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト http://localhost:18080/kabusapi)
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH (デフォルト data/kabusys.duckdb), SQLITE_PATH (デフォルト data/monitoring.db)
    - KABUSYS_ENV (development | paper_trading | live)、LOG_LEVEL（DEBUG/INFO/...）
    - OPENAI_API_KEY は ai モジュールで参照（明示引数を優先）

- データ基盤（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理ロジック（market_calendar テーブル利用）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の提供。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィル・先読み・健全性チェックを実装。
    - DB 未登録日の扱いは曜日ベースのフォールバック（土日は非営業日）。
  - pipeline / etl:
    - ETLResult データクラス（ETL 結果の集約）。data.etl は ETLResult を再エクスポート。
    - 差分取得／最終日判定ユーティリティ（_get_max_date 等）。
    - ETL の設計方針（差分更新・backfill・品質チェックを継続収集）に対応。

- AI ニュース解析・市場レジーム判定（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols を元に銘柄ごとにニュースを集約し、OpenAI (gpt-4o-mini) を用いて銘柄別センチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive で扱う calc_news_window を提供）。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、記事数／文字数上限（銘柄あたり最大 10 記事、3000 文字）でトリム。
    - JSON Mode を前提とした厳格なレスポンスバリデーションとクリップ（±1.0）。
    - レート制限（429）、ネットワーク断、タイムアウト、5xx に対する指数バックオフ再試行を実装。再試行上限到達時は該当チャンクをスキップして続行（フェイルセーフ）。
    - DuckDB の executemany の制約（空リスト不可）に配慮した安全な DB 書き込みロジック（DELETE→INSERT を個別実行）。
    - テスト用フック: _call_openai_api を patch して差し替え可能。
  - regime_detector:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、ニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出および market_regime テーブルへ冪等書き込みを実施。
    - マクロキーワードによる raw_news フィルタ、OpenAI によるマクロセンチメント評価（gpt-4o-mini）、クリップ・閾値判定を実装。
    - API エラー時は macro_sentiment=0.0 のフェイルセーフ挙動。API キー未指定時は例外を投げる。
    - DuckDB に対する BEGIN/DELETE/INSERT/COMMIT の冪等保存を行い、書込失敗時は ROLLBACK を試行。

- Research（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB を用いて計算する関数群（calc_momentum / calc_volatility / calc_value）。
    - 200 日 MA 等、データ不足時は None を返す仕様。
    - SQL 前提の実装で本番 API へのアクセスは無し（安全設計）。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns: デフォルト horizons = [1,5,21]）、IC（calc_ic: スピアマンのランク相関）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を提供。
    - 外部依存なし（pandas 等非依存）。

- 実装上のセーフガード・設計ノート（全体）
  - ルックアヘッドバイアス防止: 主要処理は datetime.today() / date.today() を参照せず、引数で与えた target_date を基準に動作する設計。
  - OpenAI 呼び出し失敗時は原則「スコア＝中立（0.0）／該当処理スキップ」で継続するフェイルセーフ設計。
  - DuckDB の挙動差異（executemany の空リスト不可など）を考慮した互換性対策。
  - ロギングを広く配置し、失敗時に詳細が出力されるように設計。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- OpenAI API キーは明示引数を優先する設計。環境変数が未設定の場合は明示的なエラーとして扱う箇所あり（誤った無自覚な運用を防止）。

---

補足:
- ドキュメント（コード内 docstring）に各モジュールの設計方針・使用上の注意を記載しています。実運用前に Settings の環境変数設定、DuckDB/SQLite の初期スキーマ、J-Quants / kabuAPI / Slack の認証情報を正しく構成してください。