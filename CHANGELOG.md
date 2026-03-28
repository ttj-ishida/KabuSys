# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
初回リリースに含まれる機能・設計方針・注意点をコードベースから推測してまとめています。

## [0.1.0] - 2026-03-28

### 追加 (Added)
- 初期リリース: kabusys パッケージを公開。
  - パッケージ初期バージョン: 0.1.0（src/kabusys/__init__.py）

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env/.env.local ファイルおよび OS 環境変数から設定を自動読み込み。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
  - .git または pyproject.toml を基準にプロジェクトルートを探索（CWD に依存しない実装）。
  - .env のパース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - 既存 OS 環境変数を保護する protected キーの仕組み（.env 上書き抑制）。
  - Settings クラスを提供し、必要な環境変数をプロパティ経由で安全に取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を必須チェック。
    - KABU_API_BASE_URL / データベースパス（DUCKDB_PATH / SQLITE_PATH）にデフォルト値を設定。
    - KABUSYS_ENV, LOG_LEVEL のバリデーション（許容値チェック）。
    - is_live / is_paper / is_dev ヘルパーを提供。

- ニュースNLP（AI） (src/kabusys/ai/news_nlp.py)
  - raw_news + news_symbols を集約し、OpenAI（gpt-4o-mini）でセンチメントを評価し ai_scores に保存する score_news を実装。
  - ニュース収集ウィンドウ計算（JST 基準の前日 15:00 ～ 当日 08:30 を UTC に変換する calc_news_window）。
  - 銘柄毎に記事をトリム（最大記事数・最大文字数）して 20 銘柄単位でバッチ送信。
  - JSON Mode を想定したレスポンスバリデーションとスコアの ±1.0 クリップ。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ・リトライ実装。
  - API 失敗時はフェイルセーフで該当チャンクをスキップ（他の銘柄への影響を最小化）。
  - DB 書き込みは冪等化（DELETE → INSERT、transaction）し、部分失敗時に既存スコアを保護（対象コードを限定して置換）。
  - テスト容易性のため _call_openai_api の差し替えを想定（unittest.mock.patch）。

- 市場レジーム判定（AI + テクニカル融合） (src/kabusys/ai/regime_detector.py)
  - ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
  - ルックアヘッドバイアス防止のため、target_date 未満のデータのみを使用する設計。
  - マクロ記事がない場合や API 失敗時は macro_sentiment = 0.0 として処理継続（フェイルセーフ）。
  - OpenAI 呼び出しは専用実装とし、news_nlp モジュールとは独立している（モジュール結合を避ける）。
  - ブル／ベア閾値、リトライ、ログ出力を備え、market_regime テーブルへの冪等書き込みを行う。

- データプラットフォーム: カレンダー管理 (src/kabusys/data/calendar_management.py)
  - JPX カレンダー管理用ユーティリティと夜間更新ジョブ calendar_update_job を実装。
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった判定関数を提供。
  - market_calendar 未取得時は曜日ベース（週末を休場）でフォールバックする実装。
  - API からの差分取得・バックフィル（直近数日再取得）・健全性チェックを含む夜間処理の実装。
  - DuckDB の NULL 値や未登録日の挙動を明確化（警告ログやフォールバック処理）。

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
  - ETLResult データクラスを定義して ETL の取得/保存件数、品質問題、エラーを集約。
  - 差分更新や品質チェックを想定した内部ユーティリティ（テーブル存在確認、最大日付取得など）。
  - data.etl から ETLResult を再エクスポート。

- Research（ファクター計算・特徴量探索） (src/kabusys/research/*.py)
  - factor_research: calc_momentum, calc_volatility, calc_value を実装。
    - モメンタム（1M/3M/6M 等）、200 日 MA 乖離、ATR（20 日）、出来高・売買代金などを計算。
    - raw_financials から財務指標（EPS/ROE）を取得し PER/ROE を算出。
    - DuckDB 内の SQL ウィンドウ関数を活用した実装。
  - feature_exploration: calc_forward_returns（任意ホライズンの将来リターン）、calc_ic（スピアマン IC）、rank、factor_summary（統計要約）を実装。
  - すべて外部 API に依存せず、pandas 等の外部ライブラリに依存しない純標準実装を志向。

- その他
  - パッケージの公開 API (__all__) に主要サブパッケージを含める（data, strategy, execution, monitoring を想定）。
  - 各モジュールで DuckDB を第一級サポート（DuckDB 接続オブジェクトを引数で受け取る設計）。
  - ロギングを広く配置して操作履歴・障害解析を容易にする。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- DB 書き込みに関連する堅牢化:
  - DuckDB の executemany に空リストを渡さないようにガード（互換性対策）。
  - トランザクション処理で例外発生時に ROLLBACK を試み、失敗時は警告ログを出力する保護処理を追加。
- OpenAI API 呼び出しに対する堅牢化:
  - 429/ネットワーク/タイムアウト/5xx に対して指数バックオフでリトライ。
  - 非 5xx の APIError や JSON パースエラーはフェイルセーフでスコアを 0.0（またはスキップ）にフォールバック。
  - レスポンスの JSON が前後余分なテキストを含む場合に {} の抽出を試みる復元ロジックを追加。

### セキュリティ / 注意事項 (Security / Notes)
- 環境変数に機密情報（OpenAI キー、J-Quants トークン、Kabu API パスワード、Slack トークン等）を使用するため、.env ファイルやデプロイ環境の管理に注意してください。
- Settings._require は未設定の必須環境変数で ValueError を送出する。起動前に必須環境変数を設定してください。
- OpenAI の使用は API キーが必須（api_key 引数または環境変数 OPENAI_API_KEY）。
- ルックアヘッドバイアス防止設計:
  - 各 AI / 研究処理は datetime.today() / date.today() を直接参照せず、明示的な target_date を受け取る設計。
  - DB クエリは target_date 未満／指定範囲等の排他条件を明示しているため、実運用でのデータリークを低減。

### 既知の制約 / 実装上の設計選択
- DuckDB を前提とした SQL（ROW_NUMBER, window 関数等）を多用。別 DB での互換性は保証しない。
- OpenAI のレスポンスパース・バリデーションは堅牢化しているが、LLM の出力形式変化により将来的に壊れる可能性あり。テスト用に _call_openai_api の差し替えを想定。
- calendar_update_job や ETL は外部 jquants_client（fetch/save 実装）に依存。API 側やネットワーク障害時はロギングして安全に終了する設計。
- ai モジュールは gpt-4o-mini を想定したプロンプト設計（JSON mode）を使用。

---

今後のリリースでは、strategy / execution / monitoring の具体的な売買ロジックや監視機能、より細かい品質チェック、単体テスト・統合テストの整備、型注釈強化やドキュメントの充実化が想定されます。ご要望があれば、CHANGELOG に追記・詳細化します。