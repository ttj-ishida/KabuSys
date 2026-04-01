# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に従います。  
慣例によりバージョンは SemVer に準拠します。

## [0.1.0] - 2026-04-01
初回公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開。バージョンは 0.1.0。
  - パッケージ公開用の __all__（data, strategy, execution, monitoring）とバージョン定義を追加。

- 設定・環境読み込み
  - .env / .env.local 自動読み込み機能を実装。
  - プロジェクトルート探索は __file__ を起点に .git / pyproject.toml を探索して行う（CWD に依存しない）。
  - export KEY=val 形式、クォート付き値や行内コメントの扱い、コメント行スキップ等に対応するパーサ実装。
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 監視閾値 / ログレベル 等を環境変数から取得するプロパティ群を用意。
  - 必須環境変数未設定時は ValueError を送出して早期検出を助ける。

- AI（OpenAI）連携
  - kabusys.ai.news_nlp: ニュース記事群から銘柄ごとのセンチメントを算出して ai_scores テーブルへ書き込むスコアリング実装。
    - JST 時間ウィンドウ（前日 15:00 ～ 当日 08:30）に基づく対象抽出（UTC 変換済み）。
    - 1 銘柄あたり記事数・文字数のトリム（トークン肥大対策）。
    - バッチ（最大 20 銘柄）で OpenAI Chat Completions（gpt-4o-mini）へ送信。
    - JSON Mode を利用して厳密な JSON 出力を期待、レスポンスのバリデーションを行う。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライを実装。
    - レスポンスパース失敗や API エラーはスキップ（フェイルセーフ）して処理継続。
    - DuckDB に対する置換操作は DELETE→INSERT の方式で idempotent に実行。DuckDB 0.10 の executemany 空リスト制約に配慮。
    - テスト容易性のため _call_openai_api をモック差し替え可能（unittest.mock.patch 対応）。

  - kabusys.ai.regime_detector: 市場レジーム（bull/neutral/bear）判定機能を実装。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成。
    - マクロニュースはニュースタイトルをマクロキーワードでフィルタして取得。
    - OpenAI 呼び出しは gpt-4o-mini（JSON mode）を利用。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - レジームの算出から market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API 呼び出しのリトライ/バックオフと 5xx 判定の扱いを実装。
    - ルックアヘッドバイアス防止のため、内部で datetime.today()/date.today() を参照しない設計。

- リサーチ（Factor / Feature）
  - kabusys.research.factor_research:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER/ROE）等のファクター計算を提供。
    - DuckDB のウィンドウ関数を活用し、営業日ベースのホライズンを扱う実装。
    - データ不足時は None を返して downstream に伝播。
  - kabusys.research.feature_exploration:
    - 将来リターン計算（任意ホライズン）、Information Coefficient（Spearman）の計算、ランク変換、ファクター統計サマリを提供。
    - pandas 等の外部依存を用いず標準ライブラリのみで実装。

- データプラットフォーム（ETL / カレンダー）
  - kabusys.data.calendar_management:
    - JPX カレンダー管理（market_calendar）の読み書き・夜間更新ジョブ（calendar_update_job）を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定 API を提供。
    - DB 登録がない場合は曜日ベース（土日非営業）でフォールバックする一貫したロジック。
    - 最大探索日数制限など異常検知を実装。
    - J-Quants クライアントを介して差分取得→保存を実行（バックフィル期間を考慮）。
  - kabusys.data.pipeline:
    - ETLResult dataclass を提供し、ETL 実行結果（取得数/保存数/品質問題/エラー）を構造化して返却。
    - 差分更新・バックフィル・品質チェックの方針を実装するための基礎機能を実装。
  - kabusys.data.etl:
    - pipeline.ETLResult の再エクスポート（公開インターフェース）。

- その他
  - OpenAI クライアント利用箇所で JSON Mode を利用し、レスポンスの厳密な JSON 出力を期待する設計。
  - 各所で詳細なログ出力（info/warning/debug）を実装して運用/トラブルシュートを支援。

### Security
- 環境変数の自動読み込み時、既存の OS 環境変数は protected として .env/.env.local による上書きを保護する仕組みを実装。
- 必須トークン（OPENAI_API_KEY 等）は Settings のプロパティで明示的にチェックし、未設定時は ValueError を送出することで誤った公開動作を防止。

### Known issues / Notices（注意事項・既知の問題）
- pipeline._get_max_date の末尾に不完全なコード（"return date.fro" のような切れた記述）が存在しており、現状では構文エラー / 実行時エラーとなる可能性があります。該当関数は実行前に修正が必要です（初期実装のスニペットが途中で切れていると思われます）。
- data/__init__.py は現状で実体が空で、必要なサブモジュールの再エクスポートを追加することが想定されます。
- jquants_client など外部クライアント実装（fetch/save 等）は別モジュールに依存しており、実行にはそれらの実装・設定が必要です。
- OpenAI（gpt-4o-mini）を利用するため実運用には OPENAI_API_KEY の設定が必須。API コストやレート制限に注意してください。

### Upgrade notes
- 初回セットアップ時は .env/.env.example を参照して必須環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、OPENAI_API_KEY 等）を設定してください。
- DuckDB / SQLite のデフォルトパスは Settings に設定されていますが、環境変数（DUCKDB_PATH / SQLITE_PATH）で変更可能です。
- 自動 .env ロードを無効化したいテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

（将来的に各変更を個別バージョンで細分化して追記してください）