CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このファイルは "Keep a Changelog" の形式に準拠します。

[Unreleased]: https://example.com/kabusys/compare/v0.1.0...HEAD

## [0.1.0] - 2026-03-27

初期リリース。日本株自動売買・データ基盤・リサーチ向けのコア機能を実装しました。
このリリースは以下の主要機能／設計方針と頑健性改善を含みます。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージ外部公開モジュール群の定義（data, strategy, execution, monitoring）。

- 環境設定管理 (src/kabusys/config.py)
  - Settings クラスを導入し、環境変数経由でアプリ設定を取得できるように。
  - .env 自動ロード機能を実装（プロジェクトルート検出: .git / pyproject.toml を起点）。
  - 読み込み優先度: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パーサーの強化: export 形式、シングル/ダブルクォート（エスケープ対応）、コメント処理に対応。
  - 必須環境変数取得ヘルパー (_require) と各種プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL の検証
    - is_live / is_paper / is_dev の補助プロパティ

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - ニュース集約ウィンドウ（JST 前日15:00 ～ 当日08:30）計算関数 calc_news_window。
    - raw_news と news_symbols から銘柄毎に記事を集約し、OpenAI（gpt-4o-mini）の JSON モードで一括スコアリング。
    - チャンク（デフォルト 20 銘柄）単位のバッチ処理、1銘柄あたりの記事・文字数制限（上限記事数、最大文字数）。
    - 再試行ロジック（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）。
    - レスポンス検証とスコアクリッピング（±1.0）、失敗時は安全にスキップ。
    - スコアを書き込む際は部分置換（DELETE → INSERT）で部分失敗時の既存データ保護。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを合成（重み: MA 70% / マクロ 30%）。
    - LLM によるマクロセンチメント評価（gpt-4o-mini, JSON 出力想定）とリトライ処理、API 失敗時は macro_sentiment=0.0 でフォールバック。
    - レジームスコアを -1.0～1.0 にクリップし、閾値に基づき label を決定（bull/neutral/bear）。
    - 結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。

- データプラットフォーム (src/kabusys/data)
  - カレンダー管理 (calendar_management.py)
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日判定 API を実装。
    - DB 登録値がない場合は曜日ベースでフォールバック（週末を非営業日扱い）。
    - calendar_update_job: J-Quants から差分取得 → market_calendar へ冪等保存。バックフィル日数・健全性チェックを実装。
  - ETL パイプライン基盤 (pipeline.py, etl.py)
    - ETLResult データクラスを追加（ETL 実行メトリクス、品質チェック結果、エラー一覧を保持）。
    - 差分取得・最終日取得補助関数（_get_max_date, _table_exists 等）を実装。
    - デフォルトの backfill 日数・calendar lookahead など ETL 設計上の定数を定義。
    - data.etl モジュールで ETLResult を再エクスポート。

- リサーチ（研究）モジュール (src/kabusys/research)
  - factor_research.py
    - モメンタム（1M/3M/6M、ma200 偏差）、ボラティリティ（20 日 ATR）、流動性指標（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）計算関数を実装。
    - DuckDB による SQL 実装で効率的に一括計算し、結果を (date, code) キーの dict リストで返却。
  - feature_exploration.py
    - 将来リターン計算 (calc_forward_returns)、IC（Spearman 相関）計算 (calc_ic)、ランク変換 (rank)、統計サマリ (factor_summary) を実装。
    - pandas 等に依存せず標準ライブラリ + DuckDB で完結する実装。
  - research.__init__ で主要関数を公開（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### 変更 (Changed)
- 設計方針の明確化（全モジュール共通）
  - ルックアヘッドバイアス防止のため、内部実装で datetime.today() / date.today() を直接参照しない設計を採用（スコア関数は target_date 引数を明示）。
  - DuckDB への書き込みはトランザクションで行い、失敗時は ROLLBACK を試み、必要に応じてログを残す。
  - OpenAI 呼び出しは JSON モードを利用し、レスポンスの堅牢な検証を行う（余分な前後テキストが混入するケースにも対応）。

### 修正 / 堅牢化 (Fixed / Robustness)
- OpenAI 呼び出し周り
  - RateLimitError、APIConnectionError、APITimeoutError、5xx 系の APIError に対する再試行（指数バックオフ）を追加。
  - JSON パース失敗・予期しないフィールド・型不一致はワーニングを出してフェールセーフに処理（例外を上位に投げないケースが多い）。
  - レスポンスからのスコア抽出時に型安全化（整数で返されたコードを str に正規化、スコアは float に変換・有限値チェック）。
- データ不足や異常値の処理
  - ma200 等の計算でデータ不足時は中立値（1.0 や None）を使用し、警告ログを出力。
  - 移動平均や ATR の窓サイズ未満のデータがある場合は None を返す旨の扱いを厳格化。
- DB 書き込みの互換性対応
  - DuckDB で executemany に空リストを渡すと失敗する問題に配慮し、空の場合は実行をスキップするガードを追加。
- カレンダ更新の安全装置
  - market_calendar の last_date が極端に将来（_SANITY_MAX_FUTURE_DAYS 超）であれば更新をスキップして警告ログを出す。
  - カレンダ更新はバックフィル期間を設け、API 側の後出し修正を取り込む設計。

### 既知の制約 / 注意事項 (Notes)
- OpenAI API
  - score_news / score_regime は OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError を送出します。
  - LLM 呼び出しは外部ネットワークと課金を伴うため、テスト時は _call_openai_api をモックする想定。
- フェイルセーフ方針
  - LLM や外部 API の障害時には「中立化（0.0）」や「スキップ」を選び、処理継続を優先する（完全停止しない）。
- 日付の取扱い
  - 全ての日付は timezone 非依存の date / naive datetime を使用する方針。JST ↔ UTC の変換は明示的に行う（news ウィンドウ等）。
- 実運用への注意
  - 本リリースはデータ取得・解析・書き込みの基盤を提供しますが、実際の売買実行ロジック（strategy / execution）や運用監視（monitoring）は別モジュールで管理されます。

### セキュリティ (Security)
- 既知の秘匿情報（API トークン等）は環境変数から取得する設計。.env 自動ロード機能を有するが、配布時に .env に秘密を含めない運用が必要です。

---

次バージョンでは以下が想定されます:
- strategy / execution の具体的な売買ロジック実装およびモニタリング・アラート機能の追加
- テストカバレッジ、CI による回帰防止、OpenAI 呼び出しのコスト最適化
- 大量データでのパフォーマンスチューニング（DuckDB クエリの最適化等）

[Unreleased]: https://example.com/kabusys/compare/v0.1.0...HEAD