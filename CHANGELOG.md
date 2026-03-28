# CHANGELOG

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

なお、本リリースはソースコードからの推測に基づく初期リリース情報です。実際の変更履歴や日付はプロジェクト運用に合わせて調整してください。

## [0.1.0] - 2026-03-28
初回リリース（推定）

### Added
- 基本パッケージ初期化
  - パッケージバージョンを src/kabusys/__init__.py にて `0.1.0` として定義。
  - パッケージの公開モジュール一覧を定義（data, strategy, execution, monitoring）。

- 環境設定・ロード機能（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - .env のパースは export 形式・クォート・エスケープ・コメント処理に対応する堅牢な実装。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - 必須変数取得時に未設定なら明確な ValueError を投げる `_require`。
  - 設定値の検証（KABUSYS_ENV, LOG_LEVEL の有効値チェック）。
  - デフォルト設定（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH など）を提供。

- AI 関連機能（src/kabusys/ai）
  - ニュース NLP スコアリング（news_nlp.py）
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へ送信し、銘柄ごとのセンチメント ai_scores を生成して書き込む。
    - タイムウィンドウ定義（前日 15:00 JST 〜 当日 08:30 JST）を calc_news_window で提供。
    - バッチ処理（最大 20 銘柄/回）、1銘柄あたり記事数・文字数の上限（トリム）をサポート。
    - API レート制限/ネットワーク/5xx に対する指数バックオフのリトライ実装。
    - レスポンスの厳密な JSON 検証とスコアのクリッピング（±1.0）。
    - DuckDB との互換性考慮（executemany の空リスト回避など）。
  - 市場レジーム判定（regime_detector.py）
    - ETF(1321) の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - マクロニュース抽出（キーワードリスト） → OpenAI 評価 → スコア合成のワークフロー。
    - OpenAI API 呼び出しに対するリトライ、フェイルセーフ（API失敗時は macro_sentiment = 0.0）を実装。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
  - 共通設計方針: ルックアヘッドバイアス回避（内部で datetime.today() を参照しない）、テスト容易性のための API 呼び出し差し替えポイントを確保。

- データプラットフォーム機能（src/kabusys/data）
  - ETL パイプライン（pipeline.py / etl.py）
    - 差分取得、保存、品質チェックのための ETLResult データクラスとユーティリティを実装。
    - 最終取得日の算出、バックフィル、品質チェックの収集とエラー集約をサポート。
  - カレンダー管理（calendar_management.py）
    - JPX マーケットカレンダー（market_calendar）の取得/保存用ジョブ（calendar_update_job）。
    - 営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。
    - DB 未取得時の曜日ベースフォールバック（週末は非営業日）や、DB 値優先の一貫した挙動を実装。
    - 最大探索範囲や健全性チェック（将来日付の異常検知等）を導入。
  - jquants_client / quality 等のクライアント抽象化を想定した設計。

- 研究用ユーティリティ（src/kabusys/research）
  - ファクター計算（factor_research.py）
    - Momentum（1M/3M/6M リターン、200日移動平均乖離）、Value（PER, ROE）、Volatility（20日 ATR）等の定量ファクターを DuckDB 上で計算する関数群を実装。
    - データ不足時の None 返却や、営業日スキャン範囲のバッファ処理を含む。
  - 特徴量探索（feature_exploration.py）
    - 将来リターン算出（calc_forward_returns）、IC（calc_ic）、ランク付けユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - 外部依存を極力避け、標準ライブラリのみで完結する設計。

- パッケージ公開インターフェース整理
  - 各サブパッケージの __init__ で主要関数を再エクスポート（例: kabusys.ai.score_news, kabusys.research.*）。

### Changed
- （初回リリースのため該当なし。実装上の設計決定をドキュメント化）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーや各種トークンは必須環境変数として扱われ、未設定時は ValueError を発生させる箇所があるため、運用時は環境変数の安全管理が必要（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等）。

### Notes / Implementation details（重要な設計上の注意）
- OpenAI 呼び出しは JSON Mode（response_format={"type":"json_object"}）を利用し、レスポンスの厳密な JSON パースとバリデーションを行う設計。ただしパースに失敗した場合は明示的にログを残してフェイルセーフで継続する（0.0 やスキップ）。
- DuckDB に対する SQL 実行では互換性・有限の挙動を考慮（例: executemany に空リストを渡さない等）。
- DB 書き込みは基本的にトランザクション（BEGIN/COMMIT/ROLLBACK）で行い、例外時には ROLLBACK を試みる実装。
- 設計方針として、ルックアヘッドバイアス防止のため内部ロジックで現在日時を暗黙に参照しない（呼び出し側が target_date を渡す設計）。

---

今後のリリースでは、実装済み機能の拡張（戦略モジュール、実行ロジック、モニタリング、テストカバレッジ向上、ドキュメント整備等）やセキュリティ改善（機密情報の管理方法）を推奨します。必要であれば、この CHANGELOG を英語版やより細かなコミット単位に分割する補助も対応します。