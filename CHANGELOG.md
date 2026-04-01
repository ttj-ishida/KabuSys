# CHANGELOG

すべての変更は Keep a Changelog の思想に準拠し、重要な変更はセマンティックバージョニングに従います。

現在のリリース:
- 0.1.0 - 2026-04-01

## [0.1.0] - 2026-04-01
初回リリース（ベースライン実装）。以下の主要機能・モジュールを提供します。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys、バージョン定義 __version__ = "0.1.0" を追加。
  - パッケージの公開 API: data, strategy, execution, monitoring を __all__ で定義。

- 設定 / 環境管理 (src/kabusys/config.py)
  - .env ファイルと環境変数からの設定自動読み込み機能を実装。
    - プロジェクトルート自動検出: .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env 解析器の実装:
    - export プレフィックス対応、クォート内のエスケープ処理、インラインコメントの扱いなどを考慮。
  - Settings クラスを提供（環境変数をラップしてプロパティで取得）
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 実行環境・ログレベル判定などのプロパティ。
    - 環境値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
    - Path 型の自動展開（expanduser）。

- AI（自然言語処理）関連 (src/kabusys/ai/)
  - news_nlp モジュール (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約して銘柄ごとのニュース本文を組立て、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメント（-1.0〜1.0）を算出。
    - バッチ処理（1リクエストあたり最大 20 銘柄）とトークン肥大対策（記事数・文字数トリム）。
    - 再試行戦略（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）。
    - レスポンスの堅牢なバリデーションとパース（余分な前後テキストの復元処理含む）。
    - ai_scores テーブルへ冪等的に部分置換（該当コードのみ DELETE→INSERT）。
    - calc_news_window: JST ベースのニュース集計ウィンドウ計算ユーティリティを提供（UTC naive datetime を返す）。
  - regime_detector モジュール (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull / neutral / bear）を判定して market_regime に保存。
    - LLM 呼び出しに対するリトライ、5xx の取り扱い、フェイルセーフ（失敗時 macro_sentiment=0.0）を実装。
    - prices_daily / raw_news を DuckDB 経由で参照し、ルックアヘッドバイアスを防ぐ設計（date < target_date 等）。
    - market_regime への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実施。

- データプラットフォーム（Data） (src/kabusys/data/)
  - calendar_management モジュール (src/kabusys/data/calendar_management.py)
    - JPX マーケットカレンダーの管理・更新ロジックを提供（夜間バッチ用 calendar_update_job）。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等の営業日判定ユーティリティを実装。
    - DB 登録優先・未登録日は曜日フォールバック、探索上限による安全策などを実装。
  - pipeline / ETL (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラス: ETL 実行結果の構造化（取得件数・保存件数・品質問題・エラー一覧など）。
    - 差分更新・バックフィル・品質チェック統合のための基本骨格を実装（jquants_client と quality モジュール経由の保存/検査を想定）。
    - ETLResult を etl モジュールで再エクスポート。

- 研究（Research） (src/kabusys/research/)
  - factor_research モジュール (src/kabusys/research/factor_research.py)
    - モメンタム（1M/3M/6M リターン・200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日移動売買代金・出来高比）、
      バリュー（PER, ROE）等のファクター計算を実装。DuckDB 上の SQL ウィンドウ関数と Python を併用。
    - 各関数は prices_daily / raw_financials のみ参照し本番発注等にはアクセスしない設計。
  - feature_exploration モジュール (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク関数（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等外部依存を用いず純粋 Python + DuckDB SQL で実装。

- 内部ユーティリティ・挙動
  - DuckDB を中心に SQL を駆使したデータ取得・集計処理を実装（各関数は DuckDB 接続を直接受け取る）。
  - OpenAI 呼び出し部分はモジュール単位で独立実装（_call_openai_api を各モジュールで定義）し、テスト時にモック差替えが容易。
  - 多数のフェイルセーフ（API 失敗時のデフォルト値、DB 書き込み時のトランザクション・ROLLBACK、空パラメータ回避など）を組み込む。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 既知の問題 / 注意事項 (Known issues / Notes)
- src/kabusys/data/pipeline.py の末尾に不完全な実装の痕跡があります（"return date.fro" のような未完了コード断片）。この箇所は実行時エラーとなるため、リリース以前/以後で修正が必要です（_get_max_date の戻り値処理が途中で切れている可能性）。
- OpenAI API 呼び出しは gpt-4o-mini を想定して実装されています。API の仕様変更・SDK バージョン差異により status_code 等の取り扱いが変わる可能性があり、将来的な互換性確認が必要です。
- DuckDB バインドの一部（executemany の空リストなど）について互換性注意（コメントで DuckDB 0.10 を意識した対応あり）。
- news_nlp / regime_detector は外部 API（OpenAI, J-Quants）を利用するため、API キー（OPENAI_API_KEY 等）やネットワーク環境に依存します。API 失敗時はフェイルセーフで継続する設計ですが、部分的なスコア欠損が発生する可能性があります。

### セキュリティ (Security)
- シークレットは環境変数（.env）経由で扱う設計。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
- 但し .env ファイルの読み込み時に注意（ファイル存在時に警告発生・読み取り失敗時には警告を発するが、権限や配置に注意してください）。

---

今後の予定（例）
- pipeline._get_max_date の不完全実装修正。
- 単体テスト・統合テストの追加（OpenAI モック・DuckDB テスト用のフィクスチャ）。
- strategy / execution / monitoring モジュールの具現化（現在は公開 API に名前を用意）。
- ドキュメント（API 使用例・運用手順・環境変数説明）の拡充。

もし CHANGELOG に追加したい改行や日付の扱い、あるいは過去のコミット履歴からより細かく分けたバージョン履歴を希望される場合は、該当する git コミットや更新差分の提示をお願いします。