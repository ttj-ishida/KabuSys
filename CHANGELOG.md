# CHANGELOG

すべての変更は Keep a Changelog の方針に従って記載しています。  
初版リリース: バージョン 0.1.0（初回公開）

## [0.1.0] - 2026-03-28

初期リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。主な追加内容は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開 API を定義（kabusys.__all__ = ["data", "strategy", "execution", "monitoring"]）。

- 環境・設定管理 (kabusys.config)
  - .env ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を追加。
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索（パッケージ配布後も動作するよう __file__ から探索）。
    - 自動ロードの無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサを実装（export 形式・クォート文字列・バックスラッシュエスケープ・インラインコメント処理に対応）。
  - 環境変数取得用 Settings クラスを追加（J-Quants / kabu API / Slack / DB パス / 実行環境・ログレベル判定等）。
    - 必須値未設定時は明示的に ValueError を発生させる `_require` を使用。
    - KABUSYS_ENV, LOG_LEVEL の値検証を実装（許容値は定義済み）。

- AI（自然言語処理）モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news および news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントスコアを算出して ai_scores テーブルへ書き込み。
    - ウィンドウ定義（JST ベース）と DuckDB の UTC 保存想定の変換ロジックを実装（calc_news_window）。
    - バッチ処理（最大 20 銘柄 / API 呼び出し）・1 銘柄あたり記事数・文字数上限の仕組みを実装。
    - API エラー（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフでリトライ。その他はスキップして継続（フェイルセーフ）。
    - レスポンスの厳密バリデーションとスコアの ±1.0 クリップを実装。
    - テスト容易性のため OpenAI 呼び出し箇所をラップ（_call_openai_api）し patch で差し替え可能。
    - DuckDB の executemany に関する互換性考慮（空リストを渡さない）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で算出、market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出用キーワード集合と取得上限（最大 20 件）を実装。
    - OpenAI 呼び出しは別実装とし、API 失敗時は macro_sentiment = 0.0 にフォールバック。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）と例外時の ROLLBACK 処理を実装。
    - リトライ回数・待機戦略・利用モデル等（gpt-4o-mini, retry=3, base wait=1s）を定義。

- Research（因子算出・特徴量探索） (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20 日 ATR）、流動性指標（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）の計算を実装。
    - DuckDB を用いた SQL ベース計算を実装し、結果は (date, code) 辺りの dict のリストで返却。
    - データ不足時の None 戻りや、計算用スキャン範囲（バッファ）を考慮。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns、各種 horizon 対応、入力検証あり）。
    - IC（Information Coefficient, Spearman ρ）計算（rank 関数・欠損・有限値チェック）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
  - research パッケージの __init__.py で主要関数を公開（zscore_normalize を data.stats から再エクスポート）。

- Data（データプラットフォーム） (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルに基づく営業日判定ロジックを提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にデータがない場合は曜日ベース（週末除外）でフォールバックする一貫した振る舞いを設計。
    - カレンダーの夜間差分更新ジョブ（calendar_update_job）を実装。J-Quants API からの差分取得→冪等保存、バックフィルや健全性チェックを含む。
  - ETL パイプライン基盤 (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを実装し、ETL の取得件数・保存件数・品質問題・エラー要約を格納可能に。
    - 差分取得・backfill（デフォルト 3 日）・品質チェックを行う設計方針を反映。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを実装。
    - ETLResult を etl モジュールで再エクスポート（pipeline.ETLResult）。

### 変更 (Changed)
- なし（初回リリースのため変更履歴はありません）。

### 修正 (Fixed)
- なし（初回リリース）。

### 設計・実装上の重要な注意点（ドキュメント的注記）
- ルックアヘッドバイアス防止:
  - AI モジュール・Research モジュールは datetime.today() / date.today() を直接参照しない設計。すべての関数は target_date を明示的に受け取り、過去データのみを参照するよう SQL に排他条件を含めています。
- フェイルセーフ挙動:
  - OpenAI 呼び出し失敗や予期しないレスポンスは致命的な例外を上げず、デフォルト値（例: macro_sentiment=0.0）やスキップで継続する方針です。これによりバッチ全体の停止を防ぎます。
- テスト容易性:
  - OpenAI への実際の呼び出しはモジュール内のラッパー関数（_call_openai_api）を介して行うため、ユニットテストで patch して差し替え可能です。score_regime / score_news は api_key を引数で注入可能。
- DuckDB 互換性:
  - executemany に空リストを渡すとエラーになる DuckDB バージョンを考慮し、空チェックを行ってから executemany を呼ぶ実装にしています。
- トランザクション安全性:
  - market_regime / ai_scores への書き込みは BEGIN/DELETE/INSERT/COMMIT を行い、例外発生時は ROLLBACK を試行してから例外を再送出します。ROLLBACK が失敗した場合は警告ログを出力します。

### 既知の制約・留意点
- OpenAI モデルと API の仕様に依存（現状 gpt-4o-mini + JSON Mode を想定）。将来の SDK 変更に備えて例外の status_code は getattr で安全に取得する実装にしていますが、API 仕様が変わると追加対応が必要になる可能性があります。
- .env 自動ロードはプロジェクトルート検出に依存します。パッケージ配布後に CWD を起点に期待通り動作しない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動で設定を注入してください。
- ai モジュールの出力は LLM に依存するため、レスポンスフォーマット違反時はそのチャンクをスキップすることがあります（部分成功が想定される）。

---

今後の予定（未実装・想定）
- strategy / execution / monitoring の詳細実装（現在は __all__ に名前を用意）。
- テスト用ユーティリティ・モックサーバー、CLI やジョブスケジューラ統合の追加。
- モデル切替・コスト最適化のための抽象化レイヤ追加。

（以上）