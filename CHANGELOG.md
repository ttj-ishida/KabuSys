# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン: 0.1.0 (初回リリース)

## [0.1.0] - 2026-04-09

初回リリース。以下の主要機能・設計方針を実装しています。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージ初期化。バージョン情報を公開（__version__ = "0.1.0"）し、主要サブパッケージを __all__ 経由でエクスポート。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイル（および .env.local）自動読み込み機能を実装（OS 環境変数優先、.env.local は上書き可能）。
  - プロジェクトルートの探索は __file__ を基準に .git または pyproject.toml を探索して実行（CWD に依存しない）。
  - 複雑な .env 行パーサを実装（export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理などに対応）。
  - 自動ロード無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / Paper Trading / 監視設定 等の設定プロパティを公開。
  - PAPER_FILL_MODE（instant/partial/never/reject）や KABUSYS_ENV（development/paper_trading/live）などの値検証を実装。
  - PID / kill flag / リソース閾値など監視用設定を用意。

- AI（NLP）モジュール (kabusys.ai)
  - ニュースセンチメント解析モジュール score_news を実装。
    - OpenAI（gpt-4o-mini）を JSON Mode で呼び出し、銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）に基づく記事集約ロジックを実装（calc_news_window）。
    - バッチ処理（銘柄を最大 20 件ずつ）・1銘柄あたり記事数/文字数上限（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）を導入。
    - 再試行（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装。
    - レスポンス検証と堅牢な JSON 抽出ロジックを実装（未知コードの無視、数値パース、±1.0 のクリップ）。
    - テスト用に内部の OpenAI 呼び出し関数を差し替え可能（unittest.mock.patch を想定）。
  - 市場レジーム判定モジュール score_regime を実装。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース（LLM によるマクロセンチメント、重み 30%）を合成して日次で regime_label（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - LLM 呼び出しは gpt-4o-mini、失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフを採用。
    - API 呼び出しに対するリトライ（RateLimit/Connection/Timeout/5xx）と待機ロジックを実装。

- データ基盤 (kabusys.data)
  - マーケットカレンダー管理（calendar_management）を実装。
    - market_calendar を用いた営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を提供。
    - DB 登録値優先・未登録日は曜日ベースのフォールバック、最大探索範囲上限の採用、冪等保存（ON CONFLICT 相当）を設計。
    - 夜間バッチ更新 job（calendar_update_job）を実装し、J-Quants クライアントを利用した差分取得／バックフィル／健全性チェックを備える。
  - ETL パイプラインインターフェースを追加（pipeline.ETLResult を data.etl で再エクスポート）。
  - ETL 実装の骨格（data.pipeline）を実装。
    - 差分更新／バックフィル／品質チェック（quality モジュール）を想定。
    - ETLResult データクラスを実装し、実行結果・品質問題・エラーを集約するユーティリティを提供。
    - DuckDB 利用を前提にした実装（取得・保存・品質レポートフロー）。

- リサーチ / ファクター (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等を計算。
    - calc_value: EPS/ROE を用いた PER / ROE 計算（latest raw_financials を使用）。
    - 計算は DuckDB の SQL と Python の組合せで実装。外部 API 不要（読み取り専用）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）の将来リターンを一括クエリで取得。
    - calc_ic: スピアマン（ランク）相関で IC（Information Coefficient）を計算。最小サンプル数チェック。
    - rank: 同順位は平均ランクで扱うランク関数（丸めで tie の検出漏れを抑制）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリ機能。
  - 研究用ユーティリティは pandas 等に依存せず純標準ライブラリのみで実装。

### 変更 (Changed)
- 設計上の明確化
  - 全ての AI / リサーチ処理で datetime.today() / date.today() を直接参照しない設計を採用（ルックアヘッドバイアス回避）。処理は引数として渡された target_date を基準に行う。
  - DB 書き込みは冪等性を重視（BEGIN / DELETE / INSERT / COMMIT といったトランザクション制御、例外時は ROLLBACK を試行）。
  - DuckDB の互換性考慮（executemany に空リストを渡せない挙動への回避ロジックなど）を実装。

### 修正 (Fixed)
- エラーハンドリングの強化
  - OpenAI API 呼び出しに関する各種例外（RateLimitError、APIConnectionError、APITimeoutError、APIError）を明示的にハンドルし、条件に応じてリトライまたはフォールバックして処理継続するように改善。
  - JSON レスポンスのパース失敗時に適切にログ出力して 0.0 や空結果にフォールバックする安全な動作を導入。

### 既知の制約 / 注意点 (Known Issues / Notes)
- OpenAI API の呼び出しは gpt-4o-mini の JSON Mode を前提にしているため、API レスポンスの仕様変更があるとパース処理の調整が必要になる可能性があります。
- DuckDB のバージョン差異（リスト型バインドや executemany の挙動）を考慮した実装だが、古い/未来のバージョンで追加の互換性対応が必要になる可能性があります。
- strategy / execution / monitoring といった実パッケージ（__all__ に列挙）は初期公開されているが、本リリースでのコード断片は主に data / research / ai 周りに集中しています（将来的な拡張を想定）。

### セキュリティ (Security)
- 機密情報（API キー等）は Settings 経由で環境変数から取得する設計。自動 .env ロードは無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）でテストや CI での誤配置を抑制。

---

今後のリリースでは、strategy / execution / monitoring の具体実装、より詳細な品質チェックモジュールの統合、ユニットテストと CI 設定の追加、ドキュメント拡充を予定しています。