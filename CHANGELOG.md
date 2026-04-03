Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

[Unreleased]: https://example.com/kabusys/compare/v0.1.0...HEAD
[0.1.0]: https://example.com/kabusys/releases/tag/v0.1.0

0.1.0 - 2026-04-03
------------------

初回リリース。KabuSys は日本株向けの自動売買/データ基盤/リサーチのためのライブラリ群で、以下の主要機能を含みます。

Added
- パッケージ基盤
  - 初期パッケージ kabusys を導入。公開 API として data, strategy, execution, monitoring を __all__ でエクスポート。
  - バージョン情報 __version__ = "0.1.0" を設定。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を読み込む Settings クラスを実装。settings インスタンスを提供。
  - 自動ロード機能:
    - プロジェクトルートを .git / pyproject.toml を基準に探索して .env / .env.local を順に読み込む（CWD に依存しない方法）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）。
    - .env 読み込み時に既存 OS 環境変数を保護する protected ロジックを採用。
  - .env 行パーサー _parse_env_line:
    - export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理など堅牢な解析。
  - 必須環境変数検査用の _require、各種パスや閾値、LOG_LEVEL / KABUSYS_ENV のバリデーション（有効値集合）などを提供。
  - データベースパス（DUCKDB_PATH / SQLITE_PATH）、監視用 PID/KILL フラグ等のプロパティを提供。

- AI モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news / news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI (gpt-4o-mini) にバッチ送信してセンチメントを算出。
    - JST ベースのニュースウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を実装（calc_news_window）。
    - バッチ処理（最大 20 銘柄 / チャンク）、個別銘柄のトリム（記事数・文字数制限）、JSON Mode のレスポンス検証、スコアクリップ（±1.0）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、失敗時はそのチャンクをスキップして継続（フェイルセーフ）。
    - valid レスポンスのみを ai_scores テーブルへ置換（DELETE → INSERT）し、部分失敗時に既存スコアを保護。
    - テスト容易性のため _call_openai_api を patch 可能な設計。
  - regime_detector.score_regime:
    - ETF(1321) の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - prices_daily を target_date 未満のデータのみ参照してルックアヘッドバイアスを防止。
    - マクロキーワードによる raw_news フィルタリング、OpenAI 呼び出し（独立実装）、API エラー時のフォールバック（macro_sentiment=0.0）。
    - 乱数や現在時刻に依存しない設計（datetime.today() を参照しない）。
    - OpenAI 呼び出しでのリトライ・エラーハンドリングを実装。

- Data モジュール (kabusys.data)
  - calendar_management:
    - JPX カレンダー（market_calendar）の管理機能を提供。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを実装。
    - DB の値を優先し、未登録日は曜日ベース（土日非営業）でフォールバックする一貫したロジック。
    - calendar_update_job: J-Quants API から差分取得 → 冪等保存（ON CONFLICT 相当）・バックフィル、健全性チェックを実装。
    - 最大探索範囲、先読み日数、バックフィル日数などの定数を設定して安全性を確保。
  - pipeline / etl:
    - ETL パイプライン用の ETLResult dataclass を提供（kabusys.data.pipeline.ETLResult を kabusys.data.etl で再エクスポート）。
    - 差分取得・保存・品質チェックフロー（jquants_client 経由で保存、quality モジュールでチェック）を想定した設計。
    - ETLResult には品質問題の一覧や処理エラー情報を持たせ、has_errors / has_quality_errors / to_dict を提供。
    - DuckDB に対する互換性考慮（executemany の空リスト禁止への対応）を実装。

- Research モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）を算出。データ不足時の None フォールバック。
    - calc_volatility: 20 日 ATR、相対 ATR (atr_pct)、平均売買代金、出来高比率を算出。NULL の伝播を考慮した true_range 計算。
    - calc_value: raw_financials から最新の財務データを結合し PER / ROE を算出（EPS=0/欠損時は None）。PBR/配当利回りは未実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン（デフォルト [1,5,21]）を取得。ホライズンバリデーション（1..252）。
    - calc_ic: Spearman 的ランク相関（Information Coefficient）を計算。レコード不足や分散ゼロ時は None を返す。
    - rank: 同順位は平均ランクにするランク関数（丸めによる tie 検出対策を実装）。
    - factor_summary: count/mean/std/min/max/median の統計サマリを計算。
  - research パッケージは主要関数をトップレベルで再エクスポート。

Changed
- 設計面の明示化（初版としての設計方針を記録）
  - ルックアヘッドバイアス回避のため、日付参照に datetime.today()/date.today() を直接使わない方針を徹底。
  - OpenAI 呼び出し・DB 書き込みに関するフェイルセーフ（API/DB失敗時に処理全体を停止しない）を採用。
  - DuckDB の互換性問題（executemany に空リスト不可）に対応する実装を組み込んだ。

Fixed
- .env 読み込みのエッジケース対応
  - export プレフィックスや引用符内のエスケープ、インラインコメントの扱いなどを考慮したパーサーを提供し、一般的な .env 形式の罠に耐性を持たせた。

Security
- API キーの取り扱い
  - OpenAI API キーは score_news / score_regime の引数で注入可能。引数未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出して明示的に失敗させる。
  - 設定ロード時に OS 環境変数が .env により上書きされないよう protected 設定を採用。

Notes / Known limitations
- 現バージョンは初期リリースのため以下を含む:
  - strategy / execution / monitoring パッケージの実装はパッケージ構成に含まれるが、ここに挙げたモジュール（data / ai / research）を中心に機能が整備されています。
  - 一部指標（PBR・配当利回り等）は未実装。
  - OpenAI との連携は gpt-4o-mini を想定。API仕様変更やモデル差し替えの影響を受ける可能性あり。
  - AI モジュールは外部 API 呼び出しが必要なため、テスト時は _call_openai_api をモックすることを推奨。

Migration
- 初回リリースのためマイグレーションはありません。

Contributing
- バグ報告・機能要求は issue を立ててください。テスト可能な形での PR を歓迎します。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して環境自動読み込みを抑止できます。

---- 

（備考）本 CHANGELOG はソースコードの記載内容から推測して作成しています。実際のリリースノート作成時は、コミット履歴やリリース方針に合わせて詳細を調整してください。