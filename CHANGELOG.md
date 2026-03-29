# Changelog

すべての重要な変更は Keep a Changelog の方針に従って記載します。  
安定版リリースや大きな変更を追跡するための履歴です。

フォーマット詳細: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-29
初回公開リリース。日本株自動売買プラットフォームのコア機能群を実装。

### Added
- パッケージのエントリポイント
  - `kabusys` パッケージを追加。サブモジュール公開: data, strategy, execution, monitoring。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 環境設定 / 設定管理 (`kabusys.config`)
  - .env ファイル（`.env` / `.env.local`）および OS 環境変数から自動で設定を読み込む機構を実装。
  - プロジェクトルートの検出は `.git` または `pyproject.toml` を基準とし、パッケージ配布後も CWD に依存しない設計。
  - `.env` パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
  - 自動読み込みの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト時に有用）。
  - `Settings` クラスを提供し、必須設定取得（未設定時は ValueError）や妥当性検証（KABUSYS_ENV, LOG_LEVEL 等）を実装。
  - デフォルトの DB パス（DuckDB/SQLite）や API ベース URL 等のプロパティを提供。

- データ処理 / カレンダー管理 (`kabusys.data.calendar_management`)
  - JPX マーケットカレンダーの管理ロジックを実装（market_calendar テーブルの読み書き用ユーティリティ）。
  - 営業日判定・前後営業日取得・期間の営業日列挙（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
  - DB にカレンダー情報がない場合の曜日ベースフォールバックを実装（週末を非営業日扱い）。
  - 夜間バッチジョブ `calendar_update_job`（J-Quants から差分取得して冪等的に保存）を実装。バックフィルや健全性チェックを組み込み。

- ETL / パイプライン基盤 (`kabusys.data.pipeline`, `kabusys.data.etl`)
  - ETL の成果を表す `ETLResult` データクラスを実装（取得件数、保存件数、品質問題、エラー一覧などを保持）。
  - 差分取得、バックフィル、品質チェック方針を想定したパイプライン用ユーティリティ群を実装。
  - DuckDB との互換性に配慮した実装（存在チェック、MAX 日付取得、executemany の空リストに関する注記等）。

- AI / ニュース NLP (`kabusys.ai.news_nlp`)
  - raw_news / news_symbols を基に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）を用いたセンチメントスコアリングを実装。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換）を厳密に定義する `calc_news_window` を実装。
  - バッチ処理: 最大 20 銘柄/回でのバッチ送信、1 銘柄につき最大記事数と文字数でトリム（過剰なトークン膨張を防止）。
  - OpenAI 呼び出しでの再試行（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装。  
  - レスポンスの厳密なバリデーションと JSON 抽出処理（前後の余計なテキストを除去する復元ロジック含む）、スコアの ±1.0 クリップ。
  - DB への書き込みは部分失敗耐性を持たせ、対象コードのみ DELETE→INSERT（冪等性・部分失敗時の保護）を実装。
  - テスト容易性: OpenAI 呼び出し箇所をモジュール内でラップし patch で差し替え可能に設計。

- AI / レジーム判定 (`kabusys.ai.regime_detector`)
  - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し市場レジーム（bull / neutral / bear）を日次判定する実装を追加。
  - prices_daily と raw_news からデータを取得し、ma200_ratio を計算する `_calc_ma200_ratio` 実装（データ不足時は中立値 1.0 を採用してフェイルセーフ化）。
  - マクロニュース抽出ロジック（キーワードリスト）と LLM 呼び出し、複数種の API エラーに対するリトライ/フォールバック（最終的に macro_sentiment=0.0）を実装。
  - 判定結果を market_regime テーブルへ冪等的に保存（BEGIN / DELETE / INSERT / COMMIT、例外時の ROLLBACK ロギング）。

- リサーチ / ファクター計算 (`kabusys.research`)
  - ファクター計算モジュール（momentum / value / volatility）を実装:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None を返す）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比等を算出。
  - 特徴量探索ユーティリティ:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを取得。horizons の妥当性検証（1〜252）を実施。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装（有効サンプルが 3 未満なら None）。
    - rank: 同順位は平均ランクとするランク化処理。
    - factor_summary: 各ファクターの基本統計量（count/mean/std/min/max/median）を計算。
  - 設計観点として DuckDB 上で SQL と Python の組合せで計算し、外部 API を呼ばない方針を遵守。

- 一般的な堅牢性・設計方針
  - ルックアヘッドバイアス排除: どのモジュールも内部で datetime.today()/date.today() を参照せず、明示的な target_date を受け取る設計。
  - フェイルセーフ: 外部 API（OpenAI / J-Quants 等）失敗時はスキップまたは既定値を用いて処理継続する方針を採用。
  - DuckDB トランザクション処理における明示的な BEGIN/COMMIT/ROLLBACK と ROLLBACK 失敗時のログ出力を実装。
  - テスト容易性のため、API 呼び出し部分は内部関数でラップして差し替え可能に実装（unittest.mock.patch を想定）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

### Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（OpenAI を利用する場合）
  - 環境設定は .env/.env.local もしくは OS 環境変数から利用可能
- テスト時のヒント:
  - 自動 .env 読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
  - OpenAI 呼び出しは内部の `_call_openai_api` を patch してモック可能
- DuckDB 注意点:
  - executemany に空リストを渡すとエラーになるバージョンがあるため、空チェックを入れている（ETL / ai モジュールで対応済み）

今後取り組む予定:
- strategy / execution / monitoring の具体的なアルゴリズム・発注連携の実装
- (改善) OpenAI レスポンスのさらなる堅牢化やコスト最適化（モデル選択やバッチ戦略の調整）
- (改善) エンドツーエンドの統合テストと CI パイプライン整備

-----

（この CHANGELOG はソースコードの実装内容を基に推測して作成しています。実際のリリースノートはプロジェクトの正式なリリースポリシーに従って調整してください。）