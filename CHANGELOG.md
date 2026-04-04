# Changelog

すべての注目すべき変更点はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  
詳細: https://keepachangelog.com/ja/

全般注意:
- 本リリースノートは提示されたコードベースの内容から推測して作成しています。
- 日付はパッケージの __version__（0.1.0）に対応する初期リリース日として 2026-04-04 を使用しています。

## [Unreleased]
- 現在未リリースの変更はありません。

## [0.1.0] - 2026-04-04

### Added
- パッケージ基盤
  - パッケージルート: `kabusys`、バージョン `0.1.0` を定義（src/kabusys/__init__.py）。
  - 主要モジュール群を公開: data, strategy, execution, monitoring。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - プロジェクトルート検出は __file__ を基点に `.git` または `pyproject.toml` により行い、CWD に依存しない実装。
  - `.env` パーサを実装（コメント、export プレフィックス、クォート処理、エスケープ対応）。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - 必須設定取得ヘルパ `_require`。未設定時は ValueError を送出。
  - Settings クラスを提供し、以下を含むプロパティを提供:
    - J-Quants / kabuステーション / LINE Messaging / データベースパス（duckdb/sqlite）/監視関連（pid, kill flag, thresholds）/運用環境（development/paper_trading/live）/ログレベル。
  - 環境変数のデフォルト値やバリデーション（`KABUSYS_ENV`, `LOG_LEVEL` 等）を実装。

- AI (自然言語処理) モジュール (src/kabusys/ai)
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのニュースセンチメント（ai_score）を算出し `ai_scores` テーブルへ書き込み。
    - 処理はタイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づく。`calc_news_window` ユーティリティあり（JST→UTC 変換）。
    - バッチ処理（最大 20 銘柄／API コール）、1 銘柄当たりの最大記事数・文字数でトリム（デフォルト 10 件、3000 文字）。
    - API 呼び出しのリトライ（429 / ネットワーク / タイムアウト / 5xx 対応）と指数バックオフを実装。
    - レスポンス検証: JSON パース、"results" リスト、コード整合性、スコア数値性をチェック。スコアは ±1.0 にクリップ。
    - 部分失敗を考慮し、書き込みは対象コードのみ DELETE → INSERT で置換（DuckDB の互換性制約に配慮して executemany を使用）。
    - テスト容易性のため `_call_openai_api` を patch 可能にしている。
    - API キーの注入（引数または環境変数 `OPENAI_API_KEY`）。

  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（`bull` / `neutral` / `bear`）を判定。
    - マクロニュースはキーワードフィルタ（複数の日本/米国キーワード）で抽出し、OpenAI（gpt-4o-mini）に JSON 出力をリクエスト。
    - LLM 呼び出し失敗時はフェイルセーフとして `macro_sentiment = 0.0` を使用。
    - レジームスコアは所定スケールで合成後クリップし閾値でラベル付け。結果を `market_regime` テーブルに対して冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス防止の設計（target_date 未満のみ参照等）。
    - `_call_openai_api` を別実装にしてモジュール結合を避け、テスト用差替えを容易にしている。
    - API キーの注入（引数または環境変数 `OPENAI_API_KEY`）。

- データプラットフォーム / ETL (src/kabusys/data)
  - calendar_management モジュール
    - JPX カレンダー管理（market_calendar）用のユーティリティを提供：営業日判定、次/前営業日取得、期間内営業日取得、SQ 日判定。
    - DB にデータがない場合は曜日ベースのフォールバック（週末を非営業日）を採用。
    - 最大探索日数 `_MAX_SEARCH_DAYS` で無限ループを回避。
    - 夜間バッチ `calendar_update_job` を実装し、J-Quants クライアントから差分取得・バックフィル・保存（jq.fetch_market_calendar / jq.save_market_calendar）を行う。健全性チェック（極端な将来日付のスキップ）を実装。

  - pipeline / ETL モジュール（src/kabusys/data/pipeline.py, etl.py）
    - ETLResult データクラスを導入し、ETL の対象日、取得/保存件数、品質問題（quality.QualityIssue）、エラー一覧を集約。
    - 差分更新・バックフィル・品質チェックの設計方針を反映（API 側の後出し修正を吸収するための再取得など）。
    - _table_exists / _get_max_date 等の内部ユーティリティを提供。
    - etl.py で pipeline.ETLResult を再エクスポート。

- 研究（Research）ツール群 (src/kabusys/research)
  - factor_research モジュール
    - モメンタム（1M/3M/6M）、200日移動平均乖離、ATR（20日）、流動性（20日平均売買代金、出来高比率）、PER/ROE（raw_financials 参照）等の計算関数を実装: `calc_momentum`, `calc_volatility`, `calc_value`。
    - DuckDB のウィンドウ関数を駆使し、データ不足時の扱い（None）を明示。
    - 設計上、本番の発注 API にアクセスしないことを明記。

  - feature_exploration モジュール
    - 将来リターン計算（`calc_forward_returns`）、IC（スピアマン相関）計算（`calc_ic`）、ランク変換（`rank`）、ファクター統計サマリー（`factor_summary`）を実装。
    - `calc_forward_returns` は複数ホライズンをサポートし、入力検証あり（ホライズンは 1..252）。
    - `calc_ic` は有効レコードが 3 件未満の場合 None を返す。

- データアクセス補助
  - DuckDB を前提とした SQL 実装（全モジュール）を採用。
  - DuckDB のバージョン差異（例: executemany に空リスト不可）に配慮したコードパスを実装。

### Changed
- 初回リリースにつき該当なし。

### Fixed
- 初回リリースにつき該当なし。

### Removed
- 初回リリースにつき該当なし。

### Security
- 環境変数に API キー（`OPENAI_API_KEY` 等）やパスワード（`KABU_API_PASSWORD`）を利用する設計のため、.env の管理には注意が必要（.env.example 参照を促すエラーメッセージあり）。
- 自動ロードをテスト用途に無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。

### Notes / Known limitations
- news_nlp の出力は LLM の挙動に依存するため、JSON パースに失敗するケースへはフォールバック処理（最外の {} を抽出）を実装しているが、完全な保証はない。
- 一部計算（PBR・配当利回りなど）は現バージョンで未実装（calc_value に注記あり）。
- OpenAI 呼び出しの実際の挙動（料金・レート制限等）はランタイム環境に依存する。コードはリトライ・バックオフを実装しているが、長時間の失敗時にはセンチメントやスコアが省略・ゼロ扱いとなる（フェイルセーフ）。
- calendar_update_job は外部 J-Quants クライアント（kabusys.data.jquants_client）に依存。API エラー時はエラーログを出力して処理を 0 件で終了する。
- DuckDB のバージョン互換性（特に executemany の扱い）に配慮した処理パスが存在するため、環境差異は注意が必要。
- ルックアヘッドバイアス防止の観点から、本コードでは datetime.today()/date.today() を直接参照しない実装方針を各所で採用している。関数は必ず明示的な target_date を受け取る。

---

（補注）この CHANGELOG は、提示されたソースコードのコメント・実装から読み取れる仕様・挙動を基に作成しています。実際の変更履歴として使用する場合は、コミット履歴やリリースノート原本と照合してください。