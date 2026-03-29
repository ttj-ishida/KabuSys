# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
このファイルはコードベース（初期リリース v0.1.0）から推測可能な機能・設計上の意図・既知の制約を基に作成しています。

## [Unreleased]

### 追加予定 / 検討中
- テストスイートと CI ワークフローに関する記載・自動化
- DuckDB バージョン差異に関するより詳細な互換性テスト
- OpenAI のモデル選択や API レート制御の設定を外部化するための設定フラグ

---

## [0.1.0] - 2026-03-29

初回公開リリース

### Added
- パッケージ基礎
  - kabusys パッケージの初期公開（__version__ = "0.1.0"）。
  - 主要サブパッケージをエクスポート: data, research, ai, monitoring 等の基盤を用意。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび OS 環境変数から設定を読み込む自動ロード実装。
    - プロジェクトルート検出は __file__ から親ディレクトリを上方向に探索し、`.git` または `pyproject.toml` を基準に判定。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - .env パーサーの強化:
    - コメント、`export KEY=val` 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いなどに対応。
  - 環境変数必須チェック関数 `_require` と Settings クラスを提供。
    - 必須項目（例）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。
    - データベースパスのデフォルト（duckdb: data/kabusys.duckdb、sqlite: data/monitoring.db）。
    - 環境 (`KABUSYS_ENV`) とログレベル (`LOG_LEVEL`) の値検証を実装。
    - is_live / is_paper / is_dev のヘルパーを提供。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理と営業日判定ロジックを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days API を実装。
    - market_calendar テーブルの有無に応じたフォールバック（曜日ベース）をサポート。
    - calendar_update_job: J-Quants API から差分取得して冪等的に保存する夜間バッチの骨組みを実装（バックフィル・健全性チェック含む）。
  - pipeline / ETL:
    - ETLResult データクラスを公開し、ETL の各種メトリクス（取得数・保存数・品質問題・エラー等）を収集できるようにした。
    - 差分取得、バックフィル、品質チェックの設計方針を反映（実装の骨子を提供）。
  - jquants_client との連携ポイント（fetch/save）を呼び出す設計。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR（atr_20 / atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER / ROE を計算（EPS が 0/欠損の際は None）。
    - DuckDB の SQL ウィンドウ関数を利用した効率的な集計を実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）に対する将来リターンを一括取得する汎用関数。
    - calc_ic: Spearman のランク相関（Information Coefficient）を計算。データ不足時は None を返す。
    - rank: 同順位は平均ランクを返すランク付け関数（丸めによる ties 検出の安定化）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
  - zscore_normalize を data.stats から再エクスポート。

- AI / NLP（kabusys.ai）
  - news_nlp:
    - score_news: raw_news と news_symbols を用いて銘柄ごとのニュースセンチメントを OpenAI（gpt-4o-mini）の JSON モードで評価し、ai_scores テーブルへ書き込む。
    - ニュースウィンドウは JST ベースで前日 15:00 ～ 当日 08:30（UTC に変換して DB と比較）を採用。calc_news_window を実装。
    - バッチ処理（1 API コールで最大 20 銘柄）と、1 銘柄あたりの最大記事数 / 最大文字数によるトークン肥大化対策を実装。
    - API 呼び出しで 429/ネットワーク/タイムアウト/5xx を対象に指数バックオフでリトライし、部分失敗時は他銘柄の既存スコアを消さない方式（対象コードのみ DELETE → INSERT）。
    - レスポンス検証ロジックを実装（JSON 抽出、"results" の存在、code と score 型検証、未知 code の無視、スコアの ±1.0 クリップ）。
    - テスト用フック: API 呼び出し関数をモック差替え可能（unittest.mock.patch 対応）。
  - regime_detector:
    - score_regime: ETF 1321 の 200 日 MA 乖離（重み 70%）と、news_nlp のマクロセンチメント（重み 30%、OpenAI による評価）を合成して market_regime テーブルへ書き込む。
    - LLM を用いるのはマクロ記事が存在する場合のみで、API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - レジームスコアを clip してラベル化（'bull' / 'neutral' / 'bear'）し、冪等的に DB に書き込む（BEGIN/DELETE/INSERT/COMMIT）。
    - API 呼び出しのリトライや HTTP 5xx 判定を含む堅牢性ロジックを実装。
    - 設計方針としてルックアヘッドバイアスを避けるため datetime.today() 等を参照しない設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）  
  ただし多くの関数で「データ不足」「API エラー」「レスポンスパース失敗」に対するフェイルセーフ処理を実装しており、運用時の障害耐性を確保。

### Security
- 環境変数と OS の値を区別し、.env ロード時に既存 OS 環境変数を保護するための protected キーセットを導入。
- API キーは明示的に引数で渡すこともでき、テスト時や CI での注入が容易。

### Notes / Migration / Usage
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（AI 機能を使う場合）
- 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- デフォルトの DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- OpenAI 呼び出しは gpt-4o-mini を想定しており、レスポンスは JSON モードで受け取るよう設計されています。
- DuckDB 0.10 系との互換性に配慮しており、executemany に空リストを渡すと失敗する点に関しては明示的なガードを入れています。
- ルックアヘッドバイアス対策:
  - news スコアリング / レジーム判定 / リサーチ計算のいずれも内部で date.today() を利用しない方針。呼び出し側が target_date を明示的に渡す設計です。

### Known limitations / TODO
- ETL の実装は pipeline の骨子を提供しているが、jquants_client や quality モジュールの具体的な実装状況に依存するため、実運用前に統合テストが必要。
- OpenAI のレート・費用管理はユーザーレベルでの制御が残っているため、運用環境では適切なモニタリング・制限を推奨。
- News/Regime の LLM 呼び出しは JSON モードだが、稀に余計なテキストが混入する場合に備えてパース補正ロジックを入れているものの、完全に網羅できないケースがあり得る。
- calendar_update_job は J-Quants API のレスポンス形状・エラー条件に依存するため、API 仕様変更時には調整が必要。

---

作成者注:
- この CHANGELOG はリポジトリ内のコードコメント・ドキュメント文字列・関数名・定数・ロジックから機能と設計意図を推測して作成しています。実際の変更履歴（コミット単位・過去のリリースノート）が存在する場合はそちらを優先してください。