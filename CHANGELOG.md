CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

[0.1.0] - 2026-03-29
--------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報: src/kabusys/__init__.py にてバージョン "0.1.0" を設定。
- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env ファイル自動ロード機能をプロジェクトルート（.git または pyproject.toml）から実装。
  - .env / .env.local の読み込み順序（OS 環境変数 > .env.local > .env）を実装。
  - export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理などに対応した堅牢な .env パーサ実装。
  - OS 環境変数を保護するための protected 上書き制御（.env.local は override=True）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - Settings クラスを提供（J-Quants / kabuAPI / Slack / DB パス / 環境モード / ログレベル等のプロパティを公開）。
  - env / log_level の入力検証（許容値チェック）を実装。
  - 必須環境変数未設定時に分かりやすい例外を送出する _require ユーティリティ。
- AI モジュール
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信してセンチメントを算出。
    - バッチサイズ、記事数上限、文字数上限、タイムウィンドウ（前日15:00 JST～当日08:30 JST）を実装。
    - API 呼び出しのリトライ（429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフでリトライ）と失敗時のフェイルセーフ（スキップ）を実装。
    - レスポンスバリデーション（JSON 抽出、results リスト、code の照合、数値チェック）を実装。スコアは ±1.0 にクリップ。
    - スコア取得後、ai_scores テーブルへ冪等的に（DELETE → INSERT）書き込むロジック実装。DuckDB の executemany 空リスト制約に配慮。
    - score_news(conn, target_date, api_key=None) を公開（戻り値: 書き込んだ銘柄数）。
    - テスト容易性: OpenAI 呼び出し箇所はモック差し替え可能（_call_openai_api の patch を想定）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成し、日次の market_regime を判定・保存。
    - マクロニュースは news_nlp.calc_news_window で定義したウィンドウから抽出し、OpenAI により macro_sentiment を算出（JSON mode、gpt-4o-mini）。
    - API 失敗時は macro_sentiment=0.0 でフォールバック（例外とせず継続）。
    - レジーム合成ロジック（スコアクリップ、閾値で "bull"/"neutral"/"bear" ラベル付け）。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - lookahead バイアスを防ぐ設計（date 比較は target_date 未満 / 排他等を明確化）。
- データプラットフォーム関連 (src/kabusys/data/...)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日判定ユーティリティを実装。
    - market_calendar テーブルを優先し、未登録日は曜日ベースのフォールバックで一貫した振る舞いを提供。
    - next/prev_trading_day といった探索で無限ループを防ぐ最大探索日数制限実装。
    - calendar_update_job により J-Quants API から差分取得し market_calendar を冪等に更新（バックフィル、健全性チェック）。
  - ETL パイプライン基盤 (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを導入（取得数・保存数・品質問題・エラー一覧等を含む）。
    - 差分更新、バックフィル、品質チェックのためのユーティリティ（テーブル存在チェック、最大日付取得など）を実装。
    - jquants_client と quality モジュールとの連携を想定した設計。
    - etl パイプライン結果型 ETLResult を公開（src/kabusys/data/etl.py で再エクスポート）。
- 研究（Research）モジュール (src/kabusys/research/...)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、ATR 相対値、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得し PER/ROE を計算（EPS が 0/欠損時は None）。
    - DuckDB 上の SQL ウィンドウ関数を多用した高効率な実装。データ不足時の None ハンドリング。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）で将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコードが 3 件未満の場合は None）。
    - rank, factor_summary: ランク計算（同順位は平均ランク）、基本統計量（count/mean/std/min/max/median）を提供。
    - 研究用ユーティリティは外部 API に依存せず DuckDB のデータのみを参照する方針。
  - 研究ユーティリティの再エクスポート（zscore_normalize など）。
- パッケージエクスポート整理
  - ai/ と research/ の __init__.py で主要関数を明示的にエクスポート。

Security / Robustness
- .env 読み込みで OS 環境変数を保護し意図しない上書きを抑止。
- OpenAI 呼び出しにおける 5xx/429/ネットワークエラーのリトライとフェイルセーフ設計。
- DB 書き込みは冪等化（DELETE → INSERT、トランザクション制御）し、ROLLBACK 失敗時の警告ログを出力。
- lookahead バイアス回避のため、date.today() を直接参照しない設計（target_date に依存する API）。

Known issues / 注意点
- DuckDB バージョン依存: executemany に空リストを渡せない等の制約を考慮した実装が入っている（互換性に注意）。
- OpenAI API との統合は gpt-4o-mini + JSON Mode を想定。実行には OPENAI_API_KEY の設定が必要。
- raw_news / prices_daily / market_regime 等の DB スキーマ（カラム名・型）に依存する実装のため、事前にスキーマを整備する必要あり。
- news_nlp と regime_detector はそれぞれ独立した _call_openai_api 実装を持ち、意図的に共有していない（テストの独立性確保）。
- 一部関数は外部モジュール（jquants_client, quality 等）を参照するため、これらの実装が別途必要。

Deprecated
- なし

Removed
- なし

Security
- なし（本リリースにおける既知の重大セキュリティ修正はなし）

記載方針・補足
- 本 CHANGELOG は現行のソースコードから実装状況と設計方針を推測して作成しています。実際のリリースノートとして利用する場合は、各機能の動作確認・API キーや DB スキーマの整合性確認を推奨します。