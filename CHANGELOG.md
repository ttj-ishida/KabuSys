# Changelog

すべての変更は Keep a Changelog のガイドラインに従い、逆順（最新が上）で記載します。

## [Unreleased]

## [0.1.0] - 2026-04-02
初回公開リリース。日本株自動売買システム "KabuSys" のコア機能群を実装しました。

### 追加
- 基本パッケージ設定
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
  - パッケージ公開 API（data, strategy, execution, monitoring）を定義。

- 環境変数 / 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機構を実装。プロジェクトルートは .git または pyproject.toml を基準に探索。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み抑止をサポート（テスト用途）。
  - .env パーサ実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理対応、インラインコメント処理、無効行スキップ。
    - 既存 OS 環境変数を保護する protected 設定（.env.local は override=True だが protected キーは上書きしない）。
  - 必須設定取得用の _require と Settings クラスを提供:
    - J-Quants / kabuAPI / Slack / DB パス / 監視設定 / ログレベル 等のプロパティを提供。
    - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の値検証を実装。
    - デフォルト値（KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、PID_FILE_PATH、閾値等）を設定。

- AI（自然言語処理）モジュール
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）にバッチ送信して銘柄別センチメント（ai_score）を取得。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算用 calc_news_window を実装。
    - バッチ処理（最大 20 銘柄 / チャンク）、各銘柄のテキスト長トリム（_MAX_CHARS_PER_STOCK）、記事数制限（_MAX_ARTICLES_PER_STOCK）。
    - JSON Mode を利用した堅牢なレスポンス検証（部分的な前後テキストの復元、results 配列・code/score のバリデーション、スコアを ±1 にクリップ）。
    - API 失敗（429・ネットワーク・タイムアウト・5xx）に対する指数バックオフリトライ、失敗時はスキップして継続するフェイルセーフ挙動。
    - DuckDB へ冪等書き込み（DELETE → INSERT、executemany の空リスト扱い回避）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次で market_regime を判定。
    - マクロセンチメントはニュースタイトルをマクロキーワードで抽出し、OpenAI に JSON 出力で評価させる。
    - LLM 呼び出しは独立実装でモジュール結合を避ける設計。
    - API 呼び出しのリトライ・バックオフを実装し、全リトライ失敗時やパース失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - レジーム（bull/neutral/bear）判定閾値と ma200_ratio 計算、DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT と ROLLBACK のハンドリング）。

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を参照した営業日判定 API（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB にデータがない場合は曜日ベース（土日除外）のフォールバックを提供。
    - カレンダー差分取得バッチ（calendar_update_job）を実装（J-Quants クライアント経由の fetch/save、バックフィル、健全性チェック）。
    - 探索範囲制限（_MAX_SEARCH_DAYS）とバックフィル（日数）を実装し無限ループ/過剰取得を防止。

  - ETL パイプライン（kabusys.data.pipeline と etl 再エクスポート）
    - ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラー一覧等を保持）。
    - 差分取得・保存・品質チェックの設計に沿ったインタフェースを用意（J-Quants クライアントおよび quality モジュールとの連携を想定）。
    - デフォルトのバックフィル日数やカレンダー先読み等を定義。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER/ROE）を DuckDB クエリで計算する関数を実装。
    - データ不足に対する None の返却やロギング、営業日スキャン幅のバッファ設計を導入。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を実装。
    - horizons の入力検証、複数ホライズンを一クエリで取得する実装、スピアマン相関（ランク相関）計算の実装。
    - 外部依存を持たず標準ライブラリと DuckDB で完結する設計。

### 変更
- 初版のため該当なし。

### 修正
- 初版のため該当なし。

### 既知の問題 / 注意点
- pipeline モジュール末尾に断片的なコード（_get_max_date の戻り値処理が途中で終わっているように見える箇所）があり、将来の小さな修正が必要と推測されます（本 Changelog はコードから推測して作成しているため、実装の最終調整や細かなバグ修正はリリース後に発生する可能性があります）。
- OpenAI API キーは引数で注入可能だが、未指定時は環境変数 OPENAI_API_KEY を参照する点に注意してください。未設定の場合は ValueError を送出します。
- DuckDB executemany はバージョン差異で空リストの扱いに注意が必要なため、空リストチェックを行う実装が含まれています。

### セキュリティ
- 初版のため該当なし。

---

参考: 本 CHANGELOG はリポジトリ内のソースコード（モジュール、関数、ドキュメンテーション文字列）から機能・設計方針を推測して作成しました。実際の利用に際しては README やドキュメント、ユニットテストを参照し、環境変数や外部 API（OpenAI/J-Quants/kabu） の設定を適切に行ってください。