Keep a Changelog に準拠した CHANGELOG.md
※コードベースから推測して作成しています。

全般
- このプロジェクトは "KabuSys - 日本株自動売買システム" の初期リリースです。
- 日付はこの CHANGELOG 作成時点（2026-03-28）をリリース日に設定しています。

Unreleased
- なし

[0.1.0] - 2026-03-28
Added
- パッケージ初期リリース。
  - パッケージ名: kabusys、バージョン 0.1.0 (src/kabusys/__init__.py)
- 環境変数・設定管理 (kabusys.config)
  - .env および .env.local からの自動ロードを実装（プロジェクトルートを .git / pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env のパース機能を強化（export プレフィックス、シングル/ダブルクォート、エスケープ、行末コメント処理など）。
  - Settings クラスを提供し、各種必須設定をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスを指定）
    - KABUSYS_ENV (development|paper_trading|live) と LOG_LEVEL の検証プロパティ
  - 未設定必須環境変数で ValueError を送出する保護機構。
- AI（自然言語処理）モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news / news_symbols を銘柄単位に集約して OpenAI（gpt-4o-mini）でセンチメント評価。
    - バッチ処理（最大 20 銘柄／リクエスト）、各銘柄は記事数と文字数でトリム。
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフとリトライ。
    - レスポンス検証（JSON 抽出、results 配列、code と score の検証）とスコアの ±1.0 クリップ。
    - 成功した銘柄のみ ai_scores テーブルを置換する（DELETE → INSERT）ことで部分失敗耐性を確保。
    - API 呼び出し箇所はテスト差し替えしやすいプライベート関数で分離。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - news_nlp のタイムウィンドウ計算 calc_news_window と連携。
    - マクロキーワードでニュースを抽出し、OpenAI（gpt-4o-mini）で macro_sentiment を取得（記事が無ければ呼び出しなし、API 失敗時は 0.0 にフォールバック）。
    - 冪等に market_regime テーブルへ書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。
- データプラットフォーム・ETL (kabusys.data)
  - pipeline.ETLResult を含む ETL 用インターフェースを実装:
    - ETL 実行結果を表す dataclass（取得件数、保存件数、品質問題リスト、エラー一覧、ユーティリティ）。
    - quality チェック結果の集約や has_errors / has_quality_errors プロパティを提供。
  - calendar_management:
    - market_calendar 管理および営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日ベースでフォールバック（週末のみ非営業日扱い）。
    - 夜間の calendar_update_job を実装（J-Quants API 経由で差分取得 → 保存、バックフィル、健全性チェック）。
    - market_calendar がまばらな場合でも挙動が一貫するよう DB 優先・未登録日はフォールバック。
  - ETL パイプライン基盤（差分取得、backfill、品質チェックの方針をコード化）。
- リサーチ（ファクター計算） (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時の None 処理）。
    - calc_volatility: 20 日 ATR（平均）、ATR 比率、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を算出（EPS が 0/欠損なら None）。
    - SQL + DuckDB による実装で外部 API に依存しない。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターンを一度に取得可能（デフォルト [1,5,21]）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装（有効レコード 3 未満なら None）。
    - rank: 同順位は平均ランクで扱うランク関数（丸めによる ties 回避）。
    - factor_summary: count/mean/std/min/max/median を算出する統計ユーティリティ。
  - research モジュールは本番発注にはアクセスせず、prices_daily / raw_financials など DB テーブルのみ参照。
- 一貫した設計方針／安全策
  - ルックアヘッドバイアス防止: datetime.today() / date.today() を参照しない方式を採用（target_date を明示的に渡す）。
  - API エラーのフェイルセーフ: LLM や外部 API の失敗時は例外を直接伝播させず、既定値（例: macro_sentiment=0.0）で継続する箇所を設置。
  - DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT を想定した保存方法など）。
  - テストしやすい設計: OpenAI 呼び出し部分や内部関数は patch / mock で置き換え可能に分離。
  - DuckDB による SQL 実装を中心に、実行時の互換性を考慮（executemany の空リスト回避等の注意）。
- ロギング
  - 各モジュールで詳細な情報・警告・例外ログを出力するようになっている（info/debug/warning/exception を適切に使用）。

Changed
- 該当なし（初回リリース）

Fixed
- 該当なし（初回リリース）

Deprecated
- 該当なし（初回リリース）

Removed
- 該当なし（初回リリース）

Security
- 環境変数による API キー管理を想定（OPENAI_API_KEY 等）。特別なセキュリティ修正は未実装。

Migration notes / 注意事項
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings のプロパティで必須とされており、未設定時は ValueError が発生します。
  - OPENAI_API_KEY は news_nlp.score_news および regime_detector.score_regime のデフォルト解決先（関数呼び出し時に明示的に api_key を渡すことも可能）。
- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込みする。テスト時やカスタム起動では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- データベースのデフォルトパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- DuckDB のバージョンや executemany の挙動に依存する箇所があるため、DuckDB を更新する際は executemany の仕様を確認してください。
- LLM（OpenAI）呼び出しは gpt-4o-mini を想定。将来変更する場合は response_format や戻り JSON 仕様に注意。

既知の制約・実装方針（参考）
- news_nlp/score_news と regime_detector/score_regime は LLM のレスポンスに依存するため、外部 API の仕様変更やレート制限に影響を受けます。両モジュールはリトライやフォールバックを備えていますが、運用時は API キー管理・コスト・レート制限に注意してください。
- 全ての日時操作は timezone-naive な date/datetime を用いる設計（UTC と JST の変換を明示的に扱う箇所あり）。タイムゾーン混在に注意してください。

開発者向けメモ
- OpenAI 呼び出し点は _call_openai_api などで分離しており、ユニットテストでは unittest.mock.patch による差し替えが容易です。
- DB 書き込みは可能な限り冪等化してあり、部分失敗時に既存データを不必要に消さない実装になっています（ai_scores の部分DELETEや market_regime の日付単位置換等）。

今後の予定（推測）
- 追加ファクターの実装（PBR・配当利回りなど）。
- モデルやプロンプト改善、LLM 呼び出しの抽象化（複数ベンダー対応）。
- より詳細な品質チェックモジュールの統合と ETL の自動化ジョブ化。

--- 
（この CHANGELOG はコードから仕様・設計意図を推測して作成しています。実際のリリースノート作成時は開発履歴やコミットログを参照して調整してください。）