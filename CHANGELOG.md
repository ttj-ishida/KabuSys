# CHANGELOG

すべての重要な変更履歴をここに記載します。フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-04-02

初回リリース。

### 追加
- パッケージ基盤
  - パッケージ初期化: kabusys.__init__ にてバージョン "0.1.0" を定義し、主要サブパッケージ（data, strategy, execution, monitoring）を公開。
- 設定管理（kabusys.config）
  - .env ファイルと OS 環境変数から設定を自動ロードする仕組みを実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - .env/.env.local の読み込み順序と .env.local による上書き動作をサポート。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パースの強化: export 形式の対応、クォート内バックスラッシュエスケープ処理、インラインコメント対応など。
  - Settings クラスを導入し、型付きプロパティ経由で必要環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）やパス/閾値（DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU/MEM/ディスク閾値等）を取得可能に。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の妥当性チェックを実装（有効値の検証）。is_live / is_paper / is_dev ヘルパーを提供。
- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（ai_score）を算出して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ（calc_news_window）。
    - バッチ処理（1APIコール最大20銘柄）、1銘柄当たりの最大記事数・文字数制限、JSON Mode 出力のバリデーション、JSON パース耐性（前後ノイズから {} を抽出する復元処理）を実装。
    - リトライ/バックオフ（429/ネットワーク断/タイムアウト/5xx）を実装。API 失敗時は対象銘柄をスキップし、フェイルセーフで処理を継続。
    - テスト容易性のため _call_openai_api をモック差替え可能に。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等的に書き込む機能を実装。
    - マクロキーワードで raw_news をフィルタしてタイトルを取得、OpenAI（gpt-4o-mini）によりマクロセンチメントを評価（記事がない場合は LLM 呼び出しを省略）。
    - API リトライ、レスポンス JSON パース失敗や API エラー時のフェイルセーフ（macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス防止設計（date < target_date の排他条件、datetime.today() 不使用）。
    - テスト用に _call_openai_api を差し替え可能。
- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得し market_calendar テーブルへ冪等保存。
    - 営業日判定ユーティリティ群を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar 未取得時の曜日ベースフォールバック（週末=非営業日）を実装し、DB 登録値がある場合はそれを優先する一貫した動作を確保。
    - 最大探索日数やバックフィル・健全性チェック等の保護ロジックを実装。
  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - ETL の結果を保持する ETLResult データクラスを追加（取得件数・保存件数・品質問題・エラーの集約と変換ユーティリティを含む）。
    - 差分更新、バックフィル、品質チェックを行うパイプライン設計に対応するユーティリティを実装方針として整備（jquants_client 連携、品質検査の重大度扱いの定義など）。
    - _table_exists / _get_max_date 等の内部ユーティリティを実装（DuckDB 前提）。
- 研究モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）などの定量ファクターを DuckDB の SQL と Python 組合せで提供。
    - データ不足時の None 扱い、営業日スキャン範囲のバッファ、デバッグログ出力などを実装。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns: 任意ホライズン、入力バリデーション、1クエリ実装）。
    - IC（Information Coefficient）計算（calc_ic: スピアマンランク相関、サンプル数チェック）。
    - ランク変換ユーティリティ（rank）およびファクター統計サマリー（factor_summary）。
    - pandas 等外部ライブラリに依存せず標準ライブラリ + duckdb で実装。
- テスト/運用支援
  - 多くの関数でルックアヘッドバイアスを避ける実装方針（datetime.today()/date.today() の不使用、target_date 引数運用）。
  - OpenAI 呼び出し周りは再利用性を下げるためモジュール間でプライベート実装を分離（news_nlp と regime_detector で独立した _call_openai_api を持つ）、かつモック差替えでテストしやすく設計。
  - DuckDB の executemany の挙動に関する互換性考慮（空リスト送信禁止）を反映した実装。

### 既知の注意点 / 実装上の制約
- 外部依存
  - DuckDB（duckdb パッケージ）と OpenAI Python SDK（OpenAI）が必須。OpenAI には OPENAI_API_KEY（または api_key 引数）を設定する必要あり。未設定時は ValueError を送出する関数がある。
  - J-Quants 連携を前提としたテーブル/データスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など）が前提。
- フェイルセーフ設計
  - AI API の失敗時には多くの処理で例外を上位に投げず、0や空結果で継続する設計（取引停止を避ける意図）。
  - ただし DB 書き込み（トランザクション内）での例外は上位に伝播し、ROLLBACK が試行される。
- 部分書き込み保護
  - ai_scores 等のテーブル更新では、失敗時に既存スコアを消さないよう、対象コードのみ削除して挿入する方式を採用。
- カレンダー挙動
  - market_calendar が未セットの環境では曜日ベースフォールバックとなるため、祝日・SQ等の判定は正確でない可能性がある。JPX カレンダーの更新ジョブを運用することを推奨。
- 未実装/限定実装
  - calc_value の PBR・配当利回りは現バージョンでは未実装。
  - research モジュールは DuckDB のみを参照し、本番の発注ロジックや取引APIとは無関係。
- テスト上の配慮
  - 自動 .env 読み込みはテスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - OpenAI 呼び出し部はモック差替えでテストを想定。

### 変更履歴に関する補足
- 初回リリースのため Breaking Changes / Removed / Fixed / Security のセクションは該当なし。

---

今後のリリースでは、下記のような改善を予定しています（予定機能の例）:
- ai_score / ai_models の継続評価とモデル選択の拡張
- ETL の詳細な品質チェック実装と自動アラート連携
- strategy / execution モジュールとの統合テストと安全弁（サンクション）
- PBR・配当利回り等バリューファクターの追加実装

ご要望や不具合報告があれば issue を作成してください。