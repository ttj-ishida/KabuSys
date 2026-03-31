# CHANGELOG

すべての重要な変更は Keep a Changelog の形式で記載します。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買システムのコアライブラリを提供します。主な追加点は以下のとおりです。

### Added
- パッケージ初期化
  - kabusys パッケージを追加。バージョンは 0.1.0。公開モジュールとして data, strategy, execution, monitoring をエクスポート。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - プロジェクトルート自動検出ロジックを実装（.git または pyproject.toml を基準）。パッケージ配布後も CWD に依存しない設計。
  - .env パーサーを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどに対応）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト用）。
  - 必須設定取得用の _require ヘルパーと Settings クラスを実装。J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等のプロパティを提供。
  - 環境値検証を実装（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

- AI（LLM）機能 (kabusys.ai)
  - news_nlp モジュールを追加:
    - raw_news と news_symbols を集約して銘柄ごとのニュース本文を構築し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント ai_score を算出。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を実装。
    - バッチサイズ、記事数上限、文字数トリム、429/ネットワーク/タイムアウト/5xx のリトライ（指数バックオフ）など、実運用向けの堅牢な API 呼び出し制御。
    - JSON mode レスポンスのバリデーション、パースの復元処理（前後テキストが混入するケースへの対処）、スコアクリップ（±1.0）。
    - 部分成功時に既存スコアを上書きしないよう、対象コードのみを DELETE → INSERT する冪等的書き込み処理（DuckDB の executemany の注意点に対応）。
    - API キー注入（api_key 引数または OPENAI_API_KEY 環境変数）をサポート。

  - regime_detector モジュールを追加:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull / neutral / bear）を判定。
    - prices_daily, raw_news を参照して ma200_ratio とマクロ記事抽出を行い、OpenAI（gpt-4o-mini）でマクロセンチメントを取得。
    - API の冗長性対策（リトライ／バックオフ）、JSON パース失敗や API エラー時は macro_sentiment=0.0 でフォールバックするフェイルセーフ設計。
    - 判定結果を market_regime テーブルへ冪等的に書き込むトランザクション処理（BEGIN / DELETE / INSERT / COMMIT）と、失敗時の ROLLBACK を実装。
    - テスト容易性のため OpenAI 呼び出しは内部ユーティリティ関数化し、差し替え可能に設計。

- データ基盤ユーティリティ (kabusys.data)
  - calendar_management モジュールを追加:
    - JPX カレンダーの夜間バッチ更新 job（calendar_update_job）を実装。J-Quants API から差分取得して market_calendar テーブルへ冪等保存（ON CONFLICT 相当の保存処理を想定）。
    - 営業日判定ユーティリティ群を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar が未取得または該当日が未登録の場合は曜日ベース（平日のみ営業日）でフォールバックする堅牢なロジック。
    - 探索上限（最大探索日数）やバックフィル、健全性チェック（将来日付の異常検出）など安全装置を実装。

  - ETL / pipeline モジュールを追加:
    - ETLResult データクラスを公開し、ETL 実行結果（取得数、保存数、品質チェック結果、エラー等）を集約できるように実装。
    - 差分更新、バックフィル、品質チェックを想定した設計（jquants_client 経由での差分取得と idempotent な保存、品質チェックの集約）。
    - 内部ユーティリティとしてテーブル存在チェックや最大日付取得ロジックを実装。

  - etl モジュールは pipeline.ETLResult を再エクスポート。

- Research（分析）機能 (kabusys.research)
  - factor_research モジュールを追加:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）などのファクター計算を実装。
    - DuckDB を用いた SQL ベースの計算で prices_daily / raw_financials のみ参照する安全設計。
    - データ不足時の None 処理やログ出力を含む堅牢な実装。
  - feature_exploration モジュールを追加:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を実装。
    - pandas 等に依存せず、標準ライブラリと DuckDB で実装。rank は同順位を平均ランクで扱う。

- 汎用・実装上の配慮
  - duckdb を前提とした接続インターフェースで各種処理（AI スコア書き込み／市場レジーム書き込み／ファクター計算）を行う。
  - 多くの関数でルックアヘッドバイアス防止を明示（datetime.today()/date.today() を直接参照しない、target_date パラメータに依存する設計）。
  - OpenAI 呼び出しはテスト差し替えを容易にするため内部関数化（unittest.mock.patch で差し替え可能）。
  - ログ出力（logger）と例外処理によりフェイルセーフ／観察性を高める実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーなどの秘密情報は Settings 経由で明示的に取得する設計。自動ロード挙動は環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

注:
- 実装はコードベースから推測して記載しています。運用時の API クレデンシャル設定や DB スキーマ（prices_daily, raw_news, ai_scores, market_calendar, raw_financials 等）は別途用意する必要があります。