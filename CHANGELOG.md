# Changelog

すべての注目すべき変更をここに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。  

- リリース日付はパッケージ内の __version__ に基づき作成しています。
- 本ファイルはコードベースから推測して自動生成しています。実装の記述に基づく要約・設計上の注意点を含みます。

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期リリース（kabusys 0.1.0）
  - パッケージの公開APIとして data / strategy / execution / monitoring をエクスポート。
  - バージョン: 0.1.0

- 環境設定管理モジュール（kabusys.config）
  - .env ファイルおよび環境変数から設定値を読み込む自動ローダーを実装。
    - 自動ロードの優先順: OS環境変数 > .env.local > .env
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索して行うため、CWD に依存しない。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）。
    - .env 読み込み時に OS 環境変数（読み込み時のキー集合）を保護する機構あり（.env.local は override=True）。
  - .env のパーサを独自実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理（クォート外での # 処理を考慮）。
  - 必須設定の取得ヘルパー _require を提供（未設定時は ValueError を送出）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等をプロパティで取得。
    - 必須環境変数（例）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - duckdb / sqlite の既定パスを提供（data/kabusys.duckdb, data/monitoring.db）
    - KABUSYS_ENV 値検証（development, paper_trading, live）
    - LOG_LEVEL 検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）

- AI モジュール（kabusys.ai）
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出。
    - タイムウィンドウ（JST基準）計算ユーティリティ calc_news_window を提供（前日15:00〜当日08:30 JST を対象）。
    - バッチ処理: 最大 20 銘柄/呼び出し、1銘柄あたり最大 10 記事、最大 3000 文字（トリム）等のトークン肥大対策。
    - JSON Mode 応答を検証・抽出するバリデーションロジックを実装（レスポンス復元処理あり）。
    - スコアは ±1.0 にクリップし、書き込みは ai_scores テーブルへ「DELETE（対象コード）→ INSERT」の手順で部分失敗耐性を確保。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
    - OpenAI 呼び出しは差し替え可能（テスト用に _call_openai_api を patch できる設計）。
    - API キー未指定時は ValueError を送出。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して daily レジームを判定（bull/neutral/bear）。
    - ma200_ratio 計算は target_date 未満のデータのみ使用（ルックアヘッドバイアスを回避）。
    - マクロニュースは raw_news をキーワードでフィルタして取得（最大 20 件）。
    - OpenAI 呼び出しは gpt-4o-mini、JSON モードで macro_sentiment を取得。API 失敗時は macro_sentiment=0.0 とするフェイルセーフ。
    - 合成スコアは clip され、閾値によりラベル判定。結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - OpenAI クライアントの注入（api_key 引数）に対応。

- Data モジュール（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定ユーティリティ群を提供:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - DB 登録がない場合は曜日ベース（平日＝営業日）のフォールバックを採用。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィル（直近 _BACKFILL_DAYS）と健全性チェック（将来日付の異常検出）を実装。
  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - ETLResult データクラスを公開（取得数・保存数・品質チェック結果・エラー一覧を格納）。
    - 差分取得、idempotent 保存（jquants_client の save_*）、品質チェック（quality モジュール）を想定した設計。
    - テーブル最大日付取得や存在確認ユーティリティを実装。
    - デフォルトの backfillDays 等の定義（_DEFAULT_BACKFILL_DAYS=3 等）。
    - DuckDB の executemany の互換性に配慮した実装（空リストチェック等）。
  - jquants_client 経由でのデータ取得/保存を前提とした設計（関数呼び出しポイントあり）。

- Research モジュール（kabusys.research）
  - factor_research: calc_momentum / calc_volatility / calc_value を実装
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - ボラティリティ: 20 日 ATR、ATR/price、20 日平均売買代金、出来高比率（データ不足時は None）。
    - バリュー: raw_financials から直近財務データを取得して PER / ROE を計算。
    - DuckDB 上の SQL とウィンドウ関数を活用して高速に計算。
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank を実装
    - 将来リターンを一度のクエリで取得する効率的な実装（horizons 検証あり）。
    - IC（Spearman のランク相関）を実装（有効レコード数が 3 未満なら None を返す）。
    - ファクター統計サマリー（count, mean, std, min, max, median）を提供。
  - データ処理は標準ライブラリ + DuckDB のみで実装（pandas 等に依存しない）。

- その他ユーティリティ
  - kabusys.data.etl から ETLResult を再エクスポート。
  - テスト容易性を考慮した補助ポイント（OpenAI 呼び出しの patchable 関数など）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーや各種世代トークンは環境変数で管理する設計。
- .env 自動読み込み時に既存の OS 環境変数を保護する仕組みを導入（.env.local は上書きするが OS 環境変数は保護）。

### Known limitations / Notes
- OpenAI (gpt-4o-mini) への依存:
  - API キー未指定時は ValueError を送出する箇所がある（news_nlp.score_news, regime_detector.score_regime）。
  - API 呼び出し失敗時は基本的にフェイルセーフでスコアを 0.0 とするか、そのチャンクをスキップする実装で、処理全体が継続する設計。ただし部分的にスコア欠落が発生する可能性あり。
- DuckDB バージョン依存の注意点:
  - executemany に空リストが渡せない点など（コード内で明示的に回避）。
- ルックアヘッドバイアス回避:
  - 各種スコアリング・集計処理は datetime.today()/date.today() を直接参照せず、target_date に依存する形で実装。
- 一部関数は DB スキーマ（prices_daily / raw_news / ai_scores / market_regime / market_calendar / raw_financials / news_symbols 等）に依存するため、正しいスキーマ／データが必要。
- 一部の内部関数（例: _adjust_to_trading_day）はコード断片ベースでの実装が進行中である場合があり、完全な実装はリポジトリ全体での確認を推奨。

---

今後のリリースでは、安定化（エラーハンドリング）、追加のファクタやストラテジー、実運用向けの監視・通知機能の拡充が予定されます。必要であれば上記の項目を英語版CHANGELOGやリリースノート形式でも出力できます。