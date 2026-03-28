# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。各エントリは主にコードベースから推測した機能追加・改善点・修正点を日本語でまとめたものです。

## [Unreleased]
- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買プラットフォームのコア機能群を実装・公開。

### Added
- パッケージ基盤
  - パッケージエントリポイントとして `kabusys` を追加。公開モジュール群として data, strategy, execution, monitoring を定義（src/kabusys/__init__.py）。
  - バージョン情報を `__version__ = "0.1.0"` として管理。

- 設定・環境変数管理（src/kabusys/config.py）
  - `.env` / `.env.local` の自動ロード機能を実装（プロジェクトルートの検出は .git / pyproject.toml を基準）。
  - 自動ロードをテスト等で無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` サポート。
  - .env の行パーサを実装（`export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
  - OS 環境変数を保護する `protected` オプションを実装（`.env.local` の override 挙動に対応）。
  - 必須環境変数チェック `_require()` と `Settings` クラスを提供。以下の設定プロパティを提供:
    - J-Quants / kabu / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベルなど。
  - `duckdb_path` / `sqlite_path` のデフォルトと Path 変換を提供。

- AI モジュール（src/kabusys/ai/*.py）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して `ai_scores` テーブルに書き込む機能を実装（`score_news`）。
    - ニュース収集ウィンドウ計算 (`calc_news_window`) を提供（前日15:00 JST ～ 当日08:30 JST を UTC に変換した半開区間）。
    - バッチ処理（最大 20 銘柄/コール）・記事/文字数トリム（最大記事数・文字数制限）・JSON mode を用いたレスポンス検証を実装。
    - 429・ネットワーク断・タイムアウト・5xx の場合の指数バックオフリトライを実装。
    - レスポンスの堅牢なパース / バリデーション（余分テキストの復元、results 配列の検証、コード正規化、スコアクリップ）を実装。
    - テスト容易性のため OpenAI 呼び出し関数をモジュール内で抽象化（patch で差し替え可能）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出する `score_regime` を実装。
    - ルックアヘッドバイアス防止の設計（target_date 未満のデータのみ参照、datetime.today() 不使用）。
    - OpenAI API 呼び出し（gpt-4o-mini）でのリトライ・エラー処理を実装。API 失敗時のフェイルセーフとして `macro_sentiment = 0.0` を使用。
    - 計算結果を `market_regime` テーブルに冪等的に書き込む処理（BEGIN / DELETE / INSERT / COMMIT）を実装。

- データ基盤（src/kabusys/data/*）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーの夜間バッチ更新ジョブ `calendar_update_job` を実装（J-Quants クライアント経由で差分取得→保存）。
    - 営業日判定と探索ユーティリティを提供: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`。DB 登録値優先、未登録日は曜日ベースでフォールバックする方針。
    - `_MAX_SEARCH_DAYS` による探索上限・健全性チェック・バックフィル挙動などを実装。

  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETL の実行結果を格納する `ETLResult` dataclass を実装。品質チェック情報とエラー情報を保持。
    - DuckDB と互換性のあるテーブル存在確認・最大日付取得ユーティリティを実装。
    - `kabusys.data` 以下の ETL インターフェース（`ETLResult` の再エクスポート）を提供。

  - jquants_client / quality を想定した差分取得・保存・品質チェック設計（実装依存箇所は jquants_client へ委譲）。

- リサーチ（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - `calc_momentum`: 1M/3M/6M リターン、200日MA乖離 (ma200_dev) を計算。
    - `calc_volatility`: 20日 ATR、ATR比率、20日平均売買代金、出来高比などを計算。
    - `calc_value`: raw_financials から財務データを取得して PER / ROE を算出。
    - DuckDB ベースの SQL + Python 実装。入力は prices_daily / raw_financials のみ。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - `calc_forward_returns`: 各ホライズン（デフォルト 1/5/21 営業日）に対する将来リターン計算を提供（LEAD を利用して1クエリで取得）。
    - `calc_ic`: スピアマンランク相関（IC）を実装。充分なサンプルがない場合は None を返す。
    - `rank`: 同順位は平均ランクで扱うランク関数を実装（丸めで ties の検出を安定化）。
    - `factor_summary`: count/mean/std/min/max/median を算出する統計サマリ関数を実装。
    - `research.__init__` で主要関数を公開。

### Changed
- 初回公開につき、後方互換性を考慮した設計注記やエラーハンドリングに重点を置いた実装となっている。API 呼び出しのテスト差し替えポイント（_call_openai_api）を明示的に設けるなどテスト容易性を改善。

### Fixed
- DuckDB の executemany における空リストバインド制約を考慮し、空パラメータ時の分岐処理を追加（`score_news` の書き込み処理等）。
- LLM レスポンスパースに関する堅牢化：JSON モードでも前後に余計なテキストが混入する場合に最外の {} を抽出して復元する処理を追加。
- OpenAI API のエラー分類に応じたリトライ戦略を導入（RateLimit / 接続エラー / タイムアウト / 5xx をリトライ対象、非5xx は即座にフォールバック）。
- 各種関数での「ルックアヘッドバイアス」対策として `date.today()` や `datetime.today()` を直接参照しない設計を徹底。

### Security
- 環境変数の自動ロードで OS 環境変数を保護する仕組みを導入（読み込み時に現行 os.environ のキーを保護セットとして扱い `.env` による上書きを制限）。
- OpenAI / J-Quants / KabuStation / Slack トークンは必須環境変数として明示し、未設定時に明確なエラーメッセージを出力。
- `.env` のパースでクォートやエスケープの取り扱いに注意しており、認証情報の誤読を軽減。

### Notes / Migration
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI API を利用する機能を使う場合は OPENAI_API_KEY が必要
- デフォルト値:
  - `KABU_API_BASE_URL` のデフォルトは "http://localhost:18080/kabusapi"
  - `DUCKDB_PATH` デフォルト "data/kabusys.duckdb"
  - `SQLITE_PATH` デフォルト "data/monitoring.db"
- テスト時のヒント:
  - 自動 .env 読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
  - OpenAI 呼び出しはモジュール内の `_call_openai_api` を patch して差し替え可能（ユニットテスト用フック）。

---

今後の予定（推測）
- strategy / execution / monitoring の詳細実装と公開（初期はデータ・研究・AIモジュール中心の実装）。
- デプロイ時のドキュメント整備、運用監視（Slack 連携の実装拡張）、より堅牢な品質チェックの実装。