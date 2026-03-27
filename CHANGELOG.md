# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
リリースの日付はコミット時点の想定日を使用しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-27
初期リリース。

### 追加
- パッケージ構成
  - kabusys コアパッケージを追加（バージョン 0.1.0）。
  - 公開モジュール: data, research, ai, config, など。トップレベル __all__ を定義。

- 設定 / 環境変数管理（kabusys.config）
  - Settings クラスを導入し、アプリケーション設定値を環境変数から取得するプロパティを提供。
  - 自動 .env ロード機能を実装（優先度: OS 環境変数 > .env.local > .env）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能（テスト等で利用）。
  - .env のパースは export キーワード、シングル/ダブルクォート、エスケープ、行末コメントの扱い等に対応。
  - OS 環境変数を保護する仕組み（読み込み時の protected set）。
  - 必須設定取得時に未設定なら ValueError を投げる _require メソッドを提供。
  - 主なプロパティ:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスあり）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG..CRITICAL の検証）
  - is_live / is_paper / is_dev の簡易判定プロパティを提供。

- データ関連（kabusys.data）
  - calendar_management
    - JPX マーケットカレンダー操作ユーティリティを追加（market_calendar を利用）。
    - 営業日判定: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
    - カレンダー未取得時は曜日（平日）によるフォールバックを使用。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等的に更新するジョブを実装。
    - バックフィル期間・先読み日数・健全性チェック等の設定を備える。

  - pipeline / etl
    - ETLResult データクラスを追加（ETL 実行結果の集約・to_dict 表現を含む）。
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）を行う ETL 設計を反映。
    - data.etl で ETLResult を再エクスポート。

  - DuckDB を前提とした安全なテーブル存在チェック・最大日付取得ユーティリティ等を実装。

  - データ/テーブル期待項目（コード内で参照）
    - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等。

- 研究・因子計算（kabusys.research）
  - factor_research: ファクター計算機能を実装
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離など。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等。
    - calc_value: PER（price / EPS）と ROE（raw_financials からの取得）。
    - 実装は DuckDB の SQL と Python の組み合わせで行い、prices_daily / raw_financials のみ参照。
    - データ不足時は None を返す設計。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（horizons に応じた LEAD を使った取得）。
    - calc_ic: スピアマン（ランク）相関による IC 計算（rank 関数を含む）。
    - factor_summary: count/mean/std/min/max/median を算出（None 除外）。
    - rank: 同順位は平均ランク扱い（浮動小数丸め処理あり）。
  - 外部ライブラリに依存せず標準ライブラリ + DuckDB のみで実装。

- AI / NLP（kabusys.ai）
  - news_nlp.score_news
    - raw_news と news_symbols を集約し、銘柄ごとに記事を結合して OpenAI（gpt-4o-mini）にバッチ送信しセンチメントを算出。
    - JSON Mode による厳密な JSON 出力期待、レスポンスのバリデーションと取り込み。
    - バッチサイズ、トークン肥大対策（記事数／文字数制限）、429/ネットワーク/5xx に対する指数バックオフリトライ実装。
    - API 失敗時は当該チャンクをスキップ（フェイルセーフ）。取得成功分のみ ai_scores テーブルに冪等的に置換（DELETE → INSERT）。
    - calc_news_window により JST ベースのタイムウィンドウを UTC naive datetime で計算（ルックアヘッド防止）。
    - API キー未設定時は ValueError を送出。

  - regime_detector.score_regime
    - ETF 1321（日経225連動）について 200 日 MA 乖離とマクロニュースの LLM センチメントを重み合成（MA 70% : マクロ 30%）して市場レジーム（bull/neutral/bear）を判定。
    - _calc_ma200_ratio（lookback 排他条件でルックアヘッド防止）、_fetch_macro_news（マクロキーワードでフィルタ）、_score_macro（OpenAI 呼び出し・リトライ・フォールバック）を実装。
    - レジーム判定結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API 失敗時は macro_sentiment = 0.0 にフォールバック（例外を上げず継続）。
    - OpenAI 呼び出しのモジュール内分離（テスト容易化のため _call_openai_api を各モジュールで独自実装）。

- OpenAI 統合
  - 共通事項:
    - 使用モデル: gpt-4o-mini（コード内定義）。
    - JSON mode を使った応答取得と厳密なバリデーション。
    - 複数の例外（RateLimitError / APIConnectionError / APITimeoutError / APIError）に対するリトライロジックを実装。
    - API レスポンスのパース失敗や非期待フォーマットに対するロギングとフェイルセーフ処理（スコアは 0.0 または該当チャンクスキップ）。
    - テスト時に _call_openai_api を patch して差し替え可能な設計。

### 仕様上の注意 / 既知のポイント
- ルックアヘッドバイアス防止:
  - score_news / score_regime 等、日付基準の処理は datetime.today() / date.today() を内部で参照しない設計。
  - DB クエリは target_date 未満／以前／以降等の条件でルックアヘッドを避ける。
- DB スキーマ依存:
  - 各モジュールは DuckDB 上の特定テーブルを参照する（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など）。利用前にスキーマ準備が必要。
- 環境変数:
  - OpenAI を使用する機能は OPENAI_API_KEY が必要（関数引数で注入可能）。
  - J-Quants / kabu API / Slack などの認証情報は環境変数から取得（未設定時は ValueError を送出する箇所あり）。
- 自動 .env 読み込み:
  - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して決定するため、CWD に依存しない。
  - プロジェクトルートが見つからない場合は自動ロードをスキップする。
- エラーハンドリング:
  - API 失敗時は原則フェイルセーフ（スコア 0.0 またはチャンク単位スキップ）で処理を継続する設計。
  - DB 書き込みは冪等性を考慮しトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。
- テスト容易性:
  - OpenAI 呼び出しや時間依存処理を差し替え可能な設計（_call_openai_api の patch 等）。

### 互換性 / 破壊的変更
- 初期リリースのため過去バージョンとの互換性に関する記載はなし。

### セキュリティ
- .env の読み込みで OS 環境変数を上書きしない既定動作（override=False）と、上書き時の protected set により OS 環境変数を保護する仕組みを実装。
- 秘匿情報（API キー等）は環境変数管理を想定。コード内に平文 API キーは含まれない。

---

必要であれば、各機能（例: score_news, score_regime, calc_momentum 等）の利用方法や期待する DB スキーマ定義・サンプル SQL、.env.example の推奨内容などの追補ドキュメントも作成できます。どの情報が必要か教えてください。