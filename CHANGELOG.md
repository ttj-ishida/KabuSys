# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [0.1.0] - 2026-04-04

### 追加 (Added)
- パッケージ初期リリース: kabusys
  - パッケージメタ情報: バージョン 0.1.0 を設定 (src/kabusys/__init__.py)。
  - パブリックサブパッケージ: data, strategy, execution, monitoring を __all__ に公開。

- 環境変数 / 設定管理モジュールを実装 (src/kabusys/config.py)
  - .env 自動ロード実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - 読み込み順序: OS 環境 > .env.local（上書き）> .env（未設定のみ）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
  - .env パーサー:
    - export PREFIX のサポート（`export KEY=val`）。
    - シングル／ダブルクォート内のバックスラッシュエスケープ対応。
    - クォートなしでのインラインコメント（#）認識（直前が空白/タブの場合にコメントとみなす）。
  - 保護されたキーセット(protected)による OS 環境変数の上書き防止。
  - Settings クラスを提供し、様々な設定値をプロパティ経由で取得:
    - J-Quants, kabu API, LINE, データベースパス（DuckDB/SQLite）、監視用ファイルパス、リソース閾値、環境/ログレベルのバリデーション等。
    - 必須項目未設定時は ValueError を送出（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - KABUSYS_ENV, LOG_LEVEL に対する許容値チェック。

- ニュースNLP と市場レジーム判定（AI）モジュールを実装 (src/kabusys/ai)
  - news_nlp.score_news:
    - raw_news / news_symbols を元に、ターゲットデートに対するニュースウィンドウを計算（JST -> UTC 変換）。
    - 銘柄ごとに最新記事を集約し、1 銘柄あたりの文字数・件数制限を適用。
    - バッチ（最大 20 銘柄/リクエスト）で OpenAI（gpt-4o-mini）へ JSON Mode で投げ、結果を ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。その他エラーはフェイルセーフでスキップ。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code/score 型チェック、未知コード無視、数値チェック）と ±1.0 でクリップ。
    - テストしやすさのため OpenAI 呼び出しは _call_openai_api で抽象化（unittest.mock.patch で差し替え可能）。
  - regime_detector.score_regime:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離 (ma200_ratio) と、マクロニュース（LLM によるセンチメント）を重み付け合成（ma 70% / macro 30%）してレジーム（bull/neutral/bear）を判定。
    - マクロキーワードフィルタで raw_news のタイトルを抽出し、OpenAI で macro_sentiment を評価（JSON レスポンス期待）。
    - API 障害時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - 計算結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書込失敗時は ROLLBACK を試行して例外を伝播。

- データプラットフォーム関連モジュールを実装 (src/kabusys/data)
  - calendar_management:
    - market_calendar の有無に応じた営業日判定 API を提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB に登録がある場合は DB 値優先、未登録日は土日フォールバックで一貫した判定を行う設計。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存。バックフィル、健全性チェック（過度に未来日が登録されている場合のスキップ）を実装。
  - pipeline / ETL:
    - ETLResult データクラスを公開（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py 経由で再エクスポート）。
    - ETLResult は取得件数・保存件数・品質問題・エラーの集約を提供し、to_dict() でシリアライズ可能。
    - 差分更新・バックフィル・品質チェック設計に基づく ETL 基盤。

- 研究（Research）モジュールを実装 (src/kabusys/research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離 (ma200_dev) を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。必要行数未満は None。
    - calc_value: raw_financials の最新レコードと価格を組み合わせて PER・ROE を算出（EPS=0/欠損時は None）。
    - 設計方針: DuckDB の SQL ウィンドウ関数を活用し、外部 API へはアクセスしない。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons 入力検証あり。
    - calc_ic: ファクターと将来リターンのスピアマン（ランク）相関を計算（有効レコードが 3 未満の場合 None）。
    - rank / factor_summary: ランク付けとファクター統計量（count/mean/std/min/max/median）を算出。外部ライブラリに依存せず実装。

- テストしやすい設計上の抽象化
  - OpenAI 呼び出し関数をモジュール内のラッパーで分離し、ユニットテスト時に差し替え可能にしている (news_nlp._call_openai_api / regime_detector._call_openai_api)。
  - DuckDB への executemany 空リスト対応など、バージョン互換性対策を明示的に実装。

### 変更 (Changed)
- 初版リリースのため該当なし。

### 修正 (Fixed)
- 初版リリースのため該当なし。

### 非推奨 (Deprecated)
- 初版リリースのため該当なし。

### 削除 (Removed)
- 初版リリースのため該当なし。

### セキュリティ (Security)
- 初版リリースのため該当なし。

---

## 設計上の重要な注意点 / 補足
- ルックアヘッドバイアス防止:
  - 各種処理（score_news, score_regime, factor 計算等）は datetime.today() / date.today() を内部参照せず、明示的な target_date を受け取り、DB クエリでも target_date 未満を厳密に扱う設計になっています。
- フェイルセーフ指向:
  - 外部 API（OpenAI / J-Quants 等）の失敗は基本的に致命エラーとせず、可能な限りフォールバック（ゼロ中立スコア、スキップ、ログ記録）して処理継続する方針です。
- DuckDB 互換性:
  - executemany に対する空リスト回避やリストバインドの代替実装など、DuckDB バージョン間の差異に対する互換性考慮が盛り込まれています。
- ID または API キー:
  - OpenAI の利用は api_key 引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照。未設定の場合は ValueError を送出して明示的にエラー検知する。

---

（このファイルはリリース時に自動生成または手動で更新してください。以降の変更は新しいバージョンセクションを追加して記録してください。）