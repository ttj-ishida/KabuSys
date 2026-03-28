KEEP A CHANGELOG
=================

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-28
-------------------

Added
- 初回リリース: kabusys パッケージ v0.1.0 を追加。
  - パッケージ構成: data, research, ai, config, などのモジュール群を提供。
  - パッケージバージョンは src/kabusys/__init__.py の __version__="0.1.0"。

- 環境・設定管理 (kabusys.config)
  - .env および .env.local からの自動読み込みを実装。読み込みはプロジェクトルート（.git または pyproject.toml）を起点に行うため、CWD に依存しない。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）。
  - .env 行パーサー (_parse_env_line) を実装:
    - export KEY=val 形式対応、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメントの扱い（非クォート時は直前に空白/タブがあれば # をコメントと判定）を考慮。
  - Settings クラスを提供（settings インスタンスを公開）:
    - 必須値取得メソッド（_require）により未設定時は ValueError を送出。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などを必須とするプロパティを実装。
    - KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL（DEBUG/INFO/...）のバリデーション。
    - DB パスのデフォルト（DUCKDB_PATH= data/kabusys.duckdb, SQLITE_PATH= data/monitoring.db）をサポート。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）の JSON mode で銘柄ごとのセンチメントを算出し、ai_scores テーブルへ書き込む。
  - 特徴:
    - スコアは -1.0～1.0 にクリップ。
    - タイムウィンドウ: 前日15:00 JST ～ 当日08:30 JST（内部は UTC naive datetime で扱う）。
    - バッチ処理（最大 20 銘柄/コール）、記事最大数・文字数のトリム（設定でトークン肥大化対策）。
    - 再試行ロジック（429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフ）。
    - レスポンス検証（JSON 抜き出し、results 配列の検証、未知コードの無視、数値チェック）。
    - 部分失敗時も既存スコアを保護するため、DELETE → INSERT をコードで絞って実行（冪等性確保）。
    - DuckDB 互換性考慮（executemany に空リストを渡さない等）。
  - 公開 API: score_news(conn, target_date, api_key: Optional[str]) → 書き込んだ銘柄数を返す。
  - API キーは引数で注入可能（テスト容易性）。未指定時は環境変数 OPENAI_API_KEY を使用。未設定時は ValueError。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等で書き込む。
  - 特徴:
    - MA200 の計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - マクロ記事抽出は news_nlp の calc_news_window を利用して時間窓でフィルタ。
    - OpenAI 呼び出しは専用の実装で行い、API 失敗時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
    - 冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）と ROLLBACK の安全処理。
  - 公開 API: score_regime(conn, target_date, api_key: Optional[str]) → 1 を返す（成功）。api_key は OPENAI_API_KEY か引数で指定。

- リサーチ（kabusys.research）
  - ファクター計算 (factor_research):
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（データ不足時は None を返す）。
    - calc_volatility: 20 日 ATR, atr_pct, avg_turnover, volume_ratio（必要な行数が満たない場合は None）。
    - calc_value: raw_financials から直近財務データを取得し PER / ROE を計算（EPS=0/欠損時は None）。
  - 特徴量探索 (feature_exploration):
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（営業日ベースの LEAD を使用）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算（有効レコード < 3 の場合は None）。
    - factor_summary: count/mean/std/min/max/median を計算（None を除外）。
    - rank: 同順位は平均ランクで扱う実装（丸めで ties を安定化）。
  - いずれも DuckDB 接続を受け取り prices_daily 等の DB テーブルのみを参照。外部 API を呼ばない設計。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が未取得の場合は曜日ベース（土日を非営業日）でフォールバック。
    - calendar_update_job により J-Quants API から差分取得 → market_calendar に冪等保存（バックフィル/健全性チェック実装）。
  - ETL パイプライン (pipeline):
    - ETLResult dataclass を提供（target_date、取得件数、保存件数、品質チェック結果、エラー等を保持）。
    - _get_max_date / _table_exists 等のユーティリティ実装。
  - etl モジュールで ETLResult を再エクスポート。

Security / Safety
- OpenAI や各種 API キーは明示的に必要（Settings 経由または score_* の api_key パラメータ）。未設定時は ValueError を発生させる箇所があるため、運用時は環境変数を適切に設定すること。
- LLM の呼び出し失敗時は原則フェイルセーフ（スコアを 0 にする、当該チャンクはスキップする等）としてシステム全体の停止を防止。
- DB 書き込みは冪等性を意識して実装。部分失敗時に既存データを不用意に削らない設計。

Compatibility / Notes
- DuckDB を前提に設計（テーブル名: prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等を想定）。
- executemany に空リストを渡すと DuckDB 0.10 系で問題となるため、空チェックを入れている。
- OpenAI モデルはデフォルト gpt-4o-mini、JSON mode を利用する設計。
- ルックアヘッドバイアス回避のため、内部処理で datetime.today() / date.today() を直接参照しない実装方針（一部ジョブは date.today() を使用するが、スコア計算側は target_date を明示的に受け取る）。

Breaking Changes
- 初版のため破壊的変更はなし。

Deprecations
- なし。

Migration / Usage（運用メモ）
- 自動 .env 読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- OpenAI キー注入:
  - 関数呼び出し側から api_key 引数を渡すか、環境変数 OPENAI_API_KEY を設定する。
- 代表的な呼び出し例:
  - ai スコア付与: score_news(conn, target_date, api_key=None)
  - レジーム判定: score_regime(conn, target_date, api_key=None)
- 必要な DB テーブルスキーマは各モジュールのドキュメントに合わせて作成すること（prices_daily / raw_news / news_symbols / ai_scores / market_regime / raw_financials / market_calendar 等）。

Acknowledgements / Design notes
- LLM 呼び出し部分はテスト容易性を考慮して _call_openai_api を切り出し、unittest.mock.patch による差し替えを想定。
- ルックアヘッドバイアス防止やフェイルセーフ、DuckDB 互換性への配慮が設計方針に強く反映されています。

[リンク]
- ソース: src/kabusys 以下のモジュール一式（config, ai, data, research 等）