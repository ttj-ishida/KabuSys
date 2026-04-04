# Changelog

すべての非互換な変更はメジャーバージョンを上げて記述します。  
この CHANGELOG は Keep a Changelog の形式に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-04-04
初回リリース。日本株自動売買システム（KabuSys）の基盤機能を実装・公開。

### Added
- パッケージ基礎
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として公開。
  - パッケージの公開 API に `data`, `strategy`, `execution`, `monitoring` を含める。

- 環境設定 / 設定管理 (kabusys.config)
  - `.env` ファイルや環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートは `__file__` を起点に `.git` または `pyproject.toml` を探索して特定。
    - 自動ロードは OS 環境変数 > `.env.local` > `.env` の優先順で行う。
    - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定可能。
    - OS 側から既に設定されているキーは保護（上書き禁止）される仕組みを導入。
    - `.env` のパースは `export KEY=val` 形式・クォート／エスケープ対応・コメント処理などに対応。
  - `Settings` クラスを提供しアプリケーション設定をプロパティ経由で取得可能。
    - 主要な環境変数:
      - J-Quants: `JQUANTS_REFRESH_TOKEN`（必須）
      - kabu API: `KABU_API_PASSWORD`, `KABU_API_BASE_URL`（デフォルト: http://localhost:18080/kabusapi）
      - LINE: `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_USER_ID`
      - DB パス: `DUCKDB_PATH`（デフォルト: data/kabusys.duckdb）、`SQLITE_PATH`（デフォルト: data/monitoring.db）
      - 監視用フラグ/閾値: `PID_FILE_PATH`, `KILL_FLAG_PATH`, `KILL_FLAG_CLEAR_ON_START`, `CPU_THRESHOLD_PCT`, `MEMORY_THRESHOLD_PCT`, `DISK_THRESHOLD_PCT`
      - 実行環境: `KABUSYS_ENV`（`development`/`paper_trading`/`live` のいずれか、検証あり）
      - ログレベル: `LOG_LEVEL`（`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`、検証あり）
    - 必須環境変数が未設定の場合は `ValueError` を送出する設計。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン
    - `ETLResult` データクラスを公開（取得数・保存数・品質問題・エラー等を含む）。
    - 差分更新・バックフィル・品質チェックを想定した設計。J-Quants クライアント経由での差分取得・冪等保存を想定。
  - カレンダー管理（market_calendar）
    - JPX カレンダー（祝日・半日・SQ）を扱うユーティリティを実装。
    - 営業日判定: `is_trading_day`, `is_sq_day`
    - 近接営業日探索: `next_trading_day`, `prev_trading_day`
    - 期間内営業日列挙: `get_trading_days`
    - 夜間バッチ更新ジョブ: `calendar_update_job`（J-Quants から差分取得、バックフィル機能、健全性チェック）
    - DB にカレンダーが未登録の場合は曜日ベース（平日を営業日）でフォールバックする一貫した挙動。
    - 最大全探索日数を設定し無限ループ防止（_MAX_SEARCH_DAYS）。

- ニュース NLP / AI モジュール（kabusys.ai）
  - ニュースセンチメント分析: `score_news`
    - 対象ウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して DB クエリに使用）。
    - `raw_news` と `news_symbols` を用いて銘柄ごとに記事を集約し、最大記事数・文字数でトリム。
    - OpenAI（モデル: `gpt-4o-mini`）を JSON Mode で呼び出して銘柄毎にスコアを取得。
    - 1 API 呼び出しあたりのバッチ最大銘柄数 `_BATCH_SIZE=20`、リトライ（429/ネットワーク/5xx）と指数バックオフを組み込み。
    - レスポンスの厳密検証（JSON 抽出、キー・型検証、未知コード無視、スコア数値化、±1 にクリップ）。
    - 成功したスコアのみ `ai_scores` テーブルへ冪等的に置換（DELETE → INSERT）。部分失敗時に既存データ保護。
    - API キー未設定時は `ValueError`。
    - 返り値は書き込んだ銘柄数。
  - 市場レジーム判定: `score_regime`（kabusys.ai.regime_detector）
    - ETF コード 1321（日経225連動）に対する 200 日移動平均乖離（重み 70%）とマクロニュースセンチメント（重み 30%）を合成して `market_regime` に日次で保存。
    - マクロニュースは `raw_news` からマクロキーワードでフィルタして取得し、OpenAI により `macro_sentiment` を JSON で取得。
    - ルックアヘッドバイアス防止のため、対象日は明示的に渡す設計（内部で date.today() を参照しない）。
    - OpenAI 呼び出しに対してリトライ戦略（429/ネットワーク/タイムアウト/5xx）を持ち、最終的に失敗した場合はフォールバック `macro_sentiment=0.0`。
    - 計算結果は `market_regime` テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試み例外を再送出。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum: 1M/3M/6M のリターン、および 200 日 MA 乖離（ma200_dev）計算（データ不足時は None）。
    - Volatility / Liquidity: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。
    - Value: 最新の `raw_financials` を用いて PER（EPS が 0 または NULL の場合は None）と ROE を計算。
    - 全関数は DuckDB の `prices_daily` / `raw_financials` のみ参照し、外部 API にアクセスしない方針。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算: `calc_forward_returns`（複数ホライズン対応、デフォルト [1,5,21]）
    - IC（Spearman の順位相関）計算: `calc_ic`（入力レコード結合・None 除外・最小サンプルチェック）
    - ランク付けユーティリティ: `rank`（同順位は平均ランク）
    - 統計サマリー: `factor_summary`（count/mean/std/min/max/median）

- 実装上の設計方針・堅牢性
  - ルックアヘッドバイアス対策: 日付参照において `datetime.today()` / `date.today()` を直接使用せず、明示的な target_date を使うよう統一。
  - OpenAI 呼び出しでのリトライ（429/接続/タイムアウト/5xx）とエラーハンドリング（5xx は再試行、それ以外はフォールバックやスキップ）。
  - DB 書き込みは冪等に設計（DELETE → INSERT、または ON CONFLICT を想定）。DuckDB の制約（executemany の空リスト不可など）に配慮。
  - テスト容易性のため、OpenAI 呼び出し箇所は内部関数をモック可能に設計（unittest.mock.patch を想定）。

### Changed
- （初版につき該当なし）

### Fixed
- （初版につき該当なし）

### Deprecated
- （初版につき該当なし）

### Removed
- （初版につき該当なし）

### Security
- OpenAI 等の外部 API キーは環境変数（例: `OPENAI_API_KEY`）で管理する設計。キー未設定時は明確に `ValueError` を発生させるため、運用時にキー漏洩防止の管理を想定。

---

注意事項（既知の前提・必須テーブル等）
- 主要な DuckDB テーブル（期待されるスキーマの存在）:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など。
- OpenAI を利用する機能（news_nlp / regime_detector）は API キーとネットワークアクセスが必須。API 呼び出し料が発生する点に注意。
- `.env` 自動ロードはプロジェクトルートの検出に依存するため、配布後や実行環境に応じて `KABUSYS_DISABLE_AUTO_ENV_LOAD` を利用して明示的に制御可能。
- DuckDB 互換性やバージョン差異（executemany の挙動等）を考慮した実装がなされているが、運用環境での動作確認を推奨。

もし CHANGELOG に追記したい特定の変更点（例: 追加モジュール、バグ修正、日付の変更など）があれば、実装差分やコミットメッセージを教えてください。それを元により詳細な履歴を作成します。