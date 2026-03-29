# CHANGELOG

すべての注目すべき変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-29

### 追加
- パッケージ基盤
  - 初期リリース。トップレベルのパッケージ情報を追加（kabusys.__version__ = "0.1.0"）。
  - 公開 API として data, strategy, execution, monitoring を __all__ に定義。

- 環境設定・ロード（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能を実装（プロジェクトルートを .git / pyproject.toml を基準に探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを強化：
    - export KEY=val 形式対応。
    - シングル/ダブルクォートを考慮した値のパース（バックスラッシュエスケープ対応）。
    - インラインコメントの取り扱い（クォート有無により挙動を分ける）。
    - 読み込み時に OS 環境変数を保護する protected 機能（.env.local の上書き挙動を制御）。
    - 読み込み失敗時に警告を出す（ファイルオープン失敗など）。
  - 設定プロパティを多数追加（必須項目は _require により未設定時に ValueError を送出）:
    - J-Quants / kabu ステーション / Slack / DB パスなど（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH）。
  - 環境検証機能:
    - KABUSYS_ENV（development, paper_trading, live）の検証。
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）の検証。
    - is_live / is_paper / is_dev の便宜プロパティ。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（news_nlp.py）
    - raw_news / news_symbols テーブルから記事を集約し、OpenAI（gpt-4o-mini）の JSON モードで銘柄ごとのセンチメントを算出して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウの計算（JST 基準、UTC 変換）を提供（calc_news_window）。
    - バッチ処理（最大 20 銘柄 / チャンク）、記事数/文字数上限（記事数: 10、文字数: 3000）によるトリム。
    - エラー耐性: 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ、その他の失敗はスキップして処理継続（フェイルセーフ）。
    - レスポンス検証ロジック（JSON 抽出、results 配列チェック、コードの正規化、スコアの数値化と ±1.0 クリップ）。
    - DuckDB に対する冪等的な書き込み（該当 date/code を DELETE → INSERT、executemany の空リスト回避）。
    - テスト容易性のため OpenAI 呼び出し関数を patch しやすく実装（kabusys.ai.news_nlp._call_openai_api を差し替え可能）。
    - 公開関数: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。

  - 市場レジーム判定（regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成し市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ保存する処理を実装。
    - マクロニュース抽出（マクロキーワード群による title 検索、最大 20 件）。
    - OpenAI（gpt-4o-mini）によるマクロセンチメント算出（JSON モード）。API エラー時は macro_sentiment=0.0 のフェイルセーフ。
    - LLM 呼び出しに対するリトライ / バックオフの実装。
    - ma200_ratio 計算は target_date 未満のデータのみを使用しルックアヘッドバイアスを排除（データ不足時は中立 1.0 を使用）。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- リサーチ（src/kabusys/research）
  - factor_research.py
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER, ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金、出来高比率）などのファクター計算を実装。
    - DuckDB のウィンドウ関数を利用し、高速に計算。
    - データ不足時の None 返却やログ出力を含む堅牢な設計。
    - 公開関数: calc_momentum, calc_volatility, calc_value（各々 target_date を引数に取り (date, code) キーの dict リストを返す）。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン（デフォルト [1,5,21]）に対応、入力検証あり。
    - IC（Information Coefficient）算出（calc_ic）: スピアマンランク相関を実装（同順位処理: 平均ランク）。
    - ランキングユーティリティ（rank）: ties を平均ランクで処理、丸めによる ties 検出の安定化。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を標準ライブラリのみで計算。
    - すべて DuckDB / 内部データを参照し外部発注等には影響を与えない設計。

- データ（src/kabusys/data）
  - calendar_management.py
    - JPX カレンダー管理 API（夜間バッチ用）。market_calendar テーブルの存在確認、DB 優先の営業日判定ロジック（未登録日は曜日フォールバック）、next/prev/get_trading_days/is_sq_day 等のユーティリティを提供。
    - calendar_update_job により J-Quants から差分取得 → 保存（バックフィル、健全性チェック、ON CONFLICT 相当の保守）を実行。
    - 最大探索日数やバックフィル日数等の安全パラメータを定義して無限ループ・異常データを防止。
  - pipeline.py / etl.py
    - ETLResult データクラス（ETL 実行結果の集約）を実装（品質問題リスト・エラーリスト・集計カウント等を含む）。
    - 差分更新・バックフィル・品質チェック連携の方針を実装（jquants_client 経由の保存、品質チェックとの連携を想定）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得、取引日調整用のヘルパー関数等。

- テスト可能性・堅牢性
  - OpenAI 呼び出し箇所での差し替え用フック（_call_openai_api の patch）を用意しており、ユニットテストが容易。
  - ルックアヘッドバイアス対策として datetime.today()/date.today() の直接参照を避け、target_date ベースの計算を徹底。

- 依存関係（実装から推測）
  - duckdb、openai ライブラリを使用しているため本リリースではそれらが必要。

### 変更
- 初回リリースのため過去バージョンからの変更はなし。

### 修正
- .env のパース周りでの既知のエッジケースに対処（クォート内部のエスケープ、export プレフィックス、インラインコメントの扱い、読み込み失敗時の警告）。
- DuckDB に対する executemany の空リストバインド問題を回避するチェックを追加（空パラメータ時に executemany を呼ばない）。

### 破壊的変更
- なし（初期リリース）。

### セキュリティ
- OpenAI API キーの取得は明示的に引数で注入可能。環境変数が未設定の場合は ValueError を送出して明示的に失敗させる（安全側の挙動）。

---

注: 本 CHANGELOG はソースコードの実装内容から推測して作成しています。API の利用方法や外部依存（J-Quants / kabuapi / OpenAI / DuckDB）については README やドキュメントを参照してください。