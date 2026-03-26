# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/）に準拠しています。

現在のバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に合わせています。

## [0.1.0] - 2026-03-26

Added
- 初回リリース。日本株自動売買システム「KabuSys」のコア機能群を追加。
- パッケージ構成
  - kabusys: パッケージルート。data, research, ai などを公開。
- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサの実装：コメント、export プレフィックス、シングル/ダブルクォート、エスケープシーケンスを適切に処理。
  - 環境変数保護（OS 環境変数を protected として .env.local が上書きしない仕組み）。
  - Settings クラスで各種必須設定をプロパティとして提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - env 値検証（KABUSYS_ENV, LOG_LEVEL の許容値検査）。
  - データベースパスのデフォルト（DuckDB / SQLite）の提供。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar を基にした営業日判定ユーティリティ（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）。
    - DB 登録がない場合は曜日ベースでフォールバック（週末は非営業日）。
    - カレンダー夜間バッチ更新（calendar_update_job）: J-Quants から差分取得して冪等保存、バックフィルと健全性チェックを実装。
    - 最大探索日数やバックフィル日数等の安全措置を導入。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL 実行結果の集約）。
    - 差分更新、バックフィル、品質チェック（quality モジュールとの連携）を想定した設計。

- AI モジュール（kabusys.ai）
  - news_nlp.score_news:
    - raw_news と news_symbols を集約して銘柄別にニュースを結合・トリムし、OpenAI（gpt-4o-mini）にバッチ送信してセンチメント（ai_score）を算出。
    - チャンク（最大 20 銘柄）単位で API 呼び出し。429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
    - JSON Mode のレスポンスを検証・抽出し、スコアを ±1.0 にクリップ。
    - スコア取得済み銘柄のみ ai_scores テーブルを置換（DELETE → INSERT）して部分失敗時に既存データを保護。
    - テスト容易性のため _call_openai_api を差し替え可能。
    - タイムウィンドウ計算（calc_news_window）を提供（JST ベース → DB との比較は UTC naive datetime）。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - マクロニュースは news_nlp の窓計算に基づき raw_news から抽出。OpenAI による JSON レスポンス（{"macro_sentiment": ...}）を想定。
    - API 障害時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - レジーム結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）し、例外時は ROLLBACK。
    - ルックアヘッドバイアス対策: datetime.today()/date.today() を参照せず、target_date 引数に厳密に依存。

- リサーチモジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。TR の NULL 伝播を考慮。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を算出（EPS 欠損や 0 の場合は None）。
    - すべて DuckDB 上の SQL／ウィンドウ関数で実装（外部 API 不使用）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 件未満なら None。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出。
    - rank: 同順位は平均ランクを返す。

- DuckDB / SQL 周りの堅牢化
  - 空パラメータに対する DuckDB 0.10 の制約を考慮（executemany 前に空チェック）。
  - テーブル存在チェックユーティリティを複数実装。
  - 日付フィールドは date オブジェクトで統一して扱うよう変換ユーティリティを用意。

Changed
- （初版リリースのため該当なし）

Fixed
- （初版リリースのため該当なし）

Security
- OpenAI API キーや各種トークンは環境変数経由で必須化。AI 関連関数はキー未設定時に ValueError を送出して誤動作を防止。

Notes / Known limitations
- 本リリースは「データ処理」「リサーチ」「NLP／LLM スコアリング」までを含むが、実際の発注・実行ロジック（execution）やモニタリング（monitoring）の詳細実装は別モジュールとして分離済み（パッケージ公開名には含まれるが、本 CHANGELOG のソースには詳細実装が存在しない可能性あり）。
- jquants_client や quality モジュール、外部 API（J-Quants、kabuステーション、OpenAI）の動作に依存する。実行には各種 API キーやテーブル（raw_news / prices_daily / ai_scores / market_regime / raw_financials など）の事前準備が必要。
- DuckDB のバージョン差分（特にリスト型バインドの挙動）に注意。コード内に互換性対策あり。
- LLM の出力は JSON Mode を期待しているが、実際の応答フォーマットの揺らぎに対してはパース復元ロジックを備える（最外の {} 抽出など）。それでも想定外の出力が来るケースはあるため運用監視を推奨。

----

この CHANGELOG はコードベースから実装意図・仕様を推測して作成しています。実際のコミット履歴や設計文書と差分がある場合はそちらを優先してください。