# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
安定版リリースや後方互換の注意点は各バージョンのセクションを参照してください。

## [Unreleased]

## [0.1.0] - 2026-04-04
最初の公開リリース。主要なモジュール群（データ取得/ETL、カレンダー管理、研究用ファクター、ニュースNLP、レジーム判定、設定管理等）を実装しました。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化。__version__ = 0.1.0、主要サブパッケージを __all__ で公開。
- 環境変数・設定管理 (kabusys.config)
  - .env ファイル自動読み込み機能を実装（プロジェクトルート判定: .git / pyproject.toml を探索）。
  - 読み込み優先順位: OS環境変数 > .env.local(上書き) > .env(初回のみ)。
  - 自動読み込みの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装:
    - export KEY=... 形式対応
    - シングル/ダブルクォート内部のバックスラッシュエスケープを考慮
    - コメント処理（クォート外、空白直前の # をコメントと判定）
  - Settings クラスを提供（プロパティ経由で取得）:
    - J-Quants / kabuステーション / LINE API の設定項目
    - DB パス（DUCKDB_PATH / SQLITE_PATH）、監視用ファイルパス（PID_FILE_PATH / KILL_FLAG_PATH）等
    - リソース閾値（CPU/MEMORY/DISK）やログレベル検証（LOG_LEVEL）、環境種別検証（KABUSYS_ENV）
- ニュースNLP (kabusys.ai.news_nlp)
  - raw_news / news_symbols を元に銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini）でセンチメントを評価し、ai_scores テーブルへ書き込むワークフローを実装。
  - マルチ銘柄バッチ処理（最大 20 銘柄/コール）、1 銘柄当たりの記事数/文字数制限（トークン肥大化対策）。
  - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、各要素の code/score 検証）と ±1.0 クリップ。
  - エラー耐性:
    - 429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフでリトライ。
    - その他のエラーは該当チャンクをスキップし他チャンクへ継続。
  - テスト容易性のため API 呼び出し部分は差し替え可能（unittest.mock.patch によるモックを想定）。
- 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定・market_regime テーブルへ冪等的に保存する処理を実装。
  - マクロキーワードによる raw_news タイトル抽出、OpenAI（gpt-4o-mini）での macro_sentiment 評価、API のリトライ/フォールバック（失敗時 macro_sentiment=0.0）。
  - レジームスコアの合成ロジック、閾値によるラベル付け、DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等処理。
- データプラットフォーム (kabusys.data)
  - ETL パイプラインのインターフェース（ETLResult データクラスを再エクスポート）。
  - pipeline モジュール:
    - 差分取得、保存、品質チェックのための基盤実装（ETLResult にて実行結果・品質問題・エラーを集約）。
    - backfill_days による後出し修正吸収の設計。
  - カレンダー管理 (calendar_management):
    - market_calendar テーブルを元に営業日判定/is_sq_day/next_trading_day/prev_trading_day/get_trading_days を提供。
    - DB にデータがない場合は曜日（土日）ベースのフォールバック。
    - calendar_update_job: J-Quants からの差分取得と冪等保存、バックフィル、健全性チェックを実装。
- 研究用モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離等を計算。データ不足時は None を返す設計。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比などを計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（EPS が無効な場合は None）。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（任意ホライズン）計算。入力バリデーションあり（0 < h <= 252）。
    - calc_ic: ファクターと将来リターンのスピアマン（ランク）相関（IC）を計算。十分なデータがない場合は None。
    - rank / factor_summary: ランク変換（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を提供。
- その他設計的配慮
  - DuckDB を前提とした SQL と Python 混合の実装（SQL 側でウィンドウ関数を利用）。
  - いずれのモジュールもルックアヘッドバイアス対策として datetime.today()/date.today() を直接参照しない設計を採用（target_date ベースで処理）。
  - DB 書き込みは冪等・トランザクション（BEGIN/COMMIT/ROLLBACK）を意識した実装。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- OpenAI API キーの解決は引数 api_key を優先し、未指定の場合に環境変数 OPENAI_API_KEY を参照する実装。キーの取り扱いについては利用者側での秘密管理を推奨。

### 注意点 / 既知の設計選択
- OpenAI 呼び出しは gpt-4o-mini + JSON mode を想定し、厳密な JSON を期待するプロンプト設計になっています。LLM の出力が完全な JSON でない場合の復元ロジック（最外側の {} を抽出）を含みますが、確実性を保証するものではありません。
- DuckDB executemany に関する互換性考慮:
  - DuckDB 0.10 系で executemany に空リストを渡せない制約を回避するため、空チェックを実装しています。
- .env の自動読み込みはプロジェクトルート検出に依存します（__file__ 起点で .git / pyproject.toml を探索）。パッケージ配布後の動作を考慮して設計していますが、特殊な配置では自動ロードがスキップされる場合があります。
- 市場カレンダーが部分的にしか登録されていない（まばらな DB）場合でも next_trading_day / prev_trading_day / get_trading_days の挙動が一貫するよう DB 優先かつ未登録日は曜日ベースのフォールバックを採用しています。
- API 呼び出し周り（ニュース・レジーム）はフェイルセーフを優先し、外部 API の障害時は該当箇所をスキップまたはゼロスコアで継続します（例: macro_sentiment=0.0、チャンク単位でのスキップ等）。

---

既知の追加タスク / 今後の改善候補（メモ）
- strategy / execution / monitoring の具体実装（パッケージ __all__ に名前はあるが、今回のスナップショットでは詳細実装が含まれていない）。
- テストカバレッジの強化（特に OpenAI 呼び出し周りのモックを用いた単体テスト）。
- パフォーマンス観点での最適化（大規模データセットでの DuckDB クエリ、並列処理等）。
- セキュリティ向上: API キー管理のドキュメント化、機密情報の取り扱いガイドライン整備。

------------------------------------------------------------------
訳注: 本 CHANGELOG は提示されたソースコードの内容から機能・設計を推測して作成しています。動作詳細や公開 API の正式仕様は実際のドキュメント・リポジトリを参照してください。