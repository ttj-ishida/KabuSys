# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
※ このリポジトリの初期リリース（0.1.0）に含まれる主要な機能・設計上の注意点をコードから推測して記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージトップでのバージョン管理（src/kabusys/__init__.py の __version__ = "0.1.0"）。
  - public API の簡易エクスポート設定（__all__ に data, strategy, execution, monitoring）。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能（プロジェクトルート検出は .git / pyproject.toml を基準）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
  - export KEY=val 形式やクォート/エスケープ、インラインコメントの扱いに対応するパーサ実装。
  - Settings クラスを通じた型付きプロパティ:
    - J-Quants / kabu API / Slack / DB パス（DUCKDB_PATH, SQLITE_PATH）などの取得。
    - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値検査）。
    - is_live / is_paper / is_dev のユーティリティ。

- AI モジュール（src/kabusys/ai）
  - ニュースセンチメント解析（news_nlp.score_news）
    - raw_news と news_symbols を集約して銘柄ごとにニュースを結合し OpenAI（gpt-4o-mini）でスコアリング。
    - チャンク処理（デフォルト 20 銘柄／回）、1 銘柄あたりの記事数上限（10 件）、文字数トリム（3000 文字）。
    - レスポンスの厳格なバリデーション（JSON 抽出、"results" リスト、code/score の検査）。
    - スコアは ±1.0 にクリップ。API エラーはエクスポネンシャルバックオフでリトライし、最終的に失敗したチャンクはスキップ（フェイルセーフ）。
    - DB 書き込みは部分置換（対象コードだけ DELETE → INSERT）して部分失敗時に既存データを保護。
    - 時間ウィンドウ計算ユーティリティ calc_news_window を提供（JST 基準の前日15:00～当日08:30 に対応、内部は UTC naive datetime を返す）。

  - 市場レジーム判定（ai.regime_detector.score_regime）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news / market_regime を使用。計算はルックアヘッドバイアスを避ける工夫あり（target_date 未満のみ使用など）。
    - OpenAI 呼び出しは独立実装で、API タイムアウト・レート制限・5xx に対するリトライ・フェイルセーフ（失敗時 macro_sentiment=0.0）を実装。
    - market_regime への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）と ROLLBACK 失敗ログ処理。

- Data モジュール（src/kabusys/data）
  - マーケットカレンダー管理（calendar_management.py）
    - market_calendar を基にした is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等のユーティリティ。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック仕様。最大探索日数を設けて無限ループを防止。
    - calendar_update_job により J-Quants API から差分取得し冪等保存。バックフィル・健全性チェックを実装。

  - ETL パイプライン（pipeline.py, etl.py）
    - 差分取得 → 保存 → 品質チェックの枠組みを実装。
    - ETLResult データクラス（ターゲット日、取得数/保存数、品質問題、エラー一覧、ユーティリティメソッド）を提供。data.etl で ETLResult を再エクスポート。
    - DuckDB との連携を前提とした _table_exists / _get_max_date 等のユーティリティ。

- Research モジュール（src/kabusys/research）
  - factor_research.py によるファクター計算:
    - Momentum（1M/3M/6M リターン、ma200_dev）、Volatility（20日 ATR、相対 ATR、出来高関連）、Value（PER, ROE）を実装。
    - DuckDB 内部 SQL を活用し、営業日ベースのラグ/ウィンドウ計算を行う。データ不足時の None ハンドリングあり。
  - feature_exploration.py による解析ユーティリティ:
    - 将来リターン calc_forward_returns（任意ホライズン対応）、IC（calc_ic: Spearman ランク相関）、rank、統計サマリー（factor_summary）。
  - data.stats の zscore_normalize を re-export。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーの扱いは引数注入または環境変数 OPENAI_API_KEY 参照で、未設定時は ValueError を発生させる仕様。自動的にキーを埋め込む等の機能は実装していない。

### Notes / 設計上の重要点
- ルックアヘッドバイアス対策:
  - AI/研究モジュールはいずれも内部で datetime.today()/date.today() を参照せず、外部から target_date を注入して計算する設計。
  - DB クエリは target_date 未満 / 以前等の排他条件を明示している。
- DB 書き込み:
  - ほとんどの書き込みは BEGIN/DELETE/INSERT/COMMIT のスタイルで冪等性を重視している。例外発生時は ROLLBACK を試み、ROLLBACK 失敗時はログ出力。
  - DuckDB の executemany の実装差異（空リスト不可）に配慮したガードあり。
- エラーハンドリング:
  - 外部 API 呼び出し（OpenAI / J-Quants）はリトライ・バックオフとフェイルセーフ（スコアを 0 にする、チャンクをスキップする等）で堅牢化。
- テストしやすさ:
  - OpenAI 呼び出し箇所は内部関数として分離されており、unittest.mock.patch による差し替えを想定した設計。
- デフォルト値・パラメータ:
  - OpenAI モデル: gpt-4o-mini（news_nlp / regime_detector）
  - news_nlp バッチサイズ: 20、最大記事数/文字数制限: 10 / 3000。
  - regime_detector は ETF 1321 を用いた 200 日 MA 乖離とマクロセンチメントの重み付け（MA 70% / macro 30%）でスコアを生成。

---

この CHANGELOG はコードベースの仕様・実装から推測して作成しています。細かな動作や外部 API の挙動については実際のランタイムおよびテスト結果を必ずご確認ください。