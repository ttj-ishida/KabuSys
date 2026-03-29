# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
本ファイルは「Keep a Changelog」準拠の形式で記載しています。

フォーマット: [Unreleased], 各バージョン見出しは [バージョン] - YYYY-MM-DD

---

## [Unreleased]
（なし）

---

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買・データプラットフォーム用ライブラリ「kabusys」の基礎機能を実装・公開。

### 追加 (Added)
- パッケージ基盤
  - パッケージの初期化（kabusys）とバージョン定義（__version__ = "0.1.0"）。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ に設定。

- 設定・環境管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動ロードする仕組みを実装。
    - プロジェクトルート検出は __file__ を起点に `.git` または `pyproject.toml` を探索して判定。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
    - ロード優先順位: OS 環境変数 > .env.local > .env。
  - .env パーサ実装（クォート、エスケープ、コメント処理を考慮）。
  - Settings クラスを提供し、以下プロパティ経由で安全に設定値へアクセス可能：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）, LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live / is_paper / is_dev のヘルパープロパティ
  - 必須環境変数未設定時に ValueError を投げる _require を提供。

- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news と news_symbols から銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードでセンチメントを取得して ai_scores テーブルへ書き込み。
    - スコアリングウィンドウは JST の前日 15:00 〜 当日 08:30 を UTC に変換して扱う（calc_news_window）。
    - バッチサイズ、トークン膨張対策（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）を実装。
    - API 呼び出しは 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。
    - レスポンスの厳密なバリデーションを実施し、不正なレスポンスはフェイルセーフでスキップ。
    - DuckDB への書き込みは冪等性を考慮（DELETE → INSERT）し、部分失敗時に既存スコアを保護。
    - テスト容易性のため OpenAI 呼び出し部分は差し替え可能（_call_openai_api を patch）。

  - regime_detector.score_regime
    - ETF 1321（日経225連動）の 200 日移動平均乖離と、マクロニュースの LLM センチメントを合成して市場レジーム（bull/neutral/bear）を日次で判定。
    - MA 側の重み 70%、マクロセンチメント 30% でスコアを合成し、閾値でラベル付け。
    - マクロキーワードによる raw_news フィルタ、OpenAI 呼び出し（gpt-4o-mini）、レスポンスパースとリトライ戦略を実装。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等操作、失敗時は ROLLBACK を試行して上位に例外を伝播。
    - API キー注入可能・環境変数 OPENAI_API_KEY を使用。

- データ（kabusys.data）
  - calendar_management
    - JPX カレンダー管理ロジックを実装（market_calendar を利用）。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day のユーティリティを提供。
    - DB データ優先、未登録日は曜日ベースのフォールバックを行い一貫性を保つ。
    - calendar_update_job により J-Quants から差分取得 → 冪等保存（jax クライアント経由）し、バックフィル・健全性チェックを実施。
  - pipeline / etl
    - ETLResult データクラスを実装（ETL 実行結果の集約と to_dict 変換を提供）。
    - ETL 実装のユーティリティ（_get_max_date など）を実装し、差分取得・保存・品質チェックのための基盤を用意。
  - data.etl は pipeline.ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER / ROE を計算（EPS が 0 または欠損時は None）。
    - すべて DuckDB の prices_daily / raw_financials のみを参照し、外部 API にはアクセスしない。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマンの順位相関に基づく IC を実装（欠損排除・最小レコード数チェック）。
    - rank: 同順位を平均ランクで処理するランク関数。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - 実装は標準ライブラリのみで依存を少なく設計。

### 安全性・信頼性上の配慮 (Highlights)
- ルックアヘッドバイアス防止
  - 各モジュール（ニューススコア・レジーム判定・ETL・リサーチ）は datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る設計。
- フェイルセーフ
  - 外部 API（OpenAI / J-Quants）失敗時は例外を投げずにフォールバック（0.0 など）またはスキップして処理を継続する箇所を多数用意。
- 冪等性
  - DuckDB への書き込みは冪等性を考慮（既存レコードは置換）し、トランザクション管理（BEGIN / COMMIT / ROLLBACK）を実施。
- テスト容易性
  - OpenAI 呼び出し等の内部ヘルパー関数を patch して差し替え可能にしており、ユニットテストでの制御が容易。

### 既知の制約 (Known limitations)
- DuckDB の executemany に空リストを渡せない制約を考慮したガードを実装（空リスト時は DB 操作をスキップ）。
- 一部の API エラーハンドリングは SDK の将来的な変更（例: status_code の有無）を想定して安全に記述しているが、将来 SDK 変更で追加調整が必要になる可能性あり。
- 一部未実装（将来拡張予定）
  - factor_research の PBR・配当利回り 等のバリュー指標は現バージョンでは未実装。

---

（注）本 CHANGELOG はソースコードの内容に基づき作成しています。実際のリリースノートに掲載する際は、公開パッケージの配布日やリリース手順・固定のバージョン管理情報を追記してください。