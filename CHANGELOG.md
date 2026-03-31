# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]
- （今後の変更をここに記載）

---

## [0.1.0] - 2026-03-31
初回公開リリース — KabuSys: 日本株自動売買 / データ基盤 / 研究用ユーティリティ群

### Added
- パッケージ基盤
  - パッケージ名: `kabusys`、バージョン: `0.1.0` を定義（src/kabusys/__init__.py）。
  - パッケージの公開モジュール一覧に `data`, `strategy`, `execution`, `monitoring` を含める。

- 設定・環境変数管理
  - .env/.env.local ファイルおよび環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルートは `.git` または `pyproject.toml` を基準に探索）。自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（src/kabusys/config.py）。
  - .env パーサーはコメント・export プレフィックス・シングル/ダブルクォート・バックスラッシュエスケープに対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パスなどの設定をプロパティとして取得。`KABUSYS_ENV` と `LOG_LEVEL` の値検証を実装（有効値チェック）、パスは Path に展開。

- データ（Data Platform）
  - ETL パイプラインの公開インターフェースとして `ETLResult` を再エクスポート（src/kabusys/data/etl.py）。
  - ETL の中核機能を実装（差分取得・保存・品質チェックの枠組み）。`ETLResult` データクラスで実行結果・品質問題・エラーを集約できる（src/kabusys/data/pipeline.py）。
  - DuckDB を前提にしたユーティリティ:
    - テーブル存在チェック、最大日付取得などの内部ユーティリティを提供。
    - executemany の空リスト問題や型変換（date）の互換性を考慮。
  - マーケットカレンダー管理モジュールを実装:
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供（src/kabusys/data/calendar_management.py）。
    - カレンダーデータがない場合は曜日ベース（土日除外）でフォールバックする堅牢な設計。
    - 夜間バッチ `calendar_update_job` を実装（J-Quants API 経由で差分取得、バックフィル、健全性チェック、冪等保存）。

- 研究（Research）機能
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離等。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等。
    - calc_value: PER、ROE（raw_financials からの取得）。
    - すべて DuckDB の prices_daily / raw_financials を参照し、ルックアヘッドを避ける設計。
  - 特徴量探索モジュール（src/kabusys/research/feature_exploration.py）:
    - calc_forward_returns: 指定ホライズン（営業日ベース）の将来リターンを一括取得。
    - calc_ic: Spearman ランク相関（Information Coefficient）を計算（欠損・少数レコード対応）。
    - rank: 同順位は平均ランクで処理するランク化ユーティリティ。
    - factor_summary: count / mean / std / min / max / median を算出する統計サマリー関数。
  - research パッケージの __init__ で zscore_normalize（kabusys.data.stats）を再エクスポートし、主要ファクター関数群を公開。

- AI（自然言語処理）機能
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）:
    - raw_news と news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコア（-1.0〜1.0）を生成。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST を UTC に変換）を計算する calc_news_window を提供。
    - バッチサイズ、文字トリム、最大記事数などトークン対策を実装。
    - リトライ（429・ネットワーク・タイムアウト・5xx）と指数バックオフを実装。レスポンスは JSON mode を想定し厳密なバリデーションを実施。部分失敗時の DB 保護（既存スコアを不用意に消さないため、該当コードのみ DELETE→INSERT）を行う。
    - テスト容易性のため、内部 OpenAI 呼び出し関数は差し替え可能（モック可能）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）:
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - prices_daily / raw_news 参照、OpenAI 呼び出しは独立実装でモジュール結合を避ける。
    - API 失敗時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実施。

- ロギング・堅牢性
  - 多数の箇所で詳細なログ出力と警告（warnings）を追加。
  - トランザクションの失敗時に ROLLBACK を試み、ROLLBACK 自体の失敗も警告する安全設計。
  - ルックアヘッドバイアスを防ぐため、datetime.today()/date.today() に依存しない設計方針を採用（全ての関数は target_date を引数として受けるか、明示的に現在日を扱う）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キー等の機密情報は Settings 経由で取得する設計。ただし、実行環境では適切なシークレット管理を行ってください。

---

## 注意事項 / 既知の制約
- OpenAI（gpt-4o-mini）を利用する機能は API キー（env: OPENAI_API_KEY または api_key 引数）が必須。キー未設定時は ValueError を送出する。
- DuckDB 上の期待されるテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials など）が存在することを前提とする。存在しない場合は関数は空結果や警告・例外を返す可能性がある。
- JSON Mode を利用しているが、LLM の出力は常に期待通りであるとは限らないため、厳密なバリデーションと失敗時のフォールバック（スキップや 0.0 フォールバック）を実装している。
- timezone はモジュール内で明示的に扱っており、news window 等は UTC naive datetime を使用している点に注意（アプリケーション側での時間管理に留意）。

---

もしリリース日や追記したい変更点（例: strategy / execution / monitoring の詳細、テストカバレッジ、ドキュメント追加など）があれば、次版の CHANGELOG に反映します。