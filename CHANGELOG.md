KEEP A CHANGELOG
すべての注目すべき変更点を時系列で記録します。本ファイルは Keep a Changelog の形式に準拠します。

## [Unreleased]
- 現在なし

## [0.1.0] - 2026-03-28
初回リリース。

### 追加 (Added)
- パッケージ骨子
  - kabusys パッケージを追加。パッケージバージョンは 0.1.0。
  - パッケージ公開インターフェースとして data, strategy, execution, monitoring を想定（__all__）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートの検出は __file__ から親ディレクトリをたどり .git または pyproject.toml を基準に判定。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパースは堅牢化（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント判定等に対応）。
  - Settings クラスを提供し、アプリケーション設定を型付きプロパティで取得可能（必須キー未設定時は明確な例外を送出）。
  - 主要な必須環境変数例を定義:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パス（DUCKDB_PATH, SQLITE_PATH）、KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL（DEBUG/INFO/...）の検証機能。

- AI / ニュース NLP (kabusys.ai.news_nlp)
  - raw_news と news_symbols を基に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出する score_news を実装。
  - 処理の特徴:
    - ニュース収集ウィンドウの明確化（前日15:00 JST〜当日08:30 JST を UTC に変換して使用）。
    - 1 銘柄あたりの上限記事数および文字数でトリム (_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK)。
    - 1 API コールあたりの最大銘柄数（チャンク）を制限し、複数チャンク処理を行う（_BATCH_SIZE）。
    - JSON mode（厳密な JSON 応答）を想定しつつ、前後余分テキストの復元処理を実装。
    - レート制限・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ、その他はスキップ（フェイルセーフ）。
    - レスポンスのバリデーション（results 配列、code の正規化、数値検査、±1.0 のクリップ）。
    - 成功分のみ ai_scores テーブルへ置換的に書き込み（DELETE → INSERT）し、部分失敗時に既存スコアを保護。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能に設計。

- AI / マーケットレジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（MA）とマクロニュースの LLM センチメントを重み合成して日次レジーム（bull/neutral/bear）を判定する score_regime を実装。
  - 処理の特徴:
    - MA200 比率計算は target_date 未満のデータのみを使用しルックアヘッドを回避。
    - マクロニュースは news_nlp.calc_news_window で算出したウィンドウからキーワードフィルタ（複数キーワード）で取得。
    - OpenAI 呼び出しは JSON mode を使用し、API エラーはフェイルセーフ（macro_sentiment=0.0）で継続。
    - 合成スコアは MA 成分（70%）とマクロ（30%）を組み合わせ clip(-1,1)。
    - market_regime テーブルへ冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。

- データプラットフォーム（kabusys.data）
  - カレンダー管理 (calendar_management)
    - market_calendar を参照して営業日判定を行うユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar 未取得時は曜日ベース（土日除外）のフォールバックロジックを提供。
    - next/prev_trading_day は DB 登録値を優先しつつ未登録日は曜日フォールバックで一貫して探索（探索上限を設定して無限ループ防止）。
    - calendar_update_job を実装し、J-Quants API から差分取得・バックフィル・保存（jq.save_market_calendar）を行う。健全性チェックやバックフィル日数の取り込みを実装。
  - ETL パイプライン (pipeline, etl)
    - ETLResult dataclass を公開（etl.py で再エクスポート）。
    - ETL の内部ユーティリティ（テーブル存在チェック、最大日付取得、取得範囲の調整）や設計方針（差分更新、バックフィル、品質チェック継続）を実装。

- リサーチモジュール (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER/ROE）を計算する関数群を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB ベースで SQL を活用した高速計算。データ不足時は None を返す設計。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を実装。
    - ランク処理は同順位を平均ランクで処理し、丸めを行って ties を安定的に扱う。

### 設計上の注意点 / セーフガード (Notes)
- ルックアヘッドバイアス対策:
  - 主要な関数（score_news, score_regime, 各種 research 関数）は datetime.today()/date.today() を内部参照せず、target_date を明示的に受け取る設計。
- フェイルセーフ:
  - OpenAI API 呼び出し失敗時は基本的に処理を継続（0.0 スコア等にフォールバック）し、ETL や部分的な DB 書き込みで他データを守る。
- トランザクションと冪等性:
  - 主要な DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等パターンを採用。異常時は ROLLBACK を試行して例外を伝播。
- DuckDB 互換性対策:
  - executemany に空リストを渡さない等、DuckDB の既知制約に配慮した実装がなされている。
- テスト性:
  - OpenAI 呼び出し部分はモック差し替え可能（モジュールローカルの _call_openai_api を patch しやすい構造）。
- ロギング:
  - 各モジュールで詳細なログ出力を行い、異常・警告・処理結果を記録するようにしている。

### 既知の必須設定 / 依存外部キー
- OpenAI を用いる機能を利用する際は OPENAI_API_KEY が必要（score_news, score_regime）。関数は引数で api_key を受け取り可能。
- J-Quants / kabu API 等の連携にはそれぞれ対応する環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）が必要。

### 既知の制限 (Known limitations)
- PBR・配当利回りなど一部ファクタは未実装（calc_value は現時点で PER / ROE のみ）。
- strategy / execution / monitoring の具体的な発注ロジックやモニタリング実装は本リリースのコード断片では提供されていない（パッケージ public API に名前があるが実装は順次追加予定）。

---

貢献・バグ報告・改善案はリポジトリの issue を通じてお願いします。