Changelog
=========

すべての注目すべき変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠します。
ソースコードから推測して初期リリース向けの変更点をまとめています。

## [Unreleased]

### Added
- （未リリースの変更はここに記載）

---

## [0.1.0] - 2026-03-31

初回公開（推測）。ライブラリ全体の基本機能と主要モジュールを実装。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を src/kabusys/__init__.py に定義。
  - __all__ に data, strategy, execution, monitoring をエクスポート（将来のモジュール拡張を想定）。

- 設定 / 環境管理（kabusys.config）
  - .env ファイル（.env, .env.local）および環境変数から設定を自動ロードする機能を実装。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に探索。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応（テスト向け）。
  - .env パーサ（クォート／エスケープ／コメント処理、export KEY= 形式対応）を実装。
  - Settings クラスを提供し、以下の主要設定をプロパティで取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - PID_FILE_PATH, CPU/MEMORY/DISK の閾値
    - KABUSYS_ENV（development/paper_trading/live）とLOG_LEVEL の検証
  - 未設定の必須環境変数は ValueError を送出する設計。

- AI モジュール（kabusys.ai）
  - news_nlp.score_news: raw_news と news_symbols からニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ保存。
    - バッチ処理（銘柄ごと最大 _BATCH_SIZE=20）、1銘柄あたり記事数・文字数上限を導入。
    - JSON mode を使ったレスポンスパース、冗長テキストからの JSON 抽出ロジックを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ再試行実装。
    - レスポンス検証（results 配列、code と score の型チェック、スコア ±1.0 クリップ）。
    - 部分失敗に備え、DB 書き込みは対象コードのみ DELETE → INSERT で置換（冪等性・部分保護を重視）。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に設計。

  - regime_detector.score_regime: ETF 1321 の 200 日移動平均乖離（重み70%）と、ニュース由来のマクロセンチメント（重み30%）を合成して market_regime テーブルへ保存。
    - ma200_ratio の計算（target_date 未満のみ使用してルックアヘッドを防止）。
    - マクロ記事抽出（マクロキーワードリストに基づき raw_news からタイトルを取得）。
    - OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を評価。API 失敗時はフェイルセーフで 0.0 を採用。
    - レジーム合成後、market_regime に冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - LLM 呼び出しの再試行・エラー処理を実装。

- Data モジュール（kabusys.data）
  - calendar_management:
    - market_calendar テーブルを使用した営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先、未登録日は曜日フォールバック（土日を非営業日扱い）。
    - JPX カレンダーを J-Quants から差分取得して保存する夜間バッチ (calendar_update_job) を実装（バックフィル・健全性チェックあり）。
  - ETL / pipeline:
    - ETLResult データクラスを定義（取得数／保存数／品質チェック／エラー情報を保持）。
    - pipeline モジュールにより差分取得・保存・品質チェックの骨組みを実装（jquants_client と quality モジュールを利用する想定）。
    - jquants_client を用いた idempotent 保存への橋渡しを想定（save_* 関数を呼ぶ設計）。
  - etl.py では ETLResult を公開インターフェースとして再エクスポート。

- Research モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算。
    - 設計で DuckDB の SQL ウィンドウ関数を活用し、営業日ベースの窓処理を行う。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターンを一度のクエリで取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。
    - rank: 平均ランク（同順位は平均ランク）に変換するユーティリティ。
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算。
  - データ前提は prices_daily / raw_financials のみで、外部発注や口座操作は行わない設計。

### Changed
- 初回リリースのため該当なし（新規実装中心）。

### Fixed
- 初回リリースのため該当なし。

### Security
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出して誤使用を防止。

### Notes / Design decisions
- ルックアヘッドバイアス防止:
  - 各アルゴリズム（news window, ma200, forward returns, regime scoring 等）は内部で datetime.today() / date.today() を直接参照せず、呼び出し側から target_date を渡す設計。
  - DB クエリでは target_date より過去のみを参照するなど、将来データの混入を避ける工夫がある。
- フェイルセーフ:
  - LLM / API 呼び出しに失敗した場合はスコアを 0.0 にフォールバックするか、該当チャンクをスキップして処理継続する。
- 冪等性:
  - DB 書き込みは DELETE → INSERT などで冪等性を確保する設計（部分失敗時に既存データを保護）。
- テスト容易性:
  - OpenAI 呼び出しや内部 API 呼び出しはモジュール内の関数をパッチ差し替え可能にしてテストしやすくしている。
- 外部依存:
  - DuckDB を主要なデータ操作エンジンとして利用。
  - OpenAI SDK（OpenAI クライアント）を用いる前提。

### Deprecated
- なし

### Removed
- なし

### Breaking Changes
- なし（初回リリースのため該当なし）

---

既知の制約 / 今後の改善候補（推測）
- strategy / execution / monitoring モジュール群は __all__ に含まれるが、今回のコード断片では実体が見当たらないため実装は今後追加される想定。
- jquants_client / quality モジュールは参照されているが、実装詳細は別途提供される想定。
- DuckDB バインドの互換性（executemany の空リスト制約等）に注意した実装があるため、DuckDB バージョンに依存する挙動の検証が必要。

もし特定リリース日や追加の変更点（テスト、CI、ドキュメント、パッケージ設定等）が判明していれば、その情報を提供してください。CHANGELOG を更新して反映します。