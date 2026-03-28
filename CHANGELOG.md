CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用しています。

[Unreleased]
------------

- （現在のリリース履歴は 0.1.0 のみ。今後の変更はこのセクションに記載します。）

[0.1.0] - 2026-03-28
--------------------

Added
- 基本パッケージ初期リリース
  - パッケージバージョンを 0.1.0 として公開（src/kabusys/__init__.py）。
  - 主要サブパッケージを公開: data, research, ai, execution, strategy, monitoring（__all__ によるエクスポート）。

- 環境設定・ロード機能（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサーの実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理（クォートあり/なしで挙動を区別）。
    - 誤った行や空行・コメント行を無視。
  - _load_env_file に保護キー（protected）を導入し、override フラグで既存 OS 環境変数を保護。
  - Settings クラスを提供し、主要設定値をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development/paper_trading/live の検証）および LOG_LEVEL の検証
    - is_live / is_paper / is_dev の判定ユーティリティ

- ニュース NLP（AI）機能（src/kabusys/ai/news_nlp.py）
  - score_news(conn, target_date, api_key=None) を実装:
    - 前日 15:00 JST ～ 当日 08:30 JST のウィンドウ計算（UTC 変換済み）を行う calc_news_window を提供。
    - raw_news と news_symbols を結合して、銘柄ごとに最新記事を集約（1 銘柄あたり最大 _MAX_ARTICLES_PER_STOCK 記事、文字数トリムあり）。
    - 最大 _BATCH_SIZE (=20) ごとにバッチ送信して OpenAI（gpt-4o-mini／JSON Mode）でセンチメントを取得。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - レスポンスの厳格なバリデーション（JSON 抽出・results キー/型検証・既知コードのみ採用・数値検査）。
    - スコアを ±1.0 にクリップし、ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT、DuckDB executemany の空リストガードあり）。
    - API キー注入をサポート（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError。
    - テストのため _call_openai_api を差し替え可能な設計（unittest.mock.patch を想定）。
    - フェイルセーフ: API 呼び出し失敗時は該当チャンクをスキップして処理継続。

- 市場レジーム判定（AI）機能（src/kabusys/ai/regime_detector.py）
  - score_regime(conn, target_date, api_key=None) を実装:
    - ETF 1321（Nikkei 225 連動型）の直近 200 日終値から MA200 乖離比（最新 / MA200）を算出（データ不足時は中立値 1.0 を使用）。
    - マクロ経済ニュースをマクロキーワードで抽出し、OpenAI（gpt-4o-mini）でマクロセンチメントを -1.0～1.0 で評価（記事が無ければ LLM 呼び出しをせず 0.0）。
    - スコア合成: 70%*(ma200_乖離スケール化) + 30%*macro_sentiment、-1..1 にクリップ。
    - 閾値により regime_label を bull/neutral/bear に分類（_BULL_THRESHOLD/_BEAR_THRESHOLD = 0.2）。
    - market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、例外時には ROLLBACK）。
    - API エラー時のフォールバック macro_sentiment=0.0 を明確化し、リトライロジックとログ出力あり。
    - API キー注入対応（api_key 引数または OPENAI_API_KEY）。未設定時は ValueError。

- 研究（Research）モジュール（src/kabusys/research）
  - factor_research.py を実装（calc_momentum, calc_volatility, calc_value）:
    - Momentum: 約1/3/6 ヶ月リターン、200 日 MA 乖離（データ不足時は None）。
    - Volatility: 20 日 ATR（true range の扱い: high/low/prev_close が NULL の場合は NULL 伝播）、相対 ATR、20 日平均売買代金、出来高比率。
    - Value: 最新の raw_financials から EPS/ROE を取得して PER/ROE を計算（EPS が 0/欠損の場合は None）。
    - DuckDB のウィンドウ関数を活用した SQL 実装。関数は prices_daily / raw_financials のみ参照し、本番 API にアクセスしない設計。
  - feature_exploration.py を実装（calc_forward_returns, calc_ic, rank, factor_summary）:
    - 将来リターン calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の LEAD ベースでのリターン計算、horizons のバリデーションあり。
    - IC（Spearman の ρ）calc_ic: factor と将来リターンを code で突合してランク相関を算出、サンプル数不足時は None。
    - ランク変換 rank: 同順位は平均ランク、丸めによる tie 対策あり。
    - factor_summary: count/mean/std/min/max/median を計算（None は除外）。
  - research パッケージの __init__ で主要関数を再エクスポート。

- データプラットフォーム（Data）モジュール（src/kabusys/data）
  - calendar_management.py を実装:
    - market_calendar を利用した営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録データ優先、未登録日は曜日ベース（平日のみ営業）でフォールバックする一貫したロジック。
    - next/prev_trading_day は最大探索日数制限（_MAX_SEARCH_DAYS）を設けて無限ループを防止。
    - calendar_update_job: J-Quants API（jquants_client を利用）から差分取得し market_calendar を冪等的に更新。バックフィルと健全性チェック（将来日異常のスキップ）あり。
  - pipeline.py に ETL パイプラインの骨格を実装:
    - ETLResult dataclass を導入（取得件数 / 保存件数 / 品質問題 / errors 等を集約）。
    - 結果の to_dict で quality_issues をシリアライズ可能に変換。
    - テーブル存在チェックや最大日付取得のユーティリティを実装。
  - etl.py で ETLResult を再エクスポート。
  - data パッケージの __init__ は関連モジュールを束ねる（jquants_client 等を想定）。

- その他
  - 単体テスト容易化のため、OpenAI 呼び出し部分はモジュール毎に private 関数（_call_openai_api）を用意し、テストで差し替え可能に設計。
  - 多数の関数で "ルックアヘッドバイアス防止" の設計方針を採用（datetime.today()/date.today() を直接参照しない、target_date を明示受け取り）。
  - DuckDB を主要なローカル分析 DB として採用し、実装は DuckDB の仕様（executemany の空リスト等）に配慮。

Changed
- 初回リリースにつき該当なし。

Fixed
- 初回リリースにつき該当なし。

Deprecated
- 初回リリースにつき該当なし。

Removed
- 初回リリースにつき該当なし。

Security
- 初回リリースにつき該当なし。

注記 / 既知の制約
- OpenAI API の利用には OPENAI_API_KEY（または関数引数での注入）が必須。未設定時は呼び出しは失敗する（ValueError）。
- AI 周りは外部 API に依存するため、ネットワーク障害やレート制限時はフェイルセーフやリトライで部分失敗を吸収する実装になっているが、完全な堅牢化は運用上の追加対策が必要。
- research モジュールは外部ネットワークにアクセスしない設計だが、正確な結果には十分な prices_daily / raw_financials データが前提。
- DuckDB のバージョン差異により SQL バインド挙動が変わる可能性があるため、executemany の空リスト扱い等に注意した実装を行っている。

[リンク]
- （リポジトリ比較リンク等を付ける場合はここに追加してください）