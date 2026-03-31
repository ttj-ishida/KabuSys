# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
初期リリース v0.1.0 の内容はコードベースから推測して記載しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-31

### Added
- 基本パッケージ導入
  - パッケージ名: kabusys、バージョン 0.1.0
  - パッケージ公開用 __init__（src/kabusys/__init__.py）を追加。主要サブパッケージとして data, strategy, execution, monitoring を公開。

- 環境設定管理モジュール（src/kabusys/config.py）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み（優先度: OS 環境変数 > .env.local > .env）。
  - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装:
    - export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
    - 上書きオプションと保護キー（protected）をサポート（OS 環境変数を誤って上書きしない設計）。
  - Settings クラスを提供。主なプロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live の検証）および LOG_LEVEL（DEBUG/INFO/... の検証）
    - is_live / is_paper / is_dev 補助プロパティ

- データプラットフォーム（src/kabusys/data）
  - calendar_management モジュール（マーケットカレンダー管理）
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - market_calendar データが無い場合は曜日（週末）ベースでフォールバックする堅牢設計。
    - calendar_update_job: J-Quants からの差分取得 → market_calendar への冪等保存（fetch + save 呼び出し）を実装。バックフィル、健全性チェックあり。
  - ETL / パイプライン（src/kabusys/data/pipeline.py, etl.py）
    - ETLResult dataclass を追加（ETL 実行結果の集約、品質チェック結果とエラーを保持）。
    - 差分更新、バックフィル、品質チェックを想定した設計（jquants_client と quality モジュールを利用するインタフェース）。
    - DuckDB との互換性を考慮したテーブル存在チェックや最大日付取得ユーティリティを実装。
  - etl モジュールは ETLResult を再エクスポート。

- AI ニュース解析（src/kabusys/ai）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を基にニュースを銘柄ごとに集約、OpenAI（gpt-4o-mini）を用いて銘柄毎にセンチメント（-1.0〜1.0）を算出。
    - バッチサイズ 20、1銘柄当たり最大記事数/文字数制限（記事トリム）を実装。
    - OpenAI JSON mode を利用し、厳密な JSON レスポンスを期待。レスポンス検証（results 配列、code/score の存在と型チェック）を実施。
    - 再試行ロジック（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）とフェイルセーフ（API 失敗時はスキップ、処理継続）。
    - DuckDB への書き込みは部分置換（対象コードのみ DELETE → INSERT）して部分失敗の影響を低減。
    - テスト容易性のため _call_openai_api を patch 可能に実装。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースはニュース NLP の窓（calc_news_window）に基づいて抽出。OpenAI を呼び出して macro_sentiment を取得（記事が無い場合は LLM 呼び出しをせず 0.0）。
    - マクロスコア取得も再試行と 5xx 判定ロジックを実装。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - 計算結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時 ROLLBACK）。
    - ルックアヘッドバイアス対策として datetime.today()/date.today() を直接参照しない実装方針。

- リサーチ・ファクター（src/kabusys/research）
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算。データ不足時は None 返却。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を参照して PER/ROE を計算（EPS が 0/欠損時は None）。PBR/配当利回りは未実装で注記あり。
    - DuckDB に対する SQL + Python の組合せで実装（外部 API へアクセスしない）。
  - feature_exploration モジュール
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons のバリデーションあり。
    - calc_ic: ファクター値と将来リターンのランク相関（Spearman ρ）を計算。3 銘柄未満は None。
    - rank: 同順位は平均ランクにする実装（丸めで ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

### Changed
- 初回リリースのため該当なし

### Fixed
- 初回リリースのため該当なし

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キーは関数引数で注入可能（api_key 引数）かつ環境変数 OPENAI_API_KEY を利用する設計。キーの直接ログ出力は行わない想定（コード中に明示的なキー出力はなし）。

### Notes / 設計上の重要ポイント
- ルックアヘッドバイアス対策: 日付依存処理は外部から与えられる target_date に基づき、内部で date.today() を参照しない実装方針を採用。
- DuckDB との互換性を考慮し、executemany に空リストを渡さない等の実装上の細かい配慮あり。
- DB への書き込みは可能な限り冪等に（DELETE → INSERT や ON CONFLICT 想定）してあり、部分失敗時の既存データ保護を優先。
- OpenAI 呼び出しは JSON モード（response_format={"type": "json_object"}）を使用。タイムアウトと温度設定（temperature=0）で決定的な出力を維持する方向。
- テストのしやすさ: API 呼び出し部分は _call_openai_api を patch して差し替え可能。設定の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

もしリリースノートに追加で記載したい項目（既知の制限、今後の予定、外部依存バージョンなど）があれば教えてください。コードからさらに詳細に推定して追記できます。