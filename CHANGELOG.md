# Changelog

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
安定性・互換性のためセマンティックバージョニングを採用します。

## [Unreleased]
- 次回リリースの変更点はここに記載します。

## [0.1.0] - 2026-03-27
初回リリース

### 追加
- パッケージ基盤
  - kabusys パッケージの公開開始（__version__ = 0.1.0）。
  - パッケージの公開シンボル: data, strategy, execution, monitoring。

- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート自動発見ロジックを実装（.git または pyproject.toml を基準に探索）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサを実装（export プレフィックス・クォート・エスケープ・インラインコメント対応）。
  - OS 環境変数保護（既存の環境変数を保護する protected 機構）と override オプション。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / システム設定等のプロパティを取得可能。
  - KABUSYS_ENV と LOG_LEVEL のバリデーションを実装（有効値チェック）。
  - 必須環境変数未設定時に説明的な ValueError を送出する _require()。

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を使って銘柄毎にニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを算出する score_news() を実装。
  - タイムウィンドウ計算ユーティリティ calc_news_window() を実装（JST ベースのウィンドウ → UTC naive datetime を返す）。
  - バッチ処理（1 API コール当たり最大 20 銘柄）と記事数 / 文字数トリム（銘柄当たり最大記事数・最大文字数）を実装。
  - OpenAI 呼び出しでのリトライ（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）を実装。
  - API レスポンスの厳格なバリデーションと復元処理（JSON mode を想定、前後余計なテキストを含む場合に最外の {} を抽出）。
  - スコアの ±1.0 クリップ、部分成功時の DB 置換ロジック（該当コードのみDELETE→INSERT）による冪等性と被害最小化。
  - フェイルセーフ設計: API 失敗時は該当チャンクをスキップして処理継続。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の200日移動平均乖離（重み70%）とマクロニュースのLLMセンチメント（重み30%）の合成で市場レジーム（bull/neutral/bear）を判定する score_regime() を実装。
  - DuckDB を用いた ma200_ratio 計算（ルックアヘッド防止のため target_date 未満データのみ使用）。データ不足時は中立（1.0）を返す。
  - マクロニュース抽出（キーワードフィルタ）と OpenAI によるマクロセンチメント算出ロジックを実装。API 失敗は macro_sentiment=0.0 にフォールバック。
  - LLM 呼び出しのリトライ・エラーハンドリング（RateLimit, APIConnectionError, APITimeoutError, APIError の取扱い）を実装。
  - レジームスコア合成・閾値判定（_BULL_THRESHOLD/_BEAR_THRESHOLD）と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。

- データ / カレンダー管理（kabusys.data.calendar_management）
  - JPX カレンダー（market_calendar）を扱うユーティリティ群を実装:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
  - DB 登録値を優先し未登録日は曜日ベース（平日）でフォールバックする一貫した動作。
  - 最大探索範囲の制限（_MAX_SEARCH_DAYS）により無限ループ回避。
  - calendar_update_job(): J-Quants からの差分取得と market_calendar への冪等保存、バックフィルと健全性チェックを実装。

- ETL / パイプライン（kabusys.data.pipeline, kabusys.data.etl）
  - ETLResult データクラスを公開し、ETL 実行結果（取得数 / 保存数 / 品質問題 / エラー）を集約可能に。
  - ETL パイプラインユーティリティの土台を実装（差分取得・保存・品質チェックの設計方針を反映）。
  - jquants_client 経由の取得と save_* 系の idempotent 保存を想定。

- リサーチ / ファクター算出（kabusys.research）
  - ファクター計算モジュールを実装:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率。
    - calc_value: PER（EPS が 0/欠損時は None）、ROE（raw_financials から最新値を取得）。
  - 特徴量探索モジュールを実装:
    - calc_forward_returns: 指定 horizon の将来リターン計算（複数ホライズン対応・入力検証あり）。
    - calc_ic: スピアマンランク相関（IC）計算（None/小サンプルの扱いを含む）。
    - rank, factor_summary: ランク付け（同順位平均ランク）および統計サマリ機能。
  - DuckDB SQL と標準ライブラリのみでの実装（pandas 等に依存しない設計）。

- 汎用実装・運用上の配慮
  - DuckDB を主要な分析 DB として利用する設計（関数引数に DuckDB 接続を受け取る）。
  - ルックアヘッドバイアス防止: 各モジュールで datetime.today()/date.today() の安易な参照を避け、target_date を明示的に受け取る設計。
  - OpenAI SDK（OpenAI クライアント）を利用する実装。テスト容易性のため _call_openai_api を patch 可能に設計。
  - エラーハンドリングとログ出力を充実させ、部分失敗時は影響を局所化して継続するフェイルセーフ設計。
  - DuckDB の executemany に関する互換性考慮（空リスト送信回避）。

### 既知の制限 / 注意点
- OpenAI API キー（OPENAI_API_KEY）は必須。score_news / score_regime 呼び出し時に api_key を直接渡すか環境変数を設定する必要があります。未設定時は ValueError を送出します。
- 一部処理は外部 API（J-Quants, OpenAI）に依存するため、ネットワーク障害や API レート制限が発生する場合はフェイルセーフ（スキップ・0.0 フォールバック等）で動作しますが、結果が不足することがあります。
- 現時点で PBR・配当利回りなど一部のバリュー指標は未実装です（calc_value の注記参照）。
- DuckDB の型返却（date 等）や executemany の挙動に対する互換性コードが含まれます。使用する DuckDB バージョンによっては挙動差があるため注意してください。
- カレンダーデータが存在しない場合は曜日ベースでのフォールバックを行います（完全なカレンダーデータ取得を推奨）。

### セキュリティ
- 環境変数のロードは既存 OS 環境変数を保護する仕組みを持ちます。ただし .env ファイルの管理はユーザ側で適切に行ってください（機密情報の管理に注意）。

---

貢献・バグ報告・改善提案は issue を通じて受け付けます。