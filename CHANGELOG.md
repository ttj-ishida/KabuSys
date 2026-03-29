# Changelog

すべての重要な変更はこのファイルに記録します。  
この CHANGELOG は「Keep a Changelog」形式に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース。日本株アルゴリズム取引プラットフォームの基盤機能を実装しています。以下の主要な機能・設計方針・品質対策を含みます。

### 追加（Added）
- 基本パッケージ初期化
  - パッケージメタ情報を公開（kabusys.__version__ = 0.1.0）。
  - パッケージ公開 API に data, strategy, execution, monitoring を含む（monitoring はエントリが公開されていることに注意）。

- 環境設定管理（kabusys.config）
  - .env / .env.local のプロジェクトルート自動読み込み（.git または pyproject.toml を起点に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサの実装（export プレフィックス対応、クォート処理、インラインコメント処理など）。
  - OS 環境変数を保護する protected オプション（.env.local の上書き制御を安全に実行）。
  - 必須環境変数取得のユーティリティ（_require）。
  - 設定オブジェクト Settings を公開（J-Quants, kabuステーション, Slack, DB パス, 環境種別・ログレベル判定）。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを算出。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/コール）、1 銘柄あたり _MAX_ARTICLES_PER_STOCK = 10 記事、_MAX_CHARS_PER_STOCK = 3000 文字トリム。
    - JSON Mode での応答処理と堅牢なパース（前後余分テキストの補正含む）。
    - リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフ実装。
    - スコアのバリデーションと ±1.0 クリップ。
    - DuckDB への冪等書き込み（DELETE → INSERT）と部分失敗時の保護（対象コードのみ）。
    - ルックアヘッドバイアス防止のため datetime.today() を参照しない設計。news ウィンドウは前日15:00 JST〜当日08:30 JST を基準。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出、OpenAI（gpt-4o-mini）呼び出し、スコア合成、_BULL/_BEAR しきい値判定。
    - LLM 呼び出し失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）と ROLLBACK に関するログ。

- 研究（research）モジュール（kabusys.research）
  - factor_research: calc_momentum, calc_value, calc_volatility を実装（prices_daily / raw_financials を参照）。
    - Momentum: 1M/3M/6M リターン、200日MA乖離（ma200_dev）。
    - Volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率。
    - Value: PER（EPS が無効時は None）、ROE（財務データから取得）。
  - feature_exploration: calc_forward_returns（horizons デフォルト [1,5,21]）、calc_ic（Spearman ランク相関）、factor_summary（統計サマリー）、rank（同順位の平均ランクを扱う安定実装）。
  - zscore_normalize を data.stats から再エクスポート。

- データ（data）モジュール
  - calendar_management: 市場カレンダー管理（market_calendar を使用）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - カレンダーデータが未取得のときは曜日ベースでフォールバック（週末を非営業日扱い）。
    - calendar_update_job: J-Quants からの差分取得、バックフィル（直近 _BACKFILL_DAYS）と健全性チェック、J-Quants クライアント呼び出し・保存処理。
  - ETL パイプライン（data.pipeline）
    - ETLResult データクラスで ETL の実行結果を集約（品質問題やエラーを収集）。
    - 差分取得、保存（jquants_client 経由の冪等保存）、品質チェックの設計方針を実装。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティ。
  - etl.py で ETLResult を公開。

### 変更（Changed）
- 設計上の品質/安全性強化（各モジュールで共通）
  - ルックアヘッドバイアス対策: 日付参照を関数引数に限定し、グローバルな datetime.today()/date.today() の直接参照を避ける設計。
  - DuckDB との互換性配慮: executemany に空リストを渡さないチェック（DuckDB 0.10 の制約回避）。
  - DB 書き込みは冪等性を重視（既存行は削除→挿入のパターンや ON CONFLICT 相当の挙動を保つ）。
  - OpenAI 呼び出しはモジュールごとに独立したラッパー実装（モジュール間のプライベート関数共有回避、テストのための patch を想定）。

### 修正（Fixed）
- .env パーサの堅牢化
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いを明確化。
  - キーが空の行や無効行を無視。

- OpenAI / LLM 周りのフォールバックとエラーハンドリング
  - リトライ対象エラー（RateLimitError, APIConnectionError, APITimeoutError, 5xx）に対する指数バックオフ。
  - 非 5xx の APIError はリトライせず警告してフォールバックする挙動。
  - JSON パース失敗時のログおよび安全なフォールバック（score_news: 空辞書、regime_detector: macro_sentiment=0.0）を追加。

- DB トランザクションの安全化
  - 例外発生時の ROLLBACK 試行と、ROLLBACK が失敗した場合の警告ログ出力。

### 既知の制約・注意点（Notes）
- monitoring がパッケージ __all__ に含まれている一方で、今回のスナップショットには monitoring 実装ファイルが含まれていません。導入時は monitoring 実装の追加を確認してください。
- OpenAI API の使用には環境変数 OPENAI_API_KEY または関数引数でのキー注入が必須です。未設定時は ValueError を送出します。
- news スコアリングとレジーム判定はいずれも LLM の応答に依存するため、API 利用料・レイテンシ・レート制限に注意してください。失敗時はフェイルセーフとして「中立」寄りの値にフォールバックしますが、完全な代替にはなりません。
- DuckDB のバージョン依存の挙動（executemany の空リスト等）に配慮した実装が入っていますが、古い/新しいバージョンでの挙動差分は運用時に確認してください。

---

今後のリリースでは、strategy / execution / monitoring の具体的実装、単体テストの充実、CI・デプロイ手順の確立、より高度な品質チェック・監視機能の追加を予定しています。