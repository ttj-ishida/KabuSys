# Changelog

すべての注目すべき変更履歴をここに記載します。  
このファイルは Keep a Changelog のフォーマットに準拠します。

## [0.1.0] - 2026-04-09

### 追加
- 初期リリース。パッケージ名: kabusys（日本株自動売買支援ライブラリ）。
- パブリックパッケージ情報
  - バージョン定義: src/kabusys/__init__.py に `__version__ = "0.1.0"` を追加。
  - モジュール公開: data, strategy, execution, monitoring を __all__ に登録。

- 環境設定・ロード機能（src/kabusys/config.py）
  - .env/.env.local ファイルおよび OS 環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロードの無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` でオフ化可能。
  - .env 解析の強化: `export KEY=val` 形式、シングル/ダブルクォート内のエスケープ処理、インラインコメントの取り扱いに対応。
  - 環境設定用 Settings クラスを提供（J-Quants、kabuステーション、LINE、データベース、監視、システム全般の設定プロパティ）。
  - バリデーション: KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE などの入力値検証を実装。
  - パス系設定は Path オブジェクトで返却し expanduser() を適用。

- AI（自然言語処理）機能（src/kabusys/ai）
  - ニュースセンチメントスコアリング（score_news）
    - raw_news / news_symbols から記事を銘柄別に集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのスコアを ai_scores テーブルへ書き込み。
    - JST 時間ウィンドウ（前日15:00〜当日08:30）を厳密に扱う calc_news_window を提供。
    - バッチ処理（最大20銘柄/コール）、記事数/文字数上限、JSON Mode 応答検証、スコア ±1.0 でクリップ。
    - API の 429/タイムアウト/接続断/5xx に対するエクスポネンシャルバックオフリトライ。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results キー/型チェック、未知コードの無視、数値チェック）。
    - API キー注入可能（引数 or 環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出。

  - 市場レジーム判定（score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次でレジーム（bull / neutral / bear）を判定。
    - MA200 の計算は target_date 未満のデータのみを使用してルックアヘッドを防止。
    - マクロニュース抽出はマクロキーワード（日本・米国など）でフィルタし、最大記事数を制限。
    - OpenAI 呼び出しはリトライ戦略とフォールバック（失敗時 macro_sentiment=0.0）を採用。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。

- Data（src/kabusys/data）
  - ETL 用公開 API: ETLResult を再エクスポート（src/kabusys/data/etl.py）。
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py）
    - 差分更新、バックフィル、J-Quants クライアント経由の idempotent 保存、品質チェック収集を想定した ETLResult データクラスを実装。
    - ETLResult は品質問題やエラーメッセージを集約でき、辞書変換メソッドを提供。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を扱う夜間バッチ（calendar_update_job）を実装し、J-Quants からの差分取得と保存（ON CONFLICT を想定）をサポート。
    - 営業日判定・翌営業日/前営業日取得・期間内営業日リスト取得・SQ日判定等のユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データが不完全な場合は曜日ベースのフォールバックを行い、一貫した挙動を保持。
    - 最大探索日数や健全性チェック、バックフィル期間の定義を実装。

- Research（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER、ROE）計算機能を実装。
    - DuckDB を用いた SQL ベースの計算で、prices_daily / raw_financials を参照。
    - データ不足時は None を返す設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク化ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB SQL で実装。
  - 再エクスポート: zscore_normalize（data.stats から）および各種ファクター関数をパッケージ公開。

### 変更（設計・品質）
- ルックアヘッドバイアス防止
  - AI モジュール（score_news, score_regime）や Research/ETL の各関数は datetime.today()/date.today() を直接参照せず、引数で与えた target_date に基づいて処理する設計を採用。
- DuckDB 互換性配慮
  - executemany の空リスト処理回避、list 型バインドの互換性回避（DELETE を個別に実行）など、DuckDB バージョン差分を想定した実装を採用。
- DB 書き込みは可能な限り冪等化（DELETE → INSERT 等）し、部分失敗時に既存データを過度に消さない設計。

### 修正（フェイルセーフ・堅牢化）
- OpenAI 呼び出しの堅牢化
  - 429・接続断・タイムアウト・5xx に対する再試行と指数バックオフを導入。
  - 非 5xx の API エラーやレスポンスパース失敗は例外で中断せずログ警告のうえフォールバック（score_regime: macro_sentiment=0.0、score_news: 該当チャンクはスキップ）する設計に変更。
- .env 読み込みでのファイルアクセス失敗時に警告を出して処理を継続するようにした（テストや権限問題で安全に動作）。

### ドキュメント
- 各モジュールに詳細な docstring を追加。処理フロー、設計方針、引数/戻り値、例外動作、DB テーブル依存などを明記。

### 既知の制限（注意事項）
- OpenAI の API キーは必須（関数引数での注入または環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出する箇所があるため、バッチ実行前にキーの設定が必要。
- 一部モジュール（例: jquants_client, quality, data.stats 等）は外部の実装を前提としている（このリポジトリ内での stub 等は存在しない可能性あり）。
- Paper Trading の挙動は設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）で制御されるが、実運用前に設定確認が必要。

## 将来の予定（メモ）
- strategy / execution / monitoring モジュールの公開 API 実装・テスト拡充。
- 追加の品質チェックやより詳細な監視（アラート閾値の自動調整等）。
- OpenAI 呼び出しのコスト最適化やローカルモデル対応の検討。

----- 

（初回リリース: 機能実装に重点を置いたリリースノートです。必要に応じて各機能の使用例や API リファレンスを別途作成してください。）