# Changelog

すべての重要な変更履歴を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。

## [0.1.0] - 2026-03-31

初回リリース — 日本株自動売買／リサーチ用ライブラリのベース実装を追加。

### 追加 (Added)

- パッケージのエントリポイント
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - 公開モジュール: data, research, ai, execution, strategy, monitoring（__all__ にてエクスポート）

- 環境設定／設定管理 (src/kabusys/config.py)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする仕組みを実装（自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env 行パーサを実装（コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント扱いなどに対応）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 動作環境・ログレベル等の getter を公開。必須環境変数が未設定の場合は ValueError を送出する安全設計。
  - デフォルトの DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON モードで一括センチメント評価を行い、ai_scores テーブルへ書き込む機能を実装。
    - ウィンドウ定義（前日 15:00 JST 〜 当日 08:30 JST）、チャンクバッチ（最大 20 銘柄）、1 銘柄あたりの最大記事数/文字数トリム、レスポンスバリデーション、スコアの ±1.0 クリップ等を実装。
    - ネットワーク/429/タイムアウト/5xx に対する指数バックオフのリトライ処理を実装。API 失敗時はフェイルセーフで該当チャンクをスキップし続行。
    - テスト容易性のため _call_openai_api をモジュール内で独立実装し、テスト時にパッチ差替え可能。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出し、market_regime テーブルへ冪等書き込みする機能を実装。
    - calc_news_window を利用してニュースウィンドウを算出（news_nlp と一貫）。
    - API 呼び出し失敗時は macro_sentiment=0.0 のフォールバックを行う安全設計。
    - OpenAI 呼び出し先は独立実装で、テスト時の差替えを想定。

- Data モジュール (src/kabusys/data)
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを元に営業日判定、前/次の営業日取得、期間内営業日リスト取得、SQ 日判定機能を実装。
    - DB にカレンダーデータがない場合は土日ベースでフォールバックする堅牢設計。
    - JPX カレンダー差分取得の夜間バッチ（calendar_update_job）とバックフィル／健全性チェックを実装。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - 差分取得→保存→品質チェックの ETLResult データクラスを実装。ETLResult は処理統計・品質問題・エラー概要を保持し to_dict() を提供。
    - DuckDB を利用した最終取得日判定ユーティリティを実装（テーブル存在チェック、最大日付取得など）。
    - jquants_client 経由での差分取得・保存を想定した設計。バックフィル日数やカレンダー先読みのデフォルト設定を定義。

- Research モジュール (src/kabusys/research)
  - factor_research (src/kabusys/research/factor_research.py)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、出来高比率、20 日平均売買代金）、Value（PER, ROE）を DuckDB 上の SQL と Python で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - 計算は prices_daily / raw_financials のみ参照し、本番の発注API等にアクセスしない設計。
  - feature_exploration (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB クエリで実装。

- ロギングと堅牢性
  - 各モジュールで詳細なログ（INFO/DEBUG/WARNING）を出力。例外時は適切にロールバック（DuckDB トランザクション）する実装。
  - ルックアヘッドバイアス防止: date.today()/datetime.today() を直接参照しない設計（target_date を明示的に受け取る設計方針を採用）。

### 変更 (Changed)

- （初版のため該当なし）

### 修正 (Fixed)

- （初版のため該当なし）

### 既知の制限 / 注意点 (Notes)

- OpenAI API
  - OpenAI API キー（OPENAI_API_KEY）が必須（関数引数で注入可能）。未設定時は ValueError を送出する。
  - 使用モデルは gpt-4o-mini。JSON Mode を期待するが、稀に余剰テキストが混入するケースをパーサ側で補正するロジックあり。
  - API レスポンスの不備や一部失敗はフェイルセーフとして該当スコアをスキップまたは 0.0 にフォールバックする設計。

- DuckDB 互換性
  - DuckDB 0.10 系列での executemany の挙動（空リスト渡し不可など）を考慮した実装を行っているが、実行環境の DuckDB バージョン差異に留意のこと。

- .env 自動ロード
  - 自動ロードはプロジェクトルート検出に依存する（.git または pyproject.toml がルート判定条件）。パッケージ配布後の利用やコンテナ化環境では環境変数経由の明示的設定を推奨。

### 互換性の破壊 (Breaking Changes)

- （初版のため該当なし）

### セキュリティ (Security)

- （現時点で報告なし）

---

今後のリリースでは、モニタリング / 実行（execution）モジュールの詳細実装、CI テスト、ドキュメント強化、型注釈の更なる厳密化、パフォーマンス改善や追加の品質チェック（quality モジュールの詳細化）などを予定しています。必要事項や追記希望があればお知らせください。