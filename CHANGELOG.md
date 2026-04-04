# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に従います。
このリポジトリはセマンティックバージョニングに従います。

## [0.1.0] - 2026-04-04
初回リリース

### 追加
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
  - 公開サブパッケージ: data, strategy, execution, monitoring を __all__ に登録。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルートを .git または pyproject.toml を起点に探索する自動ローダーを実装（CWD 非依存）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env 読み込みの優先順位: OS 環境変数 > .env.local > .env。.env.local は既存環境変数を上書き可能。
  - .env パーサの実装:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォートなし行のインラインコメント認識（'#' の前が空白/タブの場合のみ）。
    - ファイル読み込み失敗時に警告を出力し継続。
    - 上書き禁止キーセット（protected）を用いた安全な上書き制御。
  - 設定プロパティを多数用意（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD,
    KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, DUCKDB_PATH, PID_FILE_PATH 等）。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値集合をチェックし不正値は ValueError）。
  - 便利プロパティ: is_live, is_paper, is_dev。

- AI（ニュース NLP / レジーム判定）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）に JSON-mode で評価させる処理を実装。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/コール）、1銘柄あたりの最大記事数・文字数制限によるトークン肥大化対策。
    - 失敗時のリトライ（429/ネットワーク断/タイムアウト/5xx を対象）と指数バックオフを実装。
    - レスポンスの堅牢なバリデーションとスコアクリップ（±1.0）。
    - DuckDB への冪等書き込み（取得済みコードのみ削除→挿入）と部分失敗時の保護（他コードの既存スコアを消さない）。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api を patch 可能）。
    - 公開関数: score_news(conn, target_date, api_key=None) は書き込んだ銘柄数を返す。
    - タイムウィンドウ計算 util: calc_news_window(target_date)（JST基準 → UTC naive datetime を返す）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei 225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - OpenAI 呼び出しは gpt-4o-mini の JSON-mode を使用、リトライ・バックオフ・5xx 判定の扱いを実装。
    - prices_daily と raw_news を参照して ma200_ratio と macro_sentiment を計算。
    - レジームスコア合成と DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時に ROLLBACK を試み適切に例外伝播。
    - API キー解決: 引数 api_key または環境変数 OPENAI_API_KEY。未設定時は ValueError。
    - フェイルセーフ: API 失敗時は macro_sentiment=0.0 へフォールバックし処理継続。

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar を参照する営業日判定ユーティリティを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがない場合は曜日ベース（土日除外）でフォールバックする一貫したロジックを採用。
    - next/prev_trading_day の探索は最大 _MAX_SEARCH_DAYS（安全上の上限）を設けて無限ループを防止。
    - calendar_update_job: J-Quants クライアントを使った夜間バッチの差分取得、バックフィル、健全性チェック、保存処理（jq.fetch_market_calendar / jq.save_market_calendar を呼ぶ）。
    - DB の NULL 値や不整合に対する警告ログと保護ロジック。

  - ETL パイプライン（pipeline）
    - ETLResult データクラスを公開（kabusys.data.etl は再エクスポート）。
    - 差分更新・バックフィル・品質チェックを想定した設計（quality モジュールとの連携を想定）。
    - jquants_client を介した idempotent な保存（ON CONFLICT DO UPDATE）を前提とした処理フロー設計。
    - ETLResult.to_dict() により quality_issues をシリアライズ可能に。

- リサーチ / ファクター（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200日MA乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility(conn, target_date): 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。必要行数未満は None。
    - calc_value(conn, target_date): raw_financials と prices_daily を組み合わせて PER（EPS が 0/欠損なら None）、ROE を計算。
    - 設計方針: DuckDB 上の SQL と Python の組合せで実装、本番リスクのある外部 API 呼び出しは行わない。

  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns(conn, target_date, horizons=None): 任意ホライズンの将来リターンを一括取得。horizons の入力検証あり。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン順位相関（IC）を実装。有効レコード < 3 の場合は None。
    - rank(values): 同順位は平均ランク（ties の扱いは round による安定化）をするランク化ユーティリティ。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリー。
    - pandas 等外部依存を使わず標準ライブラリと DuckDB のみで実装。

### 変更（設計上の重要な方針）
- ルックアヘッドバイアス防止のため、いずれの分析/スコアリング関数も内部で datetime.today() / date.today() を参照しない設計（target_date を明示的に受け取る）。
- DuckDB 互換性のため、executemany に空リストを渡さない、リストバインドの互換性に配慮した実装。
- OpenAI 呼び出しはモジュール間でプライベート関数を共有せず、それぞれのモジュールで独立実装（テスト時は patch により差し替え可能）。
- DB 書き込みは可能な限り冪等操作（DELETE→INSERT / ON CONFLICT）で実装し、部分失敗時でも既存データを保護。

### 修正
- 初版につき、特定のバグ修正履歴はなし。各モジュールは堅牢化（入力検証、例外処理、ログ出力）を図っている。

### セキュリティ
- 環境変数の取り扱いにおいて OS 環境変数を protected として上書きを制御する仕組みを導入。
- OpenAI API キーは明示的に引数で注入可能とし、環境変数依存を緩和（テスト時の安全性向上）。

---

注:
- 本 CHANGELOG はコードベースからの推測に基づいて記載しています。実装の細かな挙動や外部依存（例: jquants_client の具体的挙動、quality モジュールの詳細、DB スキーマ）は本ファイルの範囲外です。必要であれば各モジュールの動作確認用の要約や使用例を追加で作成します。