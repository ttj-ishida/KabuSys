CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  
リリース日はコードベースから推測して付与しています。

フォーマットのルール:
- 変更はカテゴリ別（Added / Changed / Fixed / Removed / Security）に記載します。
- 初版リリースでは主要な機能追加を中心に記載しています。

Unreleased
----------
（未リリースの変更はここに記載します）

[0.1.0] - 2026-03-29
-------------------
Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報を公開（src/kabusys/__init__.py: __version__ = "0.1.0", __all__）。
- 環境設定管理機能を追加（src/kabusys/config.py）
  - .env / .env.local ファイルと OS 環境変数から設定を自動読み込み（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い（クォートあり/なしでの取り扱い差分）。
  - ファイル読み込み時の保護（protected set）により既存 OS 環境変数を上書きしないオプションをサポート。
  - Settings クラスで主要設定をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV の検証（development, paper_trading, live のみ許容）／LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev のユーティリティプロパティ
  - 必須環境変数未設定時は明示的に ValueError を送出する設計。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - 時間ウィンドウ: ターゲット日の前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して DB クエリを実行）。
    - バッチング（最大 20 銘柄/チャンク）、1 銘柄当たり最大記事数・最大文字数のトリム実装。
    - 再試行ロジック（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ、最大リトライ回数可変）。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results リスト検証、未知コードの無視、数値変換、スコアを ±1.0 にクリップ）。
    - 書き込みは部分失敗に強い設計（取得できた銘柄のみ DELETE → INSERT で置換。DuckDB executemany の空パラメータ回避処理を実装）。
    - テストのため _call_openai_api をモック可能に設計。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（Nikkei225連動ETF）の 200 日移動平均乖離（重み70%）とマクロセンチメント（LLM、重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出。
    - ma200_ratio の計算は target_date 未満のデータのみを使用し、データ不足時は中立（1.0）にフォールバック。
    - マクロニュースはニュース NLP のウィンドウ集約関数を利用して取得。記事がない場合は LLM 呼び出しをスキップ、macro_sentiment=0.0 にフォールバック。
    - OpenAI 呼び出しは独立実装（news_nlp の内部関数と共有しない）で再試行・エラーハンドリングを実装。
    - market_regime テーブルへ冪等（BEGIN/DELETE/INSERT/COMMIT）で書き込み。DB 書き込み失敗時は ROLLBACK を試行し例外を伝播。

- データプラットフォーム機能（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを基に営業日 / SQ 日判定、next/prev_trading_day、get_trading_days を提供。
    - DB データがない場合は曜日ベースのフォールバック（土日を非営業日扱い）。
    - カレンダーバッチ更新ジョブ calendar_update_job 実装（J-Quants API から差分取得→save_market_calendar 呼出→保存）。バックフィルと健全性チェック（将来過ぎる日付のスキップ）を実装。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）を設け無限ループを防止。
  - ETL / パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを定義（取得件数・保存件数・品質問題・エラーの集約と to_dict 出力）。
    - 差分取得・バックフィル・品質チェックの設計方針を実装（J-Quants クライアント経由の保存、品質チェックは致命的でも収集を続行）。
    - _get_max_date 等のユーティリティを実装してテーブル存在チェックや最大日付取得を安全に行う。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER、ROE）を DuckDB 上の SQL と Python 組合せで計算。
    - 欠損・データ不足時の戻り値は None とする設計。
    - 研究用関数は prices_daily / raw_financials のみ参照し、外部 API へはアクセスしない（安全性）。
  - 特徴量探索・統計（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）に対応、入力検証あり。
    - IC（Spearman の ρ）計算（calc_ic）、ランク化ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等外部依存を避け、標準ライブラリ＋DuckDB のみで動作。

- パッケージエクスポートの整理
  - ai パッケージは score_news を再エクスポート（src/kabusys/ai/__init__.py）。
  - research パッケージは主要関数群を __all__ にて公開（zscore_normalize は data.stats から参照）。

Design / Resilience / Notable implementation details
- ルックアヘッドバイアス対策: いずれの処理も内部で datetime.today()/date.today() を安易に参照せず、target_date 引数ベースで処理。
- OpenAI 呼び出し系は共通的な再試行ロジックとフェイルセーフ（失敗時は 0.0 や空結果で継続）を採用し、運用中の一部障害で全体停止しないよう設計。
- DB 書き込みは冪等（DELETE→INSERT または ON CONFLICT 相当）にして部分失敗時に他データを保護。
- DuckDB 0.10 の executemany の空リスト制約に対応したガードを実装。
- テスト容易性: OpenAI 呼び出し関数をモック差替えできる設計（unittest.mock.patch を想定）。
- 未実装 / TODO:
  - calc_value の PBR / 配当利回り等はこのリリースでは未実装（ドキュメントに明記）。
  - 一部のユーティリティは jquants_client 等外部クライアント実装に依存（テスト時はモックが必要）。

Changed
- 初版リリースのため該当無し。

Fixed
- 初版リリースのため該当無し。

Removed
- 初版リリースのため該当無し。

Security
- OpenAI API キーや外部資格情報は Settings で必須チェックを行う。ただし、キーの安全な保存や運用（Vault 等）は運用手順に依存。

補足（利用時の注意）
- OpenAI 連携機能を利用するには環境変数 OPENAI_API_KEY（または各関数の api_key 引数）を設定する必要があります。未設定時は ValueError が発生します。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行います。配布後やインストール先で動作させる場合、CWD に依存せず正しく動作することを意図していますが、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化してください。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）が期待されます。実行前にスキーマ準備を行ってください。

---

フィードバックや追加の変更履歴（例えばバグ修正や API 互換性の変更）を反映したい場合は、変更点の箇所を教えてください。