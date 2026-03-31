# Changelog

すべての変更は Keep a Changelog のフォーマットに従い、セマンティックバージョニングを使用しています。  
公式リリース日が不明な場合は、リリース時に日付を更新してください。

## [Unreleased]
- 今後の変更点を記載します。

## [0.1.0] - 2026-03-31
初期リリース。日本株の自動売買・データ基盤・リサーチ・AI支援分析を目的とした基盤ライブラリを提供します。

### Added
- パッケージエントリポイント
  - kabusys パッケージのバージョンを 0.1.0 として公開。
  - パッケージの公開サブパッケージとして data, strategy, execution, monitoring を __all__ で公開（パッケージ外からの参照インターフェースを明示）。

- 設定管理 (kabusys.config)
  - .env および .env.local をプロジェクトルート（.git または pyproject.toml を起点）から自動ロードする仕組みを実装。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサを実装（export 形式、シングル/ダブルクォートとエスケープ、インラインコメントの扱い、無効行スキップなどに対応）。
  - 環境変数の読み取り用 Settings クラスを追加（J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境種別・ログレベル等をプロパティで取得）。
  - 必須環境変数チェック (_require) により未設定時は ValueError を送出。
  - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"、PID ファイル等のデフォルトも定義。

- AI モジュール (kabusys.ai)
  - ニュースセンチメント解析 (news_nlp.score_news)
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合・トリムし、OpenAI（gpt-4o-mini、JSON mode）へバッチ送信して銘柄単位のセンチメント ai_score を ai_scores テーブルへ書き込む。
    - バッチサイズ制限、1銘柄当たりの記事数・文字数制限、最大リトライ（429/ネットワーク/タイムアウト/5xx）、レスポンス検証、スコアの ±1.0 クリップを実装。
    - API キーは引数注入可能（テストしやすい設計）。API失敗時は該当チャンクをスキップして継続するフェイルセーフ設計。
    - DuckDB executemany の仕様を考慮して空パラメータを回避する実装（互換性確保）。
    - calc_news_window ユーティリティ: タイムウィンドウ（JST ベース → UTC naive datetime）を返す。

  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出（マクロキーワード群でフィルタ）、OpenAI 呼び出し（gpt-4o-mini、JSON mode）による macro_sentiment 評価、リトライ＆指数バックオフ、API 失敗時は macro_sentiment = 0.0 のフォールバック。
    - DuckDB クエリはルックアヘッドを防ぐため target_date 未満のデータを利用する等、バイアス対策を実装。
    - _call_openai_api はテスト用に差し替え可能（モジュール間でプライベート関数を共有しない設計）。

- データ基盤モジュール (kabusys.data)
  - カレンダー管理 (calendar_management)
    - JPX マーケットカレンダーの更新バッチ（calendar_update_job）を実装。J-Quants API から差分取得して market_calendar テーブルへ冪等保存。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを実装。DB 未登録日は曜日ベースでフォールバックする一貫性のある挙動。
    - 最大探索日数制限やバックフィル、健全性チェック（未来日付の異常検出）などを組み込み。

  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを追加（取得数・保存数・品質問題・エラーの集約）。
    - 差分更新、バックフィル、品質チェック呼び出し等を想定した設計。jquants_client 経由の保存処理と品質検査モジュール（quality）との連携を想定。

  - jquants_client のラッパー（data モジュール内で参照）を想定した設計で API 取得→保存の差分 ETL をサポート。

- リサーチ / ファクター (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER/ROE）の計算関数を実装。prices_daily / raw_financials テーブルのみを参照する設計。
    - SQL とウィンドウ関数を活用した効率的実装。データ不足時は None を返す等の堅牢性を確保。

  - feature_exploration
    - 将来リターン calc_forward_returns（任意ホライズン対応）、IC（calc_ic：Spearman ランク相関）、rank（同順位は平均ランク方式）、factor_summary（count/mean/std/min/max/median）など、研究用途の統計解析ユーティリティを実装。
    - pandas 等の外部ライブラリに依存しない純 Python 実装を志向。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security / Operational notes
- OpenAI API キーは引数注入 or 環境変数 OPENAI_API_KEY を利用（空文字は未設定扱い）。未設定時は ValueError を発生させて明確に通知。
- .env の自動ロードはプロジェクトルート探索に基づくため、パッケージ配布後も動作するように設計。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- DB 書き込みは BEGIN / DELETE / INSERT / COMMIT のパターンで冪等性を確保、失敗時は ROLLBACK を試みる。ROLLBACK の失敗はログに警告出力。
- OpenAI 呼び出しに対してはリトライと指数バックオフを実装。API/ネットワークの一時的障害に対してフェイルセーフ（スコア=0やチャンクスキップ）で継続する設計。

### Testing / Extensibility notes
- OpenAI 呼び出し箇所（_call_openai_api）はユニットテストで patch しやすいように分離実装。
- score_news / score_regime は api_key を引数で注入可能で、テスト時に環境依存を避けられる。
- DuckDB に依存する実装だが、SQL のスコープや executemany の扱いを考慮して互換性を考慮。

---

変更履歴は今後のリリースで更新してください。リリース時には日付と必要に応じて「Changed」「Fixed」「Removed」セクションを追加してください。