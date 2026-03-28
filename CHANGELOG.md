# CHANGELOG

すべての注目すべき変更点を記録します。本ドキュメントは Keep a Changelog の形式に準拠します。  
バージョン規約は semver に準拠しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買プラットフォーム「KabuSys」の基礎機能を実装しました。主要モジュールと実装方針は下記の通りです。

### Added
- パッケージ基礎
  - パッケージ名: kabusys、バージョン: 0.1.0。
  - 公開モジュール: data, research, ai, execution, strategy, monitoring（__all__ にて一部公開）。
- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出: .git または pyproject.toml を起点に探索し、自動ロードを行う（CWD に依存しない）。
  - .env パース機能を独自実装（クォート（シングル／ダブル）、エスケープ、export KEY=val 形式、行内コメントハンドリング対応）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - Settings クラスを提供し、各種設定をプロパティとして取得可能:
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID
    - duckdb/sqlite のパス設定（DUCKDB_PATH / SQLITE_PATH）
    - 環境（KABUSYS_ENV: development / paper_trading / live）とログレベル（LOG_LEVEL）のバリデーション
    - is_live / is_paper / is_dev のヘルパープロパティ
- AI（自然言語処理）機能（kabusys.ai）
  - news_nlp.score_news:
    - raw_news と news_symbols を用いて銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode でセンチメント評価。
    - チャンク単位（最大20銘柄）でのバッチ送信、記事トリム（最大記事数・文字数制約）、リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）。
    - レスポンス検証ロジック（JSON 抽出、results 配列、code/score 検証、スコアクリップ ±1.0）。
    - 書き込みは部分的置換（DELETE → INSERT）で冪等性と部分失敗耐性を確保。DuckDB の executemany 空リスト制約に対する処理あり。
    - API 呼び出し箇所はテスト差し替え可能（_call_openai_api を patch 可能）。
    - datetime.today()/date.today() を参照せず、ルックアヘッドバイアスを避ける設計（ターゲット日ベース）。
  - regime_detector.score_regime:
    - ETF 1321（日経225連動型）の200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - マクロニュース取得は news_nlp.calc_news_window を用いる。記事がなければ LLM 呼び出しを行わず macro_sentiment=0.0。
    - OpenAI 呼び出しは独立実装でモジュール間結合を避ける。API失敗時はフォールバック（0.0）し、リトライ/バックオフ実装あり。
    - 計算結果は market_regime テーブルへトランザクションで冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時には ROLLBACK を試行して例外を伝播。
- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar に基づく営業日判定・前後営業日の探索・期間内営業日取得・SQ日判定のヘルパーを実装。
    - DB にデータがない場合は曜日（平日）ベースのフォールバックを提供。
    - calendar_update_job: J-Quants API からカレンダーを差分取得し、バックフィル、健全性チェック（将来日付の異常検知）を行った上で保存する夜間バッチ処理を実装。
  - pipeline / ETL:
    - ETLResult データクラスを公開（etl モジュール経由でも再エクスポート）。
    - 差分取得、保存（jquants_client の save_* を想定）、品質チェック（quality モジュール）を組み合わせる ETL 設計方針を実装（パーツ）。
    - 最終取得日判定ユーティリティ、テーブル存在確認ユーティリティなどを実装。
- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials を用いてファクター（モメンタム、ATR、流動性、PER/ROE等）を計算し、(date, code) ベースの dict リストで返す。
    - 計算に必要な行数不足時は None を返す等の堅牢化。
  - feature_exploration:
    - calc_forward_returns: target_date 基準で複数ホライズンの将来リターンを一括取得可能（ホライズンのバリデーションあり）。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算（有効レコード数 3 未満は None）。
    - rank: 同順位は平均ランクを返すランク関数（丸め処理で ties の扱いを安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を標準ライブラリのみで実装。
  - zscore_normalize は kabusys.data.stats から再利用可能に公開。
- ロギングとエラーハンドリング
  - 各モジュールで詳細な info/debug/warning ログを追加。
  - API 呼び出しの失敗（外部サービス）に対してフェイルセーフ設計（例: LLM 失敗時に中立値で継続）を実装。
  - トランザクション（BEGIN/COMMIT/ROLLBACK）処理で ROLLBACK 失敗時の警告ログ出力を実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数に依存する機密情報（OpenAI API キー等）は Settings 経由で参照。自動ロードは環境変数で無効化可能。

### Notes / Known limitations
- OpenAI API 依存:
  - score_news / score_regime は OpenAI API キー（引数または環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError を送出する。
  - LLM 呼び出しは gpt-4o-mini を想定し、JSON mode を利用する設計。外部APIの挙動変化に対してはログを残してフォールバックする。
- DuckDB を主要なローカルストレージとして使用。DuckDB バージョン差異（例: executemany の空リスト制約）に配慮した実装が入っているが、利用時は互換性確認を推奨。
- 日付取り扱い:
  - AI モジュールは全てターゲット日ベースで動作し、datetime.today()/date.today() の直接参照を避けることで、ルックアヘッドバイアスを排除する設計になっています。
- テスト支援:
  - OpenAI 呼び出し箇所は内部関数（_call_openai_api）をパッチして差し替え可能にしておりユニットテストを容易にしています。

### Breaking Changes
- （初回リリースのため該当なし）

---

今後のリリースでは、実際の ETL 実装（jquants_client の具体的な API 呼び出しパイプライン）、発注/実行（execution）やストラテジーの実行エンジン、モニタリング周りの詳細実装の追加が予定されています。必要であれば次回リリース向けの変更案やリリースノート案も作成します。