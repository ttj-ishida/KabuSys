# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

なお、このリポジトリの初回公開版としての変更点をソースコードから推測して記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報: __version__ = "0.1.0"、パッケージ公開 API: data, strategy, execution, monitoring を __all__ で定義。

- 環境設定モジュール（kabusys.config）
  - .env ファイルと環境変数から設定を自動ロードする機能を実装。
    - プロジェクトルートは .git または pyproject.toml を起点に上位ディレクトリから探索（CWD に依存しない）。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - .env ファイルの読み込み時に OS 環境変数を保護するための protected set を利用して上書き制御を行う。
  - .env 行パーサーを実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを考慮した値抽出。
    - クォートなし値のインラインコメント処理（`#` がスペースまたはタブ直前の場合にコメントと判定）。
  - Settings クラスを提供（settings = Settings()）。
    - J-Quants / kabuステーション / Slack / DB パス 等のプロパティを環境変数から取得。
    - duckdb/sqlite のパスはデフォルト値を持ち Path オブジェクトで返す。
    - KABUSYS_ENV と LOG_LEVEL の許容値バリデーション（不正値は ValueError）。
    - is_live/is_paper/is_dev のヘルパープロパティ。

- AI モジュール（kabusys.ai）
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元に、銘柄ごとのセンチメント ai_score を計算し ai_scores テーブルへ書き込む機能を実装。
    - OpenAI（gpt-4o-mini）へ JSON mode でバッチ送信（最大 20 銘柄/チャンク）。
    - 1 銘柄あたり最大記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列確認、コード / スコアの整合性検証、スコアのクリップ）。
    - 部分成功に備え、ai_scores へは取得済みコードのみを対象に DELETE → INSERT で冪等的に書き込み（DuckDB の executemany 空配列問題に配慮）。
    - テスト容易性のため、OpenAI 呼び出し箇所を patch 可能（内部 _call_openai_api を差し替え可能）。
    - 公開 API: score_news(conn, target_date, api_key=None)：書き込み銘柄数を返す。
    - ニュース集計ウィンドウ計算関数 calc_news_window(target_date) を実装（JST の前日 15:00 ～ 当日 08:30 を UTC naive datetime に変換）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を統合して日次レジーム（bull/neutral/bear）を判定。
    - DuckDB の prices_daily / raw_news / market_regime を参照し、冪等的に market_regime テーブルに書き込む（BEGIN / DELETE / INSERT / COMMIT）。
    - LLM 呼び出しは OpenAI SDK（gpt-4o-mini）を利用。API 障害時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
    - API 呼び出しに対してリトライ（429・ネットワーク・タイムアウト・5xx）を実装。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
    - 公開 API: score_regime(conn, target_date, api_key=None)：成功時に 1 を返す。

- データモジュール（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー（market_calendar）の夜間バッチ更新ジョブ calendar_update_job(conn, lookahead_days=...) を実装。
    - カレンダーデータの有無に応じて営業日判定を行うユーティリティ群を提供:
      - is_trading_day(conn, d), is_sq_day(conn, d)
      - next_trading_day(conn, d), prev_trading_day(conn, d)
      - get_trading_days(conn, start, end)
    - DB に登録がない日は曜日ベースのフォールバック（週末非営業日）を採用し、DB 登録ありの場合は DB 値を優先して一貫した結果を返す設計。
    - 更新時はバックフィル（直近数日を再取得）や健全性チェック（過度に未来日付の検知）を実装。
    - J-Quants クライアント（jquants_client）との連携を前提。

  - ETL パイプライン（kabusys.data.pipeline、kabusys.data.etl）
    - ETL の公開結果データクラス ETLResult を実装（target_date, fetched/saved counts, quality_issues, errors 等を格納）。
    - テーブル最大日付取得やテーブル存在チェックといった内部ユーティリティを実装。
    - 差分取得・保存・品質チェックを行う方針に基づいた骨格と定数（バックフィル日数、最小データ開始日など）を定義。
    - ETLResult.to_dict() により品質問題を serialize できるように実装。

- 研究モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum / Volatility / Value（mom_1m/3m/6m、ma200_dev、atr_20、atr_pct、avg_turnover、volume_ratio、per、roe など）を DuckDB の SQL と Python で計算する関数を実装。
    - データ不足時の扱い（必要行数未満なら None）やスキャン範囲のバッファ設計を記載。
    - 公開関数: calc_momentum, calc_volatility, calc_value（各関数は date, code をキーとする dict のリストを返す）。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算 calc_forward_returns（任意 horizon のサポート、引数検証あり）。
    - IC（Information Coefficient）計算 calc_ic（Spearman ランク相関の実装、最小有効レコード数チェック）。
    - ランク関数 rank（同順位は平均ランク）。
    - 統計サマリー関数 factor_summary（count/mean/std/min/max/median 計算）。
  - 研究用ユーティリティとして zscore_normalize を kabusys.data.stats から再エクスポート。

- ロギング・設計・品質面の注記
  - 多くの処理でログ出力（info/warning/debug）を充実させ、API失敗やデータ不足時の挙動を明示。
  - ルックアヘッドバイアス回避のため関数実装は datetime.today() / date.today() に依存しない設計（target_date を明示的に受け取る）。
  - DuckDB のバージョン差異（executemany の空配列問題、list 型バインド等）に配慮した実装。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし（ただし各モジュールでフェイルセーフやバリデーションを実装し堅牢化）。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- Secrets/API キーの扱いは環境変数経由を想定（OpenAI は OPENAI_API_KEY、各種 API トークンは Settings を通じて取得）。  
  - 環境変数が未設定の場合は明確に ValueError を発生させる仕様。

---

備考:
- 上記はソースコードから推測した初期リリースの変更履歴です。実際の変更履歴やリリース日、追加されたファイル等はリポジトリのコミット履歴やリリースノートと合わせて確認してください。