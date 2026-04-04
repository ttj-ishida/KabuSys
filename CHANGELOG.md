# CHANGELOG

すべての重要な変更点を記録します。  
このファイルは Keep a Changelog 準拠の形式で記載しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ関連

[Unreleased]
- （なし）

[0.1.0] - 2026-04-04
----------------------------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報を src/kabusys/__init__.py に定義（__version__ = "0.1.0"）。
  - パッケージ公開モジュール: data, strategy, execution, monitoring を __all__ に設定（将来的な公開インターフェースを示唆）。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - 読み込み挙動:
    - OS 環境変数 > .env.local > .env の優先度。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント（空白直前の#のみ）に対応。
    - 既存 OS 環境変数は protected として上書きを防止。
  - Settings クラスを実装し、アプリケーション設定をプロパティ経由で型付きに取得可能:
    - J-Quants / kabu ステーション / LINE / データベース（DuckDB/SQLite） / 監視設定（PID/kill flag/閾値） / システム設定（env, log_level）など。
    - env と log_level の検証（許容値チェック）と利便性プロパティ（is_live / is_paper / is_dev）。
    - 必須変数チェック用の _require() を実装（未設定時は ValueError）。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント（ai_score）を算出。
    - 時間窓は JST 基準で定義（前日 15:00 JST ～ 当日 08:30 JST）し、calc_news_window を提供。
    - バッチ処理（最大20銘柄/チャンク）、1銘柄あたり記事・文字数上限（記事数10、文字数3000）でトリム。
    - OpenAI 呼び出しに対して 429/ネットワーク/タイムアウト/5xx を対象に指数バックオフでリトライ。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、コード整合性、スコア数値化）を実装。
    - ai_scores テーブルへの置換書き込み（対象コードのみ DELETE → INSERT）で部分失敗時の既存データ保護。
    - テスト容易性: _call_openai_api の差し替えが可能、api_key を引数で注入可能。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算（target_date 未満のデータのみ使用してルックアヘッドを防止）。
    - raw_news からマクロキーワードでフィルタしてタイトルを抽出し、OpenAI によりマクロセンチメントを評価（記事なし時は LLM 呼ばず 0.0）。
    - OpenAI 呼び出しはリトライ/エラーハンドリングを実装。API 失敗時は安全に macro_sentiment=0.0 にフォールバック。
    - 判定結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 設計上、ルックアヘッドバイアスを避けるため datetime.today()/date.today() を参照しない実装。

- データプラットフォーム（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理ロジック: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得の場合は曜日ベースでフォールバック（土日を非営業日扱い）。
    - カレンダー更新ジョブ calendar_update_job を実装（J-Quants API 経由で差分取得、バックフィル、健全性チェック、冪等保存）。
    - 最大探索範囲や安全チェック（検索上限 / 将来日付の健全性）を備え、DBの有無に応じ一貫した挙動を保証。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを実装し、取得件数・保存件数・品質問題・エラーの集約を提供。
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）を想定した設計。
    - jquants_client 連携を前提とした保存（idempotent 保存）・品質チェックの集約。
    - data/etl は pipeline.ETLResult を再エクスポート。

- リサーチ（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時の挙動明記（None）。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。NULL / データ不足時の扱い。
    - calc_value: raw_financials から直近財務データを取得して PER/ROE を計算（EPS が 0/欠損時は None）。PBR/配当利回りは未実装として明記。
    - DuckDB 上で SQL + Python により完結する設計（外部 API 不使用）。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の入力検証あり。
    - calc_ic: スピアマンランク相関（IC）を計算。十分なデータがない場合は None を返す。
    - rank: 同順位は平均ランクとするランク付け実装（丸めで ties 対応）。
    - factor_summary: 各ファクター列の基本統計（count/mean/std/min/max/median）を計算。
    - research パッケージは主要関数を __all__ でエクスポート。

- 実装/運用上の堅牢性とテスト性
  - すべての AI 呼び出しは明示的なリトライ・バックオフ・例外分岐を実装し、API 側の問題に対してフェイルセーフ（ゼロ代替値やスキップ）を採用。
  - ルックアヘッドバイアス回避を明言した実装方針（target_date 未満/以前のデータのみ参照）を各モジュールで徹底。
  - テスト用フック（_call_openai_api の差し替え、api_key を引数で注入）を用意し、単体テストを容易にする。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

注記
- 本リリースの多くの機能は DuckDB 内の特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など）を前提としています。実行環境では該当スキーマ/テーブルの準備が必要です。
- OpenAI API の利用（gpt-4o-mini）については API キーが必要です。各 API 呼び出しは api_key 引数で注入可能で、環境変数 OPENAI_API_KEY もサポートします。
- strategy / execution / monitoring パッケージは __all__ に含まれていますが、このリリースで該当する具体的実装がパッケージ内に存在しない場合があります（将来的な拡張を想定）。必要に応じて当該モジュール群の実装状況を確認してください。