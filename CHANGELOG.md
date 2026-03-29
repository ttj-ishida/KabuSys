# Changelog

すべての変更は Keep a Changelog のガイドライン（https://keepachangelog.com/ja/1.0.0/）に従って記載しています。  
このプロジェクトはセマンティックバージョニングを使用しています。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回公開リリース。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ == 0.1.0）。
  - サブパッケージを公開（kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring を __all__ でエクスポート）。

- 環境・設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を解決する自動ロード機構を実装。
    - プロジェクトルート検出: .git または pyproject.toml を基準に自ファイル位置からルートを探索（CWD 非依存）。
    - 読込優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
  - .env パーサを実装:
    - export KEY=val 形式対応、コメント行・空行の無視。
    - シングル／ダブルクォート内のバックスラッシュエスケープ対応。
    - クォートなし値のインラインコメント処理（# の前が空白/タブの場合をコメントと判定）。
  - ファイル読み込み時の保護（既存 OS 環境変数を protected として上書きを制御）とエラー時の警告通知。
  - Settings クラスを提供（環境変数からアプリケーション設定を取得するプロパティ群）:
    - J-Quants, kabu ステーション, Slack, DB パス（DuckDB/SQLite）、システム環境（KABUSYS_ENV / LOG_LEVEL）等の取得。
    - 値検証（KABUSYS_ENV と LOG_LEVEL の許容値チェック）。
    - 必須値未設定時に明確な ValueError を送出する _require ユーティリティ。

- AI（自然言語処理）機能（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - calc_news_window 関数を実装（JST ベースで前日 15:00 ～ 当日 08:30 の UTC ナイーブウィンドウを返す）。
    - score_news 実装: raw_news / news_symbols を集約して銘柄毎のニュースを作成し、OpenAI（gpt-4o-mini）の JSON モードでバッチスコアリングして ai_scores テーブルへ書き込み。
      - バッチサイズ、1銘柄あたりの最大記事数・文字数トリム、チャンク処理を導入（_BATCH_SIZE/_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
      - リトライポリシー: 429・ネットワーク切断・タイムアウト・5xx に対して指数バックオフでリトライ（_MAX_RETRIES / _RETRY_BASE_SECONDS）。
      - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列検証、コードの正規化、数値検証、±1.0 のクリップ）。
      - DuckDB の executemany の制約を考慮して、DELETE と INSERT を個別実行（空リスト処理の回避）。
      - API 呼び出し箇所はテスト用に patch しやすいように _call_openai_api を分離。
      - OpenAI API キー未設定時は ValueError を送出。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）判定を実装。
      - ma200_ratio を prices_daily から計算（target_date 未満データのみを使用してルックアヘッドを防止）。
      - マクロ記事抽出は raw_news からキーワードフィルタ（定義済みの _MACRO_KEYWORDS）。
      - LLM 呼び出し（gpt-4o-mini）で JSON 出力を期待し、レスポンスパース失敗・API 失敗時はフェイルセーフとして macro_sentiment=0.0 を採用して継続。
      - レジームスコア合成はクリップ処理後、閾値によりラベルを付与。
      - market_regime テーブルへは冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）、失敗時は ROLLBACK を試行して例外を伝播。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーを保存・参照するためのユーティリティを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日判定機能を実装。
    - market_calendar が未取得の場合は曜日ベース（土日休）でフォールバックする一貫した振る舞い。
    - 次/前営業日探索に最大探索日数上限を設定して無限ループを防止。
    - calendar_update_job 実装: J-Quants から差分取得して market_calendar を冪等的に更新（バックフィル、健全性チェックを含む）。
  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - ETLResult データクラスを導入（ETL のフェッチ／保存件数や品質チェック結果、エラー一覧を保持）。
    - 差分更新、バックフィル、品質チェック（kabusys.data.quality を利用）を想定した設計。
    - _get_max_date 等のユーティリティによりテーブルの最大日付取得を実装。
    - kabusys.data.etl で ETLResult を再エクスポート。

- リサーチ用解析（kabusys.research）
  - factor_research モジュールを追加:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を prices_daily から計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR / 相対 ATR / 20 日平均売買代金 / 出来高比率を計算。true_range の NULL 伝播を慎重に扱う。
    - calc_value: raw_financials から直近の財務データを取得して PER / ROE を計算（EPS が 0/NULL の場合は None）。
    - 全て DuckDB 上の SQL ウィンドウ関数を中心に実装し、外部 API には依存しない設計。
  - feature_exploration モジュールを追加:
    - calc_forward_returns: 任意ホライズンの将来リターンを一括取得する汎用関数（ホライズンの整合性チェックあり）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。十分な有効レコードがない場合は None。
    - rank: 同順位は平均ランクで扱うランク変換実装（浮動小数点丸め対策あり）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。

### Notable design decisions / behavior
- ルックアヘッドバイアス防止:
  - AI スコアリングやレジーム判定の関数群は datetime.today() / date.today() に依存しない設計。
  - DB クエリで target_date 未満／前日等の排他条件を厳格に使用。
- フェイルセーフ優先:
  - OpenAI 呼び出し失敗時は多くのケースでゼロやスキップで継続（例外を上位に投げない設計がデフォルト）。ただし API キー未指定等、事前に致命的と判断できる場合は ValueError を送出。
- テスト支援:
  - OpenAI 呼び出しを行う内部関数（news_nlp._call_openai_api, regime_detector._call_openai_api）を差し替え可能にしてユニットテストを容易に。
- DuckDB 互換性考慮:
  - executemany に空リストを渡せない DuckDB の制約を考慮した実装（空チェックを行う）。
- DB 書き込みは可能な限り冪等に（DELETE→INSERT や ON CONFLICT 相当の保存想定）している。

### Known limitations
- OpenAI API キー（OPENAI_API_KEY）や各種必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）が未設定だと一部機能（score_news, score_regime, 外部 API 経由の ETL 等）が実行できず ValueError を投げます。README や .env.example を参照して環境を準備してください。
- パッケージ __all__ では strategy, execution, monitoring を公開していますが、本リリースでの実装範囲は主に data / ai / research に集中しています（今後のリリースで追加機能を充実予定）。
- OpenAI の JSON Mode を前提に実装しているため、モデルの挙動変更や SDK の変更に伴う調整が必要になる可能性があります。
- DuckDB のバージョン差や将来の仕様変更により executemany やリスト型バインドの挙動が変わる可能性があるため、注意が必要です。

### Breaking Changes
- 初期リリースのため既知の破壊的変更はありません。

---

（今後の変更はこのファイルに追記していきます。）