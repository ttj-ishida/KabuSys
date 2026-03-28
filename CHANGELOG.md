# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期公開（KabuSys: 日本株自動売買システム、バージョン 0.1.0）。
  - src/kabusys/__init__.py にてバージョンと公開モジュールを定義。

- 環境変数・設定管理
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索して検出）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）。
    - .env パーサ実装:
      - コメント・export 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱い。
    - _load_env_file における protected 引数により OS 環境変数の保護を実現。
    - Settings クラスにより型付きプロパティで設定値を取得:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として検証。
      - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値を提供。
      - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）の値検証。
      - is_live / is_paper / is_dev の便宜プロパティ。

- AI（ニュース NLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を用いて銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）へ JSON Mode で送信してセンチメントを算出。
    - UTC/JST を考慮したニュース収集ウィンドウ（前日15:00 JST ～ 当日08:30 JST、DB 比較は UTC naive datetime）。
    - チャンク単位処理（最大 20 銘柄／回）、1 銘柄あたり記事トリム (_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK)。
    - 再試行ポリシー: 429・接続断・タイムアウト・5xx に対する指数バックオフ（デフォルト retry 回数・ベース待機時間を定義）。
    - レスポンスバリデーション実装（JSON 抽出、results 配列、code と score の検証、スコアの ±1.0 クリップ）。
    - DuckDB への書き込みは冪等（DELETE → INSERT）かつ部分失敗時に既存スコアを保護（対象コードのみ削除→挿入）。
    - テスト容易性のため OpenAI 呼び出し関数を patchable に実装。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、news_nlp によるマクロセンチメント（重み 30%）を合成して市場レジームを判定（'bull' / 'neutral' / 'bear'）。
    - ma200_ratio 計算は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを排除。
    - マクロ記事がない場合や API 失敗時は macro_sentiment=0.0 としてフォールバック（フェイルセーフ）。
    - OpenAI 呼び出しの再試行処理とエラーハンドリング（ログ出力、最終的に 0.0 にフォールバック）。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- Research（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタムファクター（1M/3M/6M リターン、ma200 乖離）、ボラティリティ/流動性（20 日 ATR、20 日平均売買代金、出来高比率）、バリューファクター（PER, ROE）を DuckDB の SQL と Python で計算する関数を提供:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - データ不足時は None を返し、安全に扱える設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（任意 horizon、デフォルト [1,5,21]）: calc_forward_returns(conn, target_date, horizons)
    - IC（Spearman の ρ）計算: calc_ic(factor_records, forward_records, factor_col, return_col)
    - ランク変換ユーティリティ（同順位は平均ランク）: rank(values)
    - ファクター統計サマリー（count/mean/std/min/max/median）: factor_summary(records, columns)
    - pandas 等外部ライブラリに依存しない実装。

- Data（データプラットフォーム、ETL、カレンダー）
  - src/kabusys/data/calendar_management.py
    - market_calendar を参照した営業日判定ユーティリティ群:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にデータが無い場合は曜日ベースでフォールバック（土日を非営業日扱い）。
    - next/prev/get の挙動は DB 登録値を優先し、未登録日は曜日フォールバックで一貫性を保つ。
    - calendar_update_job による J-Quants からの差分取得と保存（バックフィル・健全性チェックを含む）。
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETLResult データクラス（ETL の取得数・保存数・品質問題・エラー一覧を格納）、to_dict メソッド搭載。
    - 差分取得・バックフィル、品質チェック（quality モジュール使用）の設計に準拠した ETL パイプラインユーティリティ（公開インターフェースを提供）。
    - DuckDB のテーブル存在チェックや最大日付取得などのヘルパ実装。
  - src/kabusys/data/__init__.py とエクスポート整備（ETLResult の再エクスポートなど）。

- その他
  - DuckDB を主要なローカル分析 DB として利用する設計（多くの関数は DuckDB 接続を引数に取る）。
  - OpenAI（gpt-4o-mini）を JSON Mode（response_format={"type": "json_object"}）で利用する想定。
  - ロギングを全体で利用し、運用時の監査やデバッグに配慮。
  - テスト容易性を考慮した設計（外部 API 呼び出しの差し替えポイント、KABUSYS_DISABLE_AUTO_ENV_LOAD 等）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 現時点で公開されたセキュリティ修正はなし。  
  - 注意: OpenAI API キーや各種トークンは環境変数で管理する想定（Settings にて必須チェック）。.env の取り扱いはファイル読み込み時に protected キーを尊重。

---

注:
- 実装はドキュメント内の設計方針（ルックアヘッドバイアス防止、冪等書き込み、フェイルセーフの採用、外部ライブラリ非依存など）に沿って行われています。  
- 以降のリリースでは、API クライアントの抽象化・テストカバレッジ追加・パフォーマンス最適化（クエリのインデックスや並列処理等）や外部接続の設定の拡張が想定されます。