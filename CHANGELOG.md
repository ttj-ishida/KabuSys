# CHANGELOG

すべての変更は「Keep a Changelog」形式に従い記載しています。  
バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）に合わせています。

## [Unreleased]

## [0.1.0] - 2026-04-04

### Added
- パッケージ初版を公開。
- 基本パッケージ構成を追加:
  - kabusys.data, kabusys.research, kabusys.ai, kabusys による公開 API 群を整備。
- 環境設定管理（kabusys.config）を実装:
  - .env/.env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト向け）。
  - .env パース機能を実装（コメント行、export プレフィックス、クォート中のエスケープ、行内コメントの扱いなどに対応）。
  - 環境変数上書きロジック（override / protected）を実装し、OS 環境変数の保護を考慮。
  - Settings クラスを提供し、アプリ設定をプロパティとして取得（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、LINE 等、DB パス、監視閾値、環境判定、ログレベル等）。

- AI モジュール（kabusys.ai）:
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）を実装。
    - raw_news / news_symbols を集約し、銘柄ごとに記事を結合して OpenAI（gpt-4o-mini）の JSON Mode で一括スコアリング。
    - チャンク（最大20銘柄）単位で API コール、トークン肥大化軽減のため記事数・文字数の制限（最大記事数・最大文字数）。
    - 429/ネットワーク切断/タイムアウト/5xx に対する指数バックオフリトライ。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results フォーマット確認、未知コード無視、数値チェック、±1.0 クリップ）。
    - DuckDB への冪等的な書き込み（対象コードのみ DELETE → INSERT）と、部分失敗時の既存スコア保護。
    - テストのため _call_openai_api をモック差し替え可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）を実装。
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム（bull / neutral / bear）を判定。
    - prices_daily / raw_news を参照し、OpenAI（gpt-4o-mini）でマクロセンチメントを算出。
    - API リトライ（429・ネットワーク・タイムアウト・5xx）と失敗時のフェイルセーフ（macro_sentiment=0.0）。
    - レジーム書き込みは冪等化（BEGIN / DELETE / INSERT / COMMIT）し、エラー時は ROLLBACK を試みる。
    - テスト容易性のため別実装の _call_openai_api を用意。

- Data モジュール（kabusys.data）:
  - ETL パイプライン（kabusys.data.pipeline）を実装。
    - 差分取得ロジック、バックフィル、品質チェック収集、ETL 実行結果を表現する ETLResult データクラスを提供。
    - DuckDB ベースでの最大日付検出、テーブル存在チェックなどのユーティリティ実装。
    - ETLResult.to_dict() で品質問題を辞書化（監査ログ用途）。
  - calendar_management を実装（kabusys.data.calendar_management）。
    - market_calendar を用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日ベースのフォールバック（週末を非営業日扱い）。
    - カレンダー夜間更新ジョブ calendar_update_job：J-Quants から差分取得して保存、バックフィル、健全性チェック、例外時のログ保護。
    - _MAX_SEARCH_DAYS 等の探索上限により無限ループを防止。

- Research モジュール（kabusys.research）:
  - ファクター計算（kabusys.research.factor_research）を実装。
    - Momentum（1M/3M/6M リターン / MA200 乖離）、Volatility（20日 ATR / ATR比 / 20日平均売買代金 / 出来高比率）、Value（PER/ROE）を DuckDB で計算する関数群（calc_momentum, calc_volatility, calc_value）。
    - データ不足時は None を返す等、欠損を許容する堅牢な設計。
    - SQL ウィンドウ関数を活用して一括計算。
  - 特徴量探索（kabusys.research.feature_exploration）を実装。
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応・入力検証）。
    - IC（Information Coefficient）計算（calc_ic、Spearman のランク相関を実装、最小レコード数チェック）。
    - 統計サマリー（factor_summary）とランク変換ユーティリティ（rank）。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- その他ユーティリティ:
  - data.etl で pipeline.ETLResult を再エクスポート。
  - logging を随所に導入し実行フローの可観測性を確保。

### Changed
- 初版リリースのため該当なし。

### Fixed
- 初版リリースのため該当なし。

### Security
- .env 読み込み実装で OS 環境変数を protected として上書きから保護する仕組みを導入（override 時でも protected は上書きされない）。
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で提供する設計。未設定時は ValueError を送出して誤用を防止。

### Notes / Limitations
- OpenAI を用いる機能（news_nlp, regime_detector）は外部 API に依存。API 呼び出し失敗時はフェイルセーフで処理を継続する（スコアを 0.0 にフォールバック、または該当銘柄をスキップ）。
- DuckDB の executemany に関する互換性制約を考慮して空リストは送らないようにしている（DuckDB 0.10 対応）。
- 時刻関連はすべてタイムゾーン混入を避けるため date / UTC-naive datetime を採用。ルックアヘッドバイアス対策として datetime.today()/date.today() を内部処理で参照しない設計方針が採用されている（外部から target_date を与える）。
- モデルは gpt-4o-mini を想定。将来的なモデル変更や OpenAI SDK のバージョン変化に対する扱いは今後の課題。

### Breaking Changes
- 初版リリースのため該当なし。

---

（補足）本 CHANGELOG はソースコード・ドキュメントコメントから推測して作成しています。実際のリリースノートとして用いる際は、実際に行ったコミット・変更内容と照合して適宜調整してください。