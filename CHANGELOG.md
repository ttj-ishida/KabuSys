# Changelog

すべての注目すべき変更をこのファイルに記録します。このプロジェクトは Keep a Changelog の形式に準拠しています。  
初期リリースの内容は、コードベース（src/kabusys 以下）から推測して記載しています。

## [Unreleased]

- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-29

### Added
- パッケージ基盤
  - パッケージバージョンを `0.1.0` に設定（src/kabusys/__init__.py）。
  - 主要サブパッケージを公開 (`data`, `strategy`, `execution`, `monitoring`)。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装。プロジェクトルート判定は `.git` または `pyproject.toml` を探索して行うため、CWD に依存しない（パッケージ配布後も動作）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パーサは `export KEY=val`、クォート文字列、バックスラッシュエスケープ、インラインコメントの取り扱いなどに対応。
  - `_load_env_file` は既存の OS 環境変数を保護する `protected` 機能を備え、override の挙動を制御。
  - 必須変数取得用の `_require`、アプリ設定を表す `Settings` クラスを提供（J-Quants / kabuAPI / Slack / DB パス等のプロパティを含む）。
  - `KABUSYS_ENV` と `LOG_LEVEL` の値検証（許容値セットのチェック）を実装。
  - デフォルトの DB パス（DuckDB/SQLite）の取得をサポート。

- AI モジュール (kabusys.ai)
  - ニュース NLP（news_nlp）
    - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して `ai_scores` テーブルへ書き込む機能を実装。
    - タイムウィンドウは JST ベース（前日 15:00 ～ 当日 08:30）で、内部は UTC naive datetime に変換して DB 比較を行う。
    - バッチ処理（1 回につき最大 20 銘柄）、1 銘柄あたり記事は最新 10 件・最大 3000 文字にトリム。
    - OpenAI 呼び出しは JSON Mode を用い、429/ネットワーク断/タイムアウト/5xx に対する指数的バックオフによるリトライを実装。非リトライ対象エラーはスキップ（フェイルセーフ）。
    - レスポンスバリデーションを厳格に実施（JSON 抽出、"results" 構造、既知コードの照合、数値変換、有限性チェック）。スコアは ±1.0 にクリップ。
    - DuckDB への書き込みは部分失敗時に既存スコアを保護するため、対象コードのみを DELETE → INSERT する冪等操作を行う（executemany の空パラメータ回避対応あり）。
    - 公開関数: `score_news(conn, target_date, api_key=None)` をエクスポート。

  - 市場レジーム判定（regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（'bull' / 'neutral' / 'bear'）を計算。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - マクロニュース抽出はマクロキーワード群でフィルタし、LLM（gpt-4o-mini）に JSON 出力を要求。記事が無い場合は LLM 呼び出しを省略し macro_sentiment=0.0 を用いる。
    - OpenAI 呼び出しは専用の内部実装で、API の一時的失敗に対するリトライ/バックオフを実装。最終的に macro_sentiment のフォールバックは 0.0。
    - レジームスコアを計算後、`market_regime` テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、例外時は ROLLBACK）を行う。
    - 公開関数: `score_regime(conn, target_date, api_key=None)` を提供。

- データ管理 (kabusys.data)
  - カレンダー管理（calendar_management）
    - JPX カレンダーを保持する `market_calendar` を対象に営業日判定ロジックを提供:
      - is_trading_day(conn, d)
      - next_trading_day(conn, d)
      - prev_trading_day(conn, d)
      - get_trading_days(conn, s, e)
      - is_sq_day(conn, d)
    - DB 登録値を優先し、未登録日の扱いは曜日ベースのフォールバック（土日非営業日）で一貫した挙動を実現。
    - カレンダー夜間バッチ `calendar_update_job(conn, lookahead_days=90)` を実装。J-Quants クライアントから差分取得し冪等保存。バックフィル期間や健全性チェック（過度の未来日をスキップ）を実装。
    - 内部ユーティリティ: テーブル存在チェック、値変換、NULL 値検出と警告ログ。

  - ETL / Pipeline（pipeline, etl）
    - ETL 実行結果を表す `ETLResult` データクラスを公開（kabusys.data.etl は pipeline.ETLResult を再エクスポート）。
      - 取得・保存件数、品質問題、エラー一覧を保持。`has_errors`, `has_quality_errors`, `to_dict()` を提供。
    - ETL パイプラインの設計に沿ったユーティリティ（差分取得、バックフィル、品質チェックの収集、id_token 注入によるテスト容易性など）を実装。
    - DuckDB のテーブル存在チェック、最大日付取得ユーティリティを実装。

- リサーチ（kabusys.research）
  - ファクター計算（factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER、ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金・出来高比率）を DuckDB 上の SQL と Python で計算する関数を提供:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - データ不足時は None を返す等、堅牢な欠損処理を実装。返り値は (date, code) をキーとする dict のリスト。

  - 特徴量探索・統計（feature_exploration）
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)（デフォルト [1,5,21]）
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col)（スピアマンのランク相関）
    - ランク変換ユーティリティ: rank(values)
    - 統計サマリー: factor_summary(records, columns)（count/mean/std/min/max/median）
    - 実装は外部依存（pandas 等）を避け、標準ライブラリと DuckDB だけで完結。

- その他
  - 各モジュールはログ出力（logging）を適切に行い、例外時には警告/例外ログを残すよう設計。
  - モジュール間の結合を抑えるため、内部の OpenAI 呼び出し関数はそれぞれ独立した実装になっており、テスト時には patch で差し替え可能。

### Changed
- 初回リリースのため該当なし（初期実装）。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- OpenAI API キーは引数注入または環境変数 `OPENAI_API_KEY` から解決する設計。キー管理は呼び出し側に委ねられる（ソースコードに直接埋め込まないことを想定）。

---

注:
- 上記はソースコード（src/kabusys 以下）から推測した初期リリースの機能一覧および設計方針です。実際のリリースノート作成時は、コミット履歴・リリース担当者の情報・変更差分を参照して調整してください。