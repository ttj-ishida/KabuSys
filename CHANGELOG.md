# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトの初期リリースおよび実装特徴をコードベースから推測して日本語でまとめています。

全般な注記
- このリポジトリのバージョンはパッケージメタデータに従い v0.1.0 としています。
- 多くの機能は DuckDB を利用したローカル分析 / ETL / 品質チェック、及び OpenAI（gpt-4o-mini）を用いた NLP スコアリングに依存します。
- 環境依存の設定は .env / .env.local / OS 環境変数で管理されます。OpenAI API キーなど一部は必須です（設定がない場合は ValueError を送出します）。

## [0.1.0] - 2026-04-01
初回リリース（コードベースの初期実装）

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージの初期公開（__version__ = "0.1.0"）。
  - パッケージのトップレベルエクスポートに data, strategy, execution, monitoring を含む設計。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - プロジェクトルート検出機能を実装（.git または pyproject.toml を探索）。これにより CWD に依存せず .env 自動読み込みが可能。
  - .env / .env.local の自動ロード機能を実装（読み込み優先順位: OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグをサポート（テスト用途）。
  - 安全な .env パース実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメント処理（クォートあり/なしの挙動を区別）
  - override / protected を使った上書き制御（OS 環境変数を保護する仕組み）。
  - Settings クラスを提供し、各種必須値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）をプロパティとして取得。パス・閾値・環境名（KABUSYS_ENV）やログレベル（LOG_LEVEL）のバリデーションを実装。
  - デフォルトの DB パス・PID ファイル・監視閾値などシステム設定のプロパティ化。

- AI モジュール（ニュースNLP / レジーム判定）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ定義（JST: 前日 15:00 ～ 当日 08:30、内部は UTC naive datetime）と calc_news_window ユーティリティを提供。
    - バッチサイズ、記事数・文字数のトリム制御、最大リトライ（429/ネットワーク/5xx）を実装。レスポンス検証（JSON 抽出・results キー・型検証・既知コードのみ採用）を行う。
    - フェイルセーフ設計: API 呼び出し失敗・検証失敗時は例外ではなくスキップ（空スコア）で処理を継続。部分書き換え（DELETE → INSERT）で部分失敗時に既存スコアを保護。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200日移動平均乖離（ウエイト 70%）とマクロニュースの LLM センチメント（ウエイト 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照して ma200_ratio を算出、マクロ記事を抽出して OpenAI（gpt-4o-mini）で macro_sentiment を評価しスコア合成。
    - LLM 呼び出し時のエクスポネンシャルバックオフ、API エラー種別（RateLimit, Connection, Timeout, 5xx）の分岐処理を実装。API 失敗時は macro_sentiment = 0.0 のフォールバック。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を採用。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - factor_research.py
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日 ATR）、Liquidity（20日平均売買代金・出来高比）、Value（PER, ROE）等のファクター計算機能を実装。DuckDB のウィンドウ関数を活用し date/code 単位で結果を返す。
    - 欠損やデータ不足に対する挙動を明確化（例: MA200 未満なら None）。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns: 任意ホライズン）、IC（Spearman の ρ）計算、ランク化ユーティリティ、各種統計サマリー（count/mean/std/min/max/median）を実装。
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB で実装。

- データプラットフォーム（src/kabusys/data/*）
  - calendar_management.py
    - JPX カレンダー（market_calendar）に基づく営業日判定 API を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の場合は曜日ベース（土日除外）フォールバックを行い、一貫した挙動を保証。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存（バックフィルや健全性チェック付き）。
  - pipeline.py / etl.py / ETLResult
    - ETLResult データクラスを提供し、ETL の取得数・保存数・品質問題やエラーの収集を行う設計。
    - ETL パイプライン設計方針（差分更新・backfill・品質チェック）のインターフェース実装（jquants_client / quality と連携する想定）。
  - jquants_client を介した差分取得と冪等保存を想定した実装構成。

### 変更 (Changed)
- （初回リリースのため履歴なし）

### 修正 (Fixed)
- （初回リリースのため履歴なし）

### 非推奨 (Deprecated)
- （現段階ではなし）

### 削除 (Removed)
- （現段階ではなし）

### セキュリティ (Security)
- 環境変数の自動読み込み時に OS 環境変数を上書きしない既定の動作（protected set）を採り、.env による機密情報の誤上書きを防止。
- OpenAI API キーや Slack トークン等の必須シークレットは Settings._require により未設定時に即座にエラーを出すことで、秘密情報の未設定で意図せぬ外部呼び出しが発生しないようにしている。

### 既知の制約 / 注意点（コードから推測）
- OpenAI 呼び出しは gpt-4o-mini を前提とし、JSON mode（厳密な JSON 出力）を期待する設計。モデル挙動に依存するため運用時にはレスポンス形式の確認が必要。
- DuckDB バージョンによるパラメータバインドの挙動（executemany の空リスト不可、ANY(?) の挙動差など）に配慮した実装になっている。
- ETL / カレンダー更新 / ニュース NLP 等は外部 API（J-Quants、OpenAI）や DB スキーマに依存するため、運用前に DB スキーマと環境変数を整備する必要あり。
- API 例外は多くの場合フェイルセーフでデフォルト値（0.0 やスキップ）にフォールバックする設計だが、重要な欠損や品質問題は ETLResult.quality_issues / errors に集約される想定。

---

必要であれば、実際のコミット履歴や追加のファイル（strategy, execution, monitoring 等）に基づいて CHANGELOG をより詳細に分割・改訂します。どの粒度で記載するか（モジュール別の小変更まで含める／高レベルの機能列挙に留める）を指示してください。