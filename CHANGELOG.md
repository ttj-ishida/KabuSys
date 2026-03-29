# Changelog

すべての重要な変更をここに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

## [Unreleased]

## [0.1.0] - 2026-03-29
初回公開リリース。

### Added
- パッケージ基礎
  - パッケージ名: kabusys、バージョン 0.1.0 を設定。
  - 公開モジュール群: data, research, ai, execution, strategy, monitoring（__all__ を含む初期エクスポート）。
- 設定 / 環境変数管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env の行パーサーを実装（コメント、export 形式、クォートとエスケープ処理に対応）。
  - OS 環境変数を保護する protected 機能、.env.local による上書きサポート。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプション。
  - Settings クラスを提供し、アプリケーションで利用する主要設定をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live の検証）と LOG_LEVEL の検証
    - is_live / is_paper / is_dev の便利プロパティ
  - 未設定必須環境変数取得時は ValueError を送出する安全設計。
- AI（自然言語処理）機能 (kabusys.ai)
  - news_nlp.score_news:
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI (gpt-4o-mini) に送信してセンチメントスコアを生成。
    - チャンク処理（最大 20 銘柄 / コール）、1銘柄あたりの記事上限・文字数上限 (_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK) によるトークン肥大化対策。
    - JSON Mode を利用したレスポンスパースおよび復元ロジック（前後余計なテキストを除去して JSON を抽出）。
    - 429 / 接続断 / タイムアウト / 5xx に対する指数バックオフリトライ。その他エラーはフェイルセーフにしてスキップ継続。
    - スコアは ±1.0 にクリップ。取得後は ai_scores テーブルへ冪等的に（DELETE → INSERT）書き込み。
    - 外部日付参照（datetime.today / date.today）を行わない設計（ルックアヘッド防止）。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と news_nlp ベースのマクロセンチメント（重み 30%）を合成して market_regime を日次判定（bull/neutral/bear）。
    - マクロニュースはマクロキーワードでフィルタし、最大記事数制限で LLM を呼ぶ。
    - API 呼び出しのリトライ／バックオフ、API 失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - レジーム計算の出力は market_regime テーブルへトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等的に書き込み。失敗時は ROLLBACK を試みる。
    - 外部日付の参照をせず、target_date 未満のデータのみを使用することでルックアヘッドバイアスを防止。
- Data モジュール (kabusys.data)
  - calendar_management:
    - market_calendar を用いた営業日判定と操作 API を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にカレンダー情報がない場合は曜日ベース（土日非営業）でフォールバックする一貫した挙動。
    - 最大探索日数の上限設定で無限ループ防止。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存。バックフィル・健全性チェックを実装。
  - pipeline / ETL:
    - ETLResult データクラスを実装。ETL 実行結果（取得数、保存数、品質問題、エラー等）を表現。
    - ETL の内部ユーティリティ: テーブル存在チェック、最大日付取得、market_calendar ヘルパー等。
    - デフォルトの差分／バックフィル挙動、品質チェックの収集方針（Fail-Fast ではなく検出情報を蓄積して報告）。
  - jquants_client（参照）：ETL / カレンダー更新で外部 API クライアントを利用する想定（fetch / save 関数を呼び出す）。
- Research モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を prices_daily から計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率などのボラティリティ／流動性指標を計算。
    - calc_value: raw_financials と prices_daily を結合し PER / ROE を計算（EPS が 0 または欠損時は None）。
    - 全関数は DuckDB 接続を受け取りローカル DB のみ参照する設計（発注 API 等にはアクセスしない）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンを計算。ホライズンは検証済み（整数かつ 1..252）。
    - calc_ic: factor と将来リターンのスピアマンランク相関 (IC) を計算（有効レコードが 3 未満なら None）。
    - rank: 平均ランクを返す実装（同順位は平均ランク、丸めで ties の誤検出防止）。
    - factor_summary: 指定カラムの count/mean/std/min/max/median を算出。
  - research/__init__.py で主要関数を再エクスポート（zscore_normalize を含む）。
- エラー処理・設計方針（全体）
  - ルックアヘッドバイアス防止のため、各スコアリング／判定機能は target_date を受け取り内部で現在時刻を参照しない。
  - OpenAI 呼び出しは堅牢なリトライ／バックオフとレスポンス検証を実装。API 失敗は局所的にフェイルセーフ（スコア 0 やスキップ）としてシステム全体の継続を優先。
  - DuckDB への書き込みは可能な限り冪等に実装（DELETE → INSERT、トランザクション、ROLLBACK の試行）。
  - JSON パースや数値変換時に慎重な検証を行い、LLM の出力変動を吸収する作り。
  - テスト容易性を考慮して OpenAI 呼び出しは内部関数をモック差し替え可能に設計。

### Notes / Migration
- .env の自動読み込みはパッケージ読み込み時に行われます。テストや特殊環境で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API キーは各関数呼び出しに api_key 引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を使用します（未設定時は ValueError）。
- DuckDB の各機能は特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar）に依存します。ETL 実行前にスキーマ準備を行ってください。
- ai/news_nlp と ai/regime_detector はそれぞれ独立した OpenAI 呼び出し実装（内部 private 関数を共有しない）であり、テスト時は個別にモック差し替えが可能です。

---

（将来のバージョンでは Breaking changes / Fixed / Security セクションを追加します）