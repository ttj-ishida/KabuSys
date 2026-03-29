# CHANGELOG

すべての変更は「Keep a Changelog」形式に準拠し、重要な変更点を日本語でまとめています。

※バージョン番号はパッケージ内の __version__ を基にしています。

## [0.1.0] - 2026-03-29
初回リリース（初期実装）。以下の主要機能を提供します。

### 追加
- パッケージ基礎
  - kabusys パッケージを追加。パッケージメタ情報として __version__ = "0.1.0" を設定し、主要サブパッケージ（data, strategy, execution, monitoring）を __all__ で公開。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートは __file__ の親階層を探索して .git または pyproject.toml を基準に決定。
    - 読み込み優先順位は OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用）。
  - .env パーサーは以下に対応。
    - 空行・コメント行（#）を無視。
    - export KEY=val 形式をサポート。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理。
    - クォート無しの場合の行内コメント扱い（直前が空白またはタブの # をコメントと認識）。
  - Settings クラスを提供し、キー必須取得（未設定時は ValueError）や型変換を行うプロパティを公開:
    - J-Quants / kabuAPI / Slack 用の必須トークン・ID
    - duckdb/sqlite のデフォルトパス（Path 型）
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev 補助プロパティ

- AI（kabusys.ai）
  - ニュース NLU（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとにニューステキストを結合して OpenAI（gpt-4o-mini）へバッチ送信しセンチメントを推定。
    - タイムウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST に対応）。
    - バッチサイズ、1銘柄あたりの最大記事数・最大文字数制限を導入（トークン肥大化対策）。
    - OpenAI 呼び出しは JSON Mode を利用し、レスポンスのバリデーション（results 配列 / code / score チェック）を行う。
    - レスポンスの数値を ±1.0 にクリップして ai_scores テーブルへ冪等的に（DELETE → INSERT）保存。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。失敗したチャンクはスキップして継続するフェイルセーフ設計。
    - テスト容易性のため _call_openai_api をモック差し替え可能。
    - DuckDB 0.10 の executemany の制約に配慮し、空リストでの executemany を回避する実装（部分失敗時に他銘柄の既存スコアを保護）。
    - パブリック API: score_news(conn, target_date, api_key=None) -> 書き込み件数を返す。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei 225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジームを判定（'bull' / 'neutral' / 'bear'）。
    - ma200_ratio の計算は target_date 未満のデータのみ使用してルックアヘッドを防止。
    - マクロニュースは news_nlp の calc_news_window を利用してウィンドウを計算し、キーワードフィルタで抽出したタイトルを LLM に渡す。
    - OpenAI 呼び出しは独立実装で、RateLimit/接続エラー/タイムアウト/5xx に対するリトライとフェイルセーフ（失敗時 macro_sentiment=0.0）を実装。
    - 最終的な結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - パブリック API: score_regime(conn, target_date, api_key=None) -> 1（成功）を返す設計。

- データ（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー管理用ユーティリティを提供。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - market_calendar がない場合は曜日ベース（土日除外）でフォールバック。
    - next/prev は DB 登録値を優先し、未登録日を曜日フォールバックで扱うため m と一貫性を保つ。
    - 最大探索範囲を設定して無限ループを防止（_MAX_SEARCH_DAYS）。
    - calendar_update_job: J-Quants API（jquants_client）から差分取得して market_calendar を冪等保存。バックフィルや健全性チェック（先になり過ぎた last_date のスキップ）を実装。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（kabusys.data.etl は ETLResult を再エクスポート）。
    - 差分更新・バックフィル・品質チェックの設計方針に沿った機能を提供するための基盤を実装（J-Quants クライアント連携を想定）。
    - ETLResult は品質チェック結果やエラー一覧を格納でき、has_errors / has_quality_errors / to_dict を提供。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER, ROE）、Volatility（20 日 ATR）等のファクターを DuckDB の prices_daily / raw_financials を用いて計算する関数を実装:
      - calc_momentum(conn, target_date)
      - calc_value(conn, target_date)
      - calc_volatility(conn, target_date)
    - 設計上、外部 API にはアクセスせず、本番発注ロジックと分離。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)。複数ホライズンを一度に取得するための最適化を実装。
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col)（Spearman ランク相関）。
    - 統計サマリー: factor_summary(records, columns)（count/mean/std/min/max/median）。
    - ランク関数: rank(values)（同順位は平均ランク）。
  - research パッケージの __init__.py で主要関数を再エクスポート（zscore_normalize を kabusys.data.stats から再エクスポート）。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### セキュリティ
- なし（該当なし）

---

今後のリリースで想定される改善点（今後のリファクタ案・注意点）
- OpenAI クライアント依存の抽象化（プラグイン可能なクライアントインタフェース）によるテスト性・移植性向上。
- DuckDB バインドの互換性回避ロジック（executemany 空リスト等）を更に一般化。
- J-Quants / kabuAPI 周りのエラー分類と再試行ポリシーの一元化。
- ai モジュールのモデル選択や温度（temperature）などの設定を外部設定化。

（以上）