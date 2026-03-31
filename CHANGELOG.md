# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-31
初回リリース。

### Added
- パッケージ全体
  - パッケージ名: `kabusys`、バージョン 0.1.0 を定義（src/kabusys/__init__.py）。
  - パッケージは主要サブパッケージを公開: data, strategy, execution, monitoring。

- 設定／環境変数管理（src/kabusys/config.py）
  - Settings クラスを導入し、アプリ設定を環境変数経由で取得。
  - .env 自動読み込み機能（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは export プレフィックス、クォート（エスケープ対応）、インラインコメント（スペース前の # をコメント扱い）に対応。
  - 既存 OS 環境変数を保護する仕組み（protected set）。
  - 必須変数取得用ヘルパ `_require`。
  - 提供される設定プロパティ:
    - J-Quants: JQUANTS_REFRESH_TOKEN（必須）
    - kabuステーション API: KABU_API_PASSWORD（必須）、KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN（必須）、SLACK_CHANNEL_ID（必須）
    - DB パス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - 監視: PID_FILE_PATH、CPU/MEMORY/DISK の閾値（パーセンテージ）
    - システム: KABUSYS_ENV（development/paper_trading/live のバリデーション）、LOG_LEVEL（DEBUG/INFO/... のバリデーション）、is_live/is_paper/is_dev ヘルパ

- AI モジュール（src/kabusys/ai）
  - ニュース NLP スコアリング: `score_news(conn, target_date, api_key=None)` を提供（src/kabusys/ai/news_nlp.py）。
    - タイムウィンドウ計算（JST基準 → DBは UTC 想定）を実装（calc_news_window）。
    - 銘柄別に記事を集約し、1チャンク最大 20 銘柄で OpenAI（gpt-4o-mini）へ送信。
    - 1 銘柄当たりの記事数・文字数上限を設定してトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - JSON Mode を利用した応答パース、冗長テキスト混入時は最外の {} を抽出して回復を試みる。
    - レスポンス検証（results リスト、code/score の存在、コード照合、数値変換、有限値チェック）。
    - スコアを ±1.0 にクリップ。
    - エラー・レート制限・ネットワーク障害・5xx は指数バックオフでリトライ。最終的に失敗したチャンクはスキップして継続。
    - 書き込みは冪等的に実行（DELETE 個別実行 → INSERT、DuckDB の executemany 空チェックを考慮）。
    - API 呼び出しはテスト差し替え可能な内部関数に分離（_call_openai_api）。
  - 市場レジーム判定: `score_regime(conn, target_date, api_key=None)` を提供（src/kabusys/ai/regime_detector.py）。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成してレジーム（bull/neutral/bear）を決定。
    - マクロニュースは keywords リストでフィルタし、最大 20 件まで LLM に投げる。
    - API 失敗時は macro_sentiment=0.0 のフェイルセーフを採用。
    - レジーム計算で得られた結果を market_regime テーブルへトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等保存。
    - OpenAI 呼び出しはモジュール内で独立実装され、テスト時に差し替え可能。
    - 詳細: リトライ方針、500 系の扱い、レスポンス JSON パースの堅牢化。

- データプラットフォーム（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - market_calendar テーブルが存在しない場合は曜日ベースでのフォールバック（土日を非営業日扱い）。
    - next/prev/get は DB 登録日を優先し、未登録日は曜日フォールバックで一貫性を保つ。
    - 夜間バッチ: `calendar_update_job(conn, lookahead_days=90)` を実装。J-Quants から差分取得 → jq.save_market_calendar で保存。バックフィル / 健全性チェックあり。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを導入（ETL の集計結果、品質問題、エラー列挙を含む）。
    - 差分更新、backfill、品質チェックの設計方針を実装（jquants_client 経由での取得・保存を想定）。
    - ETLResult.to_dict() は quality_issues を辞書に変換して出力。
    - etl.py は ETLResult を再エクスポート。

- Research（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）を計算。データ不足時は None。
    - calc_volatility: 20 日 ATR、ATR 比率（atr_pct）、20 日平均売買代金、出来高比率を計算。データ不足時は None。
    - calc_value: 最新財務データ（raw_financials）と株価を組み合わせて PER/ROE を算出。
    - DuckDB を使ったウィンドウ関数ベースの実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 任意ホライズンの将来リターン（デフォルト [1,5,21]）を計算。horizons のバリデーションあり。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算。有効レコードが 3 件未満なら None。
    - rank: 同順位は平均ランクとするランキング関数（丸めによる ties の扱いを調整）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - research パッケージは便利関数を __all__ で再エクスポート。

- テスト・運用を考慮した設計上の特徴（ドキュメントに明記）
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を内部ロジックで直接参照しない設計（全関数で target_date を明示）。
  - DuckDB との互換性配慮（executemany の空リスト回避、日付型変換ユーティリティなど）。
  - OpenAI / 外部 API 呼び出しに対する堅牢なリトライとフォールバック（ゼロ値で継続するフェイルセーフ）。
  - DB 書き込みは部分失敗時に既存データを保護する（書き込み対象コードの絞り込みなど）。
  - OpenAI 呼び出しはモジュールローカルに分離して unittest.mock.patch により差し替え可能。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 環境変数に機密情報（API キー、トークン、パスワード等）を利用するため、運用時は OS 環境変数や安全なシークレット管理を推奨。`.env` を利用する場合はアクセス権限管理を行うこと。

### Migration notes / 注意事項
- 必須環境変数:
  - OPENAI_API_KEY（AI 機能を利用する場合）、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID などが一部機能で必須。
- DB スキーマ期待値:
  - 本ライブラリは以下のテーブルを前提としている: prices_daily、raw_news、news_symbols、ai_scores、market_regime、market_calendar、raw_financials 等。初期導入時はスキーマとサンプルデータの準備が必要。
- OpenAI モデル:
  - デフォルトで gpt-4o-mini を使用。API レスポンス形式は JSON mode を期待しているため、互換性のある SDK/エンドポイントを使用すること。
- DuckDB バージョン依存:
  - executemany に関する挙動やリスト型バインドは DuckDB バージョン差で挙動が変わる可能性があるため、DuckDB 互換性に注意。
- テストの容易化:
  - OpenAI への実際の呼び出しはモジュール内の _call_openai_api を patch して差し替え可能。CI 環境では API 呼び出しをモックすることを推奨。

---

今後のリリースでは、strategy / execution / monitoring サブパッケージの具体的な注文ロジック・監視フローの実装や、より詳細な品質チェック・データ可視化の追加を予定しています。