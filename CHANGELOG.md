CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-27
--------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ公開情報: src/kabusys/__init__.py に __version__ = "0.1.0"、公開サブパッケージとして data, strategy, execution, monitoring をエクスポート。

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読込する仕組みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
  - .env パーサを実装（export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - 環境変数の上書き制御（override/protected）機能をサポート。
  - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス / ログレベル / 環境種別（development/paper_trading/live）等のプロパティを公開。
  - 不正な設定値や未設定必須値に対する明確なエラーメッセージを実装（例: _require、env/log_level のバリデーション）。

- AI ニュース/NLP モジュール (kabusys.ai.news_nlp)
  - raw_news および news_symbols を集約して銘柄別にニュースをまとめ、OpenAI（gpt-4o-mini の JSON mode）へバッチ送信してセンチメントを取得。
  - 処理の主な特徴:
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive で扱う calc_news_window 実装）。
    - 1リクエストあたり最大 20 銘柄（_BATCH_SIZE）。
    - 銘柄ごとに最大 10 記事・最大 3000 文字でトリムしてプロンプト生成（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフでのリトライ実装（_MAX_RETRIES、_RETRY_BASE_SECONDS）。
    - レスポンス検証: JSON パース、"results" リストの存在、コード一致、数値型チェック、±1.0 クリップ。
    - 部分失敗に備え、ai_scores テーブルへは取得できたコードのみを DELETE → INSERT で置換（部分失敗時に既存データを保護）。
  - テストしやすさを考慮し、OpenAI 呼び出し箇所は単独関数化して unittest.mock.patch により差し替え可能。

- マーケットレジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321（日経225 連動型）200日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出・保存する機能を実装。
  - 処理の主な特徴:
    - ma200_ratio の計算（target_date 未満のデータのみ使用、データ不足時は中立1.0を使用してフェイルセーフ）。
    - マクロニュース抽出はキーワードマッチ（複数キーワード群）で最大 20 件を取得。
    - OpenAI（gpt-4o-mini）へ JSON モードで送信、API エラー時は macro_sentiment=0.0 にフォールバック（WARNING ログ）。
    - スコア合成後、market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - API キー注入可能（api_key 引数）でテスト容易性を配慮。
  - API 呼び出し失敗や JSON パース失敗を安全に扱う設計。

- データプラットフォーム / ETL (kabusys.data.pipeline, kabusys.data.etl)
  - ETLResult データクラスを公開（ETL 実行結果の構造化、品質問題やエラーの集約）。
  - ETL の設計方針とユーティリティを実装:
    - 差分更新ロジック（最終取得日の検出、バックフィルの概念）。
    - 最小データ日（_MIN_DATA_DATE）、デフォルト backfill 日数（_DEFAULT_BACKFILL_DAYS = 3）等の定義。
    - DuckDB テーブル存在確認、最大日付取得ユーティリティを実装。

- マーケットカレンダー管理 (kabusys.data.calendar_management)
  - market_calendar テーブルの夜間バッチ更新ジョブ calendar_update_job 実装（J-Quants から差分取得して保存、バックフィル、健全性チェック）。
  - 営業日判定ユーティリティ群実装:
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
  - カレンダーデータが存在しない場合の曜日ベースのフォールバックや、DB 値優先の一貫した挙動を確保。
  - 最大探索範囲（_MAX_SEARCH_DAYS = 60）、先読み日数（_CALENDAR_LOOKAHEAD_DAYS = 90）、バックフィル日数（_BACKFILL_DAYS = 7）などの定義。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200日MA 乖離の計算（データ不足時の None ハンドリング）。
    - calc_volatility: 20日 ATR / ATR 比 / 20日平均売買代金 / 出来高比率。
    - calc_value: PER（EPS が 0/欠損の場合は None）、ROE（raw_financials から取得）。
    - DuckDB SQL を用いた高性能な集合処理実装。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズンの将来リターン（デフォルト [1,5,21]）。
    - calc_ic: スピアマンのランク相関（IC）計算、最小有効サンプル数チェック。
    - rank: 同順位は平均ランクとするランク付け実装（丸めで ties の誤差対策）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を算出。
  - いずれも外部 API に影響を与えない純粋計算ロジックとして設計。

Changed
- 設計上の重要な方針を明文化:
  - ルックアヘッドバイアス回避のため、datetime.today()/date.today() を内部処理で直接参照しない（すべて target_date ベースで処理）。
  - OpenAI 等外部 API 呼び出しは失敗時にフェイルセーフ（スコア 0 やスキップ）としてシステム全体の耐障害性を確保。
  - DuckDB の executemany に関する制約（空リスト不可）に対する防御コードを追加して互換性を確保。

Fixed
- ai_scores / market_regime への書き込み時に部分失敗で既存データを誤って消さないよう、対象コードを絞った DELETE → INSERT の手順を採用して安全性を向上。
- .env 読み込みでのファイルアクセス失敗時に警告を出して続行するようにし、致命的エラーとならないよう改善。

Notes / Implementation details
- OpenAI 呼び出しは gpt-4o-mini の JSON mode を利用する想定。各モジュールは _call_openai_api を内部に定義しており、テスト時はモック差し替え可能。
- 多くの API 呼び出しで指数バックオフ／リトライを実装し、429 / 接続断 / タイムアウト / 5xx をリトライ対象とする。
- スコア類は明示的に [-1.0, 1.0] の範囲へクリップして異常値を防止。
- DuckDB をデータ層に使用。SQL 内で窓関数や LEAD/LAG を多用して効率的に集計を行う設計。

Security
- 重要なトークン（OpenAI／Slack／Kabu）等は Settings 経由で必須プロパティとして取得し、未設定時は明確な例外を発生させることで漏れを防止。

Acknowledgements / Misc
- このリリースでは、システム設計・データ品質・テスト容易性を重視して実装が行われています。今後のリリースで strategy / execution / monitoring の具体的な実装や UI/運用機能、さらなるテスト網羅化などを追加予定です。