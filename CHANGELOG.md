# CHANGELOG

すべての注記は Keep a Changelog の形式に準拠しています。セマンティック バージョニングを使用しています。

なお、本リリースではパッケージバージョンは 0.1.0 です（src/kabusys/__init__.py の __version__ を参照）。

## [Unreleased]

- 現状なし。

---

## [0.1.0] - 2026-03-31

初回公開リリース。日本株のデータ取得・処理・リサーチ・AI スコアリング・市場レジーム判定・カレンダー管理・ETL パイプライン等を含む基本機能を提供します。

### 追加（Added）
- パッケージの基本構成を追加
  - モジュール: kabusys.data, kabusys.research, kabusys.ai, kabusys.config などの基本モジュール群を追加。

- 環境設定/ロード機能（kabusys.config）
  - プロジェクトルート検出: .git または pyproject.toml を起点に自動でプロジェクトルートを検出する機能を実装。
  - .env ファイル自動ロード: OS 環境変数 > .env.local > .env の順でロード。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理をサポートする堅牢なパーサを実装。
  - 上書き保護: OS 環境変数を保護する protected 機構（.env の上書き制御）。
  - Settings クラスを提供（settings オブジェクト経由で利用）
    - J-Quants / kabuステーション / Slack / DB パス（DuckDB/SQLite）などの設定プロパティ
    - KABUSYS_ENV のバリデーション（development/paper_trading/live）
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ユーティリティ

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols からニュースを銘柄別に集約し、OpenAI（gpt-4o-mini）で銘柄ごとに -1.0〜1.0 のセンチメントを評価して ai_scores に書き込む機能を実装。
  - 処理特徴:
    - JST ベースのニュース窓（前日 15:00 JST 〜 当日 08:30 JST）を正確に計算する calc_news_window を実装。
    - 1銘柄あたり最大記事数・最大文字数でトリム（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - バッチ送信（1リクエストあたり最大 20 銘柄）で効率的に API を利用。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - API レスポンスのバリデーション（JSON 解析、"results" 配列、コード整合性、スコア数値化、±1.0 クリップ）。
    - 部分失敗時に既存スコアを保護するため、置換時は対象コードに限定した DELETE → INSERT を実行（DuckDB executemany の互換性配慮あり）。
    - テストのため _call_openai_api を patch 可能に設計。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（Nikkei225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定して market_regime テーブルへ冪等書き込みする機能を実装。
  - 処理特徴:
    - MA200 乖離の計算（ルックアヘッドバイアス防止のため target_date 未満のデータのみ使用）。
    - マクロキーワードで raw_news をフィルタしてタイトルを取得。
    - OpenAI（gpt-4o-mini）によりマクロセンチメントを評価。API 障害時はフェイルセーフとして macro_sentiment=0.0 を使用。
    - レジームスコアを合成し閾値により label を決定（閾値は定数で管理）。
    - DB 書き込み時は BEGIN/DELETE/INSERT/COMMIT の冪等操作、失敗時は ROLLBACK 実行（ROLLBACK 自体の失敗はログに記録）。

- リサーチ用ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。データ不足時は None を返す設計。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播を明示的に扱う。
    - calc_value: raw_financials から直近の財務データを取得して PER/ROE を計算（EPS が 0/欠損の場合は None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。horizons の検証（正の整数かつ <=252）。
    - calc_ic: ファクターと将来リターンのスピアマン順位相関（IC）を計算。3 銘柄未満は None。
    - rank, factor_summary: ランク変換（同順位は平均ランク）および基本統計量（count/mean/std/min/max/median）を算出。
  - 設計方針: DuckDB への SQL クエリと最小の Python ロジックで実装、外部ライブラリ非依存、ルックアヘッドバイアス回避を重視。

- データ / カレンダー管理（kabusys.data.calendar_management）
  - market_calendar に基づく営業日判定: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
  - フォールバック挙動: market_calendar が未取得もしくは該当日が未登録の場合は曜日ベース（土日除外）で一貫した挙動を提供。
  - calendar_update_job: J-Quants API から差分で市場カレンダーを取得し market_calendar テーブルへ冪等保存。バックフィル／健全性チェック（未来日数閾値）を実装。
  - テーブル存在チェックや日付変換ユーティリティを提供。

- ETL パイプライン（kabusys.data.pipeline / etl）
  - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。
    - ETL 実行の取得件数・保存件数・品質問題・エラー一覧・ヘルパーメソッド（has_errors 等）を包含。
  - 差分取得・最終日取得ユーティリティ: _get_max_date 等、テーブル存在チェックを実装。
  - ETL 処理設計: 差分更新、バックフィル、品質チェックの収集方針（Fail-Fast ではなく呼び出し元で判断）を反映。

### 変更（Changed）
- （初回リリースのため該当なし）

### 修正（Fixed）
- （初回リリースのため該当なし）

### 削除（Removed）
- （初回リリースのため該当なし）

### セキュリティ（Security）
- API キーの取り扱い:
  - OpenAI の呼び出しは api_key 引数で注入可能。引数未指定の場合は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を発生させて明示。
  - .env 自動ロード時に OS 環境変数の上書きを保護する仕組みを導入。

### 重要な設計上の注意事項（Notes）
- ルックアヘッドバイアス対策: 多くの関数（news/regime/factors/forward returns 等）は datetime.today() や date.today() を内部で参照せず、呼び出し側から target_date を渡す設計です。運用時は target_date の扱いに注意してください。
- OpenAI 呼び出し: gpt-4o-mini を利用する前提で JSON mode を期待した設計。API レスポンスが期待形でない場合はフォールバック（スコア 0.0 やスキップ）する仕様です。
- DuckDB 互換性: executemany に空リストを与えると失敗するバージョンがあるため、空チェックを行った上で executemany を呼び出す実装になっています。
- DB 書き込みは冪等操作（DELETE → INSERT）を基本とし、失敗時は ROLLBACK を行います。ROLLBACK 自体が失敗する可能性はログに出力して無理に抑えません。

---

今後の予定（例）
- モデルの選択肢やプロンプト改良によるセンチメント精度向上
- ETL の並列化やパフォーマンス改善
- 監視・メトリクス収集機能の追加

もし CHANGELOG に反映してほしい追加情報・リリース日付の調整・カテゴリ分けの変更があれば教えてください。