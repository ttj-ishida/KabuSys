Keep a Changelog
================

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

注: この CHANGELOG は与えられたコードベースからの推測に基づいて作成しています。

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージ基礎
  - パッケージ初期化 (kabusys.__init__) とバージョン定義: __version__ = "0.1.0"。
  - 公開モジュール群の定義: data, strategy, execution, monitoring。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行い、CWD に依存しない設計。
    - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env のパーサは次の機能をサポート:
    - コメント行・空行の無視、export KEY=VAL 形式の対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - クォートなしの値でのインラインコメント判定（直前がスペース/タブの場合のみ）。
  - 必須環境変数取得用の _require() と Settings クラスを提供（J-Quants / kabu API / Slack / DB / 監視 / システム設定）。
  - 設定値検証:
    - KABUSYS_ENV の許容値 (development, paper_trading, live) のチェック。
    - LOG_LEVEL の許容値 (DEBUG, INFO, WARNING, ERROR, CRITICAL) のチェック。
  - 監視用しきい値（CPU / メモリ / ディスク）や PID ファイルパスの取得プロパティを提供。

- AI モジュール (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - raw_news / news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode を用いセンチメント（ai_score）を算出、ai_scores テーブルへ書き込み。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリ実行）。
    - バッチ処理: 最大 20 銘柄/コール、記事は銘柄毎に最大 10 件・3000 文字でトリム。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフ再試行（リトライ上限指定）。
    - レスポンスの厳格バリデーション（JSON 抽出、results リスト、各要素の code/score 検証、スコアの数値化と ±1.0 クリップ）。
    - 部分成功に配慮した DB 操作（取得できたコードのみ DELETE → INSERT、DuckDB の executemany 空リスト制約に配慮）。
    - ルックアヘッドバイアスを避けるため内部で datetime.today/date.today を参照しない設計。
    - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能に実装（_call_openai_api を patch 可能）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - マクロニュースは news_nlp.calc_news_window に基づくウィンドウからマクロキーワードで抽出。
    - OpenAI 呼び出しは gpt-4o-mini、JSON レスポンスを期待。API エラー時は macro_sentiment=0.0 のフェイルセーフ。
    - レジームスコアは clip して判定閾値を用いたラベル付け。
    - 結果は market_regime テーブルへ冪等的に（BEGIN / DELETE / INSERT / COMMIT）書き込み。
    - API 呼び出しについてリトライ戦略（429・ネットワーク・タイムアウト・5xx）を実装。

- データプラットフォーム (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを参照した営業日判定ロジックを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にカレンダーがない場合は曜日ベース（週末除外）でフォールバック。
    - next/prev/get_trading_days は DB 値優先・未登録日は曜日フォールバックで一貫した結果を返す。
    - calendar_update_job を実装（J-Quants API で差分取得・バックフィル・健全性チェック・保存）。
  - ETL パイプライン (kabusys.data.pipeline / etl)
    - ETLResult データクラスを公開（取得件数、保存件数、品質問題、エラーなどを含む）。
    - 差分更新・バックフィル・品質チェックを想定したユーティリティと設計（jquants_client, quality と連携）。
    - DuckDB ベースのテーブル存在/最終日取得ユーティリティを実装。
    - 初回ロードの最小日付、カレンダー先読み日数、デフォルトバックフィル日数などの定数を定義。
    - ETL の操作は idempotent（既存レコードは上書き等）を想定した設計。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB 上で計算する関数を実装。
    - データ不足時の None 返却や集計ウィンドウの扱いに配慮。
    - 結果は (date, code) をキーとする dict のリストで返却。
  - feature_exploration:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）を提供。
    - Spearman ランク相関（IC）を計算する calc_ic、ランク化ユーティリティ rank、統計サマリー factor_summary を実装。
    - Pandas 等の外部依存なしで実装。欠損・有限性チェックや最小サンプル数チェックを行う。

- その他
  - DuckDB を用いた SQL クエリ中心の実装。DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。
  - 多くの箇所で「ルックアヘッドバイアス防止」を明示した設計（date.now を直接参照しない等）。
  - OpenAI API 呼び出しは専用ラッパー関数を持ち、ユニットテストで差し替え可能に実装。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Deprecated
- 初期リリースのため該当なし。

Removed
- 初期リリースのため該当なし。

Security
- 初期リリースのため該当なし。

既知の制約・設計上の注意事項
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY に依存。未設定時は ValueError を送出する実装。
- DuckDB の executemany に空リストを渡せない制約を考慮した実装（空チェックあり）。
- 一部 OpenAI SDK の例外型／属性差異に耐性を持たせる処理あり（status_code の安全な取得等）。
- .env パーサは多くの一般的ケースを扱うが、極端に複雑なシェル展開や subshell 等はサポート対象外。
- calendar_update_job 等で外部 API（J-Quants）呼び出し失敗時はログを残して 0 を返すフェイルセーフな実装。

今後の作業（提案）
- 単体テスト・統合テストの追加（OpenAI / J-Quants 呼び出しをモックするテスト）。
- CI での環境変数の取り扱い検証と .env 自動ロードの挙動テスト。
- エラーメトリクス / 再試行統計の監視導入。