# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。慣例に従い、バージョンごとに「Added / Changed / Fixed / Removed / Deprecated / Security」などのカテゴリで記載します。

※ 注: 以下はコードベースの内容から推測して作成した初回リリース向けの変更履歴です。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-03
初回公開リリース。主要サブシステム（設定管理、データETL/カレンダー、研究用ファクター群、AIによるニュース解析/市場レジーム判定、ユーティリティ群）を実装・公開。

### Added
- パッケージ基盤
  - パッケージメタ: kabusys v0.1.0 を導入。
  - モジュール公開: data, strategy, execution, monitoring を __all__ に追加。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を安全に読み込む自動ローダーを実装。
  - プロジェクトルート検出: __file__ を起点に .git または pyproject.toml を探索してプロジェクトルートを特定するロジックを実装（配布後も動作）。
  - .env パース強化:
    - コメント行・空行の無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォートなしの場合のインラインコメント判定（直前が空白/タブ時）。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 環境変数保護: .env 読み込み時に既存 OS 環境変数を上書きしない仕組み（override/protected）。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、OPENAI 等のキー名の定義、デフォルト値や型変換、バリデーションを実装）。
  - 各種ファイルパスの既定値（duckdb, sqlite, pid, kill flag）と閾値設定（CPU/MEM/DISK）のプロパティを実装。
  - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）と利便性プロパティ（is_live / is_paper / is_dev）。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar を利用した営業日判定ユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB に登録がない日付は曜日ベース（平日＝営業日）でフォールバックする一貫した挙動を提供。
    - 最大探索範囲による無限ループ防止、健全性チェック、バックフィル設定を実装。
    - 夜間バッチジョブ calendar_update_job を実装し、J-Quants API から差分取得して冪等的に保存する処理を実装（fetch / save を jquants_client 経由で呼ぶ）。
  - pipeline / etl:
    - ETLResult dataclass を導入し ETL 実行結果（取得数・保存数・品質問題・エラー等）を集約。
    - pipeline モジュールの基本設計に基づく差分取得 / idempotent 保存 / 品質チェックのインターフェースを用意（jquants_client・quality 連携を想定）。
    - ETL のバックフィル挙動・calendar 先読み等のデフォルト設計を実装。
    - duckdb を前提としたテーブル存在チェックや最大日付取得等のユーティリティを実装（互換性を考慮）。

- AI モジュール（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信して銘柄別センチメント（ai_score）を計算。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST に対応）を提供（calc_news_window）。
    - バッチング（最大 20 銘柄/呼び出し）、1 銘柄あたりの最大記事数 / 最大文字数によるトークン肥大化対策を実装。
    - API エラー（429・ネットワーク・タイムアウト・5xx）に対する指数バックオフリトライと、非リトライ対象のエラーハンドリングを実装。
    - レスポンスのバリデーションと復元ロジック（JSON 抽出）を実装し、スコアを ±1.0 にクリップ。
    - DuckDB への書き込みは冪等的に行い、部分失敗時に既存スコアを保護するため code を絞って DELETE → INSERT を実行。
    - テスト用フック: OpenAI 呼び出しを差し替え可能（_call_openai_api を patch できる）。
  - regime_detector:
    - ETF (1321) の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算（target_date 未満のデータのみを使用してルックアヘッドバイアスを防止）。
    - マクロキーワードによるニュースフィルタ、最大件数制限、LLM によるセンチメント評価（gpt-4o-mini, JSON Mode）。
    - LLM 呼び出しはリトライ・エラーハンドリングを実装し、API 失敗時は macro_sentiment = 0.0 で継続するフェイルセーフを採用。
    - 最終結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - OpenAI クライアント生成時に api_key を引数で注入可能（環境変数 OPENAI_API_KEY もサポート）。

- 研究（kabusys.research）
  - factor_research:
    - モメンタムファクター（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ/流動性（20 日 ATR, 平均売買代金, 出来高比）、バリュー（PER, ROE）を計算する関数群を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB の SQL ウィンドウ関数を活用し、データ不足時は None を返す等、安全性を確保。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応、入力検証）、IC（Spearman ランク相関）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリ（factor_summary）を実装。
    - 外部依存（pandas など）を使わない、純 Python + DuckDB 実装。

- テスト・開発配慮
  - OpenAI 呼び出しや .env 自動ロードなど、ユニットテストで差し替え可能なポイント（関数分離・patch しやすい構造）を意図的に設計。
  - ルックアヘッドバイアス回避: AI モジュールやファクター計算で datetime.today() / date.today() を直接参照しない設計。

### Changed
- （初回リリースのためなし）

### Fixed
- （初回リリースのためなし）

### Removed
- （初回リリースのためなし）

### Deprecated
- （初回リリースのためなし）

### Security
- 外部 API キーは環境変数で設定する想定:
  - OPENAI_API_KEY（OpenAI）
  - JQUANTS_REFRESH_TOKEN（J-Quants）
  - KABU_API_PASSWORD（kabuステーション API）
- .env 自動読み込みはテスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- 設定読み込みでは OS 環境変数を優先・保護する実装により、誤った .env 上書きによる意図しない機密露出を防止。

---

備考・既知の設計方針や制約（コードから推測）
- DuckDB を主要なローカル分析 DB として使用。テーブル存在チェックや executemany の空配列制約（DuckDB 0.10 の挙動）を考慮している。
- 日付/時刻は可能な限り date / UTC naive datetime で統一し、タイムゾーン混入を避ける実装。
- API 呼び出しは冪等性・フェイルセーフを重視。部分的失敗でもシステム全体の整合性を守るよう設計。
- 外部依存は最小限に抑え、純粋な Python・DuckDB ベースでデータ処理・統計解析を行うことを意図している。

--- 

今後の追加候補（コード・設計からの示唆）
- strategy / execution / monitoring モジュールの詳細な実装とそれらに関する CHANGELOG エントリの追加。
- 単体テスト・統合テストの追加（ETL、AI 呼び出しのモックを含む）。
- エラーレポーティングや監視（LINE 通知等）の実装とそれに伴う設定説明の明示化。