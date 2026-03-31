# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠しています。

## [0.1.0] - 2026-03-31

初回公開リリース。日本株自動売買システム「kabusys」の基本機能をまとめて実装しました。主にデータ取得・ETL・マーケットカレンダー管理、リサーチ（ファクター計算）、AI を用いたニュースセンチメント評価・市場レジーム判定、環境設定管理のユーティリティ群を提供します。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化 `kabusys`（__version__ = 0.1.0）と主要サブパッケージのエクスポートを追加（data, research, ai, execution, strategy, monitoring 等を想定）。
- 環境設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env 読み込み: プロジェクトルート（.git または pyproject.toml を起点）を探索して `.env` / `.env.local` をロード。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可。
  - .env のパース実装: export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメント扱いの細かなルールを考慮したパーサ `_parse_env_line` を導入。
  - `.env.local` は `.env` を上書きする（ただし OS 環境変数は保護する仕組みあり）。
  - 必須設定取得のヘルパー `_require` と Settings のプロパティ群を追加（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH 等）。
  - KABUSYS_ENV と LOG_LEVEL の入力検証（許容値以外は ValueError を送出）。
- AI 関連 (`kabusys.ai`)
  - ニュース NLP スコアリング (`news_nlp.score_news`)
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む。
    - 時間ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を実装（calc_news_window）。
    - バッチサイズ、トークン肥大化対策、JSON Mode を利用した厳密な JSON レスポンス検証、レスポンスのバリデーションとスコアクリップを実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。API 失敗時は該当チャンクをスキップして継続するフェイルセーフ設計。
    - テスト用に OpenAI 呼び出しを差し替え可能（内部関数 _call_openai_api を patch 可能）。
  - 市場レジーム判定 (`regime_detector.score_regime`)
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を計算し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出、LLM 呼出し（gpt-4o-mini）、失敗時フォールバック macro_sentiment = 0.0、リトライロジックを含む。
    - DB 書き込み時は BEGIN / DELETE / INSERT / COMMIT のトランザクション処理、失敗時は ROLLBACK を実施。
- データ関連 (`kabusys.data`)
  - マーケットカレンダー管理 (`calendar_management`)
    - market_calendar テーブルベースの営業日判定ユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データがない場合は曜日ベース（土日除外）でフォールバックする一貫したロジック。
    - 夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants API から差分取得して保存、バックフィル・健全性チェックを含む）。
  - ETL パイプライン (`pipeline`, `etl`)
    - ETLResult データクラスを公開（ETL の取得数・保存数・品質問題・エラー情報を保持）。
    - 差分取得・保存・品質チェックを想定した設計（jquants_client と quality モジュールを利用することを前提）。
- リサーチ (`kabusys.research`)
  - ファクター計算 (`factor_research`)
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER、ROE）を計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を用いた SQL / ウィンドウ関数ベースの実装。データ不足時の None 返却、結果は (date, code) 単位の辞書リストで返す設計。
  - 特徴量探索・評価 (`feature_exploration`)
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク関数（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存しない標準ライブラリのみでの実装。
- その他
  - 一部モジュールの __all__ エクスポート整備（例: kabusys.ai.__init__）。

### 変更 (Changed)
- 設計方針（全体的）
  - ルックアヘッドバイアス回避のため、モジュール内では datetime.today()/date.today() を直接参照しない実装を徹底（すべてのバッチ関数は target_date を明示的に受け取るか、date.today() を呼ぶ場所を限定）。
  - DuckDB を利用した SQL 実装では、executemany の空リストバインド制約（DuckDB 0.10 を考慮）に対するガードを追加（空パラメータの場合は実行をスキップ）。
  - OpenAI 呼び出しのエラーハンドリング（429、ネットワーク、タイムアウト、5xx）を統一的に扱う方針を反映。

### 修正 (Fixed)
- トランザクション障害への復旧処理を強化
  - score_regime / score_news 等で DB 書き込み中に例外が発生した場合、ROLLBACK を試行し、ROLLBACK 自体の失敗もログで通知するようにした。
- .env 読み込みでの I/O エラー時にワーニングを出力して処理を継続するように修正（テストや権限不足でも致命化しないように）。

### 注意点 / 既知の制約 (Known issues / Notes)
- OpenAI API の利用には OPENAI_API_KEY が必須。score_news / score_regime は引数で API キー注入も可能。
- news_nlp と regime_detector は gpt-4o-mini と JSON Mode を前提に実装しているため、モデル・レスポンス仕様の変更があった場合は更新が必要。
- DuckDB のバージョン依存（executemany の挙動等）に注意。空のバインドリストを渡さないガードを入れているが、実行環境によっては追加調整が必要になる可能性あり。
- calendar_update_job は J-Quants API との連携を想定（`kabusys.data.jquants_client` を介す）。API 側の仕様変更があれば調整が必要。

### セキュリティ (Security)
- 環境変数の自動上書きを防ぐため、OS 環境変数は protected として .env による上書きを回避する仕組みを導入。
- 機密情報（API トークン等）は Settings._require により必須チェックを行い、未設定時は明示的にエラーを投げる（早期検出）。

---

今後の予定:
- execution / strategy / monitoring サブパッケージの実装拡充（発注ロジック、戦略実行フロー、監視・アラート統合）。
- テストカバレッジの強化（OpenAI 呼び出しのモック、DuckDB ベースの単体テスト群）。
- ドキュメント（StrategyModel.md, DataPlatform.md 等）の公開とサンプル ETL ジョブの提供。