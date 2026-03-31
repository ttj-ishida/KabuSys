# CHANGELOG

すべての重要な変更はこのファイルに記録します。
本ファイルは「Keep a Changelog」のフォーマットに準拠しています。

現在の日付: 2026-03-31

なお、本変更履歴は提示されたコードベースの内容から推測して作成したものであり、実際のコミット履歴ではありません。

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買プラットフォーム「KabuSys」のコア機能群を実装。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョンを `0.1.0` として定義。
  - パッケージの公開モジュールを __all__ で定義（data, strategy, execution, monitoring）。

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート自動検出機能を追加（.git または pyproject.toml を探索）。
  - .env ファイルの高度なパースロジックを実装（コメント、export プレフィックス、クォート内のエスケープ処理、インラインコメントの取り扱い）。
  - 自動ロードの無効化環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応。
  - 必須設定取得用 `_require`、環境のバリデーション（KABUSYS_ENV、LOG_LEVEL）を実装。
  - デフォルト値：KABUSYS_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH など。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（ai_score）を算出し ai_scores テーブルへ書き込む。
    - 対象時間ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を計算する calc_news_window を実装。
    - API バッチ処理（最大 20 銘柄 / チャンク）、記事数・文字数のトリム、レスポンスの厳密なバリデーション、スコアの ±1 クリップを実装。
    - リトライ（429・ネットワーク・タイムアウト・5xx）を指数バックオフで実施。失敗時は個別チャンクをスキップして継続するフェイルセーフ設計。
    - DuckDB の executemany の空リスト制約を考慮した安全な DB 書き込みロジック（DELETE → INSERT）を実装。
    - テスト容易性のため、OpenAI API 呼び出し部を差し替え可能に設計（ユニットテストでモック可能）。

  - レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を日次で判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出のためのキーワードリストと、OpenAI（gpt-4o-mini）呼び出しロジックを実装。API エラー時は macro_sentiment=0.0 でフォールバックするフェイルセーフを採用。
    - レジームスコアの合成、閾値判定（ブル・ベア閾値）を実装。
    - DB クエリはルックアヘッドバイアスを防ぐ条件（date < target_date 等）を徹底。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた JPX カレンダー管理ロジックを実装（営業日判定、next/prev_trading_day、get_trading_days、is_sq_day）。
    - DB 登録が無い・未登録日の場合は曜日ベースのフォールバックを使用する一貫した挙動。
    - calendar_update_job を実装（J-Quants API から差分取得 → 保存。バックフィルと健全性チェックあり）。
    - 最大探索範囲やバックフィル・先読み日数などの定数を定義し無限ループや誤動作を防止。

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETL 実行結果を表現する ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラー一覧を保持）。
    - 差分取得のためのユーティリティ（テーブル最大日付取得等）を実装。
    - J-Quants クライアント（jquants_client）および品質チェック（quality）との連携を想定。
    - 初期データロードやバックフィルのための定数（最小データ日、バックフィル日数等）を定義。

- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン）、200 日 MA 乖離（ma200_dev）、ATR ベースのボラティリティ、流動性指標（20 日平均売買代金、出来高比）を計算する関数を実装。
    - raw_financials を用いたバリューファクター（PER、ROE）計算を実装。
    - DuckDB の SQL ウィンドウ関数を活用して効率的に計算。
    - データ不足時（必要な行数以下）は None を返す安全な設計。

  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：複数ホライズン（デフォルト [1,5,21]）に対応、ホライズンの妥当性チェックを実装。
    - IC（Information Coefficient）計算（calc_ic）：スピアマンランク相関を実装し、データ不足（有効ペア < 3）時は None を返す。
    - ランク変換ユーティリティ（rank）とファクター統計サマリー（factor_summary）を実装。外部依存を使わず標準ライブラリのみで実装。

- 内部ユーティリティ・設計方針
  - ルックアヘッドバイアス防止のため、各モジュールで datetime.today()/date.today() を直接参照しない設計を徹底（すべて target_date を明示的に受け取る）。
  - OpenAI 呼び出しは明示的に API キー引数 or 環境変数 OPENAI_API_KEY で解決。未設定時は ValueError を発生させる。
  - OpenAI レスポンスは JSON モードを前提に厳密にパースし、不整合時はフェールセーフでスキップまたは中立値を採用。
  - DuckDB を前提とした SQL 実装（日付型変換ユーティリティ、テーブル存在チェックなど）を提供。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- 環境変数の読み込み時、既存の OS 環境変数を保護するためにプロテクトセットを導入（.env ロード時の上書き制御）。
- OpenAI API キーの取り扱いは明示的に渡すか環境変数から取得する設計。未設定時は例外を発生させるため誤用が早期に発見可能。

### Known issues / Limitations
- OpenAI API に依存する機能（news_nlp, regime_detector）は有料 API を利用し、レスポンス形式の変化やモデル仕様変更に弱い。現実環境ではレート制限・コスト管理が必要。
- DuckDB のバージョンによりパラメータバインドの挙動が変わるため、executemany の空リスト禁止等のワークアラウンドが入っている。DuckDB のメジャーアップデート時は互換性テストが必要。
- 一部関数は jquants_client や quality モジュールに依存している（これらは本リポジトリ外または未提示）。実行にはそれらの実装が必要。
- calendar_update_job は J-Quants クライアントの実装に依存する。API エラー時は 0 を返すフェイルセーフ挙動。

### 互換性の注意事項
- DB スキーマとして以下のテーブルを参照／更新する実装が含まれます。実行前にスキーマを準備してください。
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar
- 環境変数名:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL, OPENAI_API_KEY, KABUSYS_DISABLE_AUTO_ENV_LOAD
- OpenAI のレスポンスフォーマット（JSON Mode）に依存しているため、モデル変更時はレスポンス検証ロジックの見直しが必要。

---

今後のリリースに含める想定の項目（例）
- strategy / execution / monitoring パッケージの実装（現行コードでは __all__ に含まれるが詳細未提示）。
- 単体テスト、統合テスト、CI 設定の追加。
- モデル／API の抽象化レイヤー強化（コスト管理、メトリクス収集）。
- スキーマ移行スクリプトや初期 DB 作成ユーティリティの追加。