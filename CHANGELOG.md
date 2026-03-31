KEEP A CHANGELOG
すべての重要な変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠します。
http://keepachangelog.com/（英語）を参照してください。

## [0.1.0] - 2026-03-31
初回リリース（ベースライン実装）。日本株自動売買システムのコアライブラリを提供します。
主な目的はデータ取得・ETL、マーケットカレンダー管理、ファクター計算、ニュース/マクロの NLP スコアリング、
および市場レジーム判定ロジックの基盤を備えたリサーチ/AI ツール群の提供です。

### 追加 (Added)
- パッケージ初期化
  - kabusys.__init__ に基本的な __version__ とエクスポート対象を追加。

- 環境設定管理（kabusys.config）
  - .env/.env.local ファイルおよび OS 環境変数から設定を自動読み込み（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .git または pyproject.toml を基準にプロジェクトルートを探索して .env を解決（cwd に依存しない動作）。
  - 複雑な .env パース実装（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、コメント処理など）を追加。
  - 環境変数取得ユーティリティ Settings クラスを追加（必須キー取得時のエラー、既定値、検証ロジックを実装）。
  - 設定項目例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN/CHANNEL, DUCKDB_PATH/SQLITE_PATH, PID_FILE_PATH, CPU/MEM/DISK 閾値, KABUSYS_ENV, LOG_LEVEL。

- AI モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news / news_symbols を集約し、銘柄毎のニュースを結合して OpenAI（gpt-4o-mini）へバッチ送信。
    - バッチ処理（デフォルト最大 20 銘柄）、1 銘柄あたりの記事数・文字数制限（記事数最大 10、文字数最大 3000）。
    - 再試行ポリシー（429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ）。
    - レスポンスの厳密バリデーション（JSON 抽出・results リスト・code/score 検査）、スコアの ±1.0 クリップ。
    - 書込みは部分置換方式（成功したコードのみ DELETE → INSERT）で部分失敗時の既存データ保護。
    - calc_news_window ユーティリティ（target_date に対するニュース収集ウィンドウ算出。JST→UTC 換算）。

  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して
      市場レジーム（bull/neutral/bear）を算出して market_regime テーブルへ冪等書き込み。
    - マクロニュースは news_nlp.calc_news_window と raw_news からフィルタして取得。
    - OpenAI 呼び出しは独立実装でモック差し替えが容易（テスト用）。
    - API 失敗時は macro_sentiment を 0 にフォールバックするフェイルセーフ挙動。
    - 再試行・バックオフ、JSON パース失敗時の安全なフォールバックを実装。

- Data モジュール（kabusys.data）
  - calendar_management
    - market_calendar テーブルを利用した営業日判定ロジック（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB 登録値優先、未登録日は曜日ベースのフォールバックを統一的に適用。
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等更新（バックフィルと健全性チェック含む）。
    - 最大探索日数制限（無限ループ防止）などの安全措置を実装。

  - pipeline / etl
    - ETLResult データクラスを公開（ETL 実行結果の構造化）。
    - ETL の設計方針に沿った差分取得・バックフィル・品質チェックのための基盤を追加（jquants_client / quality モジュール経由での連携を想定）。
    - DuckDB に対する存在チェックユーティリティ等を実装。

- Research モジュール（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（prices_daily を参照）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算（EPS が 0/欠損時は None）。
    - 全て DuckDB SQL を用いた実装で、外部発注等の副作用なし。

  - feature_exploration
    - calc_forward_returns: 任意ホライズンの将来リターンをまとめて取得（デフォルト [1,5,21]）。
    - calc_ic: Spearman（ランク）に基づく IC（Information Coefficient）を計算。
    - rank: 平均ランク（同順位は平均）を返すユーティリティ。
    - factor_summary: 各列の count/mean/std/min/max/median を計算する統計サマリー。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- .env パーサーの堅牢性強化
  - クォート内のバックスラッシュエスケープ対応、コメント処理の改善、export プレフィックス対応などを導入し
    よくある .env の書式差を吸収するように改善。
- OpenAI レスポンスパースの耐性強化
  - JSON mode でも前後に余計なテキストが混入するケースを考慮して最外の `{...}` を抽出して復元するフォールバックを追加。
- DuckDB への複数行操作時の互換性対応
  - executemany に空リストを渡さないガードを追加（DuckDB 0.10 系の制約回避）。

### 既知の制限 / 設計上の注意 (Notes)
- 多くの関数は datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計（ルックアヘッドバイアス防止）。
- OpenAI の呼び出しは gpt-4o-mini を想定（モデル名は定数化）。API キーは関数引数経由で注入可能でテストが容易。
- DB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials, market_regime 等）を前提としているため、
  実運用前にスキーマ整備が必要。
- strategy / execution / monitoring パッケージは __all__ に含まれるが、本リリースでの実装が一部に留まる可能性がある（将来追加予定）。

### セキュリティ (Security)
- （初版のため該当なし）

注: この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートとして使用する場合は、実装者による確認・編集を推奨します。