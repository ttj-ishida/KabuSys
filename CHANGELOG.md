# Changelog

すべての注目すべき変更は Keep a Changelog の慣習に準拠して記載しています。  
このファイルは、コードベースの内容から推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]
- （現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-31
初期リリース。日本株自動売買システム「KabuSys」の基礎機能群を実装。

### Added
- パッケージのエントリポイントを定義
  - src/kabusys/__init__.py にてバージョン情報（0.1.0）と主要サブパッケージの公開を設定（data, research, ai 等を想定）。

- 環境変数 / 設定管理
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機能を実装（優先順位: OS 環境変数 > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
    - .env のパースは export プレフィックス、クォート、エスケープ、コメント（インラインコメント扱いの判定）に対応。
    - 既存 OS 環境変数を保護するため protected キーセットを導入し、上書き制御を提供。
    - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / 監視設定（PID ファイル、CPU/メモリ/ディスク閾値）等の設定をプロパティ経由で取得。
    - 環境値検証: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の値チェックを実装。
    - 必須値取得で未設定時は ValueError を発生させる _require を提供。

- AI: ニュース NLP（銘柄ごとのセンチメントスコアリング）
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols テーブルを集約して銘柄ごとのニュースを作成。
    - OpenAI（gpt-4o-mini）の JSON モードを用いたバッチスコアリングを実装（最大バッチサイズ 20 銘柄）。
    - API 呼び出しに対して 429 / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフリトライを実装。
    - レスポンスの厳密バリデーション（JSON 抽出、results リストの検証、コード照合、数値チェック）を実装し、不正レスポンスはスキップ（例外非伝播）。
    - スコアは ±1.0 にクリップ。
    - タイムウィンドウ計算（JST ベース: 前日 15:00 ～ 当日 08:30）を calc_news_window で提供。
    - DuckDB への書き込みは冪等（DELETE → INSERT）で、部分失敗時に既存スコアを保護するロジックを実装。
    - テスト容易性のため _call_openai_api を分離しモック差し替えに対応。

- AI: 市場レジーム判定（マクロセンチメント + MA200）
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - prices_daily と raw_news を利用してデータを取得・計算。
    - OpenAI 呼び出しは gpt-4o-mini を利用、JSON レスポンスを期待。
    - API の失敗・パースエラー時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ実装。
    - 計算結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス対策: date 比較は target_date 未満 / 未満等、datetime.today() を直接参照しない設計。

- データプラットフォーム
  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
    - ETLResult データクラスを公開（ETL 実行結果の集約: 取得数・保存数・品質問題・エラーなど）。
    - ETL パイプラインの設計方針・ユーティリティを実装（差分更新・バックフィル・品質チェック方針の記述）。
    - DuckDB によるテーブル存在チェック・最大日付取得ユーティリティ等を実装（ETL 中に利用）。

  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理ロジック（market_calendar の夜間更新ジョブ calendar_update_job) と営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得・まばらな場合の曜日ベースのフォールバック対応。
    - API からの取得は差分・バックフィル・健全性チェックを行い、安全に保存する設計。

  - src/kabusys/data/__init__.py と etl エクスポートにより外部公開インターフェースを整備（ETLResult を再エクスポート）。

- リサーチ（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M）・200日 MA 乖離・ATR（20日）・流動性指標（20日平均売買代金・出来高比率）・バリュー（PER/ROE）等のファクター計算関数を実装。
    - DuckDB 上の prices_daily / raw_financials のみ参照する純粋解析モジュール。
    - 各計算は date, code をキーとした dict のリストで結果を返す（外部 API にはアクセスしない）。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Spearman の ρ）計算、ランク変換ユーティリティ、ファクター統計サマリー等を実装。
    - 外部ライブラリに依存せず標準ライブラリで実装（pandas などの依存を回避）。
  - src/kabusys/research/__init__.py で主要関数群を公開。

- いくつかの設計上の重要点（ドキュメント化された設計方針）
  - すべての「日付基準」処理は datetime.today() / date.today() を直接参照しない（ルックアヘッドバイアス防止）。
  - OpenAI 呼び出しは失敗しても処理を継続するフェイルセーフを優先（可能な限り部分成功を取り込む）。
  - DuckDB の制約（executemany に空リスト不可等）に対応する実装上の注意が盛り込まれている。
  - テスト容易性を考慮し、外部 API 呼び出し箇所をモック差し替え可能に分離。

### Changed
- 初期リリースのため該当なし（初回導入機能群）。

### Fixed
- 初期リリースのため該当なし。

### Deprecated
- なし。

### Removed
- なし。

### Security
- OpenAI API キーは api_key 引数経由または環境変数 OPENAI_API_KEY を使用。
- 環境変数読み込み時は OS 環境変数を保護する仕組みを導入（.env の上書きを制御）。

### Notes / Known limitations
- OpenAI 呼び出しは gpt-4o-mini を前提。将来的なモデル変更や API 仕様変更に応じた対応が必要。
- news_nlp と regime_detector はそれぞれ独立した _call_openai_api 実装を持ち、意図的に共有関数を用いない設計のため重複が存在する（テスト/結合の観点で意図的決定）。
- 一部の外部モジュール（例: kabusys.data.jquants_client, kabusys.data.quality, kabusys.data.stats）が実装済みであることを前提としたコードであり、環境構築時にそれらの実装／設定が必要。
- DuckDB のバージョンによる型バインドや executemany の挙動差異に注意（コメントで対応方針あり）。

---

その他、各モジュール内に設計方針・使用上の注意・フェイルセーフ動作が詳細にコメントされているため、実運用・テスト導入に際しては各ファイルのドキュメント文字列を参照してください。