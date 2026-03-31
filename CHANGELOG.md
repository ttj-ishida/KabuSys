# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記録します。  
このファイルはリリース履歴の要約であり、コードベースの主要な追加・変更点をモジュール単位で日本語で記載しています。

注意: 以下の内容はリポジトリのソースコードから推測して作成したもので、実際のコミットメッセージやマージ履歴ではありません。

## [Unreleased]
（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-31
初期リリース。日本株自動売買システム「KabuSys」基盤のコア機能を実装しました。主な追加点は以下のとおりです。

### Added
- 基本パッケージ
  - パッケージメタ情報を追加（src/kabusys/__init__.py、__version__ = "0.1.0"）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動ロード。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用途）。
    - .env パーサは export 形式、クォートされた値、コメント処理、エスケープ等に対応。
    - OS 環境変数を保護する protected 機構を採用し、.env.local による上書き制御を実現。
  - Settings クラスを実装し、利用可能な設定プロパティを公開（J-Quants トークン、kabu API、Slack、DB パス、環境モード、ログレベル等）。
    - 環境値のバリデーション（KABUSYS_ENV / LOG_LEVEL の許容値チェック）を実装。
    - 必須変数未設定時に明確なエラーメッセージを投げる _require を提供。

- AI（自然言語処理）モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）を用いて銘柄毎のセンチメントを算出。
    - バッチ処理（最大 20 銘柄 / API コール）、1 銘柄あたりの記事数・文字数制限（記事数上限・文字トリム）を実装。
    - OpenAI JSON Mode を利用し、レスポンスを厳密にバリデート（results 配列、code/score 検証、未知コードの無視、数値性チェック）。
    - レスポンスのスコアを ±1.0 にクリップ。
    - 429 / 接続断 / タイムアウト / 5xx に対する指数バックオフリトライ（_MAX_RETRIES）を実装。その他エラーはフェイルセーフでスキップし続行。
    - DuckDB への書き込みは部分的に冪等（対象コードのみ DELETE → INSERT）で行い、部分失敗時に既存データを保護する設計。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
    - 公開 API: score_news(conn, target_date, api_key=None) — 書き込み銘柄数を返却。
    - 時間ウィンドウ計算 util: calc_news_window(target_date)（JST ベースで前日 15:00 〜 当日 08:30、DB は UTC 想定）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動）の 200 日移動平均乖離とマクロニュース LLM センチメントを重み合成して市場レジーム（bull/neutral/bear）を日次判定。
    - ma200 乖離は DuckDB の prices_daily から取得（target_date 未満のみ使用、ルックアヘッド防止）。
    - マクロニュース抽出はキーワードベースで raw_news からタイトルを取得。
    - OpenAI 呼び出しは gpt-4o-mini、JSON パース、リトライ、API エラーに対するフェイルセーフ（失敗時 macro_sentiment=0.0）。
    - レジームスコア計算とラベリング（閾値に基づく）、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - テスト容易性のため内部 API 呼び出し関数は独立実装（news_nlp と共有しない）。
    - 公開 API: score_regime(conn, target_date, api_key=None) — 成功時は 1 を返却。

- データ基盤（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルの存在に応じた営業日判定ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。DB 登録値優先、未登録日は曜日ベースでフォールバック。
    - カレンダーデータが空の場合のフォールバック動作や NULL 値検出時のログ出力を実装。
    - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得し save_market_calendar を呼び出す、バックフィル・健全性チェックをサポート）。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult dataclass を実装し、ETL の集計結果（取得数、保存数、品質問題、エラー等）を表現。
    - pipeline モジュールの主要ユーティリティ（テーブル存在チェック、最大日付取得、カレンダー調整）を実装。
    - etl パッケージから ETLResult を再エクスポート（src/kabusys/data/etl.py）。
    - 設計方針として差分更新、バックフィル、品質チェックの収集（Fail-Fast ではなく問題収集）を明記。

- リサーチ（src/kabusys/research）
  - factor_research（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20日 ATR / 相対 ATR）、流動性（20日平均売買代金・出来高比）、バリュー（PER、ROE）を計算する関数を実装。
    - DuckDB を用いた SQL ベースの計算実装。データ不足時の None ハンドリング、結果は dict のリストで返す。
    - 公開関数: calc_momentum, calc_volatility, calc_value。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（可変ホライズン、入力バリデーション）、IC（Spearman ρ）計算 calc_ic、ランク化 util rank、ファクター統計 summary（factor_summary）を実装。
    - Pandas 等外部依存を使わず標準ライブラリと DuckDB のみで実装。

- 共通・ユーティリティ
  - DuckDB 互換性や空リスト渡し制約に配慮した executemany の扱い、SQL 文字列組立て時の安全性コメント等を実装。
  - ロギングによる詳細な情報出力・警告メッセージを多数追加しデバッグを容易に。

### Design / Implementation Notes
- ルックアヘッドバイアス対策:
  - 各モジュール（score_news, score_regime, 各ファクター計算）は datetime.today() や date.today() を内部で参照せず、必ず外部から target_date を受け取る設計。
  - データ取得・集計は target_date 未満／以前のデータに限定して使用することで将来情報の混入を防止。
- フェイルセーフ戦略:
  - 外部 API（OpenAI / J-Quants）呼び出し失敗時は部分スコア 0.0 またはスキップで継続する設計（例外は通常上位へは伝播しない。ただし DB 書き込み失敗時はロールバックして例外を伝播）。
- 冪等性:
  - DB への更新処理は可能な限り冪等に（DELETE→INSERT、ON CONFLICT など）実装し、部分失敗時に既存データを不必要に消さない工夫を採用。
- テスト性:
  - OpenAI 呼び出しを _call_openai_api のパッチで差し替えできるようにしてユニットテストを容易にしている。

### Fixed
- なし（初期リリース）

### Changed
- なし（初期リリース）

### Removed
- なし（初期リリース）

### Security
- 環境変数の取り扱い: .env の自動ロードはプロジェクトルート検出に依存、OS 環境変数を保護する設計。機密情報は環境変数（または .env.local）を通じて設定する想定。

---

今後のリリースに向けての注記（推奨）
- OpenAI API や J-Quants クライアントの差分実装に合わせたインタフェースの抽象化（モック可能なクライアント注入）を進めるとテスト性がさらに向上します。
- ai モジュールのレスポンススキーマ変更に対する堅牢性（正規表現等で JSON 部分抽出）や、API 利用料最適化のためのキャッシュ機構導入を検討してください。
- DuckDB バージョン依存（executemany の挙動等）については CI に複数バージョンを追加して互換性テストを行うことを推奨します。

（以上）