# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

※このリリースノートは、提供されたコードベースの内容から推測して作成しています。

## [Unreleased]

---

## [0.1.0] - 2026-03-31

### Added
- パッケージ初期リリース。モジュール構成（kabusys）と主要機能を追加。
  - パブリック API: kabusys パッケージ（data, research, ai, config, execution, monitoring を想定）。
  - バージョン: `__version__ = "0.1.0"` を設定。

- 環境設定管理（kabusys.config）
  - プロジェクトルートを .git または pyproject.toml から自動検出し、ルート直下の `.env` / `.env.local` を自動読み込み（優先順: OS環境変数 > .env.local > .env）。
  - `.env` パーサ実装:
    - コメント・export プレフィックス・シングル/ダブルクォート・バックスラッシュエスケープ等に対応。
    - クォートなし値のインラインコメント処理（直前が空白/タブの場合は '#' をコメントと認識）。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを抑制可能（テスト用途）。
  - `Settings` クラスを提供し、主要設定をプロパティ経由で取得:
    - J-Quants: `JQUANTS_REFRESH_TOKEN`（必須）
    - kabuステーション: `KABU_API_PASSWORD`（必須）、`KABU_API_BASE_URL`（デフォルト値あり）
    - Slack: `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`（必須）
    - DBパス: `DUCKDB_PATH`（デフォルト `data/kabusys.duckdb`）、`SQLITE_PATH`（デフォルト `data/monitoring.db`）
    - 環境/ログレベル検証: `KABUSYS_ENV` は `development|paper_trading|live`、`LOG_LEVEL` は標準レベルのみ許容。
    - ヘルプ的エラーメッセージを返す必須チェック（未設定時は ValueError）。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols テーブルのニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとに -1.0〜1.0 のセンチメントスコアを算出・ai_scores テーブルへ書き込み。
    - ウィンドウ計算（JSTベースの前日15:00～当日08:30、内部は UTC naive で扱う）を提供（calc_news_window）。
    - バッチ処理（最大 20 銘柄/回）、記事数・文字数トリム、レスポンスバリデーション、スコアクリップ、リトライ（429/ネットワーク/5xx 等）、エラー時はスキップして継続するフェイルセーフ設計。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（内部関数に patch 可能）。
    - DuckDB の executemany 空リスト制約に配慮して条件分岐。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（"bull"/"neutral"/"bear"）を判定し、market_regime テーブルへ冪等書き込み。
    - マクロニュースは news_nlp の calc_news_window を利用して抽出。記事が無ければ LLM 呼び出しを行わず macro_sentiment=0.0 を使用。
    - OpenAI 呼び出しに対するリトライ・バックオフ、APIエラーやパース失敗時の安全フォールバックを実装。
    - ルックアヘッドバイアス対策（target_date 未満のみ参照、datetime.today() を直接参照しない）を明示。

- データモジュール（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを参照する営業日判定ユーティリティ群:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB にカレンダーがない場合は曜日ベースでフォールバック（土日非営業日扱い）。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等に更新。バックフィル・健全性チェックを実装（最大探索日数制限）。
  - ETL パイプライン（kabusys.data.pipeline, etl）
    - ETLResult データクラスを公開し、ETL の取得数／保存数／品質問題／エラーを集約。
    - 差分取得・バックフィル・品質チェック（quality モジュール想定）設計に準拠。
    - 内部ユーティリティでテーブル存在チェック／最大日付取得等を提供。
    - デフォルトのバックフィルなどの定数を定義（例: backfill_days=3 等）。
  - jquants_client など外部クライアント呼び出しのラッパーを想定（コード内で参照）。

- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を算出（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を算出（データ不足時は None）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（EPS 0/欠損時は None）。
    - 全関数は DuckDB 上の SQL を主体にしており、外部 API を呼ばず本番口座へはアクセスしない。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズンの将来終値リターン（デフォルト [1,5,21]）。
    - calc_ic: スピアマンのランク相関（IC）を計算。サンプル数不足時は None。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
    - rank: 同順位は平均ランクを返す実装（round による tie 対策）。
  - research パッケージはデータ処理と統計解析を用途別に分離。

- ロギングとトランザクション
  - 多くの書き込み処理で BEGIN / DELETE / INSERT / COMMIT を使う冪等操作を採用。例外時は ROLLBACK を呼び、失敗ログを出力する実装。
  - 各モジュールで詳細な情報ログ・警告ログを出力するように設計。

### Changed
- 初回リリースのためなし。

### Fixed
- 初回リリースのためなし。

### Security
- OpenAI API キー: `OPENAI_API_KEY` を環境変数または関数引数で与える必要あり。未設定時は ValueError を送出する箇所あり（news_nlp.score_news, regime_detector.score_regime）。
- 環境変数の読み込みは OS 環境変数を保護（.env の上書きを制限）する設計。

### Notes / Migration / 使用上の注意
- 必須環境変数（最低限設定が必要なもの）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY
- 自動 .env 読み込みはパッケージ配布後も .__file__ を基点にプロジェクトルートを探索するため、CWD に依存しないよう設計されています。テスト等で自動読み込みを抑止するには `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定してください。
- DuckDB の executemany の挙動に依存する箇所があるため（空リスト禁止など）、DuckDB バージョン互換性に注意してください（注釈がコード内にあります）。
- LLM による解析は外部 API を用いるため、呼び出し制限や料金に注意。失敗時は多くの箇所でフォールバック（スコア0.0やスキップ）するためフェイルセーフが組み込まれていますが、部分的に結果が欠落する可能性があります。
- 時刻関連: News ウィンドウやその他の日時処理は意図的に date/datetime の扱いを慎重に行っており、ルックアヘッドバイアスを防ぐために内部で datetime.today()/date.today() を直接参照しない設計になっています。ウィンドウの取り扱いは UTC naive datetime を使う点に注意してください。

### Breaking Changes
- 初回リリースのためなし。

---

今後のリリースでは、テストカバレッジ、より詳細な quality チェック、追加のデータ保存先やバックテスト機能、運用用の監視／通知機能の拡張が予定される可能性があります。必要であれば、各モジュールごとにさらに詳細なリリースノート（例: API サンプル、既知の制約、パフォーマンス注意点）を追加します。