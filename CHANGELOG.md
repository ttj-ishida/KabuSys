# CHANGELOG

すべての重要な変更をこのファイルに記録します。フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-04-04

### Added
- パッケージ基盤
  - パッケージバージョンを設定: kabusys 0.1.0 を追加。
  - パッケージトップの公開 API を定義（__all__）：data, strategy, execution, monitoring。
- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定値を読み込む自動ローダーを実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（カレントワーキングディレクトリに依存しない）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
    - OS 環境変数は保護（protected）され、.env.local でも上書きされない。
  - .env 行パーサーを強化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱い（クォート有無で挙動異なる）。
    - 無効行やコメント行を省略。
  - Settings クラスを提供し、主要な設定値をプロパティ経由で取得:
    - J-Quants / kabuステーション / LINE / DB パス / 監視設定（PID / kill flag /閾値）/ 環境（development/paper_trading/live）/ログレベル等。
    - 必須変数取得時は未設定で ValueError を送出する（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - env, log_level の値検証を実装（不正値は ValueError）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。
- AI モジュール（kabusys.ai）
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを算出して ai_scores テーブルへ書き込む機能を追加（score_news）。
    - タイムウィンドウ計算（JST基準 → UTC naive datetime で返す calc_news_window）。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/回）、1銘柄あたりの記事数・文字数上限（肥大化対策）。
    - リトライとエクスポネンシャルバックオフ：429・ネットワーク断・タイムアウト・5xx を対象に最大リトライを実施。
    - レスポンス検証（JSON 抽出、results リスト・各要素 code/score の検証、スコアの数値化と ±1.0 クリップ）。
    - DB 書き込みは部分失敗を考慮して idempotent（対象コードのみ DELETE → INSERT）で実行。DuckDB の executemany の空リスト制約を考慮。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）、テスト容易性のため OpenAI 呼出し部分は差し替え可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定・market_regime テーブルへ書込む機能を追加（score_regime）。
    - ma200_ratio の計算（ルックアヘッド防止のため target_date 未満のデータのみ使用、データ不足時は中立値を採用してフェイルセーフ）。
    - マクロ記事の抽出（マクロキーワードでフィルタ）と LLM スコアリング（json 出力期待）、API エラー時のフォールバック（macro_sentiment=0.0）。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時に ROLLBACK）。
    - OpenAI 呼び出しにもリトライ・バックオフを実装。
    - ルックアヘッドバイアス対策として datetime.today()/date.today() を参照しない設計。
- Data モジュール（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー管理ロジックを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar が未取得の場合は曜日ベース（土日除外）のフォールバックを提供。
    - DB 登録値を優先し、未登録日は曜日ベースで一貫した補完を行う。
    - カレンダーの夜間バッチ更新 job（calendar_update_job）を追加。J-Quants から差分取得 → 保存（バックフィル・健全性チェックあり）。
  - ETL / パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - ETLResult データクラスをエクスポートし、ETL 実行結果（取得数・保存数・品質問題・エラー）を集約可能に。
    - 差分更新、バックフィル、品質チェックのための下地を実装（jquants_client と quality モジュールを利用する設計）。
    - _table_exists / _get_max_date 等の内部ユーティリティを実装（DuckDB 対応）。
- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（calc_momentum）: 1M/3M/6M リターン、200日MA乖離（ma200_dev）を計算。データ不足時は None を返す。
    - ボラティリティ・流動性（calc_volatility）: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。必要行数不足で None を返す。
    - バリュー（calc_value）: raw_financials から直近の財務データを組合せて PER / ROE を算出（EPS 0 または欠損時は None）。
    - DuckDB のウィンドウ関数を活用し、SQL 内で効率的に計算。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：任意ホライズン（デフォルト [1,5,21]）の fwd リターンを計算。horizons の検証（1〜252）を実装。
    - IC（Information Coefficient）計算（calc_ic）：factor_records と forward_records を code ベースで結合し、スピアマン順位相関を算出。サンプル不足や等分散時の安全処理あり。
    - ランク変換ユーティリティ（rank）：同順位は平均ランクを返す（浮動小数誤差対策として round を適用）。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を算出。
  - 研究用に外部ライブラリへ依存せず標準ライブラリ + DuckDB で実装。
- テスト性・安全性の強化
  - OpenAI 呼出し部を個別関数化し、ユニットテスト時に patch で差し替え可能に（news_nlp._call_openai_api、regime_detector._call_openai_api 等）。
  - LLM レスポンスパース失敗や API 障害時は例外を直接上げずフェイルセーフでスコア=0.0 / スキップ等の挙動を採用。ログ出力で詳細を通知。
  - DuckDB 書き込みは可能な限り冪等性を担保（DELETE→INSERT、ON CONFLICT 前提の保存手法を活用する設計思想）。
- ドキュメント文字列およびログ出力を充実化し、各関数の設計意図や注意点を明記。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

---

注意:
- OpenAI（gpt-4o-mini）利用箇所は外部 API へのアクセスが必要です。score_news / score_regime 実行時は api_key 引数または環境変数 OPENAI_API_KEY を設定してください。
- 必須の環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は Settings から取得する際に未設定だと例外が発生します。.env.example を参考に設定してください。