# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

※この変更履歴は、提供されたソースコードから機能・設計方針を推測して作成しています。

## [0.1.0] - 2026-03-28

### Added
- 初回リリース: KabuSys パッケージ (バージョン 0.1.0)
  - パッケージのエントリポイントを定義 (src/kabusys/__init__.py)。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - .env のパースは以下をサポート:
    - コメント行・空行の無視、`export KEY=val` 形式
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理
    - クォートなしの値におけるインラインコメント処理（直前が空白/タブの場合に # をコメントと扱う）
  - 自動読み込みの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用途）。
  - OS 環境変数の上書き制御（.env.local が .env を上書きするが、既存の OS 環境変数は保護）。
  - 必須値チェック用の `_require` と Settings クラスを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などのプロパティ
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の値検証
    - データベースパスのデフォルト（DuckDB / SQLite）と Path 変換
    - is_live / is_paper / is_dev の便利プロパティ

- ニュース NLP（センチメント） (src/kabusys/ai/news_nlp.py)
  - raw_news / news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを評価して ai_scores テーブルへ保存する機能を実装。
  - 時間ウィンドウ: target_date の前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と照合）。
  - バッチ処理: 最大 20 銘柄 / API コール、1 銘柄あたり最大 10 記事・3000 文字にトリム。
  - エラー耐性:
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフでの再試行
    - JSON パース失敗・バリデーション失敗時は当該チャンクをスキップ（例外を投げずフェイルセーフ）
    - DuckDB の executemany に関する互換性（空パラメータ回避）を考慮して DELETE→INSERT で置換
  - レスポンスのバリデーション:
    - JSON 抽出、"results" 配列構造、code の照合、score の数値化・有限性チェック
    - スコアは ±1.0 にクリップ
  - テスト容易性のため、OpenAI 呼び出し部分（_call_openai_api）をモック差替え可能に設計
  - public API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。api_key 未設定時は環境変数 OPENAI_API_KEY を参照し、未設定であれば ValueError を送出。

- 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等書き込みする機能を実装。
  - マクロニュースは news_nlp.calc_news_window と raw_news フィルタで抽出（キーワードは内蔵リスト）。
  - OpenAI（gpt-4o-mini）を用いた JSON 出力の解析、リトライ・フェイルセーフ（失敗時 macro_sentiment=0.0）を実装。
  - レジーム合成のクリップ・閾値設定（BULL/BEAR threshold 等）を実装。
  - public API: score_regime(conn, target_date, api_key=None) → 成功時に 1 を返す。api_key が解決できない場合は ValueError。

- 研究（Research）モジュール (src/kabusys/research/)
  - ファクター計算 (src/kabusys/research/factor_research.py):
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算。データ不足時は None。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、volume_ratio を計算。
    - calc_value: raw_financials から直近財務データを結合して PER / ROE を計算。
    - いずれも DuckDB の SQL とウィンドウ関数を利用し、(date, code) 単位の結果リストを返す。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py):
    - calc_forward_returns: 指定日からの将来リターン (デフォルト [1,5,21]) を一括クエリで取得、horizons のバリデーションを実装。
    - calc_ic: Spearman ランク相関（Information Coefficient）を計算。有効レコードが 3 未満の場合は None。
    - rank: 同順位は平均ランクを返す実装（丸め処理で ties の検出漏れ対策）。
    - factor_summary: 各列の count/mean/std/min/max/median を算出。
  - ユーティリティの再エクスポート: zscore_normalize を data.stats から再エクスポート。

- データプラットフォーム / カレンダー管理 (src/kabusys/data/calendar_management.py)
  - market_calendar テーブル管理と営業日判定ロジックを提供:
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
  - DB 登録ありの場合は DB 値を優先し、未登録日は曜日ベースのフォールバック（週末判定）で補完する設計。
  - calendar_update_job: J-Quants API から差分取得 → jq.save_market_calendar による冪等保存。バックフィル（直近数日再取得）と健全性チェック（未来日付の異常検知）を実装。
  - 最大探索範囲の制約（_MAX_SEARCH_DAYS）やその他安全策を導入。

- ETL / パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
  - ETLResult dataclass を実装（取得件数/保存件数/品質問題/エラー集約、to_dict を提供）。
  - 差分更新・バックフィルの方針を反映したユーティリティ（テーブル存在確認、最大日付取得等）を実装。
  - etl.py で ETLResult を再エクスポート。

- その他の設計方針・ユーティリティ
  - 全 AI / 研究処理で datetime.today() / date.today() の直接参照を避け、ルックアヘッドバイアス対策を徹底。
  - OpenAI 呼び出し部分はモック差し替え可能にしてテスト容易性を考慮。
  - ロギングを各処理に適切に挿入（INFO/DEBUG/WARNING/EXCEPTION）。
  - DuckDB のバージョン互換性に関する注記（executemany の空リスト回避など）をソース内に明記。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決する仕様。未設定時は明示的に ValueError を送出して安全性を確保。

---

Known notes（既知の注意点）
- DuckDB のバージョン差異や executemany の挙動に依存する箇所があり、利用時は使用する DuckDB バージョンとの互換性確認を推奨します。
- OpenAI への依存部分は外部 API 呼び出しのためネットワーク障害や料金に注意してください。API 呼び出し失敗時はフェイルセーフで処理継続する設計ですが、結果欠落が発生します。
- .env の自動読み込みはパッケージ配置やプロジェクト構成に依存します。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

もしリリース日やリリースノートの粒度・表現を調整したい場合は、出力形式（英語/日本語・セクション分け等）や追加で強調したい差分を教えてください。