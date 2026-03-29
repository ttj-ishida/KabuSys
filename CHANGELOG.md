# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベース（初期リリース）の機能・設計上の重要な点をコード内容から推測して記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース。システム全体のコア機能（データ ETL / カレンダー管理 / ファクター計算 / AI ニュース解析 / 市場レジーム判定 / 設定管理）を提供します。

### Added
- パッケージのバージョンと公開モジュール
  - パッケージメタ情報を追加: kabusys v0.1.0（src/kabusys/__init__.py）。
  - 外部公開モジュール: data, strategy, execution, monitoring。

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml から探索）。
  - ロード順: OS環境 > .env.local > .env。環境変数保護（OS環境変数を上書きしない）をサポート。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途）。
  - .env パーサを実装: export 構文対応、クォート内のエスケープ、インラインコメント処理など。
  - Settings クラスを導入し、アプリケーション向け設定プロパティを提供（J-Quants, kabu API, Slack, DB パス, 環境種別・ログレベル判定など）。
  - 必須環境変数未設定時は ValueError を送出する _require の実装。

- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols を読み、銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）へ送信しセンチメントを算出して ai_scores テーブルへ書き込む機能を実装（score_news）。
  - ニュース収集ウィンドウの計算 (前日 15:00 JST ～ 当日 08:30 JST、UTC へ変換) を提供（calc_news_window）。
  - バッチ処理（1回最大20銘柄）、記事数・文字数制限（最大記事数・最大文字数）によるトリム処理を実装。
  - OpenAI 呼び出しは JSON モードで行い、レスポンスのバリデーション・スコアクリップ（±1.0）を実施。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対し指数的バックオフでリトライ。その他エラーはフェイルセーフでスキップ。
  - DuckDB への冪等書き込み（DELETE → INSERT、トランザクション、ROLLBACK 対応）を実装。
  - テスト容易性のため _call_openai_api を patch 可能に設計。

- AI 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225連動型）の 200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定する機能を実装（score_regime）。
  - マクロニュース抽出用キーワードリスト、OpenAI 呼び出し（gpt-4o-mini）および再試行ロジックを実装。API失敗時は macro_sentiment=0.0 で継続するフェイルセーフ。
  - DuckDB からのデータ取得はルックアヘッドバイアスを防ぐ形で target_date 未満のデータのみを参照。
  - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、ROLLBACK 対応）を実装。

- データ ETL / パイプライン基盤（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
  - ETLResult データクラスを導入（ETL 実行結果の集約、品質問題・エラー一覧の保持、辞書変換機能）。
  - 差分更新のためのユーティリティ（テーブル存在確認、最大日付取得等）を実装。
  - jquants_client と quality モジュールを利用する設計（外部 API 取得 → 保存 → 品質チェック のフローを想定）。
  - デフォルトのバックフィル、カレンダー先読みなど ETL 運用に必要な設計方針を反映。

- マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
  - market_calendar テーブルを使った営業日判定ロジックを実装:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
  - DB データがない/未登録日のフォールバックとして曜日ベース（平日を営業日）判定を実装。
  - calendar_update_job による J-Quants からの差分取得／保存（バックフィル、健全性チェック、ON CONFLICT 想定の保存）を実装。
  - 最大探索日数の上限設定により無限ループを回避する堅牢な設計。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - ファクター計算モジュールを実装:
    - calc_momentum: 1M/3M/6M リターンおよび 200 日 MA 乖離（ma200_dev）。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等。
    - calc_value: 最新財務情報（raw_financials）と株価を組み合わせて PER / ROE を計算。
  - 特徴量探索モジュールを実装:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）先の将来リターンをまとめて取得。
    - calc_ic: スピアマン（ランク）相関による IC 計算（3件未満で None）。
    - rank: 同順位を平均ランクで扱うランク付けユーティリティ（小数丸めで ties の検出を安定化）。
    - factor_summary: 基本統計（count/mean/std/min/max/median）を計算。
  - 結果は list[dict] 形式で返却し、DuckDB の SQL と組み合わせた処理を行う。

- テスト・デバッグに配慮した実装
  - OpenAI 呼び出しの箇所は内部関数を patch できるように実装しユニットテストで差し替え可能。
  - DuckDB 用の executemany の空リスト制約（互換性）を考慮した条件分岐を実装。

### Changed
- 初回リリースのため該当なし（新規導入）。

### Fixed
- 初回リリースのため該当なし（新規導入）。

### Security
- API キー取得は明示的に引数で注入可能（api_key）か、環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出して安全に失敗する設計。

### Notes / Implementation details
- ルックアヘッドバイアス対策:
  - AI・研究モジュールは内部で datetime.today()/date.today() を参照せず、caller が target_date を渡す設計。
  - DB クエリでも target_date 未満（または指定ウィンドウ）でデータを取得する実装になっている。
- フェイルセーフ設計:
  - OpenAI API の失敗はスコアに中立値（0.0）を使うかスキップして処理を継続する設計。
  - DB 書き込みはトランザクションで保護し、ROLLBACK を試行してから例外を伝播。
- DuckDB 互換性考慮:
  - executemany に空リストを渡さないガードや、ANY バインドの代わりに個別 DELETE の executemany を使用する等、DuckDB のバージョン差異を考慮。

---

今後のリリースでは以下のような改善が想定されます（例）:
- より細かいログ出力・メトリクス収集の追加
- OpenAI 呼び出しの抽象化と複数モデル対応
- 追加ファクター（PBR、配当利回り等）の実装
- jquants_client / kabu 関連の具体的な API 実装と統合テストの追加

もし CHANGELOG に追記してほしい点（より詳細な差分説明、個別ファイルごとの変更リスト等）があれば教えてください。