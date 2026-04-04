CHANGELOG
=========

すべての注目すべき変更点を時系列で記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。  
バージョン番号はパッケージの __version__ と合わせています。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-04
------------------

Added
- 初回公開: kabusys パッケージ v0.1.0 を追加。
  - パッケージ概要: 日本株自動売買・研究・データ基盤向けユーティリティ群を提供。
  - エントリポイント: src/kabusys/__init__.py により data, strategy, execution, monitoring を公開。

- 環境設定/起動制御
  - settings: kabusys.config.Settings を追加し、環境変数から各種設定値を取得。
    - 必須変数の取得関数 _require を実装（未設定時は ValueError）。
    - 検証済み値: KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - 各種パス設定（DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH など）と閾値（CPU/MEMORY/DISK）をプロパティで提供。
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git or pyproject.toml を基準）。
    - 読み込み優先順: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサは export 形式・引用符・インラインコメント等に柔軟に対応。

- Data（データ基盤）
  - calendar_management:
    - JPX カレンダー管理ロジックを実装（market_calendar テーブルを参照）。
    - 営業日判定 is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - calendar_update_job による J-Quants からの差分取得・冪等保存（バックフィル・健全性チェック実装）。
    - DB が未登録の場合は曜日ベースのフォールバックを実施。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL 実行結果の集約）。
    - ETL パイプライン設計に基づく差分取得、保存、品質チェックのインタフェースを整備。
    - 差分更新とバックフィル（デフォルト backfill_days）や品質問題の収集方針を反映。

- AI（自然言語処理）
  - news_nlp.score_news:
    - raw_news + news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメント（-1.0〜1.0）を算出。
    - 処理は銘柄をチャンク(_BATCH_SIZE=20) に分けてバッチ送信、1銘柄あたり記事数・文字数上限でトリム。
    - リトライ/バックオフ（429・ネットワーク断・タイムアウト・5xx を対象）を実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列検証、コード照合、数値チェック）を実施。
    - ai_scores テーブルへは取得済みコードのみ DELETE→INSERT により置換（部分失敗時に他データを保護）。
    - テスト用に _call_openai_api をパッチ差替え可能な設計。
  - regime_detector.score_regime:
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）と、ニュース由来の LLM マクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - ニュース取得ウィンドウは news_nlp.calc_news_window を利用。
    - OpenAI 呼び出しは JSON 出力を期待し、冪等に market_regime テーブルへ書き込み（BEGIN/DELETE/INSERT/COMMIT）。API 失敗時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
    - OpenAI クライアント注入は api_key 引数または環境変数 OPENAI_API_KEY に対応。

- Research（リサーチ）
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離を計算（欠損時は None を返す）。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比を算出。
    - calc_value: raw_financials の最新財務データと prices_daily を組み合わせて PER / ROE を計算。
    - DuckDB 上で SQL を組み合わせる設計、外部 API 呼び出しは行わない。
  - research.feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を使用）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。十分なデータがない場合は None を返す。
    - rank / factor_summary: ランク化（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を計算。
    - 外部依存を避け、標準ライブラリのみで実装。

- 公開 API と再利用性
  - ai モジュールは score_news, score_regime を主要エンドポイントとして提供。
  - data.pipeline.ETLResult をデータクラスとして公開（kabusys.data.etl で再エクスポート）。
  - テスト可能性のため、OpenAI 呼び出し箇所に差し替えフック（_call_openai_api）を用意。

Security / Robustness / Operational notes
- 多くの処理で "ルックアヘッドバイアス" を避けるため datetime.today()/date.today() を直接参照せず、target_date に依存する実装を採用。
- DuckDB を中心に設計（prices_daily / raw_news / ai_scores / market_regime / market_calendar / raw_financials 等の想定テーブル）。
- 外部 API 呼び出し（OpenAI / J-Quants）にはリトライ / バックオフ、HTTP 5xx の扱い、ロギングを実装しフェイルセーフを優先（完全停止ではなくスキップ・フォールバック）。
- DB 書き込みは可能な限り冪等に（DELETE→INSERT / ON CONFLICT 相当）行い、失敗時は ROLLBACK を試みる。
- .env パーサは実運用でよく見かけるフォーマット（export、クォート、コメント）に耐性あり。

Changed
- 初リリースのため該当なし。

Fixed
- 初リリースのため該当なし。

Deprecated
- 初リリースのため該当なし。

Notes / Known limitations
- OpenAI の model と response_format をコード内で指定（gpt-4o-mini、JSON mode）。将来の SDK / API 変更により動作確認が必要。
- DuckDB バージョン差分での executemany の挙動に対する回避（空パラメータの確認）を実装しているが、環境による差異が残る可能性あり。
- 現フェーズでは sentiment_score と ai_score を同値で扱う実装になっている（将来的な拡張余地あり）。
- calendar_update_job 等で J-Quants クライアント（jquants_client）に依存。実運用時は API キー / ネットワークの設定が必要。

貢献
- ご意見・バグ報告・機能提案は Issue または Pull Request で歓迎します。