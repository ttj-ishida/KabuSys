# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。形式は「Keep a Changelog」に準拠しています。  
この CHANGELOG は、提供されたコードベースの内容（モジュール・関数の追加・設計方針など）から推測して作成しています。

## [Unreleased]

### Added
- なし（現時点のパッケージバージョンは 0.1.0。今後の変更はここに追記）

### Changed
- なし

### Fixed
- なし

### Security
- なし

---

## [0.1.0] - 2026-03-31

初回公開リリース。以下の主要機能・モジュールを実装・公開。

### Added
- パッケージ基礎
  - kabusys パッケージ初期化（src/kabusys/__init__.py）を追加。バージョンは 0.1.0。パッケージ公開用に主要サブパッケージを __all__ で定義。

- 設定／環境変数管理
  - 環境変数読み込み・管理モジュール（src/kabusys/config.py）を追加。
    - .env/.env.local の自動読み込み機能（プロジェクトルート自動検出: .git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
    - .env パーサーは export KEY=val 形式、シングル／ダブルクォート（エスケープ処理含む）、およびコメント処理に対応。
    - .env ロード時の上書き制御（override）および OS 環境変数保護（protected set）を実装。
    - Settings クラスを提供し、各種必須値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）・デフォルト値（KABU_API_BASE_URL, DB パス、閾値など）をプロパティ経由で取得可能。
    - 環境変数値バリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。

- AI（自然言語処理）機能
  - ニュース NLP（センチメント）モジュール（src/kabusys/ai/news_nlp.py）を追加。
    - raw_news / news_symbols / ai_scores を対象に、指定時間ウィンドウ（前日15:00 JST〜当日08:30 JST）内の記事を銘柄別に集約して OpenAI（gpt-4o-mini）へ送信し、各銘柄のセンチメントスコアを ai_scores に保存する処理を実装。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/回）、1 銘柄あたりの記事数上限・文字数トリミングによるトークン肥大化対策を実装。
    - JSON Mode を使用し、レスポンスの堅牢なバリデーション（JSON 抽出、results 構造検査、コード照合、数値チェック、スコアクリップ ±1.0）を実装。
    - リトライ戦略：429・ネットワーク断・タイムアウト・5xx を指数バックオフでリトライ（_MAX_RETRIES, _RETRY_BASE_SECONDS）。
    - 部分失敗に備え、DuckDB の executemany の制約を考慮した安全な DELETE → INSERT ロジックを採用し、既存スコアを不必要に削除しない実装。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能に（関数単位で patch 可能）。

  - 市場レジーム判定モジュール（src/kabusys/ai/regime_detector.py）を追加。
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・保存。
    - prices_daily からの MA 計算（ルックアヘッド回避：target_date 未満のデータのみ使用）、raw_news からマクロキーワードフィルタ、OpenAI によるマクロセンチメント算出（gpt-4o-mini、JSON Mode）。
    - API エラー時のフェイルセーフ（macro_sentiment=0.0）、および API 呼び出しのリトライ（RateLimit, Connection, Timeout, 5xx）を実装。
    - 判定結果を market_regime テーブルへ冪等に書き込む（BEGIN / DELETE / INSERT / COMMIT）。

- データ基盤（Data）
  - ETL パイプラインとユーティリティ
    - ETL 用の公開インターフェース（ETLResult の再エクスポート）を追加（src/kabusys/data/etl.py）。
    - ETL パイプライン基礎（src/kabusys/data/pipeline.py）を追加。差分取得・保存・品質チェックフロー、ETLResult データクラス、DuckDB テーブル存在チェックなどを実装。
      - ETLResult: 実行結果の構造化（取得数・保存数・品質問題・エラー列挙）、has_errors / has_quality_errors / to_dict 等のユーティリティを提供。
      - 差分更新のための最小データ日付、バックフィル日数、品質チェックの重み付け方針などを定義。
      - DuckDB 互換性に配慮した実装（executemany の空リスト回避など）。

  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルの夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants クライアントを用いた差分取得・保存（バックフィル/健全性チェック）を行う。
    - 営業日判定ユーティリティ群を実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にカレンダー情報がない場合の曜日ベースフォールバック、DB とフォールバックの一貫性確保、最大探索日数上限（_MAX_SEARCH_DAYS）などの安全設計を採用。
    - API 呼び出し失敗時や保存失敗時の例外ハンドリングとログ出力を実装。

- Research（調査）モジュール
  - src/kabusys/research 配下を追加・公開:
    - factor_research.py:
      - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比）およびバリュー（PER, ROE）を計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
      - DuckDB を用いた SQL 集約＋Python での出力整形。データ不足時の None ハンドリング。
      - 設計方針として prices_daily / raw_financials のみ参照し、実トレード系 API にはアクセスしない安全設計。
    - feature_exploration.py:
      - 将来リターン計算（calc_forward_returns、任意 horizon に対応）、IC（Information Coefficient）計算（calc_ic、Spearman の rank 相関）、統計サマリー（factor_summary）、ランク付けユーティリティ（rank）を提供。
      - pandas 等に依存せず標準ライブラリのみで実装。ランクは同順位の平均ランク（ties の処理に round を利用）で計算。
  - 上記機能を容易に利用できるように re-export を行い、research パッケージから各関数をインポート可能にした。

- 研究／補助モジュール
  - src/kabusys/ai/__init__.py、src/kabusys/research/__init__.py にて主要関数を公開。

### Behavior / Implementation notes（実装上の重要点・設計判断）
- ルックアヘッドバイアス対策:
  - AI スコアリングやレジーム判定では datetime.today() / date.today() を直接参照せず、引数 target_date を用いることで将来情報の漏えいを防止。
  - DB クエリでは target_date 未満（排他）や date = target_date など明確に境界を定義。

- OpenAI 利用:
  - gpt-4o-mini を利用し JSON Mode（response_format={"type": "json_object"}）を想定。
  - API レスポンスの堅牢なパースとバリデーションを実装（不正なレスポンスはスキップしてフェイルセーフ動作）。
  - テストのため、OpenAI 呼び出し箇所を関数単位で patch できるように設計。

- DuckDB 互換・堅牢性:
  - executemany に空リストが渡せない DuckDB バージョン対策、日付値の変換ユーティリティ、テーブル存在チェックなどの互換性処理を追加。
  - DB 書き込みは冪等操作（DELETE then INSERT、BEGIN/COMMIT/ROLLBACK）で行い、部分失敗時の既存データ保護を考慮。

### Fixed
- N/A（初回リリース）

### Security
- 環境変数読み込みにおいて OS 環境変数を保護するメカニズム（protected set）を実装。API キー未設定時は明示的に例外を発生させる（OpenAI キー等）。

### Known limitations / Notes
- OpenAI のレスポンス形式に強く依存しているため、将来的な API 仕様変更に対するメンテナンスが必要。
- ai モジュールはネットワーク/API 呼び出しを行うため、運用時のレート制限やコストに注意が必要。
- 一部の J-Quants 連携（jquants_client の実装）はこのコード断片では参照のみ（fetch/save 呼び出しを期待）。実装／設定が必要。

---

参照: 各モジュールの docstring とコード実装に基づき記載しています。実際のリリースノート作成時はコミット履歴や issue/ticket を参照の上、より詳細な変更点・著者・関連チケットを追記してください。