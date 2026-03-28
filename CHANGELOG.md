# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の規約に従って管理されています。  

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。

### 追加
- パッケージ基盤
  - パッケージ名 kabusys を公開。__version__ = 0.1.0。
  - サブモジュール公開: data, strategy, execution, monitoring（__all__）。

- 設定 / 環境変数管理 (kabusys.config)
  - .env / .env.local ファイルおよび環境変数から設定を読み込む自動ローダを実装。
  - プロジェクトルート検出機能を .git または pyproject.toml を基準に実装。カレントワーキングディレクトリに依存しない探索。
  - .env パーサを実装（コメント行、export 形式、シングル/ダブルクォート、エスケープ処理、インラインコメント処理に対応）。
  - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを実装し、J-Quants / kabu API / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベル等のプロパティを提供。
  - 必須キー未設定時は _require が ValueError を送出する。

- AI 関連（kabusys.ai）
  - ニュースセンチメントスコアリング（news_nlp.score_news）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini, JSON mode）へ送信し ai_scores テーブルへ書き込む機能。
    - バッチ処理（最大 20 銘柄／リクエスト）、1 銘柄あたりの記事数・文字数上限（最大記事数/最大文字数）によるトリムを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数的バックオフでリトライ。その他エラーはスキップ（フェイルセーフ）。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列検査、コード整形、スコア数値検証、±1.0 でクリップ）。
    - 書き込み時は部分失敗で既存データを壊さないよう、対象コードのみ DELETE → INSERT の冪等置換を採用（DuckDB executemany 空リスト回避処理あり）。
    - datetime.today()/date.today() に依存せず、calc_news_window(target_date) でタイムウィンドウを決定（ルックアヘッドバイアス防止）。

  - 市場レジーム判定（ai.regime_detector.score_regime）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成し、日次で市場レジーム（bull / neutral / bear）を判定して market_regime テーブルへ書き込む。
    - マクロニュース抽出はキーワードベース（複数キーワードを定義）で最大 N 件まで取得。
    - OpenAI 呼び出しは独立した内部関数を使用しモジュール結合を避ける設計。
    - API 呼び出し失敗時は macro_sentiment=0.0 のデフォルトで継続（フェイルセーフ）。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。

- データ処理 / ETL（kabusys.data）
  - ETL パイプライン基盤（data.pipeline）
    - ETLResult データクラスを追加。ETL の取得件数／保存件数／品質チェック結果／エラー要約などを格納・辞書変換可能。
    - 差分更新、バックフィル、品質チェックの設計方針を実装（J-Quants クライアントを利用）。
    - DuckDB テーブル存在チェック、最大日付取得ユーティリティ等を実装。

  - カレンダー管理（data.calendar_management）
    - market_calendar テーブルをベースに営業日判定・前後営業日探索・期間内営業日リスト取得・SQ判定などのユーティリティを実装。
    - DB 登録が無い日については曜日ベース（土日非営業）でフォールバックする一貫した挙動。
    - next_trading_day / prev_trading_day は最大探索日数制限（_MAX_SEARCH_DAYS）を設け、発見できない場合は ValueError を返す。
    - calendar_update_job を実装し、J-Quants から差分でカレンダーを取得して保存。バックフィル、健全性チェック（過度に未来の日付はスキップ）を実装。

  - data.etl で pipeline.ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（平均売買代金・出来高比率）およびバリュー（PER, ROE）ファクター計算関数を実装。
    - DuckDB の SQL ウィンドウ関数を活用して効率的に計算。データ不足時の None 扱いを明確化。
  - feature_exploration
    - 将来リターン計算（任意ホライズン）calc_forward_returns を実装（複数ホライズンを 1 クエリで取得）。
    - IC（Information Coefficient）計算（Spearman のランク相関）calc_ic を実装。必要最小レコード数チェックあり。
    - ランク付けユーティリティ rank、統計サマリー factor_summary を実装。
  - re-export: zscore_normalize（kabusys.data.stats から）および主要関数群をパッケージ初期化で公開。

### 設計上の注意・仕様
- ルックアヘッドバイアス防止:
  - AI モジュール・ETL・リサーチの日時ロジックはすべて引数の target_date を基準にし、datetime.today()/date.today() に直接依存しない設計。
- フェイルセーフ:
  - 外部 API（OpenAI, J-Quants 等）呼び出しが失敗した場合、致命的エラーを防ぐためデフォルト値で継続する箇所を設けている（例: マクロセンチメント=0.0、スコア未取得分はスキップ）。
- 冪等性 / 部分失敗保護:
  - DB への書き込みは可能な限り冪等性を保つ（DELETE→INSERT、ON CONFLICT DO UPDATE など）。部分失敗時に既存の有効データを不必要に削除しない実装を採用。
- リトライ戦略:
  - OpenAI 呼び出しについては 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライを実装。試行回数・ベース待機時間などは定数化されている。
- DuckDB 前提:
  - 多くの機能は DuckDB のテーブル（prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_calendar など）を前提としている。テーブル構造・存在チェックを行い、未作成やレコード不足時は安全に動作するように設計。

### 既知の制約 / 将来の改善候補
- OpenAI クライアントは gpt-4o-mini と JSON Mode を利用する想定で実装されているが、モデルや API 仕様の変更に応じた更新が必要。
- ai.score_news の JSON 抽出や LLM レスポンスの堅牢化は行っているが、異常系のカバレッジをさらに拡張する余地あり。
- data.pipeline の ETL は J-Quants クライアントに依存するため、外部 API の仕様変更に追従する必要がある。

---

[Unreleased]: https://example.com/compare/v0.1.0...HEAD
[0.1.0]: https://example.com/releases/tag/v0.1.0