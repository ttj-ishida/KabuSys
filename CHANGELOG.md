# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-28
初回公開リリース

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys v0.1.0、公開用モジュール一覧: data, strategy, execution, monitoring）。
- 環境設定管理
  - 環境変数/`.env` ファイル読み込みユーティリティを実装（kabusys.config）。
  - プロジェクトルート自動検出（.git または pyproject.toml を起点）による .env/.env.local 自動読み込みをサポート。
  - `.env` パーサ実装: export 形式対応、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメントの扱い、上書き保護（protected）機能を実装。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - Settings クラスを公開し、J-Quants / kabuステーション / Slack / DB パス / 実行環境（development/paper_trading/live）などの設定を型付きプロパティとして提供。無効値は ValueError を送出。
- データプラットフォーム（Data）
  - market_calendar（JPX カレンダー）管理と夜間更新ジョブを実装（kabusys.data.calendar_management）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジックを適用。
    - 夜間バッチ (calendar_update_job) による J-Quants からの差分取得・バックフィル・保存処理を実装。健全性チェック（未来日付異常検知）を含む。
  - ETL パイプライン用インターフェース（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを実装（取得数・保存数・品質問題・エラー等を集約）。
    - 差分取得、バックフィル、品質チェックの設計に対応するユーティリティ関数と DB ヘルパーを実装。
    - jquants_client 経由での取得・保存処理を想定した設計（idempotent 保存を前提）。
- AI モジュール（kabusys.ai）
  - ニュースセンチメント分析（kabusys.ai.news_nlp）
    - OpenAI（gpt-4o-mini + JSON mode）を利用した銘柄別ニュースセンチメントスコアリングを実装。
    - 前日 15:00 JST ～ 当日 08:30 JST のウィンドウを定義する calc_news_window を実装（UTC naive datetime を返す）。
    - raw_news / news_symbols を集約し、銘柄ごとに最新記事をトリムして（記事数・文字数制限）、最大 20 銘柄ずつバッチ送信するバッチ処理を実装。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ、レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code/score チェック、スコアの数値変換・有限性、±1.0 でクリップ）。
    - 部分成功時に既存スコアを保護するため、書き込みは対象コードの DELETE → INSERT（トランザクション）方式で実行。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を統合して日次で 'bull' / 'neutral' / 'bear' を判定する score_regime を実装。
    - マクロキーワードで raw_news をフィルタし、OpenAI（gpt-4o-mini）により JSON 出力で macro_sentiment を得る仕組み。
    - LLM 呼び出し失敗時はフェイルセーフとして macro_sentiment=0.0 を使用。
    - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実行。
    - モジュール設計上、news_nlp の内部関数と共有せず独自の _call_openai_api を持つ（結合を低く保つ）。
- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20 日 ATR、ATR 比率）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER・ROE）を計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上の SQL とウィンドウ関数を活用し、date, code をキーにした辞書リストを返却。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：複数ホライズンを一度に取得する SQL 実装、入力検証（horizons は 1..252）を実装。
    - IC（Information Coefficient）計算（calc_ic）：ランク相関（Spearman）をランク関数と共に実装。必要レコード数が不足する場合は None を返却。
    - ランク変換（rank）：同順位の平均ランク処理、丸めにより ties の検出精度を向上。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を標準ライブラリのみで計算する実装。
- DuckDB を主要 DB として利用する設計。prices_daily / raw_news / raw_financials / ai_scores / market_regime / market_calendar 等のテーブルを想定した処理を実装。

### Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY にて注入する設計。キー未設定時は関数が ValueError を送出して明示的に扱う。

### Design / Behavior notes
- ルックアヘッドバイアス防止のため、内部処理は datetime.today()/date.today() を安易に参照しない設計（target_date を明示的に受け取る）。
- 外部 API 呼び出しに対してはフェイルセーフ（API 失敗でもプロセスを停止させない挙動）を採用し、部分失敗時の既存データ保護（特に ai_scores の書き込み）を行う。
- DB 書き込みは可能な限り冪等性（DELETE→INSERT、ON CONFLICT 実装を想定）を重視。
- テスト容易性を考慮し、OpenAI 呼び出し部分は _call_openai_api を patch して差し替え可能（ユニットテスト向け）。

### Fixed
- （初版のため無し）

### Removed
- （初版のため無し）

---

備考:
- 本 CHANGELOG はコードベースから機能・設計を推測して作成しています。実際の公開リリースノート作成時は追加の変更点（ドキュメント、依存関係、ビルド/配布手順等）を反映してください。