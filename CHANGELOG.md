# CHANGELOG

All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

## [0.1.0] - 2026-03-31

### Added
- 初回公開: KabuSys 日本株自動売買システムの基本モジュール群を追加。
  - パッケージ初期化: src/kabusys/__init__.py にてバージョンと公開サブパッケージを定義。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数からの設定読み込みを自動で行う機能を実装。
  - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を読み込む仕組みを導入。
  - export 形式やシングル/ダブルクォート、エスケープ、インラインコメント等を考慮した堅牢な .env パーサーを実装。
  - 環境変数の自動ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD により抑止可能。
  - 必須環境変数取得用の _require と Settings クラスを提供（J-Quants、kabuAPI、Slack、DBパス等のプロパティを含む）。
  - KABUSYS_ENV / LOG_LEVEL の入力バリデーション（許容値チェック）を実装。
- AI/自然言語処理 (src/kabusys/ai)
  - ニュースセンチメントスコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を使い、銘柄別にニュースを集約して OpenAI（gpt-4o-mini）でセンチメントを評価し ai_scores テーブルへ書き込む機能を実装。
    - バッチ処理、チャンクサイズ制御、1銘柄あたりの記事数・文字数トリム、JSON Mode レスポンス検証、スコアの ±1.0 クリッピング、DuckDB への冪等的な書き込み（DELETE→INSERT）をサポート。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ付きリトライを実装。失敗時はフェイルセーフでスキップし処理継続。
    - 単体テスト容易性のため OpenAI 呼び出し関数は差し替え可能（unittest.mock.patch を想定）。
    - タイムウィンドウ計算ユーティリティ calc_news_window を提供（JST→UTCの変換を含む）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の200日移動平均乖離（重み70%）と、マクロニュースのLLMセンチメント（重み30%）を合成して日次で market_regime を算出・保存する機能を実装。
    - OpenAI 呼び出しのリトライ/フェイルセーフ（API失敗時は macro_sentiment=0.0）やレスポンスパースの堅牢化を備える。
    - DuckDB を用いたルックアヘッドバイアス対策（target_date 未満のみ参照）や冪等的 DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - モジュール間の結合を避けるため、OpenAI 呼び出し・パース処理は news_nlp とは独立して実装。
- データ基盤 / ETL (src/kabusys/data)
  - ETL パイプライン (src/kabusys/data/pipeline.py)
    - 差分取得、保存（jquants_client 経由で冪等保存を想定）、品質チェック統合のための ETLResult データクラスとユーティリティを実装。
    - 最大日付取得、テーブル存在チェック、カレンダー補正などの内部ユーティリティを提供。
  - ETL 公開インターフェース (src/kabusys/data/etl.py)
    - ETLResult の再エクスポートを提供。
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルの管理、JPX カレンダーの夜間差分更新ジョブ calendar_update_job を実装（J-Quants から差分取得→保存）。
    - 営業日判定ユーティリティ群を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にカレンダーがない場合は曜日ベースのフォールバックを行う設計。最大探索日数やバックフィル日数、健全性チェックを導入。
- リサーチ / ファクター計算 (src/kabusys/research)
  - factor_research モジュール (src/kabusys/research/factor_research.py)
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER/ROE）等のファクター計算関数を実装。DuckDB 上の SQL とウィンドウ関数で効率的に計算。
    - データ不足時の None 処理やログ出力を含む堅牢性。
  - feature_exploration モジュール (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク化ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。外部依存無しで標準ライブラリのみで実装。
  - re-export: package レベルで主要関数を __all__ にて公開。
- データユーティリティ
  - duckdb を用いる前提で各種処理が実装されており、結果は辞書リスト形式で返却する API を採用（テスト・デバッグに優しい設計）。

### Changed
- ドキュメント指向の実装ポリシーを採用（各モジュールの docstring に処理フロー、設計方針、入力/出力仕様を明記）。
- ルックアヘッドバイアス防止のため、モジュール内部で datetime.today()/date.today() を直接参照しない方針を徹底（target_date を明示的引数に取る設計）。

### Fixed
- DB 書き込み処理での部分失敗に備え、書き込み前に対象コードの DELETE → INSERT を行うことで既存データの不要な削除を防止（ai_scores, market_regime など）。

### Security
- 環境変数読み込みに際して OS 環境変数の保護（protected set）を導入し、override 挙動時に既存 OS 環境を意図せず上書きしないように実装。

### Notes / Design decisions
- OpenAI API 呼び出しは gpt-4o-mini と JSON Mode を前提に設計。レスポンスパース失敗や API 障害に対してはフェイルセーフ（スコア0やスキップ）で継続する方針を採用。
- 単体テストを容易にするため、OpenAI 呼び出し内部関数は patch/差し替え可能に設計している（例: _call_openai_api をモック化）。
- DuckDB のバージョン差異（executemany の空リスト禁止等）を考慮した実装上の防御が行われている。

### Breaking Changes
- 初版リリースのため破壊的変更は無し。

---

今後の予定（例）
- OpenAI API のレスポンス構造の変化に対応するための適応層拡張
- ETL の監視・再実行 API、ジョブスケジューリング統合
- 追加ファクター（PBR・配当利回り等）やポートフォリオ/実行ロジックの導入

（注）本 CHANGELOG はリポジトリ内のコード・docstring から推測して作成しています。実際のリリースノート作成時はテスト結果・コミット履歴・リリース方針に基づいて適宜調整してください。