# Changelog

すべての注目すべき変更点をここに記録します。  
このファイルは「Keep a Changelog」仕様に準拠しています。

フォーマット: [バージョン] - 日付  
カテゴリ: Added / Changed / Fixed / Security

## [Unreleased]

---

## [0.1.0] - 2026-03-27

### Added
- パッケージ初回リリース: kabusys 0.1.0
  - パッケージメタ情報:
    - src/kabusys/__init__.py により public サブパッケージを公開（data, strategy, execution, monitoring）。
    - バージョンは 0.1.0。

- 環境設定・自動 .env ロード機能（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み。読み込みの優先順位は OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト向け）。
  - 強化された .env パーサ:
    - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い、無効行スキップに対応。
  - 必須環境変数取得用ヘルパー _require と Settings クラスを提供。
  - 設定項目（例）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/...）の検証ロジック
  - Settings による is_live / is_paper / is_dev の便宜プロパティ。

- ニュースNLP（AI）モジュール（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を元に、銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini）でセンチメント解析し ai_scores テーブルへ書き込み。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive datetime で扱う calc_news_window を提供）。
  - バッチ処理（1回あたり最大 20 銘柄）・1銘柄あたり最新 10 記事・3000 文字でトリム。
  - JSON Mode を用いた厳密なレスポンス検証（results 配列、code/score 検証、未知コード無視、数値性チェック）。
  - API エラー（429/ネットワーク断/タイムアウト/5xx）は指数バックオフでリトライし、最終的に失敗した場合は該当チャンクをスキップして処理継続（フェイルセーフ）。
  - スコアは ±1.0 にクリップ。
  - DuckDB 0.10 の executemany の空リスト問題に対応するため、DELETE を個別に executemany で実行するロジックを実装。
  - テスト容易性のため _call_openai_api をパッチ差し替え可能。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で market_regime テーブルへ書き込み。
  - マクロニュースは news_nlp の calc_news_window で決定されたウィンドウから抽出（最大 20 件）。
  - OpenAI（gpt-4o-mini）を JSON Mode でコールし、レスポンスをパースして macro_sentiment を取得。API 失敗時は 0.0 にフォールバック。
  - レジームスコアは clip して "bull" / "neutral" / "bear" ラベル付け。
  - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。失敗時は ROLLBACK を行い例外伝播。

- 研究（Research）モジュール（src/kabusys/research/**）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（prices_daily より）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER, ROE を計算（最新財務レコードを target_date 以前から取得）。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）で将来リターンを計算。
    - calc_ic: スピアマン順位相関（Information Coefficient）を計算。
    - factor_summary: 各ファクターの基本統計量（count/mean/std/min/max/median）を算出。
    - rank ユーティリティ（同順位は平均ランク）。
  - research パッケージは外部依存を極力避け（標準ライブラリ + DuckDB）、本番発注 API へアクセスしない設計。

- データ（Data）モジュール（src/kabusys/data/**）
  - calendar_management:
    - JPX カレンダー管理用ユーティリティ群（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB（market_calendar）未登録日は曜日ベースでフォールバックする堅牢なロジック。
    - calendar_update_job: J-Quants API から差分取得→冪等保存（fetch/save は jquants_client 経由）。
    - 最大探索日数 / バックフィル / 健全性チェック等の実装。
  - pipeline / etl:
    - ETLResult データクラス（src/kabusys/data/pipeline.py）を公開（src/kabusys/data/etl.py で再エクスポート）。
    - 差分取得、保存、品質チェックのための基盤（jquants_client と quality モジュールの連携想定）。
    - _get_max_date 等のユーティリティを実装。

- テストおよび堅牢性に配慮した設計上のハイライト
  - AI 呼び出し箇所は _call_openai_api をパッチ可能にしてユニットテストで差し替え可能。
  - LLM 失敗時はフェイルセーフ（0.0 やスキップ）を採用し、パイプライン全体を停止させない。
  - 日付の扱いはすべて date / naive datetime で統一し、datetime.today()/date.today() 参照によるルックアヘッドを起こさない設計（target_date を明示的に渡す方式）。
  - DuckDB の互換性（executemany 空リスト回避）やトランザクションの取り扱い（ROLLBACK の失敗時ログ）など実運用上の配慮を実装。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし（ただし .env パースや API エラー処理等の堅牢化が施されています）。

### Security
- 初回リリースのため該当なし。
  - ただし、APIキーは明示的に引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を使用する設計で、キーの管理を呼び出し側に委ねる形となっています。

---

Notes / 参考
- OpenAI 関連:
  - モデル: gpt-4o-mini を想定し JSON Mode（response_format={"type": "json_object"}）で利用。
  - エラー分類に応じたリトライ戦略（RateLimitError, APIConnectionError, APITimeoutError はリトライ、APIError の status_code による 5xx 判定でリトライ等）。
- 必須環境変数が未設定の場合、Settings のプロパティ呼び出しで ValueError を送出するため、起動時に必要環境の検査を行うことを推奨します。
- DuckDB を直接操作するため、テーブルスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）の準備が必要です。

もしリリースノートを英語版やセマンティックバージョニングの注記（例えば CHANGELOG にリンクや比較 URL を追加）付きで出力したい場合は指示してください。