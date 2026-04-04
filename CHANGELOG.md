# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
リリースポリシー: 0.x 系は開発初期リリースを想定します。

## [Unreleased]
- 特になし

## [0.1.0] - 2026-04-04
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。公開モジュールのエクスポート: data, strategy, execution, monitoring。
- 環境変数 / 設定管理
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パース機能を実装（export 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理）。読み込み時の上書きルール（OS 環境変数保護、.env → .env.local の優先度）を実装。
  - Settings クラスを提供（J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定など）。KABUSYS_ENV と LOG_LEVEL の値検証、パスの Path 変換、各閾値のデフォルト設定を含む。
- AI 関連
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を銘柄別に集約し、OpenAI（gpt-4o-mini、JSON mode）へバッチ送信して銘柄ごとのセンチメント ai_score を ai_scores テーブルに書き込む機能を実装（score_news）。
    - タイムウィンドウ計算ユーティリティ calc_news_window（JST ベースの窓を UTC naive datetime として返す）。
    - バッチサイズ、文字数／記事数上限、リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフ、レスポンスの厳密な JSON バリデーション、スコアの ±1.0 クリップを実装。
    - API 未設定時には ValueError を送出。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225 連動型）200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定し market_regime テーブルへ冪等書き込みを行う機能を実装（score_regime）。
    - マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini、JSON 返却想定）、リトライとフェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - lookahead バイアスを避ける設計（target_date 未満のデータのみ参照、date.today() 等を参照しない）。
- データプラットフォーム
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダーの管理と夜間バッチ更新ジョブ calendar_update_job を実装。J-Quants クライアント経由で差分取得 → idempotent 保存（ON CONFLICT 相当）をサポート。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日判定ユーティリティを実装。DB にデータがない場合は曜日ベース（月〜金を営業日）でフォールバック。
    - バックフィル、健全性チェック、最大探索日数制限を実装して無限ループや極端な値を防止。
  - ETL パイプライン (kabusys.data.pipeline / etl)
    - ETL 実行結果を表す ETLResult データクラスを公開（取得件数、保存件数、quality チェック結果、エラーリスト等を含む）。
    - 差分更新、バックフィル、品質チェックの設計方針に基づく ETL パイプラインの基礎を実装（jquants_client 経由での idempotent 保存、品質問題の収集）。
- リサーチ / ファクター
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev の計算（price 履歴から）。
    - calc_volatility: 20 日 ATR, 相対 ATR, 20 日平均売買代金, 出来高比率等の計算。
    - calc_value: raw_financials から最新の財務データを取得して PER（EPS が 0 または NULL の場合は None）と ROE を計算。
    - DuckDB（prices_daily / raw_financials）に依存し、外部 API へアクセスしない安全な設計。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンを計算。
    - calc_ic: スピアマンランク相関（IC）計算（結合・欠損排除、十分なサンプルがない場合は None）。
    - rank: 同順位は平均ランクで処理するランク変換ユーティリティ（丸めによる ties 対策）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー機能。
- 実装方針・品質
  - DuckDB を中心に SQL と純 Python の組み合わせで高性能に処理。
  - datetime.today()/date.today() を直接参照しない設計でルックアヘッドバイアスを防止。
  - API 呼び出し失敗時のフォールバックやログ（WARNING/INFO/DEBUG）を重視し、部分失敗で他データが毀損しないように設計（例: ai_scores・market_regime の置換は対象コードのみを削除→挿入）。
  - 外部ライブラリへの依存を最小化（OpenAI SDK を除く）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- OpenAI API キー（OPENAI_API_KEY）や J-Quants / KabuStation のトークンは必須的に取り扱う箇所があるため、運用環境では安全に管理すること（環境変数・シークレット管理を推奨）。
- .env 読み込み時に OS 環境変数を保護する実装あり（デフォルトで既存の OS 環境変数が上書きされない）。

---

既知の制約・注意点
- OpenAI 呼び出しは gpt-4o-mini を想定した JSON Mode を使用。API の仕様変更やモデルの挙動に依存する点に留意してください。
- DuckDB のバージョン差異による bind/list 型の挙動に配慮した実装（executemany を用いる等）を行っていますが、実行環境の DuckDB バージョンでの動作確認を推奨します。
- news_nlp/regime_detector は API キーが未設定の場合に ValueError を送出します（テスト用途には api_key 引数経由で注入可能）。

もし詳しいリリース日や追加したファイル／変更点の分類を調整したい場合は、該当するコミットログや差分を提供してください。