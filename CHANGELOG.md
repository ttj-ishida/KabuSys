# Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
初期リリース相当のコードベースをもとに、機能・設計方針・運用上の注意点を推測して記載しています。

フォーマット:
- 「Added」: 新機能
- 「Changed」: 既存機能の変更（今回の初期リリースでは該当なし）
- 「Fixed」: 修正（今回の初期リリースでは該当なし）
- 「Security」: セキュリティ・運用上の重要注意点
- 「Notes」: 運用・実装上の補足や既知の点

## [Unreleased]
- （将来の変更をここに記載）

## [0.1.0] - 2026-03-27
初回公開リリース相当。日本株自動売買・データ基盤・リサーチ・AI支援解析の基礎機能を実装。

### Added
- パッケージ基盤
  - kabusys パッケージの初期モジュール（data, research, ai, config 等）を追加。
  - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 読み込み順: OS環境変数 > .env.local (override) > .env (非上書き)。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env のパースは export 形式対応、クォート中のエスケープやインラインコメントの扱い、無効行スキップ等に対応。
  - Settings クラスを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須設定を _require で検証。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV (development/paper_trading/live), LOG_LEVEL を取得/検証するプロパティを実装。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols テーブルを入力に、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出し、ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 変換で DB クエリ）を採用。
    - バッチ処理: 1 API 呼び出しあたり最大 20 銘柄（_BATCH_SIZE）で送信。
    - 1銘柄あたり最大10記事、最大 3000 文字にトリムしてプロンプトに含める。
    - JSON Mode を利用しレスポンスを厳密に検証（results 配列、code/score の型チェック、未知コードは無視、スコアは ±1.0 にクリップ）。
    - リトライ: 429 / ネットワーク / タイムアウト / 5xx に対して指数バックオフでリトライ（最大回数定義）。
    - DB 書き込みは部分置換（指定コードだけ DELETE→INSERT）で冪等性・部分失敗時の保護を実現。
    - テスト容易性のため、OpenAI 呼び出し関数をモジュール内で差し替え可能（patch 用の分離実装）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して、市場レジーム（bull/neutral/bear）を日次で判定し market_regime テーブルへ冪等書き込み。
    - マクロニュースは news_nlp の calc_news_window と raw_news を使用して抽出。マクロキーワードでフィルタ（日本・米国系の主要語句リスト）。
    - LLM 呼び出しは gpt-4o-mini、JSON レスポンスをパースして macro_sentiment を取得。API 失敗時はフェールセーフで macro_sentiment = 0.0 にフォールバック。
    - レジームスコア合成式、閾値、DB トランザクション（BEGIN / DELETE / INSERT / COMMIT）を実装。

- Data / ETL（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーを管理する market_calendar テーブルの参照/更新ロジック。
    - 営業日判定ユーティリティ: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - DB にカレンダーがない場合は曜日（平日）ベースのフォールバックを採用。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新。バックフィル・健全性チェックを実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult dataclass を導入（取得数・保存数・品質チェック結果・エラー情報を格納）。
    - 差分更新・バックフィル・品質チェック（quality モジュール）連携のためのユーティリティ実装。
    - DuckDB を用いた日付系ユーティリティ（最大日付取得等）。
    - jquants_client 経由でのフェッチ/保存処理と連携できる設計。
  - ETL の公開インターフェース再エクスポート（src/kabusys/data/etl.py）

- Research（src/kabusys/research）
  - factor_research.py
    - モメンタム: mom_1m, mom_3m, mom_6m, ma200_dev（200日MA乖離）を計算する calc_momentum。
    - ボラティリティ・流動性: atr_20, atr_pct, avg_turnover, volume_ratio を計算する calc_volatility。
    - バリュー: per, roe を raw_financials と prices_daily を組み合わせて計算する calc_value。
    - 各関数は DuckDB 接続を受け取り SQL（ウィンドウ関数等）で実装。データ不足時は None を返す挙動。
  - feature_exploration.py
    - 将来リターン計算 calc_forward_returns（任意ホライズンの LEAD を使った実装、horizons の妥当性検証）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンのランク相関、同順位は平均ランク処理）。
    - ランク化ユーティリティ rank（丸めによる ties 対策）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median を標準ライブラリのみで計算）。
  - research パッケージの公開 API を __init__.py にて整理・再エクスポート。

### Security / Operational notes
- 認証情報
  - OpenAI API キーは score_news / score_regime の引数で注入可能。引数が未設定の場合は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出して明示的に失敗。
  - J-Quants, kabu API, Slack など外部サービスのトークン/パスワードは Settings 経由で必須チェックを行う（未設定で ValueError）。
- .env 自動ロード
  - OS 環境変数は保護され、.env/.env.local の上書きから保護される（読み込み時に既存 env キーを protected として扱う）。
  - セキュリティ運用上、ローカルでの .env 管理や自動ロードの無効化方法（KABUSYS_DISABLE_AUTO_ENV_LOAD）を周知すること。
- DB トランザクション
  - ai_scores / market_regime 等の書き込みは BEGIN / DELETE / INSERT / COMMIT を用いた冪等書き込みを行い、例外時は ROLLBACK を試みる。ROLLBACK に失敗した場合は警告ログを出力する。
- フェイルセーフ
  - LLM 呼び出しの失敗（ネットワーク・レート制限・サーバーエラー等）に対しては明示的にリトライ・バックオフを行い、最終的に失敗した場合は影響範囲を限定して（例: macro_sentiment=0.0、スコア取得スキップ）処理を継続する設計。

### Notes / Implementation details
- 時間・日付の扱い
  - 解析・ETL・スコア生成関数は datetime.today()/date.today() の直接参照を避け、必ず target_date 引数で日時を注入する設計（ルックアヘッドバイアス防止）。
  - raw_news.datetime は UTC で保存されている前提でウィンドウを計算する（ニュースの JST↔UTC の変換を calc_news_window で実施）。
- DuckDB
  - 内部データストアとして DuckDB を利用。SQL はウィンドウ関数等を多用しパフォーマンスを意識した実装。
  - DuckDB の executemany による空リストバインド制約に対する防御（空時は実行しない）を実装。
- OpenAI 呼び出しの分離
  - テストの容易さのため、_call_openai_api を各モジュール内で定義し、unittest.mock.patch により差し替えやすくしている（モジュール間で private 関数を共有しない設計）。
- テーブル想定
  - 主に参照/更新する想定のテーブル: prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials。

### Known limitations / 今後の注意点
- OpenAI のレスポンスが仕様外の形式だった場合はスコア取得がスキップされる（現フェーズでは例外を投げずログに記録して継続）。
- PBR・配当利回りなど一部バリューファクターは未実装（calc_value では per/roe のみ）。
- ETL 全体のオーケストレーション（スケジューリング・監査ログ・再実行など）は外部の仕組みで補う想定。
- Kabusys の実行環境では機密情報（.env, トークン）取り扱いに注意すること。

---

（注）この CHANGELOG.md は提供されたソースコードの設計・コメント・実装から合理的に推測して作成しています。実際のリリースノートとして使う場合は、リリース時のコミット履歴や task 管理システムの記録と合わせて調整してください。