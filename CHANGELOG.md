# Keep a Changelog

すべての公開変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。

- ルール: https://keepachangelog.com/ja/1.0.0/
- バージョンはパッケージの `src/kabusys/__init__.py` の `__version__` に合わせています。

## [Unreleased]

(現在のスナップショットは初期公開版としてリリース済みのため、未リリース項目はありません)

## [0.1.0] - 2026-04-03

最初の公開リリース。日本株自動売買システムの基礎モジュール群を実装しました。
主な追加点は以下の通りです。

### Added
- 基本パッケージ
  - パッケージメタ情報 `kabusys` を導入（`__version__ = "0.1.0"`）。公開モジュールとして data, research, ai, などをエクスポート。

- 環境設定 / 設定管理 (`kabusys.config`)
  - .env ファイル自動読み込み機構を実装（プロジェクトルートを `.git` または `pyproject.toml` から探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パーサ: `export KEY=val`、シングル/ダブルクォート内のエスケープ、インラインコメント処理などに対応。
  - 環境変数保護（既存 OS 環境変数は上書きされない仕組み）を実装。
  - `Settings` クラスを提供。J-Quants / kabuステーション / LINE / DB パス / 監視設定 / システム設定（env, log_level, is_live 等）をプロパティで取得・検証。
  - 必須値未設定時は `ValueError` を送出する `_require` を実装。

- AI モジュール (`kabusys.ai`)
  - ニュース NLP スコアリング (`news_nlp.score_news`)
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成。
    - OpenAI（gpt-4o-mini）を JSON mode で呼び出し、最大 20 銘柄/リクエストでバッチ処理。
    - リトライ（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実装。
    - レスポンスの厳格バリデーション（results リスト、code・score 検証、数値変換、スコアの ±1.0 クリップ）。
    - 書き込みは部分失敗に耐える設計：取得したコードのみ DELETE→INSERT で置換（冪等性・部分保護）。
    - スコアウィンドウは JST 基準（前日 15:00 〜 当日 08:30）を UTC に変換して取り扱う。
  - 市場レジーム判定 (`regime_detector.score_regime`)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して `market_regime` に保存。
    - マクロセンチメントはニュースタイトルを抽出して LLM に評価させる（最大記事数やキーワードフィルタあり）。
    - LLM 呼び出しは再試行ロジックを実装、失敗時はフェイルセーフとして macro_sentiment=0.0 を採用。
    - レジームスコアはクリップ・閾値により `bull` / `neutral` / `bear` ラベル化。
    - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に実装。失敗時は ROLLBACK を試行。

- データモジュール (`kabusys.data`)
  - マーケットカレンダー管理（`calendar_management`）
    - `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day` 等の営業日判定ロジックを実装。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末を非営業日）を使用。
    - 最大探索日数制限、NULL 値時の警告ログなど堅牢設計。
    - 夜間バッチ `calendar_update_job`：J-Quants から差分取得し `market_calendar` に冪等保存。バックフィル・健全性チェック実装。
  - ETL パイプライン（`pipeline`）
    - ETL の実行結果を表す `ETLResult` データクラスを提供（取得数・保存数・品質問題・エラー等を集約）。
    - 差分更新・バックフィル・品質チェックの方針を実装（ロジックは jquants_client / quality モジュールと連携）。
    - DuckDB を前提としたテーブル存在チェック等のユーティリティを実装。
  - ETL 型の再エクスポート（`kabusys.data.etl.ETLResult`）を提供。

- リサーチモジュール (`kabusys.research`)
  - ファクター計算（`research.factor_research`）
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - Volatility / Liquidity: 20 日 ATR（atr_20 / atr_pct）、20 日平均売買代金、出来高比率等。
    - Value: PER（株価/EPS）、ROE を raw_financials と prices_daily から計算。
    - DuckDB 上の SQL ウィンドウ関数を多用し、営業日ベースで計算。データ不足時は None を返す。
  - 特徴量探索（`research.feature_exploration`）
    - 将来リターン計算 (`calc_forward_returns`)：複数ホライズンを束ねて取得、ホライズン検証あり。
    - IC（Information Coefficient）計算 (`calc_ic`)：スピアマンのランク相関でファクター有効性を評価。
    - ランク変換ユーティリティ (`rank`)：同順位は平均順位に処理。
    - 統計サマリー (`factor_summary`)：count/mean/std/min/max/median を計算。
  - `kabusys.research.__init__` で主要機能をエクスポート。

### Changed
- 設計上の重要事項を明確化
  - LLM 呼び出しやファクター計算では datetime.today()/date.today() を直接参照しない実装方針を採用し、ルックアヘッドバイアスを防止。
  - API 失敗時はフェイルセーフとして「スキップして継続」する方針（例外でプロセス全体を停止しない）。
  - DuckDB のバージョン差異を考慮した実装（executemany の空リスト回避、リスト型バインドの互換性対策等）。

### Fixed
- （初版のため該当なし）

### Security
- OpenAI API キー等の機密は `OPENAI_API_KEY` や各サービス用の環境変数で管理。`Settings` は必須キー未設定時に明示的に例外を出します。
- .env 読み込みは既存の OS 環境変数を上書きしない保護機能を持ち、誤って機密を上書きするリスクを低減。

### Notes / Implementation details
- 多くの処理は DuckDB を前提（DuckDB 接続オブジェクトを引数に取る設計）。
- OpenAI クライアント呼び出し部は各モジュールで private な関数として実装しており、テスト時はモック差し替えが容易（例: unittest.mock.patch）。
- LLM レスポンスは JSON mode を利用。ただし実際に外側テキストが混入する場合を想定してパースの復元処理も実装。
- DB 書き込みは可能な限り冪等に実装（DELETE→INSERT、ON CONFLICT 相当の振る舞いを意識）。
- 既知の設計方針（例: 部分失敗時に既存データを消さない等）はコード中の docstring に詳細に記載。

---

今後のリリース候補（例）
- 監視・実行モジュール（execution / monitoring）や jquants_client の詳細実装、品質チェックモジュールの公開。
- テストカバレッジの強化、OpenAI 呼び出しのフェイルオーバー/コスト制御オプションの追加。
- duckdb スキーマ初期化ユーティリティ、CLI / サービス起動スクリプトの追加。