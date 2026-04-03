# Changelog

全ての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠しています。  
このファイルにはコードベース（kabusys パッケージ）の主な追加・設計上の決定・フェイルセーフや互換性について、コードから推測される内容を日本語で記載しています。

なお、本リポジトリの初期バージョン情報は `kabusys.__version__ = "0.1.0"` に基づきます。

## [0.1.0] - 2026-04-03

### Added
- パッケージ基盤
  - 初期パッケージ公開: `kabusys`（バージョン 0.1.0）。
  - パッケージの公開 API を `__all__ = ["data", "strategy", "execution", "monitoring"]` として定義。

- 環境設定・ロード機能（src/kabusys/config.py）
  - .env ファイル自動ロード機能を実装（プロジェクトルート判定は `.git` または `pyproject.toml` を使用）。
  - .env パーサを実装:
    - `export KEY=val` 形式対応、コメント行・空行無視、シングル／ダブルクォート内のエスケープ処理対応。
    - クォートなし値のインラインコメント処理（直前がスペース／タブの場合のみ '#' をコメントとして扱う）。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書き不可）。
  - 自動ロード停止フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト向け）。
  - 必須環境変数取得用 `_require`、および `Settings` クラスでアプリケーション設定をプロパティとして提供。
  - `Settings` にて J-Quants / kabu / LINE / DB / 監視 / システム設定等のデフォルト値や検証を実装。
    - 環境（KABUSYS_ENV）の許容値検証（development, paper_trading, live）。
    - ログレベル（LOG_LEVEL）の許容値検証。
    - パス系設定は `Path.expanduser()` で扱う。
    - プロパティで `is_live` / `is_paper` / `is_dev` を提供。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols テーブルから銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）で銘柄単位のセンチメント（-1.0〜1.0）を推定して `ai_scores` に書き込む処理を実装。
  - 時間ウィンドウ: JST 前日 15:00 〜 当日 08:30（DB には UTC で保存されている前提）を計算するユーティリティ `calc_news_window` を提供。
  - バッチ処理: 最大 20 銘柄ずつ API に送信、1銘柄あたりの記事数・文字数上限（最大10記事・3000文字）でトリム。
  - OpenAI 呼び出しのリトライ実装（RateLimit / ネットワーク / タイムアウト / 5xx に対して指数バックオフ）。
  - JSON Mode のレスポンスを堅牢にバリデーション／パースし、未知コードや不正なスコアは無視する実装。
  - 結果のクリップ（±1.0）と、部分失敗時に既存スコアを保護するための「取得済みコードのみ DELETE→INSERT」方式の DB 書き込み（冪等性を考慮）。
  - テスト容易性のため、内部の OpenAI 呼び出し `_call_openai_api` を patch で差し替え可能に設計。

- マーケットレジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225 連動）を用いた 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を日次判定する関数 `score_regime` を実装。
  - マクロニュース抽出はマクロキーワードリストでフィルタ、OpenAI 呼び出しは gpt-4o-mini を使用。記事がない場合は LLM 呼び出しをスキップして macro_sentiment=0.0 を使用。
  - API 呼び出し失敗時はフェイルセーフとして macro_sentiment=0.0 にフォールバックし、例外を上位に伝播させない設計。
  - レジーム判定スコアの合成・クリップとラベリング（閾値で bull / bear / neutral を決定）。
  - DB への冪等書き込み（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）、失敗時は ROLLBACK を行い例外を再送出。

- 研究向けユーティリティ（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）:
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - Volatility: 20 日 ATR, ATR 比率, 20 日平均売買代金, 出来高比率。
    - Value: PER（EPS が 0 または欠損のときは None）、ROE（raw_financials の最新値を target_date 以前から取得）。
    - DuckDB を用いた SQL ベースの実装、結果は (date, code) をキーにした dict リストで返却。
    - データ不足時は None を返すなど堅牢な欠損処理を実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）:
    - 将来リターン計算（calc_forward_returns: デフォルト horizons = [1,5,21]、最大 252 日制約）。
    - IC（Information Coefficient）計算（スピアマンの順位相関を独自実装、同順位は平均ランク扱い）。
    - ランク関数（ties は平均ランク、浮動小数の丸めで ties 検出漏れを防止）。
    - ファクター統計サマリー（count/mean/std/min/max/median）。
  - 研究ユーティリティをまとめて re-export（`__all__`）で提供。

- データプラットフォーム（src/kabusys/data/*）
  - カレンダー管理（src/kabusys/data/calendar_management.py）:
    - JPX カレンダーの夜間バッチ更新ジョブ `calendar_update_job`（J-Quants API から差分取得 → `market_calendar` へ保存）。
    - カレンダーが未取得時の曜日ベースフォールバック（週末は非営業日）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供（DB 登録値優先、未登録日は曜日フォールバック）。
    - 最大探索範囲 `_MAX_SEARCH_DAYS` により無限ループ回避、バックフィル日数や健全性チェックを実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py, etl.py）:
    - ETLResult dataclass を公開（取得数・保存数・品質検査結果・エラー一覧を保持）。
    - 差分取得・保存・品質チェックの設計方針を反映した処理骨格（J-Quants クライアント経由の差分取得、save_* の冪等保存、品質チェックの取り扱い方針）。
    - DuckDB のテーブル存在確認や最大日付取得ユーティリティを実装。
    - デフォルトのバックフィルやカレンダー先読みの定数を定義。

- テスト・運用上の配慮
  - LLM 呼び出し箇所において内部呼び出し関数を外部からモック可能にしてテスト容易性を確保。
  - 多くの関数で datetime.today()/date.today() を参照しない設計（ルックアヘッドバイアス防止）。
  - DB 書き込みは部分失敗を考慮した設計（影響範囲を限定する DELETE→INSERT の戦略を採用）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- （初期リリースのため該当なし）

---

注記（コードからの推測）
- OpenAI API の利用は環境変数 `OPENAI_API_KEY` または各関数の `api_key` 引数で解決される。未設定時は ValueError を発生させることで呼び出し側に明示。
- DuckDB を主要なローカル分析用 DB として利用。`duckdb.DuckDBPyConnection` をパラメータに取る API が多数存在するため、実行環境は DuckDB 接続を渡す必要があります。
- J-Quants / kabu / LINE 等の外部サービスはクライアントモジュール経由（`kabusys.data.jquants_client` 等）で扱う想定だが、実装の詳細は本差分に含まれていません（関数呼び出しとエラーハンドリングを利用）。
- 各所でログ出力（logger）と警告／例外の使い分けがなされており、運用時の観測性に配慮されている設計です。

もしこの CHANGELOG を特定のリリース作業用（Git タグ付けやリリースノート生成）に整形する必要があれば、日付の変更やセクションの追加（Breaking Changes、Migration notes など）を行います。希望があれば対応します。