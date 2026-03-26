CHANGELOG
=========

すべての重要な変更は「Keep a Changelog」形式で記載しています。  
このファイルはコードベースの内容から推測して作成した初回リリース向けの変更履歴です。

Unreleased
----------

（なし）

0.1.0 - 2026-03-26
------------------

配布初版（初期機能実装）。以下の主要機能・設計方針を含みます。

Added
- パッケージ初期化
  - kabusys パッケージのバージョンを 0.1.0 として公開。
  - __all__ に主要サブパッケージ（data, strategy, execution, monitoring）を登録。

- 環境変数 / 設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env ロード機能（プロジェクトルートの探索: .git または pyproject.toml を起点）。
    - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ（_parse_env_line）
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント解析（クォート外での '#' 扱い）。
  - .env ロードは OS 環境変数を保護（既存キーを protected として扱う）。
  - 必須環境変数チェック用の _require と各種設定プロパティを提供。
    - 必須キー例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - デフォルト値:
    - KABU_API_BASE_URL: http://localhost:18080/kabusapi
    - DUCKDB_PATH: data/kabusys.duckdb
    - SQLITE_PATH: data/monitoring.db
    - KABUSYS_ENV の有効値: development / paper_trading / live
    - LOG_LEVEL の有効値: DEBUG / INFO / WARNING / ERROR / CRITICAL

- AI 関連（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信して銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込み。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と照合）。
    - バッチ処理、銘柄あたり最大記事数・文字数制限（トークン肥大化対策）。
    - API 呼び出し: 429 / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフリトライ。
    - レスポンス検証（results 配列の存在確認、コードの一致、数値変換、±1.0 でクリップ）。
    - 部分成功時の保護: 書き込みは取得したコードに限定（DELETE→INSERT の個別実行）して既存データを不必要に消さない。
    - 主要公開関数: score_news(conn, target_date, api_key=None)
      - api_key 未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出。
    - DuckDB のバージョン差異（executemany の空リスト不可など）に配慮した実装。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動）200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出。
    - マクロニュース判定は別途 news_nlp の窓（calc_news_window）で取得したタイトル集合を OpenAI（gpt-4o-mini）へ送信して JSON で macro_sentiment を取得。
    - API 呼び出しはリトライ/バックオフを実装し、API 失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実行。
    - 主要公開関数: score_regime(conn, target_date, api_key=None)
      - api_key 未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出。

- Research（因子計算・特徴量解析）（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum: 約1M/3M/6M リターン、200日移動平均乖離（ma200_dev）
    - Volatility / Liquidity: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比（volume_ratio）
    - Value: PER（price / EPS、EPS が 0 または欠損なら None）、ROE（raw_financials から取得）
    - 全関数は DuckDB 接続を受け取り prices_daily / raw_financials のみを参照（本番 API へのアクセスなし）。
    - 結果は (date, code) をキーとする dict のリストで返却。
    - 公開関数: calc_momentum, calc_volatility, calc_value
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）：複数ホライズン（デフォルト [1,5,21]）に対応、ホライズンの検証。
    - IC（Information Coefficient）計算（calc_ic）：スピアマンの順位相関（ランク）を計算、データ不十分（<3）なら None。
    - ランク変換ユーティリティ（rank）: 同順位は平均ランクを付与し丸めによる ties を考慮。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。
  - research パッケージで必要なユーティリティを再エクスポート（zscore_normalize 等）。

- Data / ETL / カレンダー管理（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーを扱うユーティリティ群:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB（market_calendar）にデータがない場合は曜日ベース（土日休み）でフォールバック。
    - カレンダー更新ジョブ（calendar_update_job）: J-Quants から差分取得→保存（バックフィル、健全性チェック含む）。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult dataclass を定義し、ETL 実行の収集メタデータ（取得数・保存数・品質問題・エラー等）を格納。
    - 差分取得、backfill、品質チェック（quality モジュール）との連携を想定。
    - DuckDB 接続を使用して DB 最大日付取得などのユーティリティを実装。
    - data.etl から ETLResult を再エクスポート。
  - jquants_client を通じた外部データ取得を想定（fetch/save 関数と連携）。

Design / Behavior notes（設計上の特徴）
- ルックアヘッドバイアス回避
  - 多くのモジュール（news_nlp, regime_detector, research）は datetime.today()/date.today() を内部で参照せず、明示的な target_date を引数に取る設計。
  - DB クエリでは date < target_date や 半開区間等で先行データ参照を防止。
- フェイルセーフ
  - OpenAI API 呼び出しや外部 API の失敗時は過度に例外を投げず、中立スコアやスキップで継続しシステムの頑健性を優先。
- 冪等性
  - DB 保存処理は冪等設計（DELETE→INSERT、ON CONFLICT DO UPDATE 想定）で部分失敗時のデータ保護を行う。
- DuckDB 互換性への配慮
  - executemany に空リストを渡せない点など、DuckDB バージョン差を考慮した実装がある。
- OpenAI 呼び出し
  - gpt-4o-mini を利用、JSON Mode（response_format={"type":"json_object"}）を前提にレスポンス処理を行う。
  - API キーは関数引数で注入可能（テスト容易性）。未指定時は OPENAI_API_KEY を参照。
- ロギング
  - 各処理で情報/警告/例外ログを出力するよう実装。

Security / Privacy
- API キーや機密設定は環境変数で管理することを想定。
- .env 自動ロードは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Breaking Changes
- 初回リリースのため破壊的変更はなし。

Migration notes
- 初期リリース。インストール後は必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY など）を設定してください。
- デフォルト DB パス（DUCKDB_PATH, SQLITE_PATH）は data/ 配下を想定しているため、適切なディレクトリ作成と権限設定を行ってください。

Acknowledgements / References
- DuckDB を主たるローカル分析 DB として利用する設計。
- J-Quants / kabu ステーション等の外部クライアント関数（jquants_client 等）を想定した統合設計。