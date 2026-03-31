# Keep a Changelog — CHANGELOG.md

すべての変更は https://keepachangelog.com/ja/ のガイドラインに従って記載しています。

全般方針:
- リリースはセマンティックバージョニングに従います。
- 設計上の重要な振る舞い（例: ルックアヘッドバイアス防止、フェイルセーフ、DuckDB互換性）を明記します。

## [0.1.0] - 2026-03-31
初回公開リリース。日本株自動売買システム「KabuSys」のコア機能を提供します。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイント: kabusys.__version__ = 0.1.0、パブリックAPIとして "data", "strategy", "execution", "monitoring" を公開。
- 設定・環境管理 (kabusys.config)
  - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を探索）。
  - .env/.env.local の自動読み込み（優先度: OS環境 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサを実装。以下に対応:
    - export KEY=val 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォート無しのインラインコメント処理（直前が空白/タブの場合のみ）
  - .env 読み込みで OS 環境変数を保護する protected キーセットを導入。
  - Settings クラスを提供し、必須環境変数取得メソッドを集約:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値を定義。
    - KABUSYS_ENV (development/paper_trading/live) と LOG_LEVEL のバリデーション。
    - is_live / is_paper / is_dev のユーティリティプロパティ。
- AI モジュール (kabusys.ai)
  - news_nlp
    - raw_news を用いたニュースセンチメント付与機能を実装（score_news）。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - news_symbols と結合して銘柄ごとに記事を集約し、1銘柄あたり最大記事数 / 最大文字数でトリム。
    - OpenAI（gpt-4o-mini）へバッチ送信（バッチサイズ最大 20 銘柄）。JSON Mode（response_format={"type":"json_object"}）を使用。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装。
    - レスポンス検証ロジック（results 配列、code/score チェック、数値の有限性チェック）と ±1.0 クリッピング。
    - DuckDB への冪等書き込み（対象コードのみ DELETE→INSERT）を実装。部分失敗時に既存スコアを保護する。
    - テスト容易性: OpenAI 呼び出しを _call_openai_api を通してパッチ可能に設計。
  - regime_detector
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）判定を行う score_regime を実装。
    - ma200_ratio 計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）、マクロ記事抽出（キーワードベース）、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込みをサポート。
    - OpenAI API 呼び出しはニュースモジュールとは別実装にしてモジュール結合を避ける。
    - API失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ設計。
- リサーチ機能 (kabusys.research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率(ma200_dev) を計算。
    - calc_volatility: 20日 ATR、ATR/価格比、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得して PER、ROE を算出（EPS が 0/欠損時は None）。
    - DuckDB SQL ベースで高性能に計算、外部APIや本番注文系へのアクセスは一切なし。
  - feature_exploration
    - calc_forward_returns: 翌日/翌週/翌月など将来リターン計算（デフォルト: [1,5,21]）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。データ不足時は None を返す。
    - rank: 同順位は平均ランクを採るランク変換ユーティリティ（丸めによる ties の検出漏れ防止のため round を使用）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー関数。
  - すべて標準ライブラリと DuckDB のみで実装（pandas 等へ依存しない）。
- データ管理 (kabusys.data)
  - calendar_management
    - market_calendar 管理、営業日判定、next/prev_trading_day、get_trading_days、is_sq_day を実装。
    - DB にデータがある場合は DB 値優先、未登録日は曜日 (土日) ベースでフォールバック。
    - calendar_update_job にて J-Quants API から差分取得 → 冪等保存（jquants_client 経由）を実行。バックフィル・健全性チェックを実装。
  - pipeline / ETL
    - ETLResult データクラスを実装（取得数、保存数、品質問題、エラー等を格納）。
    - 差分更新・バックフィル・品質チェックを想定した ETL パイプライン基盤。
    - DuckDB テーブル存在チェックや最大日付取得ユーティリティを実装。
  - etl モジュールでは pipeline.ETLResult を再エクスポート。
- DuckDB 互換性考慮
  - executemany に空リストを渡せない DuckDB 0.10 の制約に対応した分岐ロジックを導入。
- テスト設計上の配慮
  - OpenAI 呼び出し (_call_openai_api) や時間参照を直接用いない設計（ルックアヘッドバイアス防止）によりユニットテスト容易性を確保。

### 変更 (Changed)
- （初版につき変更履歴はありません）

### 修正 (Fixed)
- （初版につき修正履歴はありません）

### 破壊的変更 (Removed / Deprecated)
- （初版につきなし）

### セキュリティ (Security)
- OpenAI API キー未設定時に明確な ValueError を発生させることで誤動作を防止（score_news / score_regime）。
- .env ファイル読み込み失敗時は警告を出して継続（読み込み時に機密情報の誤上書きを防ぐ設計）。

### 実装上の注意点 / 既知の振る舞い
- 多くの関数は datetime.today() / date.today() を直接参照せず、引数で target_date を受け取ることでルックアヘッドバイアスを回避しています。スケジューリング時は適切な target_date を渡してください。
- OpenAI の呼び出しは外部 API であり失敗する可能性があるため、失敗時はフェイルセーフとしてスコアに中立値（0.0）を使う等の設計にしています。これにより処理は継続しますが、スコア結果が欠落する場合があります。
- DuckDB による SQL 実行の返却型（日付等）を想定しており、型変換ヘルパーを用いて date オブジェクトへ正規化しています。
- jquants_client や quality モジュール等は外部インタフェースとして呼び出しており、環境に合わせた実装（またはモック）を用意してください。

---

将来のリリースでは以下を予定:
- strategy / execution / monitoring の実装補完および統合テスト
- ai モデルやプロンプトの改善（説明可能性・安定性向上）
- ETL の詳細な品質チェックルール追加とメトリクス出力

（必要があれば各モジュールごとにより詳細なリリースノートを追記します。）